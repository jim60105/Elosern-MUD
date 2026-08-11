# Stabilize and Accelerate the Quality Gate

## Why

The quality-gate CI has failed on two consecutive feature merges: the
non-browser Evennia suite errors with
`GuildOfferError: conflicting offer 'introductory_hunt' already registered for
branch 'guild_branch_altoria'` because `OnboardingHuntIntegrationTests` leaks
the catalog offer into the process-global `GUILD_OFFER_REGISTRY`, which
`CapBreakTurnInTests.setUp` then trips over. A second latent isolation bug
(unrestored registry `clear()` in `test_scenario_director`) breaks the
parallel profile the repository already documents as its development default.
Meanwhile the gate takes about 1h43m (~62 min browser, ~40 min serial Evennia)
and the last green run sat at exactly 90% aggregate coverage, leaving no
margin for the scene-flavor and affinity code that landed since.

## What Changes

- Fix test isolation at the three confirmed leak sites and any additional
  order-dependent tests the audit surfaces:
  - `world/maps/tests/test_wilderness_population.py::OnboardingHuntIntegrationTests`
    snapshots/restores `GUILD_OFFER_REGISTRY` around its `sync_guild_economy()`
    calls, mirroring the established isolation pattern.
  - `world/ai/tests/test_scenario_director.py` replaces its three destructive
    registry `clear()` calls with snapshot/restore of
    `QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`, and
    `SCENE_REQUIREMENT_REGISTRY`.
  - `typeclasses/tests/test_appearance.py::DisplayedStatsBlockTests` registers
    the quest catalog in its own `setUp` instead of relying on a previous test
    to have done so.
  - A regression test proves the leak fix (cap-break turn-in setUp succeeds
    after a `sync_guild_economy()` run in the same process).
- Accelerate the CI quality gate:
  - The non-browser Evennia suite runs with `--parallel 4` and subprocess-aware
    coverage (`coverage run --concurrency=multiprocessing --parallel-mode`),
    replacing the 40-minute serial step. The mechanism is already validated
    locally: 3,004 tests in 202s with coverage, vs 2,385s serial in CI.
  - The managed browser suite is sharded across parallel CI jobs (by test
    file, balancing the per-test server boots of the combat files); each shard
    stays the sole serial owner of its files, and coverage plus traceability
    evidence are uploaded and aggregated exactly once.
  - A final gate job combines all coverage files, verifies coverage roots and
    the 90% aggregate threshold, verifies requirement execution evidence, and
    publishes Codecov XML from the combined data.
- Raise the measured coverage: measure the combined aggregate, then add
  focused tests for the biggest uncovered branches in the newest modules
  (scene flavor, characterization, scene builder, affinity cap-break,
  scenario-director additions) to land comfortably above the 90% gate with a
  real margin.
- Update the performance report (`docs/development/evennia-test-performance.md`),
  the testing guide, and `AGENTS.md` with the new CI profile and measurements.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `evennia-test-optimization`: Requirement changes cover (1) a new isolation
  contract — any test that mutates a process-global registry must restore it
  to its pre-test contents; (2) parallel execution moving from "optional and
  gated" to the canonical non-browser profile once equivalence is proven, with
  CI adopting it; (3) the quality-gate requirements being amended so the
  managed browser suite may be executed once across parallel CI jobs with a
  single aggregated evidence and coverage result.

## Impact

- Test isolation fixes in `world/maps/tests/test_wilderness_population.py`,
  `world/ai/tests/test_scenario_director.py`,
  `typeclasses/tests/test_appearance.py`, plus audit-driven fixes in any other
  order-dependent test files; a new regression test near the cap-break tests.
- `.github/workflows/quality-gate.yml` restructured into parallel jobs with
  coverage/evidence artifacts and a final aggregation job; the non-browser
  Evennia step gains `--parallel 4` and multiprocessing-aware coverage flags.
- New coverage tests under the affected packages (pure-logic and
  lightweight-fixture tests per the fixture guidance; no assertion weakening
  and no skipped-test shortcuts).
- Documentation: `docs/development/evennia-test-performance.md`,
  `docs/development/evennia-testing-guide.md`, `AGENTS.md`.
- No production code behavior changes; no dependency changes; no
  backward-compatibility or migration concerns (project is unreleased).
