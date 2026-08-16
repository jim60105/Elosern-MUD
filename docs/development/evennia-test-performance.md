# Evennia Test Performance

This report records the measured basis for the `optimize-evennia-testing`
change. Durations are reference-machine observations, not portable limits. The
general optimization playbook lives in the
[Evennia 測試效能優化指南](evennia-testing-guide).

## Environment

- Baseline commit: `d258ed7b65fb0e2e2d461c16b2ca806f76fe3fa8`
- Optimized revision identity: dirty worktree branch
  `feat/optimize-evennia-testing`, based on
  `d258ed7b65fb0e2e2d461c16b2ca806f76fe3fa8`; replace this provisional identity
  with the eventual commit SHA when these reviewed changes are committed
- Python: 3.13.14
- Evennia: 6.1.0
- Django: 6.0.7
- uv: 0.12.0
- Logical processors: 24
- `uv.lock` SHA-256: `bd909fdaa68a4aa76ba72897f0e568b1a58f579e425be58c1f2e25fa8defec1b`
- Coverage instrumentation: disabled for performance runs
- Target ownership: `commands server typeclasses world web.webclient`
- Database state: serial `--keepdb` with the same migrations, fixtures, target
  set, and warm-up protocol. The baseline defaulted to an in-memory database,
  so it rebuilt schema on each process despite `--keepdb`; the optimized
  storage profile uses the dedicated file named by
  `DATABASES["default"]["TEST"]["NAME"]` and reuses its warm schema. This
  recorded storage difference is an intentional optimization variable.

## Runner Verification

The pinned Evennia launcher forwards the exact `test` operation and unknown
options to Django's runner. Direct probes verified dotted module/class/method
labels, `--keepdb`, `--noinput`, `--timing`, and `--durations`. Both `--parallel 4` and bare
`--parallel` are accepted by Django 6.0; their suitability is evaluated below.
The test settings guard requires the operation argument at `sys.argv[1]` to be
exactly `test` together with `MUD_TEST_SETTINGS=1`; later arguments containing
that token cannot authorize a server or migration command.

The source-note suggestion to combine `:memory:` with `--keepdb` is rejected:
an in-memory database cannot survive process exit. The source-note suggestion
to enable parallel workers unconditionally is also rejected unless evidence,
coverage, resource isolation, and repeated timing are equivalent.

## Baseline

Command:

```sh
uv run --locked evennia test --settings settings.py --keepdb --timing \
  --durations 20 commands server typeclasses world web.webclient
```

One warm-up and three measured serial runs all passed 1,146 tests.

| Run | Test time | Database setup | Total time | Result |
|---|---:|---:|---:|---|
| Warm-up | 515.414 s | 2.551 s | 519.151 s | Pass |
| Measured 1 | 514.764 s | 2.339 s | 518.046 s | Pass |
| Measured 2 | 519.437 s | 2.515 s | 522.980 s | Pass |
| Measured 3 | 516.756 s | 2.510 s | 520.285 s | Pass |

The measured median is **520.285 seconds**.

The slowest tests were consistently integration journeys in
`test_onboarding_journey.py` and `test_phase4_integration.py`, around 1.47 to
1.92 seconds each. They exercise real typeclasses, commands, transactions, and
guild/combat state, so fixture removal would change the tested boundary.

## Fixture Inventory

Before conversion, 84 test files imported `EvenniaTest`, 66 files declared a
direct `EvenniaTest` class, 9 files used `EvenniaCommandTestMixin`, 53 files
declared `setUp()`, and no file used `EvenniaTestCase` or `setUpTestData()`.
The WebClient ownership scan found six non-browser files under
`web/webclient/**/test*.py` and five managed browser files under
`web/tests/browser/test*.py` at the baseline SHA. The sets are disjoint and
their union is every Python test under `web`.

The first safe optimization batch moves seven pure parser, AST, and YAML tests
off full-world fixtures:

- `RegistrationBoundaryScanTests`
- `InstanceYamlTests`
- two storage tests in `CombatSessionRecordTests`
- `ExamRecordTests`

The database-backed deterministic session-ID method remains in a separate
`EvenniaTest` class. No class-level mutable fixtures or external-I/O mocks were
introduced because the measured candidates did not justify them.

## Optimized Results

The optimized revision was measured from this worktree after the test-only
settings, fixture batch, and disjoint ownership changes. One warm-up and three
measured serial runs all passed the same 1,146 tests.

