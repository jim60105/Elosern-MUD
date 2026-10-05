# official-artwork-catalog Specification

## Purpose
Define the read-only external official-artwork directory: the `ART_OFFICIAL_ROOT` setting, the closed `monster/preset/npc` content-kind layout with root-relative stable asset identities, the startup snapshot catalog with admission validation and bounded diagnostics, the optional per-content manifest, and the per-file content fingerprint used as the media cache token.

## Requirements

### Requirement: Official artwork lives outside git behind one directory-root setting
`server/conf/settings.py` SHALL declare `ART_OFFICIAL_ROOT`, defaulting to the `art-official` directory under `GAME_DIR` and overridable through an environment variable of the same name, following the `ART_SEED_ROOT`/`PROMPT_ROOT` directory-root precedent rather than the typed `ART_SD_*` knob table. The repository SHALL gitignore the default directory, and the variable SHALL be carried in the exact `.env.example` inventory and the settings-and-environment guide. `ART_OFFICIAL_ROOT` SHALL be distinct from `ART_STORE_ROOT` and `ART_SEED_ROOT`, and the game process SHALL treat it as read-only: no game code path SHALL create, rename, replace, or delete any file under it.

#### Scenario: The environment override is honored
- **WHEN** settings import runs with `ART_OFFICIAL_ROOT` set in the environment to an operator directory
- **THEN** the effective `ART_OFFICIAL_ROOT` is that directory and ordinary startup reads it

#### Scenario: The default directory is not tracked
- **WHEN** the repository is inspected for tracked paths
- **THEN** `art-official/` is gitignored and no official artwork blob is tracked, while the six committed built-in defaults remain tracked

#### Scenario: The game never writes the official root
- **WHEN** the production modules are inspected for filesystem writes
- **THEN** no module resolves a write path under `ART_OFFICIAL_ROOT`

### Requirement: A missing or empty official root is a valid no-art configuration
A missing, empty, or unreadable `ART_OFFICIAL_ROOT` directory SHALL be a supported startup configuration. Catalog load SHALL complete with an empty index, SHALL emit one bounded info diagnostic naming the empty/absent condition, and startup SHALL proceed with the existing runtime-art and built-in fallback behavior unchanged. Startup SHALL NOT download, extract, sync, or otherwise acquire artwork, and SHALL NOT require Git, S3, or archive availability.

#### Scenario: Startup with no artwork directory
- **WHEN** the server starts with `ART_OFFICIAL_ROOT` naming a directory that does not exist
- **THEN** startup completes, the catalog is empty, one bounded `official_art_catalog_loaded` diagnostic reports the empty root, and no network or extraction call occurs

#### Scenario: Ordinary gameplay never acquires artwork
- **WHEN** a player resolves any portrait while the catalog holds zero entries
- **THEN** resolution uses only the loaded snapshot and the existing chain, with no filesystem acquisition attempt

### Requirement: The catalog indexes the mounted layout once at startup and serves from that snapshot
`world/art/official.py` SHALL index the official root at startup — owned by the art service alongside the other startup synchronization steps — and ordinary resolution SHALL read from that in-memory snapshot only. The index SHALL cover the layout `monster/<species-key>/<image-file>`, `preset/<preset-key>/<image-file>`, `npc/<npc-or-profile-key>/<image-file>`, where the content kind is exactly one of `monster`, `preset`, `npc` and the directory key identifies registered authored content — never a runtime database row or a translated display name. An image's root-relative path SHALL be its stable official asset identity. Updating artwork SHALL take effect only through a restart: no file watcher, hot activation, or refresh path SHALL exist, and the catalog SHALL never call Git, S3, an archive extractor, or an external host.

#### Scenario: The snapshot is built at startup and reused
- **WHEN** the server starts with a populated official root and ten portraits resolve during ordinary play
- **THEN** the filesystem index was walked once at startup and all ten resolutions answered from the snapshot without re-walking the root

#### Scenario: Replacement takes effect after restart only
- **WHEN** an operator replaces a file inside the live root and gameplay continues before any restart
- **THEN** the catalog continues to serve the previously indexed identity and fingerprint, and the replacement appears only after the next startup

#### Scenario: Unsupported content directories are ignored with a diagnostic
- **WHEN** the root contains a top-level directory whose name is not `monster`, `preset`, or `npc`
- **THEN** it is skipped with one bounded diagnostic and valid known-kind directories still index

#### Scenario: Unknown registry references are skipped, not fatal
- **WHEN** the root holds a content directory keyed to a name that no registry declares
- **THEN** that directory is skipped with a bounded diagnostic and unrelated valid artwork indexes normally

