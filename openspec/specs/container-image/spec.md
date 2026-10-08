## Purpose

Define the Podman container image and Compose deployment for the Evennia service.

## Requirements

### Requirement: Multi-stage Containerfile
The project SHALL provide a Podman-focused multi-stage `Containerfile` with a downloader stage that verifies the init binary, a builder stage, an application-layout stage that prepares the runtime tree and permissions, and a final stage that carries only the resulting virtual environment, init binary, and application code.

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

#### Scenario: The builder stage installs locked dependencies with cached mounts
- **WHEN** the builder stage runs
- **THEN** it installs the dependencies locked by `uv.lock` using `uv sync --locked` and architecture-scoped Buildah cache mounts

#### Scenario: Linked-layer reuse targets supported tooling versions
- **WHEN** full `COPY --link` layer reuse is evaluated
- **THEN** it SHALL target Podman 5.6 or later with Buildah 1.41 or later

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
The project SHALL provide a `compose.yaml` that runs the Evennia service with the ports and volumes design doc §9 specifies, persisting the SQLite database, logs, generated static files, uploaded media, scene art, and the background-removal model cache.

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

#### Scenario: Prompts are baked into the image and mounted read-only from the host
- **WHEN** `compose.yaml` is inspected
- **THEN** the image bakes the repo's `prompts/` directory at `/app/prompts` and the host prompt folder is mounted read-only at `/app/prompts` via `${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z`, so an admin can edit prompt files on the host and apply them by restarting or reloading the server without rebuilding the image

#### Scenario: The ,z option keeps read-only mounts readable under enforcing SELinux
- **WHEN** a `,z` bind mount is used on an enforcing SELinux host (for example Fedora or RHEL)
- **THEN** the option relabels the bind mount with the SELinux container context so the read-only mount stays readable under enforcing SELinux without weakening its read-only semantics

#### Scenario: Seed art mounts read-only and is never baked in
- **WHEN** `compose.yaml` is inspected
- **THEN** the host bulk seed-art folder is mounted read-only at `/app/art-seed` via `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z}`, following the same read-only, SELinux-relabelled pattern as the prompt mount, so an operator supplies large prebuilt character art without adding it to the image or to version control; unlike `prompts/`, the seed folder SHALL NOT be baked into the image, and an absent mount is a supported configuration in which the engine simply synchronizes nothing

#### Scenario: Official artwork mounts read-only with its root forwarded
- **WHEN** `compose.yaml` is inspected
- **THEN** the host official-artwork directory is mounted read-only at `/app/art-official` via `${ART_OFFICIAL_DIR:-./art-official}:/app/art-official:ro,z}`, following the same read-only, SELinux-relabelled pattern, and the `evennia` service environment forwards `ART_OFFICIAL_ROOT=/app/art-official` so the game reads exactly that mount

#### Scenario: An absent official directory is a supported no-art configuration
- **WHEN** the host official directory is absent
- **THEN** it remains a supported no-art configuration that starts normally, and the bind mount remains read-only: the game process SHALL never write through it

#### Scenario: The named-volume alternative is equally supported
- **WHEN** a named volume is used for official artwork
- **THEN** a dedicated `evennia-art-official` volume is mounted read-only at the same container path, with the operator configuring `ART_OFFICIAL_ROOT` to the volume's prepared content subdirectory (never the mount point itself)

#### Scenario: The runtime image carries no acquisition tooling
- **WHEN** the runtime image is inspected
- **THEN** it carries no Git client, S3 client, or archive-extraction workflow of its own: every preparation method is host/deployment tooling

#### Scenario: The background-removal model cache is a prepared writable volume
- **WHEN** `compose.yaml` and the image are inspected
- **THEN** the background-removal model cache is a writable named volume mounted at `/app/server/.rembg`, matching the code-only `ART_REMBG_MODEL_DIR` setting; the image prepares that directory `root:0` and group-writable in the application-layout stage and declares it alongside the other persistent paths, exactly like `/app/server/.art`, so an arbitrary-UID run can write it

#### Scenario: The ~1 GB background-removal model is fetched, never baked
- **WHEN** the background-removal model artifact is considered
- **THEN** the ~1 GB model artifact SHALL NOT be baked into the image: it is fetched on first use into the volume and reused across container recreations, and an operator MAY pre-seed the volume and set `ART_REMBG_DOWNLOAD_ENABLED=false` for an air-gapped deployment

