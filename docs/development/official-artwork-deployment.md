# Official artwork deployment

Official artwork (monsters, player presets, authored NPCs, and optional
scene/room overrides) is distributed outside the code repository, under its own
license, and is read by the server from one external directory. This guide is
the operator/deployment surface for that directory: how to prepare it, how to
mount it, and how to update it. The required built-in scene collection is the
one documented exception and is committed in the repository.

The game only ever **reads** this directory. Startup never downloads, syncs, or
extracts anything, so a host with no Git remote, no S3 credentials, and no
archive tooling still starts normally: an absent or empty directory is a
supported "no official artwork" configuration, and the built-in silhouettes and
runtime art behave exactly as if no official artwork existed.

Related documentation: [Settings and environment](/development/settings-and-environment)
(the `ART_OFFICIAL_ROOT` setting), [Prompts](/gm/prompts) and
[Operations](/gm/operations) (the other bind-mounted operator inputs).

## Bundled scene artwork is a tracked exception

The repository also commits the required built-in scene illustrations — the
closed eleven-path set under `web/static/art/scenes/`, delivered by the
artwork packs — because a scene's own background must render with no operator
mount and no generation service. Those files are tracked in git deliberately,
are bounded in size, and each carries a `<key>.provenance.json` sidecar
recording its source, distribution terms, production method and content
checksum.

This exception never moves operator artwork into git: everything under
`ART_OFFICIAL_ROOT` stays external, untracked and read-only, and the runtime
art store and seed roots stay outside the repository exactly as before.

The registry that resolves the bundled scene keys lives in
`world/art/scene_definitions.py`: every registered scene archetype plus the
explicit dream scene (`dream_throne`) declares a required illustration and a
terminal scene key (`city_street` or `forest_path`). Startup admits the
committed files once per boot and serves them through the application's own
media boundary as `bundled-scene/<scene-key>/<sha256>.webp` identities
(`/art/bundled-scene/<scene-key>/<sha256>.webp` URLs), from the FIXED in-repo
`web/static/art/scenes/` root — never from `ART_OFFICIAL_ROOT`, and with no new
setting. The key is the closed declaration registry and the fingerprint is the
content digest of the committed bytes, so an operator file cannot replace a
bundled identity or a terminal scene image, a bundled request can never be
answered from an operator root, and a missing file is a real 404 rather than a
substitute image. The plain static path `/static/art/scenes/<scene-key>.webp`
serves the identical committed bytes from the collected static root; it is the
historical asset location, not an authoritative identity, and it carries no
fingerprint — resolve scene artwork through `/art/bundled-scene/...`.

Delivered so far, each produced through the repository's own sd-webui client
and prompt library, encoded by `world.art.formats.encode`, and reviewed at
native scale and under the desktop cover crop:

- the outdoor pack — `wilderness_path`, `mountain_path`, `coastal_path`;
- the interior pack — `tavern_interior`, `dungeon_interior`, `ruin_interior`;
- the sacred pack — `cave_interior`, `shrine_interior`, `dream_throne`;
- the terminal pack — `forest_path`, `city_street`.

Every file is original, redistributable work by the project maintainers (no
third-party stock or externally licensed imagery) and its
`<key>.provenance.json` sidecar records the source, distribution terms,
production method, WebP processing, SHA-256 of the shipped bytes and the
visual review. The complete collection is a contract: a missing declaration, a
terminal that names an unregistered scene key, and a missing, unreadable,
oversized, undecodable or non-full-bleed required image each fail the named
contract (`world.art.tests.test_bundled_scenes`) naming the affected scene key,
while a deployment that loses one of these validated files still starts: the
request for the lost file is a 404 and everything else keeps serving.

The dream scene and the collaborative dream stage are two different assets:
`dream_throne` is the bundled scene background above, while the stage's
illustration is the optional operator `npc` asset
`<root>/npc/dream_goddess/dream-throne.webp` documented below. Neither replaces
the other.

## Room identities and authored metadata

