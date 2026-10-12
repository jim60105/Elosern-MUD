# Spec Delta

## MODIFIED Requirements

### Requirement: Multi-stage Containerfile
The project SHALL provide a Podman-focused multi-stage `Containerfile` with a downloader stage that verifies the init binary, a builder stage, an application-layout stage that prepares the runtime tree and permissions, and a final stage that carries only the resulting virtual environment, init binary, application code, and the build-acquired default background-removal model. Model acquisition SHALL occur after locked dependency installation and before application-source copying, so application-only rebuilds can reuse the model layer.

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
  binary, prepared application tree, or default-model artifact
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

#### Scenario: Application-only rebuilds reuse model acquisition
- **WHEN** application code changes without a change to the locked dependencies or the
  model acquisition instruction
- **THEN** the build can reuse the layer containing the already-acquired default weight
  without fetching it again

## REMOVED Requirements

### Requirement: compose.yaml for local and networked GPU services

**Reason**: The former composite contract requires a writable rembg volume and forbids baking the weight. The replacement preserves every unrelated Compose behavior and replaces only rembg delivery and comparisons to it.

**Migration**: Update the six old requirement annotations in `tests/test_container_contract.py` to `container-image::compose-persists-mutable-state-and-exposes-image-data`. Remove the rembg-only mount and declaration; existing volumes remain untouched and unused. No runtime migration or compatibility alias is introduced.

## ADDED Requirements

### Requirement: Compose persists mutable state and exposes image data
The project SHALL provide a `compose.yaml` that runs the Evennia service with the ports and volumes design doc §9 specifies, persisting the SQLite database, logs, generated static files, uploaded media, scene art, and translation model cache. The background-removal weight SHALL come from the image; Compose SHALL NOT mount a volume over `/app/server/.rembg` or declare `evennia-rembg`, and the image SHALL NOT declare a rembg `VOLUME`.

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
- **THEN** the SQLite database, scene art store, logs, generated
  static files, and media contents from the previous volume contents are still present, because they are
  backed by volumes rather than the container's writable layer

#### Scenario: The default removal weight is visible from the image
- **WHEN** Compose and the final image are inspected
- **THEN** the service has no mount over `/app/server/.rembg`, the image declares no
  volume for that path, and the default weight is present there in an image layer

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

#### Scenario: An old named volume cannot hide the baked artifact
- **WHEN** the revised standard Compose deployment runs on a host where an existing
  `evennia-rembg` volume is empty or contains only a former model
- **THEN** that volume is unused and unchanged, the service reads the image's default
  artifact, and no model download, startup copy, or migration is needed

#### Scenario: An air-gapped deployment transfers the complete image
- **WHEN** an operator deploys an image built on a connected machine to an air-gapped
  runtime host and disables runtime rembg downloads
- **THEN** the image's baked default weight is sufficient for enabled cutouts without
  rembg volume pre-seeding or runtime acquisition

#### Scenario: The model cache lives in neither the art store nor $HOME
- **WHEN** the model cache location is considered
- **THEN** it SHALL NOT live under `/app/server/.art`, whose contents are governed by the art store's confinement, media route, and orphan-prune rules, and SHALL NOT use the library default under `$HOME`, which the image maps to the `tmpfs`-mounted `/tmp` and would therefore re-download on every container start

#### Scenario: The translation model cache is a declared writable volume
- **WHEN** `compose.yaml` and the image are inspected
- **THEN** the translation model cache is a writable named volume mounted at `/app/server/.translate`, matching the code-only `ART_TRANSLATE_MODEL_DIR` setting; the image declares that path as a persistent volume with a `root:0` group-writable directory and SHALL NOT bake any translation model artifact into a layer

#### Scenario: The translation volume fills at run time or is pre-seeded
- **WHEN** the translation volume is used
- **THEN** it is filled at run time only by the backend's own first-use fetch when `ART_TRANSLATE_DOWNLOAD_ENABLED=true` (the default), and reused across container recreations; an operator MAY pre-seed the volume with `scripts/fetch-translate-model.sh` and set `ART_TRANSLATE_DOWNLOAD_ENABLED=false` for an air-gapped deployment, in which case the fetch is structurally impossible

#### Scenario: An empty translation volume is a bounded error, never a crash
- **WHEN** the translation volume is empty on either track
- **THEN** the result is a bounded `art_translate_unavailable`, never a crash, and the image itself carries no translation model on either track

#### Scenario: Bootstrap keeps the admin password out of service configuration
- **WHEN** `compose.yaml` is inspected
- **THEN** it provides a profile-gated, interactive one-shot bootstrap service for initializing a fresh database without storing the initial administrator's password in the long-lived service configuration

#### Scenario: Background-removal availability survives recreation through the image
- **WHEN** the service is recreated with the same revised image and standard Compose file
- **THEN** the same default-model artifact remains available from the image and no
  writable rembg cache is initialized or required

### Requirement: The default background-removal model is acquired during image build

The Containerfile SHALL acquire the locked rembg default `bria-rmbg` weight during image
construction with its upstream checksum verification enabled and SHALL ship the nonempty
artifact at `/app/server/.rembg/models/bria-rmbg/bria-rmbg.onnx`. Acquisition failure SHALL
fail the build. The artifact SHALL be readable without modification by the default
non-root user and arbitrary numeric UID with GID 0. Build acquisition SHALL be independent
of runtime rembg switches.

#### Scenario: Successful image construction includes the default artifact
- **WHEN** a clean image build completes
- **THEN** the final image contains the default artifact with the locked upstream checksum
  and no isnet or u2net weight, and no model output exists solely in a build cache mount
- **AND** build-only caches and downloader scaffolding are absent from the runtime image

#### Scenario: Acquisition failure cannot publish an incomplete image
- **WHEN** model acquisition encounters a download failure, checksum mismatch, or absent
  or empty output artifact
- **THEN** the image build exits unsuccessfully rather than producing an image that
  defers obtaining its required model to first use

#### Scenario: Runtime switches cannot omit the required image payload
- **WHEN** an image is built while the operator's runtime configuration disables cutouts
  or disables runtime model downloads
- **THEN** the build still acquires and ships the default weight

#### Scenario: Offline inference reads the weight as the default non-root user
- **WHEN** the built image performs its first real cutout as its default user without
  runtime network access and with a read-only root filesystem
- **THEN** CPU-only inference reads the baked artifact and returns an alpha-carrying PNG
  without writing, copying, or downloading a model

#### Scenario: Offline inference reads the weight as an arbitrary UID
- **WHEN** the same image cutout smoke runs with UID `1000630000` and GID `0`, no runtime
  network access, and a read-only root filesystem
- **THEN** the result has the same model-readability and no-acquisition behavior as the
  default-user run, without permission errors

#### Scenario: Image size and licence obligations are disclosed
- **WHEN** the operator documentation describes image construction and delivery
- **THEN** it states the approximately 1.02 GB uncompressed model payload and the BRIA
  weight's applicable use and redistribution licence obligations
- **AND** it distinguishes transferring a built image for offline use from a cold image
  build, which requires access to the model source