| Run | Test time | Database setup | Total time | Result |
|---|---:|---:|---:|---|
| Warm-up | 353.774 s | 0.549 s | 355.384 s | Pass |
| Measured 1 | 353.021 s | 0.418 s | 354.432 s | Pass |
| Measured 2 | 352.608 s | 0.591 s | 354.189 s | Pass |
| Measured 3 | 355.937 s | 0.480 s | 357.400 s | Pass |

The optimized median is **354.432 seconds**, a **31.9% reduction** from the
520.285-second baseline median. It passes the 416.228-second acceptance
threshold. A focused clean-database run passed, and two consecutive retained
focused runs reduced database setup from 3.086 seconds on initial creation to
0.463 seconds on reuse while leaving the developer database untouched.

## Parallel Evaluation

The first retained `--parallel 4` run passed all 1,146 tests in 60.395 seconds.
The immediately repeated run was not stable: shared monster-skill registry
state caused `test_depleted_resource_falls_back_to_basic_attack` to receive
`shadow_slash` instead of `basic_attack`, after which Django could not pickle
the failure traceback from its worker. This is a correctness, isolation, and
diagnostic failure, so parallel execution is rejected without spending more
time on bare `--parallel`, clean-clone, evidence, or subprocess-coverage runs.

### 2026-08-11: Quality-gate stabilization and parallel CI adoption

The quality gate previously ran the entire non-browser Evennia suite serially
with coverage in one job: at 3,004 tests this took **2,385 s (~40 min)** in CI
and failed on two consecutive merges with order-dependent registry leaks. This
change fixed the isolation defects, proved parallel equivalence, adopted the
parallel profile in CI, and raised the aggregate coverage above the gate.

**Isolation defects fixed (root causes of the CI failures):**

- `OnboardingHuntIntegrationTests` ran `sync_guild_economy()` and restored only
  `QUEST_DEFINITION_REGISTRY`, leaking the canonical `introductory_hunt` offer
  into the process-global `GUILD_OFFER_REGISTRY`; a later test's conflicting
  `×1` registration then raised `GuildOfferError`. All three registries
  (`QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`,
  `SCENE_REQUIREMENT_REGISTRY`) are now snapshotted and restored through one
  reusable `RegistryIsolationMixin` (`world/quests/tests/_fixtures.py`) whose
  restoration is registered via `addCleanup` before any mutation, so a failing
  `setUp` cannot leak either.
- `test_scenario_director` cleared the three registries destructively without
  restoring prior contents; those sites now use the mixin. The cold-start
  module re-import test restored `sys.modules` but not the `world.ai` package
  attributes, invalidating module identity for later tests; both are restored
  now.
- `test_clock` reloaded `world.rules.clock` in place, invalidating every class
  identity other modules bound at import time; the module-level interval
  validation was extracted into `_validate_settlement_intervals()` and the test
  calls it directly instead of reloading.
- Combat tests left stale entries in the process-global skip-safety
  `_BATTLEFIELDS` registry (keyed by entity keys that Evennia's fixtures reuse,
  e.g. every `char1` is `"Char"`), and tests calling `at_server_start()` or
  `sync_guild_economy()` re-registered abandoned combat sessions. A
  `BattlefieldIsolation` mixin now snapshots/restores `_BATTLEFIELDS` in every
  combat-touching class and in every sync/startup caller.
- Several classes reached the affinity-rulebook load (which resolves
  `introductory_hunt`) without registering the quest catalog in their own
  setup, failing on whatever worker ran them first; each now calls
  `register_catalog()` in its own `setUp`.

**Equivalence evidence (3,007 tests at the time, 3,104 after the coverage
tests):** plain `--parallel 4` twice consecutively, `--shuffle 42`, `-r`
(reversed), and additional `--parallel 16` runs all passed green. Requirement
evidence collected under parallel workers combines into a parseable JSONL with
no interleaved lines. Subprocess coverage (`coverage run
--concurrency=multiprocessing --parallel-mode`) produces one sidecar per
worker; `coverage combine` merges them and the combined report keeps the exact
`commands server typeclasses web world` roots.