An operator `room/<room-art-key>/` directory only reaches a room the map layer
has tagged. The map owner (`world/maps/room_art.py`) is the single writer of
each supported room's scene facts, applied idempotently at startup and at
construction: the registered **scene archetype** the room renders from, the
optional registered **room_art_key**, and a bounded logical **scene identity**.
No key is inferred from a room name, a runtime row id, a threat tier or a
neighbouring room.

- **Authored grid rooms** (`world/maps/altoria_capital.py`,
  `world/maps/village_ciaran.py`) are keyed by their authored `(map, x, y)`
  coordinate; they declare no room-art key, and their identity is that
  coordinate.
- **Permanent interiors** (the rooms `sync_service_interiors` builds from
  `world.lore.settlements.places`) are plain `Room`s that now carry scene
  metadata: their place key is their registered room-art key, their scene
  archetype is declared per place in `room_art.py`, and their identity is the
  authored place key.
- **Pooled wilderness** rooms derive their archetype from the explicit
  region→scene mapping (`forest_path` for forest regions, `mountain_path` for
  the central mountains, `coastal_path` for the coasts, `wilderness_path` for
  plains and hills); a preparation re-sets every fact and clears the previous
  place's room-art key, so a pooled object never leaks an old key or identity
  into another coordinate.
- **Declared instances** carry an explicitly authored registered
  `room_art_key` and scene archetype into supported construction; an
  undeclared dynamic instance has none and falls back to its archetype chain.
  The art resolver only reads these facts and never writes or repairs them.

Declaring a new authored place or grid node without its room-art metadata fails
closed at import; the authored tables are validated against the registered
scene-archetype and room-art vocabularies, so a bad edit names the offending
key instead of silently degrading a room to no scene art.

## The directory contract

One directory root, `ART_OFFICIAL_ROOT`, holds the current artwork only:

```text
<root>/
  LICENSE                                  # optional license notice (never served)
  monster/<species-key>/<image-file>       # e.g. monster/alpha_wolf/portrait.webp
  preset/<preset-key>/<image-file>         # e.g. preset/example_preset/portrait.png
  npc/<npc-or-profile-key>/<image-file>    # e.g. npc/example_contact/portrait.webp
  scene/<scene-key>/<image-file>           # optional per-scene override
  room/<room-art-key>/<image-file>         # optional per-authored-room override
```

- `<kind>` is exactly `monster`, `preset`, `npc`, `scene`, or `room`. Any other
  top-level directory is skipped (one bounded diagnostic), and the four image
  extensions `.png`, `.webp`, `.jpg`, and `.avif` are the closed accepted set.
- `scene/<scene-key>/` and `room/<room-art-key>/` name registered authored
  content, never a database row id or a translated display name. The scene keys
  are the eleven declared in `world/art/scene_definitions.py`; the room-art keys
  are the authored room vocabulary of the same module. A directory keyed to a
  name no registry declares is skipped with one bounded diagnostic while
  unrelated artwork still indexes.
- Operator scene/room artwork overrides the archetype chain of a room that
  references it; the required bundled scene illustration above always remains
  available for the built-in collection.
- The collaborative dream stage's illustration is an official `npc` asset
  addressed by its **exact** identity
  `<root>/npc/dream_goddess/dream-throne.webp`, so that exact filename is what
  must be present (the game resolves that path, not the directory's default or
  manifest choice). It is optional: without it the dream stage renders its
  prose on the flat background instead of an illustration.
  The dream scene fills the viewport below the navigation header, covering
  the underlying game's bottom controls rather than reserving the drawer
  workspace's bottom inset.
