# Tasks

Precondition: `subrace-start-settlements` and `entrance-probe-fixtures` are archived on
master. Test commands follow
AGENTS.md: run each command on its own. `EV` stands for
`uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb`.

## 1. 虛境 owns no exits (design D1)

- [x] 1.1 In `world/maps/bootstrap.py`, remove the Limbo block from `sync_grid()`.
  Delete `_ensure_exit` and `_prune_exits_into`, add `_prune_limbo_exits` exactly as in
  D1, call it at the end of `sync_limbo()`, and update both docstrings.
- [x] 1.2 In `world/maps/tests/test_limbo_room.py`, add the four `sync_limbo` prune tests
  from D5 and annotate them with
  `limbo-one-way-gates::sync-limbo-removes-every-exit-that-touches-虛境` (exact ID from
  `uv run --locked python -m tools.spec_traceability list`). Delete the module's
  gate-row helper `_gate_row` and every test that uses it or patches
  `world.rules.city_gates`.
  Acceptance: `EV world.maps.tests.test_limbo_room` passes.

## 2. Delete the gate view (design D2)

- [x] 2.1 Delete `world/maps/city_gates.py`. Edit `world/maps/map_data.py` and
  `world/maps/static_references.py` as in D2.
- [x] 2.2 Run `rg -n "city_gates|CITY_GATE|CityGateDef|world\.maps\.city_gates|\"city_gates\"" world web server typeclasses commands tests`
  and fix every hit outside the D5 document assertions.

## 3. Delete the re-anchor (design D3)

- [x] 3.1 Delete `world/rules/city_gates.py`. Edit `typeclasses/exits.py` and
  `world/rules/movement_settlement.py` as in D3.
- [x] 3.2 Retarget the two fault-injection tests in `world/maps/tests/test_gm.py` as in D5.
  Acceptance: `EV world.maps.tests.test_gm` and
  `EV world.rules.tests.test_movement_settlement` pass.

## 4. Fixtures and synthetic kit (design D4)

- [x] 4.1 Synthetic kit: delete `SYNTH_CITY_GATES`, `make_city_gate` and the
  `city_gates` target rows, as in D4. Acceptance: `EV world.tests.test_synthetic_data`
  passes.
- [x] 4.2 Map-knowledge fixtures: edit `_support.py`, `test_recording.py` and
  `_knowledge_probes.py` as in D4. Then run each module of
  `world/rules/tests/test_map_knowledge_integration` with `EV`.
- [x] 4.3 Rewrite the remaining call sites from D4:
  `world/maps/tests/_bootstrap_fixtures.py`,
  `world/maps/tests/test_bootstrap/{_support,test_bootstrap_grid,test_bootstrap_selection}.py`,
  `world/maps/tests/test_bootstrap_sync.py`,
  `world/maps/tests/test_static_map_references.py`,
  `world/maps/tests/_editor_adoption_fixtures.py`,
  `world/rules/tests/test_met_people.py`,
  `web/tests/browser/fixtures.py` and `web/tests/browser/incremental_sync_fixture.py`.
- [x] 4.4 Delete or retarget the gate-behavior tests listed in D5 in
  `world/maps/tests/test_bootstrap_sync.py`, `test_bootstrap/test_bootstrap_grid.py`,
  `test_bootstrap/test_bootstrap_selection.py`, `test_settlement_sources.py` and
  `test_village_ciaran.py`. Add the `sync_grid` no-exit test to `test_bootstrap_sync.py`,
  annotated with the same ID as 1.2.
- [x] 4.5 Add the "no city room is joined to 虛境" assertion and annotate the
  wilderness-gate connectivity test with
  `sample-city-altoria::the-sample-city-connects-to-the-world-only-through-its-wilderness-gates`,
  as in D5.
- [x] 4.6 Delete each `covers_requirement` that names a requirement this change removes:
  `rg -n "limbo-one-way-gates::(the-city-gate|sync-grid-creates|every-sync-prunes|a-registry-row|adding-a-city|the-first-city-gate)|grid-room-sync::a-single-authored|limbo-room::the-bridge|sample-city-altoria::the-sample-city-connects-to-the-rest" --glob '*.py'`.
  If a test only established a removed requirement, delete the test.
  Move the annotations for `village-ciaran-map::the-village-has-exactly-one-concealed-entrance`
  to the new `village-ciaran-map` requirement ID wherever the test still asserts the
  entrance-node prose or the wilderness gate destination. In `world/maps/tests/test_village_ciaran.py`,
  replace the "reachable from the starting room" test with one that asserts no exit joins
  虛境 and the village after `sync_grid`.

