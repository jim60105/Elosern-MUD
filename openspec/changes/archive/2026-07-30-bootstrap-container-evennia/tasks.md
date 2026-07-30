## 1. Dependency pinning

- [x] 1.1 Add a dependency file (`requirements.txt` or `pyproject.toml`) pinning `evennia==6.1.0`
      (the version verified during this change's proposal), its XYZ grid contrib dependency
      `scipy==1.16.0`, and Python `3.13` as the explicit container base version (`>=3.12` is
      Evennia's declared floor).
- [x] 1.2 Record the pinned Evennia version and Python version in the project's top-level
      documentation so future changes know what was verified.

## 2. Evennia project skeleton

- [x] 2.1 Run `evennia --init` to scaffold the game directory at the repository root (see
      design.md D-4), producing `typeclasses/`, `server/`, `world/`, `commands/`, `web/`.
- [x] 2.2 Add empty-stub subpackages under `world/` for the directories design doc §3.2 names
      (`world/lore/`, `world/rules/` with `world/rules/rulebook/`, `world/quests/`, `world/ai/`
      with `world/ai/schemas/`, `world/imports/` with `world/imports/examples/`, `world/art/`) so
      later changes have a landing spot without redesigning the tree.
- [x] 2.3 Run `evennia migrate` locally to confirm the skeleton is valid before containerizing it;
      discard this local DB afterward. Create Account #1 interactively through the profile-gated
      one-shot bootstrap service against the mounted database volume before starting the normal
      service.
- [x] 2.4 Confirm `.gitignore` covers `server/conf/secret_settings.py` and any local SQLite DB file
      the skeleton generates, so secrets and local state are never committed.

## 3. Containerfile

- [x] 3.1 Write a Podman-focused multi-stage `Containerfile`: downloader stage verifies
      architecture-specific `dumb-init`; builder stage installs the pinned dependencies into a
      venv using an architecture-scoped Buildah cache mount; application-layout stage prepares
      runtime code and modes; final stage carries only the prepared runtime artifacts.
- [x] 3.2 Create a non-root runtime user in group `0`; keep the application code and virtual
      environment read-only, and set `server/` (sticky for PID files), `server/db/`,
      `server/logs/`, `server/.static/`, `server/.media/`, and the scene art store path to `root:0`
      with group-write in the application-layout stage. Import the complete prepared `/app` tree
      as one `COPY --link` layer. Set a writable `HOME` so the image works under its default UID
      and an arbitrary UID with GID 0.
- [x] 3.3 Set the container's entrypoint/CMD to run `evennia start --log` in the foreground (see
      design.md D-5 for why this still requires the `server/logs` volume mount), after an
      idempotent `evennia migrate` against the mounted database volume.
- [x] 3.4 Add standard OCI `LABEL` metadata last, with a Buildah cache barrier that consumes
      `VERSION` and `RELEASE` so changed build metadata does not reuse a stale label.

## 4. compose.yaml and .dockerignore

- [x] 4.1 Write `compose.yaml` defining the `evennia` service: build from the `Containerfile`,
      publish ports 4000/4001/4002, and mount volumes for the SQLite DB directory, scene art,
      `server/logs`, generated static files, and uploaded media.
- [x] 4.2 Add environment variables for the Ollama and sd-webui base URLs (unused by this change's
      code, but present so later changes have a place to wire them in), defaulting to Podman's
      `host.containers.internal` hostname for host-local GPU services.
- [x] 4.3 Write `.dockerignore` excluding `.git/`, local virtualenvs, `__pycache__/`,
      `.env`, `tmp/`, and any other gitignored development-only paths.
- [x] 4.4 Add a profile-gated, interactive one-shot `bootstrap` service that shares only the
      database volume, runs migrations, and creates Account #1 without storing its password in
      long-lived container metadata. Document the build, bootstrap, and normal startup sequence.

## 5. Contrib matrix regression check

- [x] 5.1 Write a small test module that, for every row corrected or confirmed in design doc §4,
      imports the named module and resolves every named class/function via `getattr`, asserting
      each succeeds.
- [x] 5.2 Wire this test into the project's normal test run so it executes alongside any other
      tests added by this change (no separate CI system is being introduced by this change).

## 6. Verification

- [x] 6.1 Build the image with Podman, run the one-shot bootstrap against a fresh database volume,
      and start the normal service via `podman compose up`; confirm Portal+Server both come up and
      logs stream to stdout.
- [x] 6.2 Connect over telnet (port 4000) and over the webclient (port 4001) and confirm the
      default Evennia welcome/login screen appears on both.
- [x] 6.3 Re-run the container with `--user 1002:0` (an arbitrary UID, GID 0) against a fresh volume
      set and confirm it starts cleanly, writes logs, and collects static resources without permission
      errors.
- [x] 6.4 Stop and recreate the service container and confirm the database, art store, logs, static
      files, and media from the previous run persisted via the volumes.
- [x] 6.5 Run the contrib matrix regression check (task 5.1) and confirm it passes against the
      pinned Evennia version.
- [x] 6.6 Confirm no secret_settings file or local SQLite DB is present in any layer of the built
      image using Podman layer inspection.
- [x] 6.7 Rebuild without source changes and confirm every dependency, application-layout, and
      final linked-copy step hits the Buildah layer cache. Rebuild with only `RELEASE` changed and
      confirm all preceding runtime layers remain cached while the OCI revision label updates.