- A content directory MAY carry a `manifest.json` with an optional `default`
  filename, a `face_rect`, and a `stage` placement. Without a valid explicit
  default, the first image in deterministic filename order is used; a missing
  manifest is normal and a broken one degrades to the fitted defaults without
  blocking the directory's other images. The startup snapshot keeps those
  outcomes as bounded, attributable facts. A declared `default` that is missing
  or was refused at admission is reported against that declared name and
  **before** the deterministic substitute (`explicit_reference_missing`, or
  `source_rejected` when a file of that name was present but inadmissible); a
  declared default that was admitted keeps no fault. Rejected or inapplicable
  manifest metadata is reported as `metadata_invalid` beside the fitted
  geometry the image actually renders with — the valid image bytes are still
  served. Only a source's own default/metadata facts are attributed to it: a
  refused unselected sibling stays a bounded admission diagnostic and never
  makes a healthy image look broken.
- Admission is per entry: symlinked, out-of-root, non-regular, unsupported,
  unreadable, undecodable, and oversized files are refused with bounded
  diagnostics while unrelated artwork still loads. Keep the tree to ordinary
  files and directories.

### What the gallery shows an operator about these facts

The gallery's official rows (schema version 3) present each admitted image as
the exact catalog identity inside the canonical artwork descriptor, so the
retained startup facts above reach the player-facing read model instead of
staying in the boot log:

- each row carries that ONE exact image as its rank-10 official candidate — the
  fingerprinted `/art/official/<sha256>/<identity>` route, the admitted decoded
  size and the catalog's validated metadata-or-fitted rectangle, with no stage;
- the directory's **declared-default fault precedes the deterministic
  substitute it caused** (`source_id` naming the refused declared identity), and
  an image's own `metadata_invalid` fact sits at that candidate's own source and
  rank. Adding either fault changes no source priority, and neither ever taints
  a healthy sibling;
- the selected subject's own committed silhouette rides as the row's terminal
  alpha mask, so a preview still has a subject-appropriate fallback if the
  official bytes fail to load in the browser;
- an identity whose fingerprinted URL would exceed the shared media ceiling
  (256 code points) is still omitted with the single bounded
  `gallery_official_entry_skipped` diagnostic rather than failing the panel.

Nothing in this path writes: the mounted directory stays read-only and no
preference, card or file is touched by rendering the panel.

### What the portrait resolver shows about the same facts

One art-owned enumerator in `world/art/presenter.py` decides which portrait a
subject presents, and it is the single place the portrait source policy lives:
the equipment-bound card, the player's explicit personal official selection,
the record's default card, the classic generated asset, the reference's
official default and the subject's committed silhouette, in that precedence.
The mounted directory contributes only the official positions of that order:

- the entity's official content reference is ONE source position
  (`portrait.official:<kind>/<key>`), so the admitted default image and every
  fault retained against that source share one identity and one rank;
- an entity whose stored provenance declares no reference adds **no** official
  attempt and no fault — a never-mounted directory is the ordinary
  no-artwork configuration, exactly as it is for the gallery;
- root-level availability (`official_art_catalog_loaded`'s `root_state` and
  `root_fault`) stays a deployment fact of the whole catalog rather than a
  per-subject fault: an explicitly configured but unreadable root is reported
  once at startup, and no subject's attempts carry a directory-wide taint;
- a personal selection or a named default card that can no longer resolve
  keeps its bounded fault at its own position, before the substitute that
  follows it, and the stored preference is never deleted;
- the recorded generation truth (pending, failed, done or missing) is a fact
  of the subject's own records, so an admitted official image can present
  while a recorded generation stays failed, and a deliberate no-generation
  configuration claims nothing.

`world.art.presenter.describe_entity` is now the ONE production enumerator
behind every portrait surface: the art panel's v3 catalog value is exactly
`{artwork, context}`, the roster v3 row's `portrait` IS the descriptor, and
the party/exploration `portrait_ref` names that same descriptor's catalog key.
Catalog **admission** and real-image **eligibility** are different facts:
membership is `world.rules.art_view`'s bounded decision (the currently present
focusable entities in exploration, the participant set in combat), while an
entry's own attempts state whether any real image resolves. An admitted entity
with no eligible portrait subject still carries its complete refusal
descriptor — no image attempt, no generated subject key, no prompt — plus the
deterministic attribute-selected alpha terminal, so no surface ever has to
guess imagery from a missing field and no reference is withheld merely because
real artwork has not resolved. A personal selection or a named default card
that can no longer resolve keeps its bounded fault at its own position, before
the substitute that follows it, and the stored preference is never deleted.

