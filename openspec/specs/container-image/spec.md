## Purpose

Define the Podman container image and Compose deployment for the Evennia service.

## Requirements

### Requirement: Multi-stage Containerfile
The project SHALL provide a Podman-focused multi-stage `Containerfile`: a downloader stage that
verifies the init binary, a builder stage that installs the dependencies locked by `uv.lock` using
`uv sync --locked` and architecture-scoped Buildah cache mounts, an application-layout stage that
prepares the runtime tree and permissions, and a final stage that carries only the resulting
virtual environment, init binary, and application code. Full `COPY --link` layer reuse SHALL
target Podman 5.6 or later with Buildah 1.41 or later.

#### Scenario: Builder artifacts do not reach the runtime image
- **WHEN** the image is built with `podman build` from the `Containerfile`
- **THEN** the final image contains no compiler toolchain, no uv download cache, and no build-only
  dependency that is not required to run `evennia start`

#### Scenario: Repeated builds reuse the dependency layer
- **WHEN** the image is rebuilt after only application code changed (neither `pyproject.toml` nor
  `uv.lock` changed)
- **THEN** the dependency-install step is reused from the Buildah layer cache, and its
  architecture-scoped uv cache mount remains available if the step must execute again

#### Scenario: Stale dependency metadata fails the image build
- **WHEN** `pyproject.toml` and `uv.lock` disagree during an image build
- **THEN** `uv sync --locked` fails instead of resolving or changing dependencies implicitly

#### Scenario: Final artifacts use independent linked layers
- **WHEN** a final-stage base or metadata instruction changes without changing the venv, init
  binary, or prepared application tree
- **THEN** Buildah can reuse the unchanged `COPY --link` layers independently of earlier
  final-stage filesystem layers

#### Scenario: Build metadata invalidates only metadata layers
- **WHEN** `VERSION` or `RELEASE` changes while runtime artifacts remain unchanged
- **THEN** the resulting OCI labels contain the new values, all preceding runtime layers remain
  cache-eligible, and only the metadata cache barrier and label are rebuilt

### Requirement: Non-root, arbitrary-UID-capable runtime
The container SHALL run as a non-root user by default, and SHALL also start successfully when run
with an arbitrary numeric UID and GID 0 (the OpenShift restricted SCC pattern), writing no files
outside directories that are group-0 writable. Application code and the virtual environment SHALL
remain read-only at runtime.

#### Scenario: Default run is non-root
- **WHEN** the container is started with no `--user` override
- **THEN** the main process runs as a non-root UID and can write to its log, database, and art-store
  paths

#### Scenario: Arbitrary UID with GID 0
- **WHEN** the container is started with `--user 1000630000:0` (an arbitrary UID not present in
  `/etc/passwd`, GID 0)
- **THEN** Evennia starts successfully and writes logs, without permission errors, because the
  relevant directories are owned by `root:0` with group-writable permissions

### Requirement: compose.yaml for local and networked GPU services
The project SHALL provide a `compose.yaml` that runs the Evennia service with the ports and
volumes design doc §9 specifies. It SHALL persist the SQLite database, logs, generated static
files, uploaded media, scene art, and the background-removal model cache. It SHALL bake the
repo's `prompts/` directory into the image
at `/app/prompts` and mount the host prompt folder read-only into the container at `/app/prompts`
via `${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z`, so an admin can edit prompt files on the host and
apply them by restarting or reloading the server without rebuilding the image. The `,z` option
relabels the bind mount with the SELinux container context so the read-only mount stays readable
under enforcing SELinux (for example on Fedora or RHEL hosts) without weakening its read-only
semantics. It SHALL additionally mount the host bulk seed-art folder read-only into the container at
`/app/art-seed` via `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z}`, following the same
read-only, SELinux-relabelled pattern as the prompt mount, so an operator supplies large prebuilt
character art without adding it to the image or to version control. Unlike `prompts/`, the seed
folder SHALL NOT be baked into the image: an absent mount is a supported configuration in which the
engine simply synchronizes nothing.

It SHALL additionally mount the host official-artwork directory read-only into the container at
`/app/art-official` via `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z`, following the
same read-only, SELinux-relabelled pattern, and the `evennia` service environment SHALL forward
`ART_OFFICIAL_ROOT=/app/art-official` so the game reads exactly that mount. The official directory
SHALL NOT be baked into the image, an absent host directory SHALL remain a supported no-art
configuration that starts normally, and the bind mount SHALL remain read-only: the game process
SHALL never write through it. The named-volume alternative is equally supported: a dedicated
`evennia-art-official` volume mounted read-only at the same container path, with the operator
configuring `ART_OFFICIAL_ROOT` to the volume's prepared content subdirectory (never the mount
point itself). The runtime image SHALL carry no Git client, S3 client, or archive-extraction
workflow of its own: every preparation method is host/deployment tooling.