#### Scenario: The model cache lives in neither the art store nor $HOME
- **WHEN** the model cache location is considered
- **THEN** it SHALL NOT live under `/app/server/.art`, whose contents are governed by the art store's confinement, media route, and orphan-prune rules, and SHALL NOT use the library default under `$HOME`, which the image maps to the `tmpfs`-mounted `/tmp` and would therefore re-download on every container start

#### Scenario: The translation model cache is a declared writable volume
- **WHEN** `compose.yaml` and the image are inspected
- **THEN** the translation model cache is a writable named volume mounted at `/app/server/.translate`, matching the code-only `ART_TRANSLATE_MODEL_DIR` setting; the image declares that path as a persistent volume with a `root:0` group-writable directory and SHALL NOT bake any model artifact into a layer

#### Scenario: The translation volume fills at run time or is pre-seeded
- **WHEN** the translation volume is used
- **THEN** like the background-removal cache, it is filled at run time only by the backend's own first-use fetch when `ART_TRANSLATE_DOWNLOAD_ENABLED=true` (the default), and reused across container recreations; an operator MAY pre-seed the volume with `scripts/fetch-translate-model.sh` and set `ART_TRANSLATE_DOWNLOAD_ENABLED=false` for an air-gapped deployment, in which case the fetch is structurally impossible

#### Scenario: An empty translation volume is a bounded error, never a crash
- **WHEN** the translation volume is empty on either track
- **THEN** the result is a bounded `art_translate_unavailable`, never a crash, and the image itself carries no model on either track

#### Scenario: Bootstrap keeps the admin password out of service configuration
- **WHEN** `compose.yaml` is inspected
- **THEN** it provides a profile-gated, interactive one-shot bootstrap service for initializing a fresh database without storing the initial administrator's password in the long-lived service configuration

### Requirement: Container ignore file excludes non-build-context files
The project SHALL provide a `.containerignore` that excludes version control metadata, local virtual
environments, caches, and any gitignored development-only paths (such as `tmp/`) from the build
context.

#### Scenario: Build context stays small
- **WHEN** the image is built from the repository root
- **THEN** the build context sent to the builder does not include `.git/`, any local virtualenv
  directory, `__pycache__/`, `.env`, or `tmp/`

### Requirement: One-shot official-artwork archive preparation service
The project SHALL provide a profile-gated, non-interactive one-shot `artwork-prepare` service for named-volume deployments. It SHALL run only when explicitly invoked during deployment, with write access to the official-artwork volume and — when supplied — one operator-provided archive mounted read-only as its input; game startup SHALL never invoke it and the game process SHALL never extract anything.

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

#### Scenario: Extraction is safe, bounded, and atomic
- **WHEN** the preparation service is given an archive
- **THEN** it extracts with native tooling into a fresh empty temporary directory, refuses unsafe path entries (parent-directory traversal, absolute paths, link entries) and finite resource limits (entry count, total expanded size, per-file size), and only on complete success replaces the volume's prepared content subdirectory (never the mount point itself) so a failed or interrupted preparation leaves the previously prepared tree byte-for-byte unchanged

#### Scenario: The archive input is trusted operator supply only
- **WHEN** the service's input provenance is inspected
- **THEN** it SHALL treat its archive input as trusted operator supply — never a player upload or an arbitrary game-selected remote source

#### Scenario: The documentation presents equivalent operator procedures
- **WHEN** the accompanying documentation is inspected
- **THEN** it presents plain copy/sync, separate Git repository/submodule checkout, and S3 CLI synchronization as equivalent operator procedures over the same mounted-directory interface, including the stop/replace/start maintenance window

### Requirement: Official artwork is excluded from publication inputs while built-in defaults ship
The build context and every public container layer SHALL exclude the official-artwork directory: the project SHALL list `art-official/` (and any configured official-root override path) in `.containerignore` alongside the existing gitignored development-only paths.

#### Scenario: The image carries no official artwork
- **WHEN** the image is built from a repository root whose `art-official/` directory is populated
- **THEN** the build context excludes `art-official/`, the resulting image contains no official artwork file, and the six built-in default images are still present and servable

#### Scenario: No publication input receives copied official artwork
- **WHEN** any build stage publishes outputs
- **THEN** it SHALL NOT copy official artwork into an image layer, a frontend bundle, a Storybook export, a documentation screenshot set, or a public CI artifact

#### Scenario: The built-in fallback originals are preserved
- **WHEN** the exclusion is applied
- **THEN** the six committed built-in fallback originals under `web/static/art/defaults/` SHALL remain in the code repository and in the served static assets: the exclusion SHALL NOT remove them