- Place the license notice for the artwork itself as a top-level `LICENSE`
  (or alongside the artwork in your own distribution); the server ignores
  non-directory root entries and never serves or logs the file. Official
  artwork is distributed under its own terms — the code repository's license
  says nothing about it.
- The root inside a container is `/app/art-official` (bind mount) or the
  prepared content subdirectory of the `evennia-art-official` volume (see
  below). On bare metal, `ART_OFFICIAL_ROOT` defaults to `art-official/` under
  the game directory.

## Preparing the directory

Every procedure below produces the same mounted directory. Pick one; do not
implement acquisition inside the game, and do not add downloader, sync, or
extractor logic to the runtime image.

### 1. Plain directory, bind mount (default)

Copy or synchronize the files with any ordinary transfer method and point
compose at the directory:

```sh
mkdir -p art-official                     # or any host path
rsync -a --delete artwork-source/ art-official/
```

```sh
# .env (or the shell environment)
ART_OFFICIAL_DIR=./art-official           # relative to the compose project
```

`compose.yaml` mounts `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z`
read-only (the `z` option relabels the mount for SELinux-enforcing hosts) and
forwards `ART_OFFICIAL_ROOT=/app/art-official`, so the game reads exactly that
mount. Minimal infrastructure, easy inspection and backup. The host directory is
gitignored and excluded from the container build context.

### 2. Separate Git repository or submodule

Host the artwork in its own repository, check it out on the host, and mount the
worktree:

```sh
git submodule add https://example.test/artwork.git art-official
git -C art-official checkout <tag-or-commit>
```

The code repository records only the submodule reference, never artwork blobs;
history, storage, and access control stay with the artwork repository. Do not
add Git LFS without a demonstrated need, and do not let the game run `git`.

### 3. S3 or S3-compatible storage

Synchronize with the provider CLI on the host before starting the game:

```sh
aws s3 sync s3://example-artwork/current/ art-official/ --delete
```

Credentials and network access belong to the deployment, never to gameplay.
The same command works against the volume's prepared content directory when a
helper container mounts the volume with write access.

### 4. Local archive with the one-shot preparation service

For named-volume deployments, `compose.yaml` ships a profile-gated one-shot
service that extracts a trusted operator archive into a dedicated
`evennia-art-official` volume:

```sh
# 1. Put the archive where the service can read it (read-only mount).
cp official-art-2026-10.tar.gz art-official-archives/

# 2. Extract it into the volume's content subdirectory.
ART_OFFICIAL_ARCHIVE=official-art-2026-10.tar.gz \
  podman compose --profile artwork-prepare run --rm artwork-prepare
```

- `ART_OFFICIAL_ARCHIVE` names the archive. A bare name is resolved inside
  `/app/art-official-archives` (the host directory
  `${ART_OFFICIAL_ARCHIVES_DIR:-./art-official-archives}` mounted read-only); an
  absolute path inside the container also works. **Without
  `ART_OFFICIAL_ARCHIVE` the run is a no-op** — the prepared tree is neither
  erased nor re-extracted, so a reused volume is never disturbed.
- Supported inputs are uncompressed tar and gzip-compressed tar (`.tar`,
  `.tar.gz`, `.tgz`): the runtime image carries `tar` and `gzip` only. Convert
  or unpack any other format on the host, then use procedure 1 or 3.
- The archive is **trusted operator supply** — never a player upload, and never
  an archive the game selects from a remote source.
- The service is never started by `podman compose up` (it is behind the
  `artwork-prepare` profile), is non-interactive, runs without a network, and
  can write only the volume and its tmpfs.

Safety contract, so a bad archive can never leave a half-replaced directory:

