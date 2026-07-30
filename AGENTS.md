# Elosern MUD Agent Guide

## Project

Elosern is an unreleased, single-player, adult, AI-driven MUD built on Evennia
6.1.0 and Python 3.13. The deterministic game must remain fully playable when
all LLM and image-generation services are offline.

Read `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` before planning
feature work. It is the architectural source of truth for every OpenSpec change;
if a change conflicts with it, the design document wins unless the change
explicitly amends the design.

The main code areas are:

- `typeclasses/`: persistent Evennia entities such as characters, NPCs,
  monsters, rooms, and objects.
- `world/lore/`: immutable, registry-backed world data, mirrored idempotently
  into Evennia Scripts at startup.
- `world/rules/`: deterministic rules and the sole writer of game state.
- `world/imports/`: versioned JSON schemas, validation, and transactional
  loading.
- `world/ai/`: generative systems. They may read state and emit validated
  proposals, but must never mutate game state directly.
- `commands/`, `server/`, and `web/`: Evennia command, configuration, and web
  extension points.
- `openspec/`: main specifications, active changes, and archived changes.

## Architectural invariants

- Preserve the single-writer boundary: only the deterministic core in
  `world/rules/` applies state changes. Generative code submits schema-valid
  proposals through that core.
- Treat module-level lore registries as the source of truth. Use frozen
  dataclasses and keyed registries, and make startup synchronization idempotent.
  Consumers must read registry values instead of duplicating balance constants.
- Imported base stats are literal values. Do not bake skill multipliers into
  stored traits.
- `disguised_stats` is display-only and may affect appearance, guild
  registration, and appraisal. Combat and resolution always use true traits.
- Every character is an adult. Imports must reject both `age < 18` and
  `apparent_age < 18`; never weaken or bypass this invariant.
- Import and action-resolution workflows are all-or-nothing. Validate before
  persistence and use transactions where partial state would be invalid.
- Store currency as integer copper. Convert units only for display; do not use
  floating-point money.
- Keep forward-declared seams and guarded tests intact when their owning change
  has not landed yet. A deliberate skip is preferable to a fake implementation.
- The project has no released users. Do not add backward-compatibility layers or
  data migrations unless a task explicitly requires them.

## Python and Evennia conventions

- Match the surrounding Python style: four spaces, modern type annotations
  (`str | None`, built-in generics), short focused functions, and descriptive
  module/class docstrings.
- Group imports as standard library, third party, then project imports. Use
  absolute imports across top-level packages and concise relative imports
  within one package.
- Use `AttributeProperty`, Evennia handlers, or `entity.db` for persistent
  typeclass state as appropriate; do not rely on ordinary instance attributes
  for data that must survive reloads.
- Pure logic tests use `unittest.TestCase`. Database, typeclass, command, and
  other Evennia integration tests use `evennia.utils.test_resources.EvenniaTest`.
  Keep package tests beside their code under `<package>/tests/`; reserve
  top-level `tests/` for repository-wide checks.
- Tests must be deterministic. Use fixed inputs or seeds, never live LLM,
  Stable Diffusion, or other network services.
- Write code comments, docstrings, commit messages, and technical documentation
  in English. Preserve canonical Traditional Chinese lore terms and use
  Traditional Chinese for player-facing game prose.
- No formatter, linter, or static type checker is currently configured. Follow
  the existing idiom and keep `git diff --check` clean.

## uv workflow

Use uv 0.12.0 or newer for every Python environment and command. The interpreter
is pinned to Python 3.13 by `.python-version`, and `uv.lock` is authoritative.

```sh
uv sync --locked
uv run --locked evennia test --settings settings.py .
uv run --locked -m unittest discover tests
uv run --locked -m world.imports.validate world/imports/examples/example_character.json
uv run --locked python -m compileall -q world typeclasses commands server
```

The Evennia command is the full project suite. The `unittest discover tests`
command is only the top-level contrib-matrix regression check, not a substitute
for the full suite. Run focused tests while iterating and the full relevant
suite before handing work off.

Use `uv add <package>` and `uv remove <package>` for dependency changes so
`pyproject.toml` and `uv.lock` remain synchronized. Never edit `uv.lock`
manually, invoke project Python tools outside `uv run --locked`, or use `pip`
against the project environment.

## OpenSpec workflow

Feature work is specification-driven. Use the matching repository skill under
`.agents/skills/` for proposing, exploring, updating, applying, verifying,
syncing, or archiving a change. Follow that skill rather than inventing an
ad-hoc artifact workflow.

- Run `openspec list --json` to inspect active changes. For a selected change,
  run `openspec status --change <name> --json` and use the returned artifact
  paths and schema; do not assume paths for custom schemas.
- Keep `proposal.md` (why and scope), `design.md` (technical decisions), delta
  specs (requirements and scenarios), and `tasks.md` (implementation work)
  mutually consistent. Respect the dependency order in the project roadmap.
- During implementation, follow `tasks.md`, add tests with the behavior, and
  mark a checkbox complete only after that task is actually verified.
- Before handoff, compare the implementation with all change artifacts and run
  `openspec validate <change> --strict` plus the relevant uv-managed tests.
- Archive only completed, verified changes. Always sync delta specs into
  `openspec/specs/` as part of the archive workflow, preserve the dated archive
  under `openspec/changes/archive/`, and finish with
  `openspec validate --all --strict`.

Main specs describe the current contract. Active changes contain proposed
deltas; archived changes are historical evidence and must not be treated as the
current source over `openspec/specs/`.

## Container behavior

Use Podman Compose for container workflows (`podman compose build` and
`podman compose up`). Preserve the multi-stage, non-root, arbitrary-UID image
design and the persistent mounts for the SQLite database, logs, static/media
files, and art. Evennia's `start --log` still writes to `server/logs`, so that
volume is required. Ollama and sd-webui are external services configured by
environment variables; do not add them to this image.
