# Official artwork deployment

Official artwork (monsters, player presets, and authored NPCs) is distributed
outside the code repository, under its own license, and is read by the server
from one external directory. This guide is the operator/deployment surface for
that directory: how to prepare it, how to mount it, and how to update it.

The game only ever **reads** this directory. Startup never downloads, syncs, or
extracts anything, so a host with no Git remote, no S3 credentials, and no
archive tooling still starts normally: an absent or empty directory is a
supported "no official artwork" configuration, and the built-in silhouettes and
runtime art behave exactly as if no official artwork existed.

Related documentation: [Settings and environment](/development/settings-and-environment)
(the `ART_OFFICIAL_ROOT` setting), [Prompts](/gm/prompts) and
[Operations](/gm/operations) (the other bind-mounted operator inputs).

## The directory contract

One directory root, `ART_OFFICIAL_ROOT`, holds the current artwork only:

```text
<root>/
  LICENSE                                  # optional license notice (never served)
  monster/<species-key>/<image-file>       # e.g. monster/alpha_wolf/portrait.webp
  preset/<preset-key>/<image-file>         # e.g. preset/example_preset/portrait.png
  npc/<npc-or-profile-key>/<image-file>    # e.g. npc/example_contact/portrait.webp
```

- `<kind>` is exactly `monster`, `preset`, or `npc`. Any other top-level
  directory is skipped (one bounded diagnostic), and the four image extensions
  `.png`, `.webp`, `.jpg`, and `.avif` are the closed accepted set.
- A content directory MAY carry a `manifest.json` with an optional `default`
  filename, a `face_rect`, and a `stage` placement. Without a valid explicit
  default, the first image in deterministic filename order is used; a missing
  manifest is normal and a broken one degrades to the fitted defaults without
  blocking the directory's other images.
- Admission is per entry: symlinked, out-of-root, non-regular, unsupported,
  unreadable, undecodable, and oversized files are refused with bounded
  diagnostics while unrelated artwork still loads. Keep the tree to ordinary
  files and directories.
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

## Verifying a deployment

```sh
# The mount and interpolation the service will use.
podman compose config

# A no-art start is valid: the server starts, the catalog is empty, and one
# `official_art_catalog_loaded` info event reports the empty/absent root.
podman compose logs --since 5m | grep official_art_catalog_loaded
```

After preparing artwork, expect the same event to report indexed content
directories and images instead of the empty condition, and refused entries for
anything the admission rules rejected.

### Troubleshooting

| Symptom | Cause and remedy |
| --- | --- |
| `archive is not a regular file` | `ART_OFFICIAL_ARCHIVE` names a missing file inside `/app/art-official-archives`. Check `ART_OFFICIAL_ARCHIVES_DIR` and the file name. |
| `archive is not a readable tar archive` | The input is not an uncompressed or gzip tar archive (a zip or xz/bzip2 archive). Unpack or repack it on the host. |
| `permission denied` while creating the content directory | The named volume must be writable by the preparation service's user (UID 1001 of the image). Podman creates a fresh named volume owned by that user; if your engine creates it root-owned, `chown` the volume or run the preparation as root for one invocation (`podman compose --profile artwork-prepare run --rm --user 0 artwork-prepare`). |
| Artwork replaced but the game serves the old bytes | The catalog refreshes only at startup, and old fingerprint URLs intentionally 404. Restart the service. |
| `official_art_catalog_loaded` reports refusals | Per-entry admission refused unsupported, symlinked, out-of-root, or oversized files; the event and its bounded diagnostics name the offending root-relative paths and the unrelated artwork still loads. |
