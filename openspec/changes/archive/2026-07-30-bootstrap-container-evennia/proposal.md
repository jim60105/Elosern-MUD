## Why

This is roadmap item #1: the foundation every other change in the project builds on. Nothing can
be implemented — not entities, not rules, not the generative layer — without a runnable,
containerized Evennia project to put it in. Separately, the design doc's Contrib Reuse Matrix (§4)
is explicitly flagged as unverified, sourced from a secondary research document rather than the
installed Evennia. Twenty-two later changes design against that matrix; if it is wrong, they design
against modules and class names that do not exist. Verifying it now, once, is far cheaper than
discovering the drift piecemeal across 22 later changes.

## What Changes

- Add a Podman-only multi-stage `Containerfile`: the builder stage installs dependencies with
  architecture-scoped Buildah cache mounts; an application-layout stage prepares the runtime
  permissions; and the final stage imports the venv, application tree, and init binary as
  independently reusable `COPY --link` layers. The image runs as a non-root,
  arbitrary-UID-capable user (group-0 writable, OpenShift-compatible). Full linked-layer cache
  reuse requires Podman 5.6 or later with Buildah 1.41 or later.
- Add `compose.yaml` defining the `evennia` service (ports 4000 telnet / 4001 webserver / 4002
  websocket; volumes for the SQLite DB, scene art store, logs, generated static files, and media)
  and a profile-gated, interactive one-shot `bootstrap` service that migrates a fresh database and
  creates Account #1 without placing its password in the long-lived service configuration. Ollama
  and sd-webui are reached through Podman's `host.containers.internal` hostname and environment
  variables, never bundled into the image.
- Add `.dockerignore` excluding VCS, `.env`, caches, local virtualenvs, and anything not needed in
  the build context.
- Add an Evennia project skeleton (generated via `evennia --init`, then reconciled with the
  directory layout in design doc §3.2) that starts inside the container and accepts a telnet or
  webclient connection end-to-end.
- **Verify and correct design doc §4** (the Contrib Reuse Matrix) against the actually-installed
  Evennia version. This has already been done as part of writing this proposal: Evennia **6.1.0**
   was installed in an isolated environment and every listed module path and class name was checked
   against the real source tree. Four corrections were made in place:
  1. `evadventure` lives under `evennia.contrib.tutorials`, not `evennia.contrib.rpg`.
  2. No `OrderedLevelTrait` class exists anywhere in Evennia. `rules/sexual_state.py` must author
     its own ordered-level `Trait` subclass from scratch and register it via
     `settings.TRAIT_CLASS_PATHS`, following the pattern the contrib's own example (`RageTrait`)
     demonstrates. There is nothing pre-built to subclass.
   3. `evennia.prototypes.spawner` is core Evennia, not a contrib module — it should not be searched
      for under `evennia.contrib`.
   4. `PyramidMapProvider` is an example in the `wilderness` module documentation, not an importable
      contrib class. Only `WildernessMapProvider` is available for subclassing.
  All other rows (traits, buffs, components, xyzgrid, wilderness, llm client/npc, dice, WebClient
  GoldenLayout config path) were confirmed accurate as originally written.
- Add a small regression check that imports every module path named in the corrected matrix, so a
  future Evennia upgrade that breaks one of these paths fails a test immediately instead of
  silently invalidating the design that 22 later changes rely on.

## Capabilities

### New Capabilities
- `container-image`: The Podman-focused Containerfile, compose.yaml, and .dockerignore that build,
  bootstrap, and run the Evennia service as a container per design doc §9 (multi-stage,
  linked-layer cache reuse, non-root/arbitrary-UID, correct ports and volumes, no GPU runtime in
  the image).
- `evennia-project-skeleton`: A running Evennia game directory, structured per design doc §3.2,
  that starts inside the container and accepts a player connection.
- `contrib-matrix-verification`: The verified, corrected Contrib Reuse Matrix (design doc §4) and
  an automated check that guards every listed module path against silent drift on future Evennia
  upgrades.

### Modified Capabilities
- None. This is the first change in the project; `openspec/specs/` is currently empty.

## Impact

- **New files**: `Containerfile`, `compose.yaml`, `.dockerignore`, an Evennia game directory
  skeleton (typeclasses/, server/, world/, commands/, web/ per §3.2), and one small test module
  that import-checks the contrib matrix's module paths.
- **Modified**: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §4 — already corrected
  as described above.
- **No existing runtime code is affected** — this is a greenfield change with zero prior
  implementation.
- **Dependencies confirmed**: Evennia 6.1.0 requires Python >=3.12 (verified working on 3.14.6 in
  an isolated venv during this proposal's research; the Containerfile pins Python 3.13). Its
  `xyzgrid` contrib requires the separately pinned SciPy 1.16.0 dependency for import and use.
