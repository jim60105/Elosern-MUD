# Elosern MUD Agent Guide

## Project

Elosern is an unreleased, single-player, adult, AI-driven MUD built on Evennia
6.1.0 and Python 3.13. The deterministic game must remain fully playable when
all LLM and image-generation services are offline.

Read `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` before planning
feature work. It is the architectural source of truth for every OpenSpec change;
if a change conflicts with it, the design document wins unless the change
explicitly amends the design.

## Start here

### Commands that always work

Copy these exactly; replace only the `<...>` part.

| Purpose | Command |
| --- | --- |
| One non-browser test module, class or method (`commands`, `server`, `typeclasses`, `world`, `web/webclient`, `web/gm`) | `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb <dotted.label>` |
| One repository-wide module under `tests/` | `uv run --locked python -m unittest tests.<module>` |
| One browser test (run `pnpm run build` first if any JS or Vue source changed) | `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.<file>.<Class>.<method>` |
| Vue component suite / one file | `pnpm test` / `pnpm exec vitest run <path>` |
| Dependency-free Node gate | `node --test web/static/webclient/js/tests/*.test.js` |
| Give a new, renamed, moved or deleted test its CI owner | `uv run --locked python -m tools.shard_register fix` |
| All cheap contracts before handoff (about 30 s; prints the repair for each failure) | `uv run --locked python -m tools.contract_gate` |
| Validate one OpenSpec change | `openspec validate <change> --strict` |

A hook (the Evennia test guard) inspects every shell command and blocks the
ones it cannot bound. It is deliberate: never work around it.

- Run a test command alone. Nothing may follow it: no `|`, `>`, `;`, here-doc,
  `$(...)` or `&`. Only `cd <dir> &&` may precede it. The tool already returns
  the output, so there is nothing to redirect.
- Never put a test command inside a script, `python -c`, `bash -c` or any other
  wrapper program.
- One command may discover at most 100 tests. Narrow the label instead of
  splitting a big run into batches.
- The guard also reads commands that only mention a test invocation (an `echo`,
  `printf` or here-doc that writes such text). Create those files with the
  file-writing tool, not the shell.
- `.env.evennia-test` is the committed opt-in file. Do not create another one;
  a task list that names `/tmp/mud-test.env` means this file.

### Where to work

Read the named guide before touching the directory. A package guide lists the
modules by task, so you do not have to read the package to find the owner.

| Task | Read first | Code and data |
| --- | --- | --- |
| A game rule or any state change | `world/rules/AGENTS.md` | `world/rules/`, numbers in `world/rules/rulebook/*.yaml` |
| An item, spell, monster, NPC or player preset | `docs/development/adding-items.md`, `adding-spells.md`, `adding-monsters.md`, `adding-npcs.md`, `adding-player-presets.md` | `world/lore/`, `world/skills/registry/` |
| NPC dialogue, voice lines, persona cards | `.agents/skills/npc-dialogue-content/SKILL.md` | named in the skill |
| Map, settlement or interior data | `.agents/skills/map-data-authoring/SKILL.md`, `world/maps/AGENTS.md` | `content/maps/` |
| Monster population, sites, field behaviour | `world/maps/AGENTS.md`, `docs/development/regional-monster-population.md`, `monster-field-behaviour.md` | `world/maps/`, `world/lore/monster_*.py` |
| Quests | `docs/gm/quests.md`, `docs/development/quest-generation-modes.md` | `world/quests/` |
| An LLM layer or a prompt | `world/ai/AGENTS.md`, `docs/development/llm-architecture.md` | `world/ai/`, `world/prompts/`, `prompts/` |
| Memory, recall, threads, dreams, letters | `world/narrative/AGENTS.md`, `docs/development/narrative-memory-and-recall.md` | `world/narrative/` |
| A player text command | the command-documentation rule below | `commands/`, `docs/game/commands.md`, `docs/game/command-reference.md` |
| A webclient panel or UI action (server side) | `docs/development/webclient-synchronization.md` | `web/webclient/presentation/` (one module per panel), `web/webclient/actions/` (one module per action family, allowlisted in `registry.py`) |
| Webclient UI (Vue) | `web/webclient-app/AGENTS.md`, `docs/development/frontend-developer-guide.md`, `hud-instrument-panels.md` (borderless HUD panel style) | `web/webclient-app/` |
| A browser acceptance test | `web/tests/browser/AGENTS.md` | `web/tests/browser/` |
| GM portal | `docs/development/gm-portal-runtime-inspection.md`, `gm-portal-world-data.md`, `gm-portal-saves.md` | `web/gm/`, `web/admin-app/`, `server/console/` |
| Settings and environment variables | `docs/development/settings-and-environment.md` | `server/conf/settings.py`, `.env.example` |
| Writing or restructuring tests | `docs/development/evennia-testing-guide.md` | `<package>/tests/`, `world/tests/synthetic_data/` |