The background-removal model cache SHALL be a writable named volume mounted at
`/app/server/.rembg`, matching the code-only `ART_REMBG_MODEL_DIR` setting. The image SHALL
prepare that directory `root:0` and group-writable in the application-layout stage and declare it
alongside the other persistent paths, exactly like `/app/server/.art`, so an arbitrary-UID run can
write it. The ~1 GB model artifact SHALL NOT be baked into the image: it is fetched on first use
into the volume and reused across container recreations, and an operator MAY pre-seed the volume
and set `ART_REMBG_DOWNLOAD_ENABLED=false` for an air-gapped deployment. The model cache
SHALL NOT live under `/app/server/.art`, whose contents are governed by the art store's
confinement, media route, and orphan-prune rules, and SHALL NOT use the library default
under `$HOME`, which the image maps to the `tmpfs`-mounted `/tmp` and would therefore
re-download on every container start.

The translation model cache SHALL be a writable named volume mounted at
`/app/server/.translate`, matching the code-only `ART_TRANSLATE_MODEL_DIR` setting. The image
SHALL declare that path as a persistent volume with a `root:0` group-writable directory and
SHALL NOT bake any model artifact into a layer. Like the background-removal cache, this volume
is filled at run time only by the backend's own first-use fetch when
`ART_TRANSLATE_DOWNLOAD_ENABLED=true` (the default), and reused across container recreations;
an operator MAY pre-seed the volume with `scripts/fetch-translate-model.sh` and set
`ART_TRANSLATE_DOWNLOAD_ENABLED=false` for an air-gapped deployment, in which case the fetch is
structurally impossible. An empty volume on either track is a bounded
`art_translate_unavailable`, never a crash, and the image itself carries no model on either
track.

It SHALL also
provide a profile-gated, interactive one-shot bootstrap service for initializing a fresh database
without storing the initial administrator's password in the long-lived service configuration.

#### Scenario: Fresh database is bootstrapped interactively
- **WHEN** an operator runs `podman compose --profile bootstrap run --rm bootstrap` against a fresh
  database volume
- **THEN** the one-shot service migrates the database, interactively creates Account #1, and exits
  without placing the supplied password in the image, Compose environment, or normal service
  container metadata

#### Scenario: Normal service starts after bootstrap
- **WHEN** the bootstrap service has created Account #1 and the operator runs `podman compose up`
- **THEN** the normal service applies pending migrations and starts the Portal and Server without
  requiring bootstrap credentials

#### Scenario: Ports match the design
- **WHEN** the `evennia` service starts via `compose up`
- **THEN** ports 4000 (telnet), 4001 (webserver), and 4002 (websocket) are published and reachable
  from the host

#### Scenario: Persistent state survives container recreation
- **WHEN** the `evennia` service container is removed and recreated (`compose up --force-recreate`)
- **THEN** the SQLite database, scene art store, background-removal model cache, logs, generated
  static files, and media contents from the previous volume contents are still present, because they are
  backed by volumes rather than the container's writable layer

#### Scenario: The model cache is a volume, never an image layer
- **WHEN** `compose.yaml` and the built image are inspected
- **THEN** the `evennia` service mounts a named volume at `/app/server/.rembg`, the image declares
  that path as a persistent volume with a `root:0` group-writable directory, and the image itself
  contains no `.onnx` model artifact

#### Scenario: Prompt files are mounted read-only from the host
- **WHEN** `compose.yaml` is inspected and the container is started
- **THEN** the `evennia` service mounts `${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z`, the server
  reads prompts from that mount, and the image also contains the same default files at
  `/app/prompts` for standalone runs

#### Scenario: GPU services are configured, not containerized
- **WHEN** `compose.yaml` is inspected
- **THEN** it defines no Ollama or sd-webui service, and the `evennia` service instead reads their
  base URLs from environment variables that default to Podman's `host.containers.internal`
  hostname for host-local GPU services

#### Scenario: Seed art is mounted read-only and never baked into the image
- **WHEN** `compose.yaml` and the built image are inspected
- **THEN** the `evennia` service mounts `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z}`, and the image itself contains no seed-art directory

#### Scenario: A deployment with no seed folder still starts
- **WHEN** the service is started with no host seed folder present
- **THEN** the server starts normally, synchronizes no seed art, and reports the skip once

