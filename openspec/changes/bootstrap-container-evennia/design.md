## Context

This is the first change in the project (roadmap #1, design doc §11). There is no existing code:
the repository currently holds only docs, OpenSpec scaffolding, and a gitignored `tmp/`. Everything
downstream — entities, rules, the generative layer, art — is built inside the Evennia project this
change creates, and 22 later changes' designs cite the Contrib Reuse Matrix (design doc §4) as
ground truth. Both deliverables (a running container, a corrected matrix) must land together
because a change that only containerizes an empty skeleton, without fixing §4, leaves every
subsequent change designing against fiction.

Evennia **6.1.0** was installed and inspected directly (isolated venv, `pip install evennia`) while
writing this proposal; findings are already folded into design doc §4. This design.md covers how
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
minor version (implementer chooses 3.12 or 3.13 at build time; 3.14 was confirmed to work in
research for this proposal but is newer than Evennia's declared floor and not yet the safer
default) rather than floating `-slim` tags, so the image doesn't silently change Python versions
across rebuilds.

**D-2. Multi-stage build with a builder stage and a slim runtime stage.**
Builder stage installs into a venv using BuildKit cache mounts for pip's cache; runtime stage
copies only the venv and application code, per the `containerfile-creator` skill's standard
pattern and design doc §9's explicit requirement. This keeps compilers, wheel caches, and
build-only dependencies out of the shipped image.

**D-3. Non-root, arbitrary-UID-capable runtime user.**
Create a dedicated non-root user, but make the application directories and any dirs Evennia writes
to at runtime (`server/logs/`, the SQLite DB path, the scene-art store path) owned by `root:root`
with group `0` and mode `g+rwX`, so the container also runs correctly under an arbitrary UID with
GID 0 (the OpenShift restricted SCC pattern), not just under its baked-in UID. This satisfies both
"non-root locally" and "arbitrary-UID on OpenShift" from the same file, without profile-specific
branches.

**D-4. Evennia game directory lives at the repository root, not in a nested subfolder.**
Design doc §3.2 shows a tree rooted at `mygame/`. That label reads as a generic placeholder for
"wherever the Evennia game directory is," not a literal required folder name — the repository is
already dedicated solely to this project, so nesting an inner `mygame/` would just add a path
segment every later change's file references would have to repeat. **Judgment call**: the game
directory (`typeclasses/`, `server/`, `world/`, `commands/`, `web/`) is created directly at the
repository root. If this is wrong, it is a one-time rename before Phase 1 starts, not a redesign.

**D-5. Foreground process is `evennia start --log`, with `server/logs/` mounted as a volume.**
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
mounts named volumes for the SQLite DB file's parent directory, the scene art store path (a stub
directory for now — `world/art/` is Phase 6), and `server/logs`.

**D-7. Contrib matrix verification is captured as a standing regression check, not just prose.**
A one-time manual verification (already done for this proposal) rots the moment Evennia is
upgraded. Change 1 adds a small test that does nothing but `importlib.import_module()` every
module path named in the corrected §4 table and `getattr()` every named class/function, asserting
they exist. This is intentionally dumb — it is a tripwire, not a behavior test — but it is the
cheapest possible protection for the 22 changes that trust the matrix.

**D-8. GPU services are configuration, not containers.**
`compose.yaml` defines only the `evennia` service. Ollama/sd-webui base URLs are environment
variables (e.g. `OLLAMA_BASE_URL`, `SD_WEBUI_BASE_URL`) with `extra_hosts: ["host.docker.internal:
host-gateway"]` documented in a comment for the common case of GPU services running on the Docker
host itself. No GPU runtime, no `deploy.resources.reservations.devices` block — the image and
compose file stay GPU-agnostic per D11.

## Risks / Trade-offs

- **[Risk] The verified matrix (Evennia 6.1.0, checked outside the container) drifts from whatever
  version actually resolves inside the built image if the Containerfile doesn't pin a version.** →
  Mitigation: pin `evennia==6.1.0` explicitly in the dependency file; the D-7 import-check test runs
  in CI/on build and fails immediately if a future unpinned upgrade breaks a path.
- **[Risk] Debian-slim images are larger than Alpine.** → Accepted trade-off; Evennia's dependency
  stack (Twisted, autobahn, Django, cryptography via Twisted's TLS support) makes musl-based builds
  fragile enough that image size is the cheaper problem to have.
- **[Risk] `evennia --init` scaffolds files (`server/conf/settings.py`, a default `secret_settings`
  pattern) that assume interactive `evennia migrate` / superuser creation.** → Mitigation: document
  the one-time init sequence (`evennia migrate`, create superuser) as a task, not something baked
  into the image at build time — the SQLite DB is a runtime volume, not a build artifact.
  `server/conf/secret_settings.py` is a generated secret; it must never be baked into the image.
- **[Risk] Arbitrary-UID support is easy to assert and easy to accidentally break with a later
  `COPY --chown=<baked-uid>` or a hardcoded log path outside group-0 permissions.** → Mitigation:
  the tasks include an explicit test — run the built image with `--user 1000630000:0` (an arbitrary
  OpenShift-style UID) and confirm the server still starts and writes logs.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, so
there is no prior deployment to migrate from and no rollback path to preserve. The only "migration"
is the one-time first-run sequence documented as tasks: build the image, run `evennia migrate`
inside it once against the mounted DB volume, create the initial superuser, then bring the service
up via `compose.yaml` for all subsequent runs.

## Open Questions

- Should the Evennia game directory be named after the project (`elosern/`, matching the setting's
  name, 伊洛瑟恩) instead of sitting at the repository root with no distinguishing name? Left as a
  repository-root placement for this change (D-4); trivial to rename later if the user prefers a
  named subfolder.
- Exact base image tag (`python:3.12-slim-trixie` vs. `python:3.13-slim-trixie`) is left to the
  implementer to pin at build time; both satisfy Evennia's `>=3.12` floor.