`world/README.md` maps every package under `world/` to its ownership role.

### When something fails

| Symptom | What to do |
| --- | --- |
| "Evennia test guard blocked this command" | Re-run the bare command from the table above, with nothing before or after it. |
| `restricted to test commands`, or settings refuse to import | The opt-in is missing: use `--env-file=.env.evennia-test` as one token. |
| A contract test reports an unowned or stale shard label | `uv run --locked python -m tools.shard_register fix`, then commit the manifest with the test. |
| `content/map-reference-context.json is stale` | `uv run --locked python -m tools.map_reference_context`, then commit the file. It changes whenever a registry entry, quest, service host or monster placement row changes. |
| An uncovered requirement in the traceability gate | Annotate the test whose assertions establish it (see "OpenSpec test traceability"). Never annotate an unrelated test and never look for a waiver. |
| The test-data lint flags a test file | The test names shipped content. Rebuild it on `world.tests.synthetic_data`; do not add the file to the ledger. |
| The observability lint flags a line | Follow the "Observability" section; never add to `tools/observability_freeze.json`. |
| `MapWorldNotLoaded` or `SettlementNotLoaded` in a test | Nothing published the map world. Call `world.tests.geography_fixture.publish_shipped_map_world()` in setup; see `world/maps/AGENTS.md`. |
| A test passes alone and fails in the suite (or the reverse) | Shared mutable state leaked: a registry, a clock event source, an idmapper cache. See "檢查全域 mutable state" in `docs/development/evennia-testing-guide.md`. |
| A browser test fails locally after a JS fix | The served bundle is stale: `pnpm run build`. |
| A retained-database failure you cannot explain | Drop `--keepdb` and add `--noinput` once, or delete only `server/db/evennia-test.sqlite3`. |

### Choices already made

- Requirements and tests define logic, never game data. No scenario or test
  pins a specific settlement, population, coordinate, count or ID roster, so a
  data edit never needs a spec or test edit. A change that is only game data
  may ship without a spec.
- No test asserts real elapsed time or anything else that depends on hardware
  speed: CI runners are slow and uneven. Pin a performance fix with call
  counts, write counts or scheduling values, and benchmark in a throwaway
  script.
- Do not add a probe or gate whose every outcome is "continue anyway". Record
  the measurement without blocking and fix slowness in a follow-up.
- The standalone map editor is a developer-only tool: it takes the lowest
  implementation complexity that still keeps its guarantees (a status
  indicator and a server-side rejection instead of per-control UI state) and
  reuses the game's visual theme.

## Architectural invariants

- Preserve the single-writer boundary: it separates generative from
  deterministic, not `world/rules/` from every other directory. State changes
  are applied by the deterministic core — `world/rules/` (the primary,
  general-purpose engine) plus the sibling packages that own one persistent
  subsystem's own data directly (`world/maps/` for room/instance lifecycle,
  `world/quests/` for quest lifecycle, and `world/narrative/` for persistent
  narrative state: events, memory, threads, correspondence, attention/context
  snapshots, authoring records, beat scheduling; each such package is named
  explicitly here, not implied by proximity). `world/skills/` and `world/lore/` stay
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
- Character ages are reasonable-range values. Imports must reject any
  `age`/`apparent_age` outside `0..10000`; never weaken or bypass this bound.