#### Scenario: Official artwork is mounted read-only and never baked into the image
- **WHEN** `compose.yaml` and the built image are inspected
- **THEN** the `evennia` service mounts `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z}` with `ART_OFFICIAL_ROOT=/app/art-official` forwarded, and the image itself contains no official-artwork directory

#### Scenario: A deployment with no official directory still starts
- **WHEN** the service is started with neither a host official directory nor a prepared volume
- **THEN** the server starts normally with an empty official catalog and built-in silhouettes, and no startup step attempts any acquisition

#### Scenario: The translation model cache is an operator-seeded volume, never an image layer
- **WHEN** the built image and the compose configuration are inspected
- **THEN** the `evennia` service mounts a named volume at `/app/server/.translate`, the image
  declares that path as a persistent volume with a `root:0` group-writable directory, the image
  itself contains no translation model artifact, and no service definition performs a model
  fetch at start (the only fetch is the backend's lazy first-use download inside the running
  server when `ART_TRANSLATE_DOWNLOAD_ENABLED=true`)

### Requirement: Container ignore file excludes non-build-context files
The project SHALL provide a `.containerignore` that excludes version control metadata, local virtual
environments, caches, and any gitignored development-only paths (such as `tmp/`) from the build
context.

#### Scenario: Build context stays small
- **WHEN** the image is built from the repository root
- **THEN** the build context sent to the builder does not include `.git/`, any local virtualenv
  directory, `__pycache__/`, `.env`, or `tmp/`

### Requirement: One-shot official-artwork archive preparation service
The project SHALL provide a profile-gated, non-interactive one-shot `artwork-prepare` service for
named-volume deployments. It SHALL run only when explicitly invoked during deployment, with write
access to the official-artwork volume and — when supplied — one operator-provided archive mounted
read-only as its input; game startup SHALL never invoke it and the game process SHALL never extract
anything. Given an archive it SHALL extract with native tooling into a fresh empty temporary
directory, refuse unsafe path entries (parent-directory traversal, absolute paths, link entries)
and finite resource limits (entry count, total expanded size, per-file size), and only on complete
success replace the volume's prepared content subdirectory (never the mount point itself) so a
failed or interrupted preparation leaves the previously prepared tree byte-for-byte unchanged. Given
no supplied archive it SHALL be a no-op that neither erases nor re-extracts the volume. The service
SHALL treat its archive input as trusted operator supply — never a player upload or an
arbitrary game-selected remote source — and the accompanying documentation SHALL present plain
copy/sync, separate Git repository/submodule checkout, and S3 CLI synchronization as equivalent
operator procedures over the same mounted-directory interface, including the stop/replace/start
maintenance window.

#### Scenario: Successful preparation populates the volume
- **WHEN** an operator invokes the preparation service with a valid archive
- **THEN** the volume's content subdirectory holds the extracted tree, the game (re)started with `ART_OFFICIAL_ROOT` pointing at it resolves that artwork, and no game-side process performed the extraction

#### Scenario: Failed extraction leaves the prepared tree unchanged
- **WHEN** the preparation service runs against an archive that fails extraction (corrupt stream, refused unsafe entry, or exceeded limit)
- **THEN** the service exits non-zero and the volume's previously prepared tree is byte-for-byte unchanged — no partial output replaced it

#### Scenario: Reuse without an archive erases nothing
- **WHEN** the preparation service is invoked with no archive input against an already-populated volume
- **THEN** it is a no-op, the prepared tree is unchanged, and ordinary startup neither invokes it nor re-extracts an old archive

#### Scenario: Startup needs no Git or S3
- **WHEN** the `evennia` service starts on a host with no Git remote reachable and no S3 credentials
- **THEN** startup completes using the mounted directory as-is, and the runtime image contains no fetch/sync/extract workflow

### Requirement: Official artwork is excluded from publication inputs while built-in defaults ship
The build context and every public container layer SHALL exclude the official-artwork directory: the
project SHALL list `art-official/` (and any configured official-root override path) in
`.containerignore` alongside the existing gitignored development-only paths, and no build stage SHALL
copy official artwork into an image layer, a frontend bundle, a Storybook export, a documentation
screenshot set, or a public CI artifact. The six committed built-in fallback originals under
`web/static/art/defaults/` SHALL remain in the code repository and in the served static assets: the
exclusion SHALL NOT remove them.

#### Scenario: The image carries no official artwork
- **WHEN** the image is built from a repository root whose `art-official/` directory is populated
- **THEN** the build context excludes `art-official/`, the resulting image contains no official artwork file, and the six built-in default images are still present and servable
