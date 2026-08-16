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

- Preserve the single-writer boundary: it separates generative from
  deterministic, not `world/rules/` from every other directory. State changes
  are applied by the deterministic core — `world/rules/` (the primary,
  general-purpose engine) plus the sibling packages that own one persistent
  subsystem's own data directly (`world/maps/` for room/instance lifecycle,
  `world/quests/` for quest lifecycle; each such package is named explicitly
  here, not implied by proximity). `world/skills/` and `world/lore/` stay
  read-only/registry-only — any mutation they trigger routes back through
  `world/rules/`. No module under `world/ai/` applies a state change under any
  circumstance; it submits schema-valid proposals through the deterministic
  core instead.
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
- Player-facing command documentation is part of the command surface: any
  change that adds, removes, renames, or alters a player command (key, alias,
  syntax, or availability context) MUST update `docs/game/commands.md` and
  `docs/game/command-reference.md` in the same change and keep
  `tests/test_command_docs.py` green.
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
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands server typeclasses world web.webclient
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --noinput --parallel 16 commands server typeclasses world web.webclient
uv run --locked python -m unittest discover -s web/tests/browser -t .
uv run --locked -m unittest discover -s tests -t .
uv run --locked -m world.imports.validate world/imports/examples/example_character.json
uv run --locked python -m compileall -q world typeclasses commands server
```

The three Python commands have disjoint ownership: the Evennia command runs
non-browser package tests, browser discovery owns managed Playwright tests, and
`unittest discover -s tests -t .` owns repository-wide contracts. Run focused
dotted labels while iterating, but run every affected ownership domain before
handoff. The retained database is `server/db/evennia-test.sqlite3`; omit
`--keepdb` and add `--noinput`, or remove only that file, after migration changes or unexplained
retained-state failures. See `docs/development/evennia-test-performance.md` for
profiling and parallel-evaluation commands.

### Test runtime budget (measured, do not waste wall-clock)

The full Evennia suite (`evennia test ... commands server typeclasses web
world`) is now **4,263 tests**: ~45 s with `--parallel 16` on the 24-core
development machine, and ~152 s with `--parallel 4` including coverage
instrumentation (the CI worker profile). Serial remains canonical for final
handoff evidence, but `--parallel 16 --noinput` is the default full-suite
command during development. The managed browser suite is the slowest thing in the repo
and dominates total runtime (measured 3,465 s locally for the full 148-test
run):

- Each Playwright test boots a real Evennia server. Foundation browser tests
  share one server per process (~30–40s each); **combat browser tests boot one
  server per test** because a live combat session (or an abnormal transport
  close during combat) leaves the shared Evennia server in a state that corrupts
  later fresh logins. A combat test therefore takes ~35–70s each.
- The CI quality gate packs the managed browser suite into 11 two-process
  shards by `.github/browser-shards.json`; each shard job runs two isolated
  test processes from two separate checkouts (`w-a`/`w-b`) because the Evennia
  launcher writes GAMEDIR-relative pidfiles (`server/server.pid`,
  `server/portal.pid`) and two harnesses in one working tree would race on
  them. Every test method has exactly one serial execution owner across the
  22 process lists (enforced by a top-level AST-based contract test).
- The CI quality gate machine-shards the non-browser Evennia suite across six
  parallel jobs by `.github/evennia-shards.json`; each test module has exactly
  one serial execution owner (enforced by a top-level contract test). The
  evennia shard commands are **CI-only**: every invocation writes to the same
  local test database path (`server/db/evennia-test.sqlite3`), so never run
  shard invocations concurrently on one machine. Locally, run the full suite
  once with the full label set.
- Node tests (`node --test web/static/webclient/js/tests/*.test.js`) are ~1s.
- `tools/spec_traceability check` is seconds; the `verify --evidence` gate needs
  the full evidence run only at final handoff.

During iteration, run **only the package tests your change touches** (e.g.
`uv run --locked evennia test --settings settings.py world.rules.tests.test_combat_session`)
or the specific Node/browser file. Run the full Evennia suite and the browser
suite only (a) after a large cross-cutting change, or (b) once, as part of the
final pre-handoff check. When a browser test needs to be re-run, prefer a single
test class or file over the whole suite, and reuse a still-running managed
server rather than booting another.

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

## OpenSpec test traceability

Every requirement in a direct main capability spec at
`openspec/specs/<capability>/spec.md` must have at least one substantively
matching unit or integration test. Active and archived change specs are outside
the current-contract index. Read
`docs/development/spec-test-traceability.md` before adding or changing a main
requirement or its tests.

- Obtain canonical requirement IDs with
  `uv run --locked python -m tools.spec_traceability list`; do not construct IDs
  manually.
- Import `covers_requirement` from `tools.spec_traceability` and apply it to the
  discoverable `test_*` function or method whose assertions establish the
  requirement. Arguments must be literal IDs.
- Run `uv run --locked python -m tools.spec_traceability check` while editing.
  Before handoff, run both required test entry points with the same
  `OPENSPEC_TEST_EVIDENCE` path, then run the verifier's `verify --evidence`
  mode.
- An annotation is a traceability claim, not a substitute for a behavior test.
  Never associate an unrelated, skipped, placeholder, or assertion-free test.
  There is no waiver or allowlist for an uncovered main requirement.
- When a genuine gap is found, keep it visible in the deterministic JSON report
  and add the missing test in the behavior change that owns the requirement.
  Do not enable or weaken the required CI workflow to bypass the gap.
- The final coverage gate measures branches in exactly `commands`, `server`,
  `typeclasses`, `web`, and `world`, omits only `*/tests/*`, combines the
  non-browser Evennia, managed browser, and top-level regression data files,
  and enforces a hard gate of at least 80% while targeting 90%.

## Container behavior

Use Podman Compose for container workflows (`podman compose build` and
`podman compose up`). Preserve the multi-stage, non-root, arbitrary-UID image
design and the persistent mounts for the SQLite database, logs, static/media
files, and art. Evennia's `start --log` still writes to `server/logs`, so that
volume is required. Ollama and sd-webui are external services configured by
environment variables; do not add them to this image.
