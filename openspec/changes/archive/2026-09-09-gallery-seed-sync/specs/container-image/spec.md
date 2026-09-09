## MODIFIED Requirements

### Requirement: compose.yaml for local and networked GPU services
The project SHALL provide a `compose.yaml` that runs the Evennia service with the ports and
volumes design doc §9 specifies. It SHALL persist the SQLite database, logs, generated static
files, uploaded media, and scene art. It SHALL bake the repo's `prompts/` directory into the image
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
engine simply synchronizes nothing. It SHALL also
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
- **THEN** the SQLite database, scene art store, logs, generated static files, and media contents
  from the previous run are still present, because they are backed by volumes rather than the
  container's writable layer

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
