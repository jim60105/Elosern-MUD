# Tasks

"The test prefix" means `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`. Run each test command standalone (no pipe, no redirect), with one dotted label.
Do not add `covers_requirement` for the ADDED requirement of this change; that happens at archive. Tests of the three MODIFIED requirements keep or receive the existing identifiers already used in `world/maps/tests/test_population_drain.py`.
No test may sleep, start a timer or assert elapsed real time. Work is bounded and asserted by counts (steps, events, calls).
Tests use the synthetic two-zone world of `DrainFixture` only.
Where a test must rewrite a stored group, use `monster_activity.write_monster_activity` when that function exists and the fixture's existing `link_group_home` helper otherwise.
Do not edit `world/maps/population_lifecycle.py`, `world/maps/monster_activity.py`, `world/maps/regional_population.py`, or the signatures and results of `lagging_sets` and `build_scope`.

## 1. Preconditions

- [x] 1.1 Confirm the baseline and the earlier changes are merged. Verify: `grep -c "_AREA_UNITS = SourceMemo()" world/maps/population_units.py` prints 1 (commit `c0736d44`), and `grep -c "POPULATION_DRAIN_IDLE_SECONDS" world/maps/population_drain.py` prints 1 or more (`population-drain-idle-gate`). If either prints 0, stop and report.

## 2. Shared group units

- [x] 2.1 Apply design D3 to `world/maps/population_units.py`. Verify: `grep -c "_GROUP_UNITS = SourceMemo()" world/maps/population_units.py` prints 1.
- [x] 2.2 In `world/maps/tests/test_population_drain.py` add a class `SharedGroupUnitsTests(DrainFixture)` with the two scenarios of "Group units are computed once per activity record". First test: `self.set_world_tick(FAR_TICK)`; `self.write_cursors(FAR_TICK, {self.unit_a: START})`; make the memo miss by rewriting one group through `self.link_group_home(group_id, cell)` with the group's present home cell (any stored write replaces the record object); then patch `world.maps.population_units.group_units` with `wraps=`, call `lagging_sets(self.wilderness, FAR_TICK)` and `population_units.build_scope(self.wilderness, {self.unit_a})` twice, and assert the call count equals `len(read_monster_activity(self.wilderness).groups)`. Second test: build the scope of `self.unit_a`, call `self.link_group_home` to move one first-zone group's home to a second-zone cell, build the scope again and assert its `units` contain `self.unit_b`. Verify: the test prefix with `world.maps.tests.test_population_drain` passes.

## 3. Steps per run

- [x] 3.1 Apply design D2's setting to `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example` and `server/conf/tests/test_env_overrides/_support.py`. Verify: the test prefix with `server.conf.tests.test_env_overrides` passes.
- [x] 3.2 Apply design D1 and the `at_repeat` line of D2 to `world/maps/population_drain.py`. In `world/maps/tests/test_population_drain.py`: replace the two uses of `MAX_SETS_PER_RUN` with `MAX_FAILED_SETS_PER_RUN`; give `DrainFixture.drain` a `max_steps: int = 1` parameter passed through; change `drain.assert_called_once_with(SLICE)` to `drain.assert_called_once_with(SLICE, django_settings.POPULATION_DRAIN_STEPS_PER_RUN)`; add the new scenarios of the two MODIFIED drain requirements ("Several sets in one run", "A far-behind set takes several steps", "The run ends when nothing lags", "One event per step", "A failed set is not retried in the same run"), following `test_one_slice_moves_the_most_lagging_set_and_keeps_the_world_tick`, `test_reported_slice` and `test_a_failing_set_does_not_starve_the_next` for set-up, event capture and fault injection; add one test that `drain_population_backlog(SLICE, 0)`, `(SLICE, True)` and `(SLICE, -1)` raise `ValueError`; in `DrainEquivalenceTests` add one test that drains to completion with `max_steps=3` and compares the projection with one whole-world pass, annotated with the existing identifier of "Draining gives the whole-world result". Verify: the test prefix with `world.maps.tests.test_population_drain` passes.
- [x] 3.3 Apply design D5 to the three documents. Verify: `grep -c POPULATION_DRAIN_STEPS_PER_RUN docs/development/settings-and-environment.md` and the same command on `docs/development/regional-monster-population.md` each print 1 or more, and `grep -c MAX_SETS_PER_RUN docs/development/regional-monster-population.md` prints 0.

## 4. Gates

- [x] 4.1 Run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate population-drain-batched-runs --strict`. Verify: all exit 0.
- [x] 4.2 Observation, recorded in the hand-off as information only and never a gate: when a provisioned development database is available, from `evennia shell` time one `drain_population_backlog(600, 4)` call, count its SQL statements with `django.test.utils.CaptureQueriesContext`, and note both numbers with the `remaining` value of its last event. Skip and say so when no such database exists. Resolved by skip: `server/db/evennia.db3` has zero tables, so no provisioned development database exists; recorded in the 2026-11-16 hand-off.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests of the ADDED requirement with the identifier printed by `uv run --locked python -m tools.spec_traceability list`.
