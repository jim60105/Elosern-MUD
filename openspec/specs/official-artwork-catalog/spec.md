# official-artwork-catalog Specification

## Purpose
Define the read-only external official-artwork directory: the `ART_OFFICIAL_ROOT` setting, the closed `monster/preset/npc` content-kind layout with root-relative stable asset identities, the startup snapshot catalog with admission validation and bounded diagnostics, the optional per-content manifest, and the per-file content fingerprint used as the media cache token.

## Requirements

### Requirement: Official artwork lives outside git behind one directory-root setting
`server/conf/settings.py` SHALL declare `ART_OFFICIAL_ROOT`, defaulting to the `art-official` directory under `GAME_DIR` and overridable through an environment variable of the same name. The repository SHALL gitignore the default directory, and the variable SHALL be carried in the exact `.env.example` inventory and the settings-and-environment guide. `ART_OFFICIAL_ROOT` SHALL be distinct from `ART_STORE_ROOT` and `ART_SEED_ROOT`, and the game process SHALL treat it as read-only.

#### Scenario: The environment override is honored
- **WHEN** settings import runs with `ART_OFFICIAL_ROOT` set in the environment to an operator directory
- **THEN** the effective `ART_OFFICIAL_ROOT` is that directory and ordinary startup reads it

#### Scenario: The default directory is not tracked
- **WHEN** the repository is inspected for tracked paths
- **THEN** `art-official/` is gitignored and no official artwork blob is tracked, while the six committed built-in defaults remain tracked

#### Scenario: The game never writes the official root
- **WHEN** the production modules are inspected for filesystem writes
- **THEN** no module resolves a write path under `ART_OFFICIAL_ROOT`

#### Scenario: The setting follows the directory-root precedent
- **WHEN** `ART_OFFICIAL_ROOT` is declared
- **THEN** it follows the `ART_SEED_ROOT`/`PROMPT_ROOT` directory-root precedent rather than the typed `ART_SD_*` knob table

#### Scenario: Read-only means no create, rename, replace, or delete
- **WHEN** any game code path touches `ART_OFFICIAL_ROOT`
- **THEN** it never creates, renames, replaces, or deletes any file under it

### Requirement: A missing or empty official root is a valid no-art configuration
A missing, empty, or unreadable `ART_OFFICIAL_ROOT` directory SHALL be a supported startup configuration. Catalog load SHALL complete with an empty index, SHALL emit one bounded info diagnostic naming the empty/absent condition, and startup SHALL proceed with the existing runtime-art and built-in fallback behavior unchanged. Startup SHALL NOT download, extract, sync, or otherwise acquire artwork, and SHALL NOT require Git, S3, or archive availability.

#### Scenario: Startup with no artwork directory
- **WHEN** the server starts with `ART_OFFICIAL_ROOT` naming a directory that does not exist
- **THEN** startup completes, the catalog is empty, one bounded `official_art_catalog_loaded` diagnostic reports the empty root, and no network or extraction call occurs

#### Scenario: Ordinary gameplay never acquires artwork
- **WHEN** a player resolves any portrait while the catalog holds zero entries
- **THEN** resolution uses only the loaded snapshot and the existing chain, with no filesystem acquisition attempt

### Requirement: The catalog indexes the mounted layout once at startup and serves from that snapshot
`world/art/official.py` SHALL index the official root once at startup and ordinary resolution SHALL read from that in-memory snapshot only. The index SHALL cover the layout `monster/<species-key>/<image-file>`, `preset/<preset-key>/<image-file>`, `npc/<npc-or-profile-key>/<image-file>`, where the content kind is exactly one of `monster`, `preset`, `npc`. An image's root-relative path SHALL be its stable official asset identity.

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

#### Scenario: Directory keys name authored content only
- **WHEN** an indexed directory key is resolved
- **THEN** it identifies registered authored content — never a runtime database row or a translated display name

#### Scenario: Artwork updates restart-only with no external acquisition
- **WHEN** artwork in the official root is updated
- **THEN** it takes effect only through a restart: no file watcher, hot activation, or refresh path exists, and the catalog never calls Git, S3, an archive extractor, or an external host

#### Scenario: Indexing is owned by the art service's startup steps
- **WHEN** the official root is indexed
- **THEN** it is owned by the art service alongside the other startup synchronization steps

### Requirement: Admission admits only valid images confined to the configured root
Catalog admission SHALL accept only regular, non-symlinked image files that (a) match the existing closed image-format extension vocabulary, (b) decode successfully under the existing bounded image limits, and (c) resolve strictly inside `ART_OFFICIAL_ROOT`. Every other entry SHALL be refused with bounded diagnostics. Each refusal SHALL be per-entry: the catalog SHALL never reject the whole root.

#### Scenario: An out-of-root symlink is refused
- **WHEN** a content directory contains a symlink whose target resolves outside `ART_OFFICIAL_ROOT`
- **THEN** admission refuses that entry with one bounded diagnostic, no identity is indexed for it, and the rest of the content directory indexes normally

#### Scenario: An undecodable or oversized image is refused
- **WHEN** a content directory holds a corrupt image and an image exceeding the bounded pixel/dimension limits
- **THEN** both are refused with bounded diagnostics while the directory's remaining valid images index

