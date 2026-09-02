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

## Observability

- All game-code operational logging goes through the `world.observability`
  facade (`log_debug`/`log_info`/`log_warn`/`log_error`). Importing the Evennia
  logger or stdlib `logging` in production modules is forbidden and enforced by
  `uv run --locked python -m tools.observability_lint check`. Production code
  uses named imports (`from world.observability import log_warn`); event
  assertions in tests patch the caller module's binding, never
  `world.observability.*`.
- `event` is a stable snake_case identifier in English; player-facing prose
  never enters logs. Exception chains ride `exc=` (any level renders a one-line
  `tb:` summary; `log_error` also double-writes the full traceback).
- Every call carries a `context` dict; put every business identifier available
  at the site (`room`, `tick`, `layer`, `quest`, `job`, `char`, `step`, ...) in
  context keys instead of the message text.
- An `except` block must do exactly one of three things: re-raise, emit a
  facade event with the exception, or carry a reasoned exemption comment
  (`# observability: ignore R2: <reason>`). Silent swallowing is a lint
  violation in facade-adopter files.
- Normal paths leave traces: any new or changed persistent state change,
  external I/O, or cross-system workflow emits its boundary info event per the
  catalog in
  `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4
  (`cmd_in`/`cmd_done`, `startup_step`, `action_commit`, `clock_advance`,
  `llm_call`, worker settlement events, ...).
- Whenever a logging code path changes, run the observability lint plus the
  focused tests in the same batch. The freeze list
  `tools/observability_freeze.json` is shrink-only: migrating a file removes
  its entry in the same change, never adds one.

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
uv run --locked -m world.imports.validate world/imports/examples/example_character.json
uv run --locked python -m compileall -q world typeclasses commands server
```

### Frontend (npm)

The Vue 3 SPA webclient (view layer only) builds to `web/static/webclient/app/dist`
from `web/webclient-app/` sources plus locked npm dependencies. The npm toolchain
is a dev/CI-time dependency only (no runtime npm dependency); the built page is
served entirely from the project origin.

```sh
npm ci --no-audit --no-fund
npm run build
npm test
npm run build-storybook
npm run showcase-coverage
```

- `npm run build` → the Vite production bundle (`web/static/webclient/app/dist`).
- `npm test` → the Vitest component suite under `web/webclient-app/tests/`.
- `npm run build-storybook` → the offline component showcase (Storybook).
- `npm run showcase-coverage` → the component-coverage check against the frozen
  required-set manifest.

## Python-vs-npm split

- **Python gates (uv-managed):** the non-browser Evennia suite, top-level
  regression tests, and the aggregate Python branch-coverage gate (exact-root,
  ≥80%).
- **JS gates (npm/dev-time only):** the dependency-free Node gate
  (`node --test web/static/webclient/js/tests/*.test.js`), the Vitest component
  suite (`npm test`), and the Storybook component-coverage gate
  (`npm run build-storybook` + `npm run showcase-coverage`).
- The browser-test workspaces and the container image build the `dist` bundle
  from the authored sources plus locked npm dependencies (never hand-authored).

The Evennia commands run non-browser package tests. Managed Playwright tests,
repository-wide contracts, and complete evidence verification are CI-owned.
The retained database is `server/db/evennia-test.sqlite3`; after migration
changes or unexplained retained-state failures, omit `--keepdb` and add
`--noinput`, or remove only that file.

### Testing

- Run the smallest focused test label, Node file, or browser class that covers
  the change. A local command estimated above 10 minutes is forbidden.
- Every non-browser test module under `commands`, `server`, `typeclasses`,
  `world`, or `web/webclient` must be registered in exactly one shard of
  `.github/evennia-shards.json`. Adding, renaming, or moving a test module MUST
  update that manifest in the same change, or the CI ownership contract
  (`tests.test_evennia_test_optimization_contract`) fails on every branch after
  yours. Verify locally with
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`.
- The full non-browser Evennia suite is allowed once only when needed, under 10
  minutes, and run with `--parallel 16 --noinput`; never run it serially.
- The full managed browser suite and `tools.spec_traceability verify --evidence`
  are CI-only. Local browser testing uses one class or file within the budget.
- Do not run CI shard commands locally. They share database and pidfile paths.
- Node tests (`node --test web/static/webclient/js/tests/*.test.js`) are fast;
  `tools.spec_traceability check` is the local traceability gate.
- JS gates: the dependency-free Node gate, the Vitest component suite
  (`npm test`), and the Storybook build + component-coverage
  (`npm run build-storybook`, `npm run showcase-coverage`) are the applicable JS
  gates. The full managed browser suite, `tools.spec_traceability verify
  --evidence`, and the aggregate Python branch-coverage gate are CI-owned.
- A browser test file that exceeds five minutes in CI must be split.
- Save CPU time: capture a long command's output to a temp file once, then inspect that file with whichever read or search tool is available — the `read` tool, `grep` (`rg`), or `bash` (`head`/`tail`/`sed`/`awk`). Do not re-run the test just to recapture its output.

See `docs/development/evennia-test-performance.md` and
`docs/development/evennia-testing-guide.md` before broadening or restructuring
test runs.

For guidance on why tests get slow and how to keep them fast — fixture
selection (`unittest.TestCase` / `EvenniaTestCase` / `EvenniaTest` /
`EvenniaCommandTest`), `setUpTestData()` and `subTest()` reuse, `--keepdb` and
`--parallel`, mocking external I/O, and isolation debugging — read
`docs/development/evennia-testing-guide.md` before adding or restructuring
tests.

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
  Local handoff uses focused tests; CI owns complete `verify --evidence`.
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

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