## 5. Verification

- [x] 5.1 Run `EV <module>` for every module touched in sections 1 to 4, one at a time.
  All must pass.
- [x] 5.2 `uv run --locked python -m tools.shard_register fix`, then
  `uv run --locked python -m tools.contract_gate --change retire-limbo-city-gates`. It
  must exit 0. Also `uv run --locked python -m tools.observability_lint check` and
  `uv run --locked python -m tools.test_data_lint check` must be clean.
- [x] 5.3 Run `pnpm run build`, then
  `uv run --locked python -m web.tests.browser.unittest_driver` for, one per command:
  the minimap class (`rg -l "ELOSERN_BROWSER_MINIMAP" web/tests/browser/test_*.py`,
  first file), the class using `incremental_sync_fixture.second_map_xyz`
  (`rg -l "second_map_xyz" web/tests/browser/test_*.py`), and
  `web.tests.browser.test_browser_creation_preset`. All must pass.
- [x] 5.4 Regenerate `content/map-reference-context.json` if it changes (D6), and run
  `uv run --locked python -m tools.map_reference_context`.

## 6. Specs and docs (design D6)

- [x] 6.1 Edit the four main-spec Purpose lines exactly as D6 says.
- [x] 6.2 Update `world/maps/AGENTS.md`, `world/rules/AGENTS.md` and the three docs, and
  add the superseded note to the 2026-09-04 design document.
- [x] 6.3 `openspec validate retire-limbo-city-gates --strict` passes.

## Apply notes

- Annotations (1.2, 4.4, 4.5, 4.6): ADDED requirement IDs exist only after archive sync, so
  the new tests are left unannotated, and surviving annotations that name a REMOVED
  requirement are left in place. Archive re-annotates post-sync:
  - `limbo-one-way-gates::sync-limbo-removes-every-exit-that-touches-虛境`:
    `world/maps/tests/test_limbo_room.py::LimboExitPruneTests` (4 tests, one per
    scenario 1-4), `world/maps/tests/test_bootstrap_sync.py::GridBootstrapBridgingTests::test_sync_grid_creates_no_exit_touching_the_starting_room`
    (scenario 5).
  - `sample-city-altoria::the-sample-city-connects-to-the-world-only-through-its-wilderness-gates`:
    `world/maps/tests/test_city_walkthrough.py::SampleCityWalkthroughTests::test_wilderness_gates_are_the_only_way_out_and_no_room_joins_limbo`.
  - The new `village-ciaran-map` entrance requirement: `world/maps/tests/test_bootstrap_sync.py::GridBootstrapBridgingTests::test_no_exit_joins_the_starting_room_and_the_village`
    and `world/maps/tests/test_village_ciaran.py::...::test_the_entrance_does_not_read_as_a_gate`
    (both still carry `village-ciaran-map::the-village-has-exactly-one-concealed-entrance`).
  - Surviving tests still naming removed IDs: `test_bootstrap_grid.py::test_sync_grid_spawns_both_settlements_rooms_and_exits`
    (`grid-room-sync::a-single-authored-...`), `test_city_walkthrough.py::test_every_room_is_reachable_from_south_gate`
    (`sample-city-altoria::the-sample-city-connects-to-the-rest-...`), and
    `test_bootstrap_sync.py::test_no_exit_joins_the_starting_room_and_the_village`
    (`limbo-one-way-gates::every-sync-prunes-...`).
- 3.2: the fault is injected through `world.rules.movement_settlement.invalidate_previous_edge`
  instead of `clear_dialogue_session`, because an NPC hook
  (`typeclasses/npcs.py::_clear_dialogue_sessions_naming_me`) also calls
  `clear_dialogue_session` during the teleport. The tests assert the patched step ran once.
- 4.3: `CITY_GATE_MAP_IDS` had no consumer left after the gate tests were deleted, so no
  `PROBE_MAP_IDS` constant was added. The four `test_static_map_references.py` patch tests that
  also establish preflight or rejection behavior were retargeted to the anchor-placement family.
- `test_limbo_room.py::test_at_server_start_renames_legacy_room_and_bridges_it` was retargeted to
  assert the renamed room has no exits; the sync_limbo-before-sync_grid ordering test was deleted.
