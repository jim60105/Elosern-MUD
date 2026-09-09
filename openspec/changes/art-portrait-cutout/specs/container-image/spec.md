## MODIFIED Requirements

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
`/app/art-seed` via `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z`, following the same
read-only, SELinux-relabelled pattern as the prompt mount, so an operator supplies large prebuilt
character art without adding it to the image or to version control. Unlike `prompts/`, the seed
folder SHALL NOT be baked into the image: an absent mount is a supported configuration in which the
engine simply synchronizes nothing.

The background-removal model cache SHALL be a writable named volume mounted at
`/app/server/.rembg`, matching the code-only `ART_REMBG_MODEL_DIR` setting. The image SHALL
prepare that directory `root:0` and group-writable in the application-layout stage and declare it
alongside the other persistent paths, exactly like `/app/server/.art`, so an arbitrary-UID run can
write it. The ~1 GB model artifact SHALL NOT be baked into the image: it is fetched on first use
into the volume and reused across container recreations, and an operator MAY pre-seed the volume
and set `ART_REMBG_DOWNLOAD_ENABLED=false` for an air-gapped deployment. The model cache SHALL NOT
live under `/app/server/.art`, whose contents are governed by the art store's confinement, media
route, and orphan-prune rules, and SHALL NOT use the library default under `$HOME`, which the image
maps to the `tmpfs`-mounted `/tmp` and would therefore re-download on every container start.

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
  static files, and media contents from the previous run are still present, because they are
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
- **THEN** the `evennia` service mounts `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z`, and the image itself contains no seed-art directory

#### Scenario: A deployment with no seed folder still starts
- **WHEN** the service is started with no host seed folder present
- **THEN** the server starts normally, synchronizes no seed art, and reports the skip once