- Import and action-resolution workflows are all-or-nothing. Validate before
  persistence and use transactions where partial state would be invalid.
- GM console domain verbs belong to `world/rules/gm.py`, `world/maps/gm.py`,
  `world/quests/gm.py`, and `world/narrative/gm.py`, each under its package's
  existing ownership. `server/console/raw.py` is the explicit raw repair
  exception for transactional Evennia Attributes, tags, and location; it
  bypasses rule validation, never edits typeclasses or other models.
- Manual patching of quest records, money, experience, inventory, and combat
  results happens only through the GM console, never a Django shell. The
  console takes an undo snapshot on the first write after process start and
  whenever in-game time differs from its saved baseline. Authored data remains
  source edited through git; this guidance does not add further domain verbs.
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
- `event` is a stable snake_case identifier in English. Prose (player input,
  letter bodies, dream text, prompts, model output) may ride `context`; every
  context value renders single-line and truncated at 200 characters. Full LLM
  payloads live in the transcript (`world/observability/transcript.py`,
  `server/logs/llm/`) keyed by `call_id`. Credentials (API keys, auth headers,
  URL userinfo) never enter any log or transcript. In-world knowledge
  boundaries (`private` visibility, memory/recall/thread access) are not
  logging rules and stay enforced. Exception chains ride `exc=` (any level
  renders a one-line `tb:` summary; `log_error` also double-writes the full
  traceback).
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

## uv workflow

Use uv 0.12.0 or newer for every Python environment and command. The interpreter
is pinned to Python 3.13 by `.python-version`, and `uv.lock` is authoritative.

### Frontend (pnpm)

The Vue 3 SPA webclient (view layer only) builds to `web/static/webclient/app/dist`
from `web/webclient-app/` sources plus locked pnpm dependencies. The pnpm toolchain
is a dev/CI-time dependency only (no runtime npm or pnpm dependency); the built page is
served entirely from the project origin. The Developer-only GM portal SPA
(`web/admin-app/`, mounted at `/gm/` by `web/gm/`) builds separately through
`vite.gm.config.js` (`pnpm run build:gm`) to `web/static/gm/dist`; it may import
only `styles/tokens.css` and `styles/fonts*.css` from the game tree (enforced by
`pnpm run test:gm-boundary`).

## NPC and dialogue content

- NPC authored dialogue, voice lines, and persona cards are strictly in-character
  (no OOC): an NPC never names a command, game mechanic, or UI element, and
  describes the world-side equivalent instead.
- Setting is JRPG 劍與魔法奇幻, never 中式武俠 vocabulary.
- Read `.agents/skills/npc-dialogue-content/SKILL.md` before writing or reviewing
  NPC content.

Webclient design direction and styling pitfalls live in
`web/webclient-app/AGENTS.md`; read it before changing webclient UI.

## Python-vs-pnpm split

- **Python gates (uv-managed):** the non-browser Evennia suite, top-level
  regression tests, and the aggregate Python branch-coverage gate (exact-root,
  ≥80%).
- **JS gates (pnpm/dev-time only):** the dependency-free Node gate
  (`node --test web/static/webclient/js/tests/*.test.js`), the Vitest component
  suite (`pnpm test`), and the Storybook component-coverage gate
  (`pnpm run build-storybook` + `pnpm run showcase-coverage`).
- The browser-test workspaces and the container image build the `dist` bundle
  from the authored sources plus locked pnpm dependencies (never hand-authored).

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
  yours. Do not edit the manifest by hand: run
  `uv run --locked python -m tools.shard_register fix` (it also covers
  `.github/browser-shards.json` and `.github/top-level-shards.json`), then
  verify with `uv run --locked python -m tools.contract_gate manifests contracts`.
  A module under a package label (`server`) is already owned and must not get
  its own label; the tool knows this.