**Wall time (CI-relevant profile):** the full non-browser Evennia suite runs in
~152 s with `--parallel 4` including coverage instrumentation, versus the
2,385 s serial CI step — an ~15x speedup. On the 24-core development machine
`--parallel 16` runs the suite in ~45 s. The managed browser suite (148 tests,
one real Evennia server per shard process, combat tests booting a dedicated
server per test) was measured at 3,465 s (~58 min) locally and is sharded
across six CI jobs by a committed manifest (`.github/browser-shards.json`);
each shard remains the sole serial owner of its files, and a top-level
regression test asserts every discovered browser test file belongs to exactly
one shard.

**Coverage:** the full three-entry-point aggregate (complete non-browser
Evennia suite with subprocess coverage, complete managed browser suite, and
the top-level regression suite) measured 88% at the start of this change and
**91.06%** after adding focused tests for the largest uncovered branches in
`commands/localized/` (account, general, help, xyzgrid commands), the
scenario-director dataclass/validator shapes, the quest compile boundary,
guild config/exam validation, buff definition validation, and the character
creation panel. The browser suite's parent process contributes no measurable
coverage to the five roots (the game code executes in the managed server
subprocess), so the aggregate is dominated by the non-browser Evennia suite —
exactly as the gate computed it before.

**CI adoption:** the single quality-gate job became five: a fast `preflight`
job (OpenSpec validation, static traceability checks, Node suite, shard-matrix
computation), the `evennia` job (parallel profile with subprocess coverage),
the six `browser` matrix shards, the `top-level` job, and a `gate` job that
downloads every artifact, validates that each expected coverage and evidence
artifact arrived non-empty, concatenates the evidence files in entry-point
order, runs `spec_traceability verify`, combines every uploaded sidecar with
`coverage combine`, verifies the coverage roots, enforces the aggregate 80%
branch gate, and publishes Codecov XML from the combined data only. Serial
execution remains the canonical final-handoff evidence profile.

### 2026-08: Parallel adopted after isolation fixes

At 2,525 tests the serial suite had grown to ~1,033 s. Parallel was
re-evaluated and the root causes of every observed failure were fixed:

- **Non-deterministic dice tie-break**: the mid-tier `pack_hunter` monster
  profile picks skills by highest expected damage, and two affordable
  single-target physical skills tie, so `_choose_skill` resolves the tie with
  `dice.roll_d100()`. The unseeded global PRNG state differs per worker, so
  `test_depleted_resource_falls_back_and_resolves` and
  `test_unaffordable_preference_falls_back_to_affordable_skill` asserted
  `shadow_slash` but occasionally received `basic_attack`. Both tests now pin
  the tie-break roll with `patch("world.rules.monster_behaviour.dice.roll_d100", return_value=0)`.
- **Unpicklable failure tracebacks**: `tblib` (3.2.2) was added as a dev
  dependency so Django can pickle worker tracebacks; failures are now
  diagnosable in parallel mode.
- **Shared-rulebook file race**: `AffinityConfigValidationTests` rewrote
  `world/rules/rulebook/affinity.yaml` in place and restored it in
  `tearDown`; parallel workers raced on the file and read deviant floors.
  `load_config(path=...)` now accepts an explicit rulebook path and the tests
  exercise deviant rulebooks from `TemporaryDirectory` copies. The shared
  source file is never rewritten.
- **Process-global quest/catalog registry leaks**: several test classes
  registered `QUEST_DEFINITION_REGISTRY`/`GUILD_OFFER_REGISTRY`/`CATALOG`
  without snapshot-restore (or snapshot after registering), leaking
  `introductory_hunt` into whichever worker ran them. Fixed in
  `test_onboarding_journey`, `test_guild_config`, `test_dialogue`,
  `test_service_view`, `test_service_view_side_effects`,
  `test_guild_economy_sync`, `test_party_offline_loop`,
  `test_guild_registration`, and the converted `web.webclient` presenter/action
  classes. The compile-boundary tests now assert registry-unchanged relative
  to their own setUp snapshot instead of a literal empty registry, which is
  the semantically correct contract.
- **Read-path database write**: `map_knowledge._registered_grid_bounds` called
  the xyzgrid contrib's `get_xyzgrid()`, which creates the global `XYZGrid`
  script on a pure read. A pure `unittest.TestCase` runs with autocommit, so a
  grammar test permanently committed the script and poisoned every later
  `--keepdb` bootstrap run. The lookup now returns `None` when no grid has
  been provisioned, so validation paths never write the database.
