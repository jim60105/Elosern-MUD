## 1. Dependency pinning

- [ ] 1.1 Add a dependency file (`requirements.txt` or `pyproject.toml`) pinning `evennia==6.1.0`
      (the version verified during this change's proposal) and a specific Python base version
      (`>=3.12`, per Evennia's declared floor).
- [ ] 1.2 Record the pinned Evennia version and Python version in the project's top-level
      documentation so future changes know what was verified.

## 2. Evennia project skeleton

- [ ] 2.1 Run `evennia --init` to scaffold the game directory at the repository root (see
      design.md D-4), producing `typeclasses/`, `server/`, `world/`, `commands/`, `web/`.
- [ ] 2.2 Add empty-stub subpackages under `world/` for the directories design doc §3.2 names
      (`world/lore/`, `world/rules/` with `world/rules/rulebook/`, `world/quests/`, `world/ai/`
      with `world/ai/schemas/`, `world/imports/` with `world/imports/examples/`, `world/art/`) so
      later changes have a landing spot without redesigning the tree.
- [ ] 2.3 Run `evennia migrate` and create the initial superuser locally (outside the container)
      to confirm the skeleton is valid before containerizing it; discard this local DB afterward —
      the container's first run repeats this step against its own volume.
- [ ] 2.4 Confirm `.gitignore` covers `server/conf/secret_settings.py` and any local SQLite DB file
      the skeleton generates, so secrets and local state are never committed.

## 3. Containerfile

- [ ] 3.1 Write a multi-stage `Containerfile`: builder stage installs the pinned dependencies into
      a venv using a BuildKit cache mount; runtime stage copies only the venv and application code.
- [ ] 3.2 Create a non-root runtime user; set ownership/permissions on the application directory,
      `server/logs/`, the SQLite DB path, and the scene art store path to `root:0` with group-write,
      so the image works both under its default UID and under an arbitrary UID with GID 0.
- [ ] 3.3 Set the container's entrypoint/CMD to run `evennia start --log` in the foreground (see
      design.md D-5 for why this still requires the `server/logs` volume mount).
- [ ] 3.4 Add standard OCI `LABEL` metadata.

## 4. compose.yaml and .dockerignore

- [ ] 4.1 Write `compose.yaml` defining the `evennia` service: build from the `Containerfile`,
      publish ports 4000/4001/4002, and mount volumes for the SQLite DB directory, the scene art
      store directory, and `server/logs`.
- [ ] 4.2 Add environment variables for the Ollama and sd-webui base URLs (unused by this change's
      code, but present so later changes have a place to wire them in), with a commented
      `extra_hosts` example for reaching host-local GPU services.
- [ ] 4.3 Write `.dockerignore` excluding `.git/`, local virtualenvs, `__pycache__/`,
      `tmp/`, and any other gitignored development-only paths.

## 5. Contrib matrix regression check

- [ ] 5.1 Write a small test module that, for every row corrected or confirmed in design doc §4,
      imports the named module and resolves every named class/function via `getattr`, asserting
      each succeeds.
- [ ] 5.2 Wire this test into the project's normal test run so it executes alongside any other
      tests added by this change (no separate CI system is being introduced by this change).

## 6. Verification

- [ ] 6.1 Build the image and start it via `compose up`; confirm Portal+Server both come up and
      logs stream to stdout.
- [ ] 6.2 Connect over telnet (port 4000) and over the webclient (port 4001) and confirm the
      default Evennia welcome/login screen appears on both.
- [ ] 6.3 Re-run the container with `--user 1000630000:0` (an arbitrary UID, GID 0) against a fresh
      volume set and confirm it starts cleanly and writes logs without permission errors.
- [ ] 6.4 Stop and recreate the `evennia` service (`compose up --force-recreate`) and confirm the
      database, art store, and logs from the previous run persisted via the volumes.
- [ ] 6.5 Run the contrib matrix regression check (task 5.1) and confirm it passes against the
      pinned Evennia version.
- [ ] 6.6 Confirm no secret_settings file or local SQLite DB is present in any layer of the built
      image (`docker history` / layer inspection).
