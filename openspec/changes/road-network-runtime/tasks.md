# Tasks

Shared test command, with `<env>` a scratch file containing `MUD_TEST_SETTINGS=1`:
`uv run --locked --env-file=<env> evennia test --settings test_settings.py --keepdb <label>`

Do not add `covers_requirement` in any task here; see D6.

## 1. Read view and adoption gate

- [x] 1.1 Confirm `road-network-generation` is merged: `uv run --locked python -m tools.road_network --check` exits 0. If not, stop and report.
- [x] 1.2 Implement `world/maps/road_network.py` per D1. Add "Independent runtime" to `tests/test_road_network_format.py` using its `run_with_numpy_blocked` helper. Verify with the shared command on `tests.test_road_network_format`.
- [x] 1.3 Implement the D2 gate, the `MapWorld.roads` field, `identity`, `_install` and `_uninstall` in `world/maps/runtime.py`. Update the adoption fixtures named in D5. Create `world/maps/tests/test_road_network_runtime.py` covering "Adoption requires a current road network" and "Road cell lookup reads the published bundle" with `runtime.road_freshness_for`, `road_network.artifact_metadata` and synthetic `RoadNetwork` values patched in. Register it in shard `maps-33-1` of `.github/evennia-shards.json`. Verify with the shared command on `world.maps.tests.test_road_network_runtime`, `world.maps.tests.test_runtime_adoption`, `world.maps.tests.test_runtime_adoption_rollback`, `world.maps.tests.test_editor_final_yaml_adoption`, `world.maps.tests.test_editor_final_yaml_moved_location`, `world.maps.tests.test_editor_final_yaml_rejection` and `tests.test_evennia_test_optimization_contract`.

## 2. Test isolation

- [x] 2.1 Apply the `roads=None` publications of D5. Add cases to `test_road_network_runtime.py`: after `publish_geography`, and inside a synthetic patching scope that applies geography, `road_network.road_cells()` is empty. Verify with the shared command on `world.maps.tests.test_road_network_runtime`.

## 3. Movement and map

- [x] 3.1 Implement D3 in `world/rules/travel_cost.py`. Create `world/rules/tests/test_road_terrain.py` covering "Road speed needs road cells at both ends of a step", publishing a synthetic network through `road_network._install` with cleanup, and for the planner scenario reusing the patch setup in `world/rules/tests/test_travel_plan.py`. Register it next to `world.rules.tests.test_travel_plan` in `.github/evennia-shards.json`. Verify with the shared command on `world.rules.tests.test_road_terrain`, `world.rules.tests.test_travel_plan`, `world.rules.tests.test_travel_capacity` and `world.maps.tests.test_wilderness_clock`.
- [x] 3.2 Implement D4 in `web/webclient/presentation/area_map.py`. Add the scenarios of "Map facts publish the road fact within disclosure" to `web/webclient/presentation/tests/test_area_map/test_wilderness_content.py`, with a synthetic network and no shipped cell. Verify with the shared command on `web.webclient.presentation.tests.test_area_map` and `web.webclient.presentation.tests.test_map_panel_protocol`.
- [x] 3.3 Extend `docs/development/road-network.md` with how the runtime reads the artifact and what a rejected startup means, and add a pending row for map legibility at 1451x790 and 2560x1440 to its "Human review record". Verify: the file names `uv run --locked python -m tools.road_network`.

## 4. Integration

- [x] 4.1 Run `uv run --locked python -m tools.observability_lint check` and `uv run --locked python -m tools.test_data_lint check`. Verify: both exit 0.
- [x] 4.2 After the last source edit, run `uv run --locked python -m tools.map_reference_context` and commit `content/map-reference-context.json`. Verify: the same command with `--check` exits 0.
- [ ] 4.3 Run the full non-browser Evennia suite once with `--parallel 16 --noinput`, capturing output to a scratch file. Fix any failure caused by shipped road cells as the design's risk section states. Verify: the suite exits 0.
- [x] 4.4 List each new test with the delta requirement and scenario it establishes in the change report. Verify: every requirement in `specs/wilderness-roads/spec.md` has at least one test.
- [x] 4.5 Run `uv run --locked python -m tools.contract_gate --change road-network-runtime` and `openspec validate road-network-runtime --strict`. Verify: both exit 0.

## Workflow follow-up

- During archive, after the delta sync, annotate the tests named in 4.4 with the tool-generated IDs from `uv run --locked python -m tools.spec_traceability list`.
- The human reviewer fills in the map legibility row of `docs/development/road-network.md`. It does not block archive.