- **Fixture-heavy presenter tests**: the `web.webclient` presentation and
  action adapter classes (213 methods, ~1.8 s each because every test paid for
  `sync_grid()`/`sync_wilderness()`) moved from `EvenniaTest` to
  `EvenniaTestCase` with the expensive grid/wilderness/catalog sync hoisted to
  class level and per-test entity creation. They now run in ~13 s serial and
  are parallel-safe.

Evidence runs (full 2,525-test suite, `--parallel 4 --noinput`, twice
consecutively):

| Run | Test time | Total time | Result |
|---|---:|---:|---|
| Parallel 1 | 125.423 s | 129.525 s | Pass |
| Parallel 2 | 125.149 s | 129.153 s | Pass |

This is an **~8.2x speedup** over the 1,033 s serial baseline. Serial remains
canonical for final handoff evidence; the converted and newly isolated test
classes also pass the full serial suite (measured 1,006–1,054 s across runs,
with the same 1,146-test set at 354 s in the earlier phase-1 report). The
retained `--keepdb` database stays clean after full runs: the
`world.maps.tests.test_bootstrap` fresh-grid precondition now passes on
repeated consecutive runs.

Serial execution remains the handoff standard, but `--parallel 16 --noinput`
is the documented default full-suite command during development (CI keeps
`--parallel 4` as its worker profile). Removing
duplicate managed-browser discovery is accepted
separately only after the final serial evidence and aggregate coverage run
passes.

The final clean coverage probe also confirmed that an existing retained SQLite
file causes Django to request deletion confirmation. Canonical non-interactive
clean commands therefore pass `--noinput`; this permits replacement of only the
dedicated test database and avoids an `EOFError` in CI.

### 2026-08-16: Evennia suite machine-sharded across six CI jobs

The single CI evennia job (one `ubuntu-latest` runner executing the whole
non-browser suite, **14 m 02 s** in run 31939321935) was replaced by a six-job
matrix driven by `.github/evennia-shards.json`. Each shard runs its manifest
labels on its own runner with the same worker profile (`--parallel 4`,
subprocess coverage), writes `coverage-evennia-shard-<n>*` and
`evidence.evennia-shard-<n>.jsonl`, and uploads them as per-shard artifacts.
The gate loops over the manifest indices for completeness, concatenates
`evidence.evennia-shard-*.jsonl` with the browser and top-level evidence, and
combines `coverage-evennia*` sidecars with the rest — aggregation semantics
unchanged. This targets cutting the evennia job from ~14 min to ~2–4 min and
off the CI critical path at zero cost on the public Free plan (6 additional
`ubuntu-latest` jobs; total evennia+browser jobs stay ≤ 20).

**Suite size (2026-08-16):** the non-browser Evennia suite now discovers
**4,263 tests** (grown from the 3,104 recorded in the 2026-08-11 CI adoption
after the intervening feature and catalog changes), 267 test modules across
`commands`, `server`, `typeclasses`, `world`, and `web.webclient`.

**Manifest split and local serial timing** (24-core reference machine,
`--keepdb`, no coverage; CI runs the same labels with `--parallel 4`):

| Shard | Labels | Tests | Serial test time | Serial wall time |
|---|---|---:|---:|---:|
| 1 rules-a | 38 `world.rules.tests` modules | 650 | 137.6 s | ~2:40 |
| 2 rules-b | 37 `world.rules.tests` modules | 596 | 163.0 s | 2:47 |
| 3 rules-c | 37 `world.rules.tests` modules | 574 | 96.2 s | 1:39 |
| 4 | `world.quests world.skills world.art world.ai world.onboarding world.lore` | 1,154 | 171.7 s | 2:55 |
| 5 | `world.maps web.webclient world.imports world.prompts world.tests` | 817 | 153.3 s | 2:36 |
| 6 | `commands server typeclasses` | 472 | 118.0 s | 2:01 |
One rebalance pass was applied after the first measurement: the initial
package grouping produced a 19 s shard and a ~226 s shard (max/mean ≈ 1.6);
moving `web.webclient` away from `commands`/`typeclasses` (whose combined run
is ~2× the sum of parts) and pairing `world.quests` with lightweight packages
brought max/mean to **1.23** (172 s / 140 s mean), below the 1.35 rebalance
threshold.

**First CI observation (run 31945742664, branch `feat/split-evennia-ci-shards`,
green on the first try):**

