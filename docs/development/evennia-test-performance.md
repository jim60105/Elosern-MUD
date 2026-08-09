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

Serial execution remains the handoff standard, but `--parallel 4 --noinput`
is the documented default full-suite command during development. Removing
duplicate managed-browser discovery is accepted
separately only after the final serial evidence and aggregate coverage run
passes.

The final clean coverage probe also confirmed that an existing retained SQLite
file causes Django to request deletion confirmation. Canonical non-interactive
clean commands therefore pass `--noinput`; this permits replacement of only the
dedicated test database and avoids an `EOFError` in CI.