#### Scenario: A refused entry never blocks unrelated artwork
- **WHEN** the root holds one invalid file among many valid preset, npc, and monster content directories
- **THEN** every valid content directory's images are indexed and resolvable

#### Scenario: Identities are never inferred or remapped
- **WHEN** admission encounters a display name or an unknown content key
- **THEN** it never infers a species or content identity from a display name, and never maps an unknown content key to any other key such as a threat tier

#### Scenario: Each named refusal class is refused with a bounded diagnostic
- **WHEN** an entry is a symlinked or out-of-root path, an unsupported format, an unreadable or undecodable file, or an image exceeding the bounded limits
- **THEN** it is refused entry with a bounded diagnostic

### Requirement: The optional per-content manifest follows the seed-metadata convention
A content directory MAY carry a `manifest.json` declaring a `default` filename, a `face_rect`, and a `stage` placement, following the existing seed-metadata convention. When no valid explicit default is declared, the content's default image SHALL be the first valid image in deterministic filename order. An invalid or unreadable manifest SHALL emit one bounded diagnostic and behave as if absent, and SHALL NOT prevent that directory's valid images from loading.

#### Scenario: No manifest uses deterministic filename order
- **WHEN** a preset content directory holds three valid images and no manifest
- **THEN** its default image is the first filename in deterministic order

#### Scenario: An invalid manifest degrades without blocking images
- **WHEN** a content directory's manifest names a nonexistent `default` filename and carries a malformed face rectangle
- **THEN** one bounded diagnostic is emitted, the fitted default rectangle and identity stage are used, and the directory's valid images still index and resolve

#### Scenario: A face rectangle invalid for one image is ignored for rendering
- **WHEN** a manifest declares a rectangle that fails validation against one of the images it would apply to
- **THEN** that rectangle is ignored and the fitted default rectangle is reported for that image, with a bounded diagnostic

#### Scenario: Absent-manifest behaviour uses fitted defaults
- **WHEN** a manifest is absent or treated as absent
- **THEN** the fitted per-image default face rectangle and identity stage placement are used

#### Scenario: Image dimensions are decoded locally, never declared
- **WHEN** a manifest is authored for a content directory
- **THEN** image dimensions are decoded locally and are not required in the manifest

#### Scenario: No package-level metadata is required or honored
- **WHEN** artwork is admitted under the manifest convention
- **THEN** no mandatory top-level manifest, package ID, release number, declared checksum, or schema matrix is required or honored

#### Scenario: A missing manifest is normal
- **WHEN** a content directory carries no manifest
- **THEN** that is normal and emits no diagnostic

### Requirement: Each indexed image carries a startup-computed content fingerprint
At catalog load the catalog SHALL compute one fingerprint of the file's content for every admitted image, exactly once per startup — never per resolution or per request. The fingerprint SHALL be the cache token in official media URLs so replacing the bytes at the same root-relative path invalidates browser caches after a maintenance restart. The fingerprint SHALL NOT be read from or written to any metadata file and SHALL NOT be a package version.

#### Scenario: Replacement changes the fingerprint after restart
- **WHEN** an operator replaces the bytes at an indexed path and the server restarts
- **THEN** the path's catalog fingerprint differs from the previous startup's, and the URL carrying the old fingerprint returns 404 while the new fingerprint serves the new bytes

#### Scenario: Fingerprint computation is load-time only
- **WHEN** one image is resolved a hundred times during ordinary play
- **THEN** the file's bytes are hashed zero additional times after catalog load

#### Scenario: A stale fingerprint is a 404
- **WHEN** a request names a fingerprint that is not the current catalog value
- **THEN** it returns 404, since no historical fingerprint is retained or served

### Requirement: Catalog load and refusals are observable through the facade
Catalog load SHALL record one `official_art_catalog_loaded` boundary event through the `world.observability` named-import facade at info level, carrying counts of indexed content directories, indexed images, and refused entries, and SHALL report the empty/absent-root condition through the same event. Every per-entry admission or manifest refusal SHALL emit a bounded diagnostic event carrying the content kind, content key (where known), and the offending relative path.

#### Scenario: One boundary event per startup
- **WHEN** the server starts with a populated official root containing two invalid entries
- **THEN** exactly one `official_art_catalog_loaded` info event reports indexed and refused counts, and the two refusals carry bounded per-entry events within the diagnostic budget

#### Scenario: Catalog load writes no game state
- **WHEN** catalog load completes against a populated root
- **THEN** no asset record, queue record, gallery record, or stored file was created or modified

#### Scenario: Diagnostics never leak prose, credentials, or roots
- **WHEN** a bounded diagnostic event is emitted
- **THEN** it carries no player-facing prose, credentials, or absolute filesystem roots

#### Scenario: Image reads and indexing create no jobs or state
- **WHEN** images are read and the catalog indexes them
- **THEN** no art jobs or persistent game state are created

#### Scenario: Leaf diagnostics are budget-capped
- **WHEN** many leaf diagnostics accumulate in one load
- **THEN** a budget caps them per load with the suppressed count reported in the boundary event,
  following the seed-sync discipline