| Job | Duration |
|---|---:|
| preflight | 24 s |
| evennia shard 1 (rules-a) | 2 m 10 s |
| evennia shard 2 (rules-b) | 2 m 46 s |
| evennia shard 3 (rules-c) | 1 m 39 s |
| evennia shard 4 (quests-skills-art-ai-onboarding-lore) | 2 m 23 s |
| evennia shard 5 (maps-webclient-imports-prompts-tests) | 2 m 8 s |
| evennia shard 6 (commands-server-typeclasses) | 1 m 40 s |
| top-level | 23 s |
| browser shard 1 (combat) | 19 m 10 s |
| browser shard 2 (creation-layout) | 16 m 31 s |
| browser shard 3 (exploration-reconnect) | 13 m 4 s |
| browser shard 4 (shell-actions-local-map-input-narrative) | 5 m 23 s |
| browser shard 5 (services-pointer) | 16 m 26 s |
| browser shard 6 (art-harness) | 11 m 36 s |
| gate | 23 s |

The evennia suite is now off the CI critical path: its worst shard (2 m 46 s)
replaces the previous single-job 14 m 02 s, and the six shards finish within a
max/median of 1.29 (166 s / 129 s), below the ≥ 2× rebalance threshold, so no
further rebalance was needed. Total workflow wall time is still ~20 min only
because the managed browser suite dominates (combat 19 m 10 s); that half is
addressed by the sibling `pack-browser-ci-shards` change.

### 2026-08-16: Browser suite packed into 11 two-process shards

The six browser jobs (each one `unittest` process, file-level manifest labels)
were replaced by **11 jobs × 2 isolated processes**. Each browser shard checks
out the repository twice (`w-a` and `w-b`) because the Evennia launcher writes
GAMEDIR-relative pidfiles (`server/server.pid`, `server/portal.pid`); two
harnesses in one working tree would race on them and kill each other's
processes. The second checkout is cheap (repo pack ~5 MB).

- `.github/browser-shards.json` now carries 11 shards, each with two process
  lists `files_a`/`files_b` of module/class/method dotted labels. Combat tests
  (per-test server boot, ~50 s each) are split at method level across five
  lists of 4–5 tests; creation and services classes split at class level;
  exploration and art split at method level; the cheap shell-family files pack
  whole into one or two lists. Every process list targets ≤ 240 s estimated
  from the measured per-test weights (combat ~50 s, creation/layout ~38 s,
  services/pointer ~47 s, exploration/reconnect ~40 s, art/harness ~36 s,
  shell family ~6.4 s).
- The `browser` job runs its two `unittest` invocations as parallel background
  processes with inline per-process `COVERAGE_FILE`
  (`coverage-browser-shard-<n>-p1`/`-p2`) and
  `OPENSPEC_TEST_EVIDENCE` (`evidence.browser-shard-<n>-p1.jsonl`/`-p2.jsonl`),
  waits on both with guarded `wait "$pid" || status=$?` (GitHub's `set -e`
  aborts on a failing bare `wait`), concatenates the two evidence files
  A-then-B into `evidence.browser-shard-<n>.jsonl`, copies both coverage files
  to the job root, and fails the step unless both statuses are zero. No
  `|| true`, no `continue-on-error`.
- The gate's aggregation contract is unchanged: per-shard artifacts keep the
  `coverage-browser-shard-<n>*` and `evidence.browser-shard-<n>.jsonl` names,
  the completeness loop, evidence concatenation, and `coverage combine
  coverage-browser-shard-*` all work index-based. The 20-slot concurrent-job
  ceiling counts jobs, not processes: 1 preflight + 6 evennia + 11 browser + 1
  top-level + 1 gate = 20.
- The browser ownership contract test moved from file-level to **method-level
  partition** (AST-based, import-free): every `test_*` method of every
  `web/tests/browser/test_*.py` file is owned by exactly one of the 22 process
  lists. Rebalancing after future CI observations is a manifest edit plus the
  contract tests, not a workflow edit.

Expected effect: the combat shard's 19 m 09 s splits across ~5 parallel
process lists (~4–5 min each), bringing the browser critical path to ~5–6 min
and total quality-gate wall time under 10 min together with the evennia
machine sharding. First CI observation (branch `feat/pack-browser-ci-shards`)
recorded in a later run; if any process list dominates (≥ 2× the median or
> 7 min), rebalance the manifest once and re-record.