- every archive member is listed and validated **before anything is written**:
  absolute paths, `..` traversal, symlinks, hard links, and device/fifo/socket
  members are refused, and finite caps apply to the member count, the declared
  size of one member, and the total declared size (defaults 50000 members,
  64 MiB, 8 GiB; override with `ART_OFFICIAL_MAX_ENTRIES`,
  `ART_OFFICIAL_MAX_FILE_BYTES`, `ART_OFFICIAL_MAX_TOTAL_BYTES`);
- extraction runs into a fresh empty staging directory inside the volume, never
  over the prepared tree, and the finished tree is installed by renames;
- a refused, corrupt, or interrupted run exits non-zero and leaves the
  previously prepared tree byte-for-byte unchanged. If a run is killed between
  the install renames, the next invocation restores the last prepared tree
  before installing the new one.

The service uses `scripts/prepare-official-artwork.sh` from the repository,
mounted read-only; it is not baked into the image, and the game process never
runs it.

## Named-volume deployments

The bind mount is the default. To keep the artwork in the `evennia-art-official`
volume instead, edit `compose.yaml` (there is no way to remove a bind mount with
an override file):

```yaml
  evennia:
    environment:
      # was: ART_OFFICIAL_ROOT: /app/art-official
      ART_OFFICIAL_ROOT: /app/art-official/content
    volumes:
      # replace: - ${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z
      - evennia-art-official:/app/art-official:ro
```

Two rules make this safe:

- the game mounts the volume **read-only** at `/app/art-official`;
- `ART_OFFICIAL_ROOT` points at the volume's **prepared content
  subdirectory** (`/app/art-official/content`), never at the mount point
  itself. Preparation replaces that subdirectory by renaming a finished tree
  into place; the mount point itself is never replaced, and any files you keep
  in the volume root (backups, licenses) survive every preparation.

Prepare or update the volume with procedure 4 above.

## Updating artwork: the maintenance window

Every procedure is a stop / prepare / replace / start window; artwork changes
are infrequent and restart-only by design.

```sh
podman compose down                       # 1. stop the game
#  2. prepare the replacement: sync the directory, or run the
#     artwork-prepare service for the volume
podman compose up -d                      # 3. start the game again
```

- **Restart-only refresh.** The catalog is indexed once at startup: no file
  watcher, no hot activation, and no refresh path exists, so edits to a live
  directory have no effect until the next start. Media URLs carry a fingerprint
  of the file bytes computed at startup, so after a replacement the URLs of the
  old bytes return 404 (clients then re-resolve from the refreshed state).
- **No partial replacement.** Never extract or synchronize over the live
  prepared tree: build the complete replacement first, then swap it in (the
  preparation service does exactly that). A failed transfer must leave the
  current tree untouched — retaining a backup and restoring it manually is the
  intended recovery; there is no release registry and no automatic rollback.
- Startup never acquires artwork: after an operator error the server simply
  serves the artwork it finds, or the built-in silhouettes when it finds none.
- Run one preparation at a time: the service replaces the prepared tree as a
  unit, and two concurrent runs would race over each other's staging directory.

## Verifying a deployment

```sh
# The mount and interpolation the service will use.
podman compose config

# The catalog reports what the server actually indexed at startup, once per
# boot, including the empty/absent-root condition.
podman compose logs --since 5m | grep official_art_catalog_loaded

# The committed bundled scene collection is admitted by the same startup step
# under its own event, on every boot — with or without an operator mount.
podman compose logs --since 5m | grep bundled_scene_catalog_loaded
```

A container that is merely "up" is not proof that artwork is being served: a
missing, empty, unreadable or unusable root starts normally, and the game then
uses the built-in silhouettes. The boundary event carries the root's retained
health, so the cases are distinguishable instead of guesses:

- `reason=official_root_absent root_state=absent_default root_fault=False` —
  the optional root was never configured (or `ART_OFFICIAL_ROOT` is empty).
  This is the supported no-art configuration; there is nothing to fix.
