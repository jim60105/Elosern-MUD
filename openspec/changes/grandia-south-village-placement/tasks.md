# Tasks

Test prefix: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb`
(`/tmp/mud-test.env` contains the single line `MUD_TEST_SETTINGS=1`; create it if missing).
Run only the focused labels named below, one command per label. Never run a whole test suite for this change.

Ground rules:
- Change only these files, plus residual-pin test rewrites under the "Residual pin rule" of `docs/development/settlement-synthesis.md`:
  - new rows in `content/maps/locations.yaml` and `world/lore/anchors.py`;
  - new `content/maps/settlements/<id>.yaml` files for the new IDs;
  - `tools/settlement_spacing_areas.json`;
  - `world/maps/data/road_network.json`, `world/maps/data/district_partition.json`, `content/map-reference-context.json`;
  - files under `openspec/changes/grandia-south-village-placement/`.

- Never hand-edit generated YAML or a generated artifact.
- Keep previews, captures and prose JSON in the scratchpad, outside the repository.
- Ask before writing if the map editor has one of these documents open.

## 1. Baseline

- [x] 1.1 Confirm the prerequisites: `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`, `uv run --locked python -m tools.road_network --check` exits 0, `uv run --locked python -m tools.settlement_synthesis generate --help` lists `--kind`, and `tools/settlement_spacing_areas.json` equals the "Before" content of design D7. If any fails, stop and report.

  Result: all four hold on `174fa05c`. `spacing: 0 problems`; the road
  artifact reports `is up to date`; `generate --help` lists
  `--kind {capital,city,town,port,village,hamlet}`; the area file is exactly
  the Before content.
- [x] 1.2 Record the first timing line of design D9. Verify: the line is saved for the hand-off.

  Result: `Ran 46 tests in 354.518s`, `OK` (start of the change, no data edits
  yet).
- [x] 1.3 Write the placement script per design D1 and list the road gaps over 75 km inside this change's scope. Verify: the list is saved under `snippets/` and names each gap's road, end cells and length.

  Result: `snippets/place.py`, `snippets/plan.json`, `snippets/gaps_before.json`
  and `snippets/gaps_before.txt`. Eleven gaps: `city_spice_road --
  city_twin_currents` 221.3 km, `city_spice_road -- town_orange_blossom`
  169.7, `city_starglow -- town_emerald_lake` 154.8, `city_twin_currents --
  port_east_bay` 526.9, `city_twin_currents -- port_golden_sheaf` 492.5,
  `city_twin_currents -- town_emerald_lake` 266.0, `port_east_bay --
  port_golden_sheaf` 767.1, `port_east_bay -- town_east_pasture` 479.8,
  `town_emerald_lake -- town_steed_plain` 225.4, `town_orange_blossom --
  town_silver_ridge` 390.8, `town_silver_ridge -- town_steed_plain` 206.8.
  The script's `cover` command found a minimal 39 on-road cell set that cuts
  every in-scope gap to 75 km or less with 15 km spacing and zero over-length
  left; the full 51-site plan validated with no cell, spacing or gap problem.

## 2. Villages

- [x] 2.1 Propose villages, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` (command in design Context) reports every new cell walkable, off the water and of nation `grandia`, and `uv run --locked python -m tools.settlement_spacing` reports no problem except `village_off_road` for the new villages.

  Result: 17 villages, 14 on an inner trunk cell and 3 off-trunk
  (`village_west_bend`, `village_mill_flat`, `village_river_plain`, at 21 to
  46 km from the nearest road on the imperial river). `place_sites.py
  --locations` reports `201/201 sites valid` (exit 0); `settlement_spacing`
  reports exactly three problems, all `village_off_road`, for those three
  sites. No exemption.
- [x] 2.2 Regenerate per design D6. Verify: `uv run --locked python -m tools.settlement_spacing` reports no `village_off_road`, and every new village ID appears as a `spur_of` value in `world/maps/data/road_network.json`.

  Result: `spacing: 0 problems`; all 17 new village IDs are `spur_of` values
  and the road artifact grew from 92 to 109 nodes. The three off-trunk spurs
  are 41 to 275 km long; the 275 km `village_pasture_road -- village_west_bend`
  spur is why task 3.1 adds three hamlets on it.

## 3. Hamlets

- [x] 3.1 Propose hamlets against the regenerated roads, approve each against design D2 and D3, and write the rows of design D4. Verify: `place_sites.py --locations` reports every new cell valid, and `uv run --locked python -m tools.settlement_spacing` reports no `hamlet_spacing`, `village_spacing`, `id_prefix`, `duplicate_name`, `no_nation`, `nation_mismatch`, `population_range` or `forbidden_region` problem.

  Result: 34 hamlets: 28 on a road (25 of the cover cells plus
  `hamlet_wild_road`, `hamlet_open_wild` and `hamlet_west_road` on the
  west-bend spur) and 6 off every road (`hamlet_river_mouth`,
  `hamlet_bay_head`, `hamlet_spring_flat`, `hamlet_lake_flat`,
  `hamlet_orange_garden`, `hamlet_south_sand`). `place_sites.py --locations`
  reports `235/235 sites valid` (exit 0); `settlement_spacing` reports
  `spacing: 0 problems` and no identity or population problem.
