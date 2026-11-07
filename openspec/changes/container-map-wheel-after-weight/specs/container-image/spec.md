## MODIFIED Requirements

### Requirement: Multi-stage Containerfile
`Containerfile` SHALL be a Podman-focused multi-stage build: a downloader verifying the init binary, a builder, an application-layout stage that prepares the runtime tree, and a final stage carrying only the venv, init binary, application code, and the acquired removal weight. Model acquisition SHALL follow locked third-party dependency installation. The locked local `elosern-map-core` wheel SHALL install from `packages/map-core/` after acquisition and SHALL be rebuilt, never a cached wheel.

#### Scenario: The idmapper memory probe has ps available
- **WHEN** the served server runs its periodic idmapper cache maintenance
- **THEN** `ps` exists in the runtime image, so the resident-memory probe returns a
  number instead of raising and the cache cap stays operational

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

#### Scenario: Map-package source edits reuse model acquisition
- **WHEN** only the map package's source files change, while the root `pyproject.toml`, `uv.lock`, and `packages/map-core/pyproject.toml` stay unchanged
- **THEN** the build reuses the layer containing the already-acquired default weight and rebuilds and installs exactly that one package

#### Scenario: A rebuilt image carries the current map-package code
- **WHEN** the map package's source changes and the image is rebuilt
- **THEN** the installed `elosern_map_core` files match the rebuilt source, never a previously cached wheel
