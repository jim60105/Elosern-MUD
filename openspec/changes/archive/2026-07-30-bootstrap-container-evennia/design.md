## Context

This is the first change in the project (roadmap #1, design doc §11). There is no existing code:
the repository currently holds only docs, OpenSpec scaffolding, and a gitignored `tmp/`. Everything
downstream — entities, rules, the generative layer, art — is built inside the Evennia project this
change creates, and 22 later changes' designs cite the Contrib Reuse Matrix (design doc §4) as
ground truth. Both deliverables (a running container, a corrected matrix) must land together
because a change that only containerizes an empty skeleton, without fixing §4, leaves every
subsequent change designing against fiction.

Evennia **6.1.0** was installed and inspected directly (isolated venv, `pip install evennia`) while
writing this proposal; findings are already folded into design doc §4. Its `xyzgrid` contrib also
requires SciPy, so this change pins `scipy==1.16.0` alongside Evennia. This design.md covers how
change 1 turns those findings into a running, containerized project.

## Goals / Non-Goals

**Goals:**
- A `Containerfile` + `compose.yaml` + `.dockerignore` that build and run Evennia as a container
  per design doc §9, connectable on the standard ports.
- An Evennia project skeleton, structured to match design doc §3.2, that starts inside the
  container and accepts a player connection (telnet and/or webclient).
- The Contrib Reuse Matrix (§4) verified against the installed version, corrected in place, and
  protected by an automated import check so future Evennia upgrades fail loudly instead of
  silently invalidating downstream designs.

**Non-Goals:**
- No game logic. `typeclasses/`, `world/lore/`, `world/rules/`, etc. stay empty stubs or absent;
  Phase 1+ changes populate them.
- No CI/CD pipeline, no image publishing, no Kubernetes/OpenShift manifests — only
  arbitrary-UID/group-0 compatibility, which is a Containerfile property, not a deployment one.
- No GPU services (Ollama, sd-webui) are containerized here — design doc §9 keeps them external by
  decision (D11 and the containerization section).
- No backward-compatibility, migration, or deprecation handling of any kind — the project is
  unreleased with zero users.

## Decisions

**D-1. Base image: Debian-slim Python, explicit pinned minor version.**
Evennia 6.1.0 requires Python >=3.12 (confirmed via package metadata) and depends on Twisted,
Django 6, and autobahn — all of which ship well-tested manylinux/glibc wheels. Alpine's musl libc
is a recurring source of subtle Twisted/cryptography build failures in the Evennia community, so
Debian-slim is chosen over Alpine despite the larger base size. Pin to a specific `python:3.1X-slim`
minor version rather than floating `-slim` tags, so the image doesn't silently change Python
versions across rebuilds. The implementation selects `python:3.13-slim`, which satisfies Evennia's
declared floor without adopting the newer Python 3.14 used only during proposal research.

**D-2. Podman/Buildah multi-stage build with linked final imports.**
The Containerfile has four stages: a downloader verifies the architecture-specific `dumb-init`
binary; a builder installs the pinned dependencies into a venv using an architecture-scoped UV
cache mount; an application-layout stage assembles only the runtime source tree and applies its
final ownership and modes; and the slim final stage imports those prepared artifacts.

`requirements.txt` uses a normal `COPY` because the following dependency-install `RUN` must read
it. The venv, init binary, and prepared `/app` tree are terminal imports in the final stage, so
they use `COPY --link` and can be cached independently of earlier final-stage filesystem changes.
Full linked-layer cache behavior requires Podman 5.6 or later with Buildah 1.41 or later. Buildah
does not invalidate a cached `LABEL` from changed `ARG` values alone, so a no-output `RUN` consumes
`VERSION` and `RELEASE` immediately before the final label as a metadata cache barrier. This
structure keeps download caches and build tooling out of the shipped image while preserving the
largest reusable layers across rebuilds.

**D-3. Non-root, arbitrary-UID-capable runtime user.**
Create a dedicated non-root user in group `0`. Keep the application code and virtual environment
read-only, but make the directories Evennia writes to at runtime (`server/` for PID files,
`server/db/`, `server/logs/`, `server/.static/`, `server/.media/`, and the scene-art store path)
owned by `root:0` with mode `g+rwX`. Apply the sticky bit to `server/` so runtime users cannot
remove or replace root-owned configuration files. Set `HOME` to the writable system temporary
directory so an arbitrary UID without an `/etc/passwd` entry has a safe home path. The
application-layout stage establishes these modes before the whole tree becomes one linked final
layer, avoiding colliding linked-copy metadata that could overwrite writable directory modes.
This supports the OpenShift restricted SCC pattern without making code mutable.

**D-4. Evennia game directory lives at the repository root, not in a nested subfolder.**
Design doc §3.2 shows a tree rooted at `mygame/`. That label reads as a generic placeholder for
"wherever the Evennia game directory is," not a literal required folder name — the repository is
already dedicated solely to this project, so nesting an inner `mygame/` would just add a path
segment every later change's file references would have to repeat. **Judgment call**: the game
directory (`typeclasses/`, `server/`, `world/`, `commands/`, `web/`) is created directly at the
repository root. If this is wrong, it is a one-time rename before Phase 1 starts, not a redesign.

**D-5. A one-shot bootstrap creates Account #1 before the normal service starts.**
Evennia 6.1.0 recursively retries superuser creation when `evennia start` sees a migrated database
without Account #1 in a non-interactive container. `compose.yaml` therefore provides a
profile-gated `bootstrap` service that mounts only the database volume, runs the migrations, and
executes `evennia createsuperuser` interactively. The operator runs it once with
`podman compose --profile bootstrap run --rm bootstrap`, then starts the normal service. The
password travels through the interactive terminal and is never stored in the image, Compose
environment, or long-lived container configuration.

The normal runtime startup script still runs the idempotent `evennia migrate` command against the
mounted SQLite database directory before invoking `evennia start --log`.
Verified behavior (evennia_launcher.py): `start` still daemonizes Portal+Server as two OS processes
writing to `server/logs/{portal,server}.log` as usual; `--log` is a separate `tail_log_files()` call
that streams those files to stdout and blocks the foreground process. This is *not* "logs go to
stdout instead of files" as a first read of §9 might suggest — logs go to both places. Consequence
for this change: the `server/logs` volume mount is load-bearing (§9 already lists it, so no doc
change needed there), and the container's healthiness is really "is the tail process still
attached," which is an acceptable proxy for "is Portal+Server still up" for this change's scope.

**D-6. Ports and volumes exactly as design doc §9 states.**
Confirmed against `settings_default.py`: `TELNET_PORTS = [4000]`, `WEBSERVER_PORTS = [(4001, 4005)]`,
`WEBSOCKET_CLIENT_PORT = 4002`. No correction needed. `compose.yaml` exposes 4000/4001/4002 and
mounts named volumes for the SQLite DB file's parent directory, `server/logs`, generated static
files, uploaded media, and the scene art store path (a stub directory for now — `world/art/` is
Phase 6). The bootstrap service shares only the database volume required for migration and
Account #1 creation.

**D-7. Contrib matrix verification is captured as a standing regression check, not just prose.**
A one-time manual verification (already done for this proposal) rots the moment Evennia is
upgraded. Change 1 adds a small test that does nothing but `importlib.import_module()` every
module path named in the corrected §4 table and `getattr()` every named class/function, asserting
they exist. This is intentionally dumb — it is a tripwire, not a behavior test — but it is the
cheapest possible protection for the 22 changes that trust the matrix.

**D-8. GPU services are configuration, not containers.**
`compose.yaml` defines the long-lived `evennia` service and the profile-gated one-shot `bootstrap`
service; it defines no GPU service. Ollama/sd-webui base URLs are environment variables (e.g.
`OLLAMA_BASE_URL`, `SD_WEBUI_BASE_URL`) that default to Podman's `host.containers.internal`
hostname for services running on the container host. No GPU runtime and no
`deploy.resources.reservations.devices` block are present, so the image and compose file stay
GPU-agnostic per D11.

## Risks / Trade-offs

- **[Risk] The verified matrix (Evennia 6.1.0, checked outside the container) drifts from whatever
  version actually resolves inside the built image if the Containerfile doesn't pin a version.** →
  Mitigation: pin `evennia==6.1.0` and `scipy==1.16.0` explicitly in the dependency file; the D-7
  import-check test runs in CI/on build and fails immediately if a future unpinned upgrade breaks a
  path. The test also distinguishes documented examples, such as `PyramidMapProvider`, from public
  importable API.
- **[Risk] Debian-slim images are larger than Alpine.** → Accepted trade-off; Evennia's dependency
  stack (Twisted, autobahn, Django, cryptography via Twisted's TLS support) makes musl-based builds
  fragile enough that image size is the cheaper problem to have.
- **[Risk] `evennia --init` scaffolds files (`server/conf/settings.py`, a default `secret_settings`
  pattern) that require migration before use.** → Mitigation: the runtime startup script performs
  the idempotent `evennia migrate` command against the mounted database volume. A documented
  one-shot bootstrap service performs the first migration and interactive Account #1 creation
  before normal startup; neither credentials nor a database are build artifacts or long-lived
  service configuration.
  `server/conf/secret_settings.py` is a generated secret; it must never be baked into the image.
- **[Risk] `COPY --link` applies an independent layer whose directory metadata can collide with
  paths prepared by earlier final-stage instructions.** → Mitigation: assemble and chmod the
  complete `/app` tree in a dedicated application-layout stage, then import it as one coherent
  linked layer. Use normal `COPY` for files consumed by a later `RUN`.
- **[Risk] Buildah may reuse a stale `LABEL` when only a build argument changes.** → Mitigation:
  consume `VERSION` and `RELEASE` in a no-output `RUN` immediately before the final label. A
  build-argument probe confirms that all preceding layers remain cached while the metadata layers
  rebuild with the new revision.
- **[Risk] Arbitrary-UID support is easy to assert and easy to accidentally break with a later
  `COPY --chown=<baked-uid>` or a hardcoded log path outside group-0 permissions.** → Mitigation:
  the tasks include an explicit test — run the built image with `--user 1000630000:0` (an arbitrary
  OpenShift-style UID) and confirm the server still starts and writes logs.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, so
there is no prior deployment to migrate from and no rollback path to preserve. On each startup, the
runtime script runs idempotent database migrations against the mounted DB volume before launching
Evennia. Against a fresh volume, first build the image, run the profile-gated interactive
`bootstrap` service once to migrate and create Account #1, and then start the normal service.

## Open Questions

- Should the Evennia game directory be named after the project (`elosern/`, matching the setting's
  name, 伊洛瑟恩) instead of sitting at the repository root with no distinguishing name? Left as a
  repository-root placement for this change (D-4); trivial to rename later if the user prefers a
  named subfolder.