### Requirement: Admission admits only valid images confined to the configured root
Catalog admission SHALL accept only regular, non-symlinked image files that (a) match the existing closed image-format extension vocabulary, (b) decode successfully under the existing bounded image limits, and (c) resolve strictly inside `ART_OFFICIAL_ROOT`. Symlinked or out-of-root paths, unsupported formats, unreadable or undecodable files, and images exceeding the bounded limits SHALL be refused entry with bounded diagnostics. Each refusal SHALL be per-entry: the catalog SHALL never reject the whole root, and a refused entry SHALL NOT block valid unrelated artwork from indexing. Admission SHALL NOT infer a species or content identity from a display name, and SHALL NOT map an unknown content key to any other key such as a threat tier.

#### Scenario: An out-of-root symlink is refused
- **WHEN** a content directory contains a symlink whose target resolves outside `ART_OFFICIAL_ROOT`
- **THEN** admission refuses that entry with one bounded diagnostic, no identity is indexed for it, and the rest of the content directory indexes normally

#### Scenario: An undecodable or oversized image is refused
- **WHEN** a content directory holds a corrupt image and an image exceeding the bounded pixel/dimension limits
- **THEN** both are refused with bounded diagnostics while the directory's remaining valid images index

#### Scenario: A refused entry never blocks unrelated artwork
- **WHEN** the root holds one invalid file among many valid preset, npc, and monster content directories
- **THEN** every valid content directory's images are indexed and resolvable

### Requirement: The optional per-content manifest follows the seed-metadata convention
A content directory MAY carry a `manifest.json` declaring a `default` filename, a `face_rect`, and a `stage` placement, following the existing seed-metadata convention. When no valid explicit default is declared, the content's default image SHALL be the first valid image in deterministic filename order. A missing manifest SHALL be normal and emit no diagnostic. An invalid or unreadable manifest SHALL emit one bounded diagnostic and behave as if absent — the fitted per-image default face rectangle and identity stage placement — and SHALL NOT prevent that directory's valid images from loading. If a declared `face_rect` is invalid for any image it applies to, that rectangle SHALL be ignored in favor of the fitted per-image default; image dimensions SHALL be decoded locally and SHALL NOT be required in the manifest. No mandatory top-level manifest, package ID, release number, declared checksum, or schema matrix SHALL be required or honored.

#### Scenario: No manifest uses deterministic filename order
- **WHEN** a preset content directory holds three valid images and no manifest
- **THEN** its default image is the first filename in deterministic order

#### Scenario: An invalid manifest degrades without blocking images
- **WHEN** a content directory's manifest names a nonexistent `default` filename and carries a malformed face rectangle
- **THEN** one bounded diagnostic is emitted, the fitted default rectangle and identity stage are used, and the directory's valid images still index and resolve

#### Scenario: A face rectangle invalid for one image is ignored for rendering
- **WHEN** a manifest declares a rectangle that fails validation against one of the images it would apply to
- **THEN** that rectangle is ignored and the fitted default rectangle is reported for that image, with a bounded diagnostic

### Requirement: Each indexed image carries a startup-computed content fingerprint
At catalog load the catalog SHALL compute one fingerprint of the file's content for every admitted image, exactly once per startup — never per resolution or per request. The fingerprint SHALL be the cache token in official media URLs so replacing the bytes at the same root-relative path invalidates browser caches after a maintenance restart. The fingerprint SHALL NOT be read from or written to any metadata file, SHALL NOT be a package version, and no historical fingerprint SHALL be retained or served: a request naming a fingerprint that is not the current catalog value SHALL return 404.

#### Scenario: Replacement changes the fingerprint after restart
- **WHEN** an operator replaces the bytes at an indexed path and the server restarts
- **THEN** the path's catalog fingerprint differs from the previous startup's, and the URL carrying the old fingerprint returns 404 while the new fingerprint serves the new bytes

#### Scenario: Fingerprint computation is load-time only
- **WHEN** one image is resolved a hundred times during ordinary play
- **THEN** the file's bytes are hashed zero additional times after catalog load

### Requirement: Catalog load and refusals are observable through the facade
Catalog load SHALL record one `official_art_catalog_loaded` boundary event through the `world.observability` named-import facade at info level, carrying counts of indexed content directories, indexed images, and refused entries, and SHALL report the empty/absent-root condition through the same event. Every per-entry admission or manifest refusal SHALL emit a bounded diagnostic event carrying the content kind, content key (where known), and the offending relative path — never player-facing prose, credentials, or absolute filesystem roots. A budget SHALL cap leaf diagnostics per load with the suppressed count reported in the boundary event, following the seed-sync discipline. Image reads and catalog indexing SHALL NOT create art jobs or persistent game state.

#### Scenario: One boundary event per startup
- **WHEN** the server starts with a populated official root containing two invalid entries
- **THEN** exactly one `official_art_catalog_loaded` info event reports indexed and refused counts, and the two refusals carry bounded per-entry events within the diagnostic budget

#### Scenario: Catalog load writes no game state
- **WHEN** catalog load completes against a populated root
- **THEN** no asset record, queue record, gallery record, or stored file was created or modified
