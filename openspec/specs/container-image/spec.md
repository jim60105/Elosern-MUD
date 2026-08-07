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
files, uploaded media, and scene art. It SHALL bake the repo's `prompts/` directory into the image
at `/app/prompts` and mount the host prompt folder read-only into the container at `/app/prompts`
via `${PROMPTS_DIR:-./prompts}:/app/prompts:ro,z`, so an admin can edit prompt files on the host and
apply them by restarting or reloading the server without rebuilding the image. The `,z` option
relabels the bind mount with the SELinux container context so the read-only mount stays readable
under enforcing SELinux (for example on Fedora or RHEL hosts) without weakening its read-only
semantics. It SHALL also
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

### Requirement: Container ignore file excludes non-build-context files
The project SHALL provide a `.containerignore` that excludes version control metadata, local virtual
environments, caches, and any gitignored development-only paths (such as `tmp/`) from the build
context.

#### Scenario: Build context stays small
- **WHEN** the image is built from the repository root
- **THEN** the build context sent to the builder does not include `.git/`, any local virtualenv
  directory, `__pycache__/`, `.env`, or `tmp/`
