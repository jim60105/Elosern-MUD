# Tasks

"The test prefix" means `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`. Run each test command standalone (no pipe, no redirect), with one dotted label.
Do not add `covers_requirement` for the ADDED requirement of this change; that happens at archive. Tests of the three MODIFIED requirements keep or receive the existing identifiers already used in `world/maps/tests/test_population_drain.py`.
No test may sleep, start a timer or assert elapsed real time. Work is bounded and asserted by counts (steps, events, calls).
Tests use the synthetic two-zone world of `DrainFixture` only.
Do not edit `world/maps/population_lifecycle.py`, `world/maps/monster_activity.py`, `world/maps/regional_population.py`, or the signatures and results of `lagging_sets` and `build_scope`.

## 1. Preconditions

- [ ] 1.1 Confirm the baseline and the earlier changes are merged. Verify: `grep -c "_AREA_UNITS = SourceMemo()" world/maps/population_units.py` prints 1 (commit `c0736d44`), `grep -c "POPULATION_DRAIN_IDLE_SECONDS" world/maps/population_drain.py` prints 1 or more (`population-drain-idle-gate`), and `grep -c "def scope_part_units" world/maps/monster_activity.py` prints 1 (`population-snapshot-part-scoping`). If any prints 0, stop and report.

## 2. Shared group units

- [ ] 2.1 Apply design D3 to `world/maps/population_units.py`. Verify: `grep -c "_GROUP_UNITS = SourceMemo()" world/maps/population_units.py` prints 1.
- [ ] 2.2 In `world/maps/tests/test_population_units.py`, beside the existing `warm_group_units` test, add the two scenarios of "Group units are computed once per activity record": patch `world.maps.population_units.group_units` with `wraps=`; call `lagging_sets(wilderness, now)` with one unit behind, then `build_scope` twice; assert the call count equals the number of stored groups. Then rewrite one group's home to a cell of another unit through `monster_activity.write_monster_activity`, build the scope again and assert the scope's `units` contain the other unit. Verify: the test prefix with `world.maps.tests.test_population_units` passes.

## 3. Steps per run

- [ ] 3.1 Apply design D2's setting to `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example` and `server/conf/tests/test_env_overrides/_support.py`. Verify: the test prefix with `server.conf.tests.test_env_overrides` passes.
- [ ] 3.2 Apply design D1 and the `at_repeat` line of D2 to `world/maps/population_drain.py`. In `world/maps/tests/test_population_drain.py`: replace the two uses of `MAX_SETS_PER_RUN` with `MAX_FAILED_SETS_PER_RUN`; give `DrainFixture.drain` a `max_steps: int = 1` parameter passed through; change `drain.assert_called_once_with(SLICE)` to `drain.assert_called_once_with(SLICE, django_settings.POPULATION_DRAIN_STEPS_PER_RUN)`; add the new scenarios of the two MODIFIED drain requirements ("Several sets in one run", "A far-behind set takes several steps", "The run ends when nothing lags", "One event per step", "A failed set is not retried in the same run"), following `test_one_slice_moves_the_most_lagging_set_and_keeps_the_world_tick`, `test_reported_slice` and `test_a_failing_set_does_not_starve_the_next` for set-up, event capture and fault injection; add one test that `drain_population_backlog(SLICE, 0)`, `(SLICE, True)` and `(SLICE, -1)` raise `ValueError`; in `DrainEquivalenceTests` add one test that drains to completion with `max_steps=3` and compares the projection with one whole-world pass, annotated with the existing identifier of "Draining gives the whole-world result". Verify: the test prefix with `world.maps.tests.test_population_drain` passes.
- [ ] 3.3 Apply design D5 to the three documents. Verify: `grep -c POPULATION_DRAIN_STEPS_PER_RUN docs/development/settings-and-environment.md` and the same command on `docs/development/regional-monster-population.md` each print 1 or more, and `grep -c MAX_SETS_PER_RUN docs/development/regional-monster-population.md` prints 0.

## 4. Gates

- [ ] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate population-drain-batched-runs --strict`. Verify: all exit 0.
- [ ] 4.2 Observation, recorded in the hand-off as information only and never a gate: when a provisioned development database is available, from `evennia shell` time one `drain_population_backlog(600, 4)` call, count its SQL statements with `django.test.utils.CaptureQueriesContext`, and note both numbers with the `remaining` value of its last event. Skip and say so when no such database exists.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the ADDED requirement with the identifier printed by `uv run --locked python -m tools.spec_traceability list`.