- `reason=official_root_empty root_state=empty root_fault=False` — a mounted
  root that holds no admissible content: the volume is mounted but still empty.
- `root_state=unavailable root_fault=True` — a real failure. Either the root was
  **explicitly configured** (the environment bound `ART_OFFICIAL_ROOT`) and is
  missing, or it cannot be read, or it is a symlink, or it is an existing
  non-directory entry. The same boot logs one further bounded
  `reason=source_unavailable` diagnostic on the same event, and neither line
  names the absolute root. A failed operator root never hides the committed
  bundled collection and never becomes a substitute image: every identity the
  catalog did not admit answers 404.

After preparing artwork, require the same event to report the indexed content
directories and images with `reason=official_root_indexed` (for example
`contents=1 images=7 refused=0`), and treat any refusal count as a to-do
naming the offending root-relative paths the diagnostics carry.

The bundled event is independent of the operator root: require
`reason=bundled_root_indexed definitions=11 images=11 refused=0` on every
deployment, including one with no `ART_OFFICIAL_ROOT` mounted. A lower `images`
count means the checkout is incomplete (`refused` names the affected scene
keys), and the missing identities answer 404 rather than a substitute image.

For the collaborative dream stage specifically, the indexed image count must
include `npc/dream_goddess/dream-throne.webp`: run one `sleep dream` and check
that the dream panel's `scene_art` state field is a non-empty
`/art/official/...` URL (an empty value means the artwork was not indexed,
which the stage survives by design).

### Troubleshooting

| Symptom | Cause and remedy |
| --- | --- |
| `archive is not a regular file` | `ART_OFFICIAL_ARCHIVE` names a missing file inside `/app/art-official-archives`. Check `ART_OFFICIAL_ARCHIVES_DIR` and the file name. |
| `archive is not a readable tar archive` | The input is not an uncompressed or gzip tar archive (a zip or xz/bzip2 archive). Unpack or repack it on the host. |
| `permission denied` while creating the content directory | The named volume must be writable by the preparation service's user (UID 1001 of the image). Podman creates a fresh named volume owned by that user; if your engine creates it root-owned, either `chown` the volume to UID 1001 or run one preparation as root (`podman compose --profile artwork-prepare run --rm --user 0 artwork-prepare`) and then **repair ownership**, because root-owned content is unreadable to the game (UID 1001), which would start and silently serve silhouettes: `podman unshare chown -R 1001:1001 "$(podman volume inspect <project>_evennia-art-official --format '{{.Mountpoint}}')"`. |
| Artwork replaced but the game serves the old bytes | The catalog refreshes only at startup, and old fingerprint URLs intentionally 404. Restart the service. |
| `official_art_catalog_loaded` reports refusals | Per-entry admission refused unsupported, symlinked, out-of-root, or oversized files; the event and its bounded diagnostics name the offending root-relative paths and the unrelated artwork still loads. |
| `official_art_catalog_loaded` reports `root_state=unavailable` (with `root_fault=True` and a `reason=source_unavailable` line) | The configured root cannot be used: missing while explicitly bound, unreadable, a symlink, or an existing non-directory entry. Fix the mount or the `ART_OFFICIAL_ROOT` path; a bare `root_state=absent_default root_fault=False` line is the normal unconfigured case and needs no action. |
| A manifest's declared `default` is not the image the game resolves | The declared filename is missing or was refused at admission. The directory's bounded `manifest_default_not_an_admitted_file` diagnostic names the cause, and the first filename in deterministic order is served instead (a declared default that was admitted is always the one used). |
| `bundled_scene_catalog_loaded` reports fewer than eleven images | The checkout is missing or has a corrupt `web/static/art/scenes/<scene-key>.webp`; the diagnostics name the affected scene keys. The served identity for a lost file is a real 404 — never another image. |
| A `scene/<key>/` or `room/<key>/` directory was ignored | The directory key is not registered authored content (the declared scene keys and the authored room-art vocabulary of `world/art/scene_definitions.py`), or the directory entry was refused; the bounded diagnostic names it. |
