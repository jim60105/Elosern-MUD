## ADDED Requirements

### Requirement: Multi-stage Containerfile
The project SHALL provide a `Containerfile` using a multi-stage build: a builder stage that
installs Python dependencies using BuildKit cache mounts, and a runtime stage that carries only
the resulting virtual environment and application code.

#### Scenario: Builder artifacts do not reach the runtime image
- **WHEN** the image is built with `docker build` (or `podman build`) from the `Containerfile`
- **THEN** the final image contains no compiler toolchain, no pip download cache, and no build-only
  dependency that is not required to run `evennia start`

#### Scenario: Repeated builds reuse the dependency cache
- **WHEN** the image is rebuilt after only application code changed (no dependency file changed)
- **THEN** the dependency-install layer is served from the BuildKit cache mount rather than
  re-downloading packages

### Requirement: Non-root, arbitrary-UID-capable runtime
The container SHALL run as a non-root user by default, and SHALL also start successfully when run
with an arbitrary numeric UID and GID 0 (the OpenShift restricted SCC pattern), writing no files
outside directories that are group-0 writable.

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
volumes design doc §9 specifies, and that reaches Ollama and sd-webui over the network rather than
bundling them as containers.

#### Scenario: Ports match the design
- **WHEN** the `evennia` service starts via `compose up`
- **THEN** ports 4000 (telnet), 4001 (webserver), and 4002 (websocket) are published and reachable
  from the host

#### Scenario: Persistent state survives container recreation
- **WHEN** the `evennia` service container is removed and recreated (`compose up --force-recreate`)
- **THEN** the SQLite database, scene art store, and `server/logs` contents from the previous run
  are still present, because they are backed by volumes rather than the container's writable layer

#### Scenario: GPU services are configured, not containerized
- **WHEN** `compose.yaml` is inspected
- **THEN** it defines no Ollama or sd-webui service, and the `evennia` service instead reads their
  base URLs from environment variables (with an `extra_hosts` example for host-local GPU services
  in a comment)

### Requirement: .dockerignore excludes non-build-context files
The project SHALL provide a `.dockerignore` that excludes version control metadata, local virtual
environments, caches, and any gitignored development-only paths (such as `tmp/`) from the build
context.

#### Scenario: Build context stays small
- **WHEN** the image is built from the repository root
- **THEN** the build context sent to the builder does not include `.git/`, any local virtualenv
  directory, `__pycache__/`, or `tmp/`