- Evennia test commands take the opt-in through the committed file as one
  token, `--env-file=.env.evennia-test`: the Evennia test guard rejects both an
  inline `MUD_TEST_SETTINGS=1 ...` prefix and the two-token `--env-file <file>`
  form.
- Before handoff or archive, run `uv run --locked python -m tools.contract_gate`
  (traceability, the two lints, shard manifests, and the shard-ownership and
  frozen-audit contracts; seconds). It is not a test run to skip; CI preflight
  reuses it. On a feature worktree before archive sync, add `--change <change>`
  so traceability tolerates only requirements that change's delta removes or
  renames; never pass it after the sync.
- The full non-browser Evennia suite is allowed once only when needed, under 10
  minutes, and run with `--parallel 16 --noinput`; never run it serially.
- The full managed browser suite and `tools.spec_traceability verify --evidence`
  are CI-only. Local browser testing uses one class or file within the budget.
- Do not run CI shard commands locally. They share database and pidfile paths.
- `tools.spec_traceability check` is the local traceability gate.
- A browser test file that exceeds five minutes in CI must be split.
- Browser tests: pick the specific affected `def test_` methods (or one class or
  file) and run each batch as its own short command, e.g.
  `uv run --locked python -m web.tests.browser.unittest_driver <mod>.<Class>.<test> ...`
  with output captured to a scratch file. Never loop over many whole
  `web/tests/browser/*` files in one command.
- Every new browser test class or method under `web/tests/browser/` MUST be added
  to `.github/browser-shards.json` in the same feature commit
  (`uv run --locked python -m tools.shard_register fix` does it).
  `tests.test_evennia_test_optimization_contract`
  (`test_browser_method_labels_preserve_exact_ownership`) enforces exact
  ownership; the workflow's inline validator checks structure only, so registration
  is not optional. Before archive, run `tests.test_evennia_test_optimization_contract`
  and `tests.test_webclient_frozen_contract` even when other tests are skipped. If a
  blocker (such as foreign uncommitted edits to the manifest) forced a deferral,
  re-check it right before merge.
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

Behavior tests resolve game data through the synthetic test-data kit or
file-local synthetic fixtures; only tagged data-contract tests (first docstring
line `Data-contract test: <rationale>`, registered in
`tools/test_data_freeze.json`) may name shipped content. The gate is
`uv run --locked python -m tools.test_data_lint check`. Assertions establish
mechanics rather than echo fixture or registry content; data-echo tests are
replaced, not multiplied (the aggregate coverage gate stays a floor, not a
target).

Keep each assertion's role and detectable defect explicit. Generic production
integrity checks retain identity, references, recipient/hit topology, schema
bounds and intentional quality relationships. Mutable balance magnitudes belong
to the authored declarations, with no second approval table.

Shared synthetic mechanism tests use fixed inputs and independently known
outcomes. A target with MP 3, requested drain 10 and full recovery share leaves
the target at 0 and a caster starting at MP 20 with cost 10 at 13. That assertion
detects recovery credited on requested loss. Never obtain expected arithmetic
by calling the calculator under test or copying its formula into a helper.

Representative production smoke executes a distinct consumer boundary through
real construction, selection, payment, resolution and committed reload. Reading
the declared profile and observing stored literal bases detects wrong source
selection or baked multipliers; it does not establish calculation correctness.
Keep untouched recipient controls and fault injection after relevant writes or
practice claims. Classification tags and requirement decorators carry claims,
so maintain their matching ledger/seed reasons and meaningful assertions.

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
- When spawning an apply worker, state the exact branch `feat/<change-slug>` and
  worktree `.worktrees/<change-slug>` in its assignment; otherwise `os-phase`
  cannot see the change (it shows it as `proposed` plus an orphan
  `archived-unmerged` branch and blocks the pre-archive gate).
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