- [x] 3.2 Regenerate per design D6 and make the trunk comparison of D6. Verify: no road row without `spur_of` changed.

  Result: the artifact is 109 nodes and 128 road rows before and after; the
  only changed top-level field is `source_signature`, zero road rows changed,
  and every trunk row is byte-identical.

## 4. Maps and prose

- [x] 4.1 Run `uv run --locked python -m tools.settlement_synthesis generate --missing --nation grandia --kind village --plan-only`, then without `--plan-only`; then the same two commands with `--kind hamlet`. Verify: each new ID has exactly one new file, no existing settlement file changed (`git status --short content/maps/settlements` shows only additions), and `uv run --locked python -m tools.settlement_synthesis lint` exits 0. A refusal is fixed by moving that location and repeating from group 2 or 3; never by hand-writing a map.

  Result: 17 village maps (4 nodes each) and 34 hamlet maps (2 nodes each),
  136 nodes in all, every report warning-free. `git status --short
  content/maps/settlements` lists 51 additions and no modification, and
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings` and exits 0.
- [x] 4.2 Write and apply the prose of every new map per design D5a. Verify: `brief` of each new map shows no empty description and no duplicate key.

  Result: 51 prose files written under `/tmp/grandia-south/` and applied with
  `prose`; every one of the 136 nodes now carries a `key` of 2 to 8 characters
  and a `desc` of 40 to 140 characters, keys are unique within their map and
  no description is empty. Villages name the green, its well and the church
  front; hamlets name the crossing and the single farmstead; each entrance
  names the direction or the neighbour it leads to; no shop, guild branch or
  service is presented as usable.
- [x] 4.3 Regenerate per design D6. Verify: compared with the artifact of task 3.2 (keep a copy in the scratchpad), the only changed line of `world/maps/data/road_network.json` is `source_signature`.

  Result: `algorithm_version`, `fingerprint`, `frame_cells`, `nodes`, `roads`
  and `version` are unchanged; only `source_signature` differs, and zero road
  rows changed.

## 5. Validation and hand-off

- [x] 5.1 Replace `tools/settlement_spacing_areas.json` with the "After" content of design D7 and run the four checks of D7. Verify: all four hold. Fix a `road_gap` as D7 says and repeat the affected groups.

  Result: all four hold. `tools.settlement_spacing` prints `spacing: 0
  problems` with the new `southeast_coast` and bounded `eastern_plains_south`
  areas in place; `check_map_sources.py` reports `cross-file problems: 0` and
  `RESULT: game-ready as far as static checks can tell`, exit 0;
  `settlement_synthesis lint` prints `fit: 0 errors, 0 warnings`;
  `road_network --check` and `map_reference_context --check` both report
  `is up to date`, exit 0. Enabling the areas surfaced no remaining road gap
  and the three spur hamlets of task 3.1 were already in place.
- [x] 5.2 Run every module of `docs/development/settlement-synthesis.md` § Settlement-sensitive test modules, one per command, plus `world.lore.tests.test_anchors` and `world.maps.tests.test_population_geometry` with the test prefix. Verify: every one passes. Handle a failure with that section's "Residual pin rule" and list every rewritten test in the hand-off. Any other failure stops the change without a commit.

  Result: every label of the list was run against this tree, grouped only
  where the guard's 100-test cap required it: `world.lore.tests.test_anchors
  test_settlements test_anchor_placement` 48 OK and `test_map_district_content
  test_nations test_sync test_wilderness_entry` 39 OK;
  `world.maps.tests.test_altoria_capital test_city_movement_cost
  test_city_walkthrough test_city_wilderness_roundtrip
  test_editor_final_yaml_adoption test_geography_source test_limbo_room
  test_movement_roundtrip` 70 OK (303.5 s), `test_runtime_adoption
  test_settlement_reload test_sparse_graph test_static_map_references
  test_village_ciaran` 46 OK, `test_wilderness_destination
  test_wilderness_geography_contract test_wilderness_population
  test_wilderness_provider` 75 OK, `test_population_geometry` 28 OK;
  `web.webclient.actions.tests.test_exploration_actions.test_move_and_look
  test_node_ids` 43 OK, `test_travel_actions
  web.webclient.presentation.tests.test_area_map` 70 OK (skipped=1),
  `test_exploration_panel.test_presenter
  test_exploration_panel.test_wilderness_and_npc_titles
  test_local_map.test_gate_capacity` 50 OK, `test_local_map
  .test_gateway_resolution test_grid_gateways test_grid_helpers` 43 OK,
  `test_local_map.test_per_gate_footprint test_presenter test_wilderness`
  43 OK, `test_map_quest_destinations test_world_map` 28 OK;
  `typeclasses.tests.test_exit_movement_cost test_exits test_map_discovery`
  48 OK, `test_npc_dialogue
  commands.tests.test_localized.test_xyz_grid_and_help
  world.quests.tests.test_room_observation` 94 OK;
  `world.rules.tests.test_movement_settlement test_party_time_settlement
  test_travel_plan` 77 OK (skipped=1), `test_guild_config.test_price_scaling
  test_guild_config.test_service_host_roster test_map_knowledge_integration`
  70 OK, `test_movement test_party_follow test_party_follow_possession` 77 OK,
  `test_sight` 45 OK;
  `world.quests.tests.test_compile_offline test_definitions
  test_scene_builder_offline test_story_effects` 74 OK,
  `test_compile_blueprint test_compile_registration test_encounter_activation`
  93 OK, `test_encounter_dispatch test_generated_dialogue_scenes
  test_package_proposal test_quests_observability` 76 OK,
  `test_scene_smoke test_story_dialogue
  world.rules.tests.test_dialogue_refresh_lifecycle` 24 OK. That is 1,307
  evennia tests across 23 commands, every one green.

  `tests.test_map_core_contract` under the plain `unittest` runner: `Ran 4
  tests`, one error, the documented `ImproperlyConfigured: Requested setting
  CHANNEL_LOG_NUM_TAIL_LINES, but settings are not configured` raised while
  importing `evennia.contrib.grid.wilderness` - the runner/settings shape,
  not a data finding. No residual-pin rewrite was needed.
- [x] 5.3 Capture the continent with `capture_map.py --hide partition` and the settlement views of two new villages and two new hamlets (one on a through road, one at a spur end, one off-road where one exists). Read the images. Verify: the hand-off gives the absolute path of each image and of the last road preview, and states for each captured map which road each entrance meets.

  Result: five images rendered and read. Continent:
  `/tmp/grandia-south/continent.webp` (`--hide partition`). Settlements:
  `/tmp/grandia-south/village_reed_ford.webp`,
  `/tmp/grandia-south/village_west_bend.webp`,
  `/tmp/grandia-south/hamlet_bay_flat.webp`,
  `/tmp/grandia-south/hamlet_river_mouth.webp`. Entrances:
  `village_reed_ford` has an east and a west entrance on the shared coast
  stretch of `city_twin_currents--port_east_bay` and
  `port_east_bay--port_golden_sheaf`; the east entrance meets the highway
  toward East Bay and the west one the road toward Twin Currents.
  `village_west_bend` has one east entrance at the end of its spur
  `village_pasture_road--village_west_bend`. `hamlet_bay_flat` has an east
  and a west entrance on `city_twin_currents--port_east_bay`, east toward
  East Bay and west toward Twin Currents. `hamlet_river_mouth` touches no
  road; its single north entrance faces the wilderness track toward Golden
  Sheaf. The last road preview is `/tmp/grandia-south/roads_final.png`;
  earlier runs left `roads_villages.png`, `roads_hamlets.png` and
  `roads_maps.png`. The capture reported one advisory diagnostic about
  `city_imperial_ferry`'s footprint offset, which belongs to an earlier
  change.
- [x] 5.4 Record the second timing line of design D9, then run `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.contract_gate` and `openspec validate grandia-south-village-placement --strict`. Verify: all exit 0. The hand-off lists the count of villages and hamlets, every exemption with its reason, every hamlet placed under the boundary exception of D2, and both timing lines.

  Result: `test_data_lint check` -> `scanned=1619 flagged=121 universe=4362+37
  quantity-pins=8 violations=0`, exit 0; `tools.contract_gate` -> `contract
  gate passed: reference-context, traceability, observability, test-data,
  manifests, contracts`, exit 0; `openspec validate
  grandia-south-village-placement --strict` -> `Change
  'grandia-south-village-placement' is valid`, exit 0. First timing line:
  `Ran 46 tests in 354.518s`, `OK`. Second timing line: `Ran 46 tests in
  345.207s`, `OK`. Fifty-one settlements were added: 17 villages (14 on a
  trunk, 3 off-trunk river sites) and 34 hamlets (28 on a road or a spur,
  6 off every road). No spacing exemption is used and no hamlet stands
  on the earlier side of a boundary; the new area does not adjoin a completed
  area by land.

## Workflow follow-up

- After merge, the user reviews the new maps and markers in the map editor and the webclient. The review does not block archive.