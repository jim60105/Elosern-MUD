# Settlement-sensitive sweep, valhalla-village-placement

Runner: `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings
test_settings.py --keepdb <label>`, except `tests.*` which runs under
`uv run --locked python -m unittest`.

Groups of several labels are used where the guard's 100-discovered-test cap
permits, the same smallest-grouping rule the Grandia north change recorded; a
label that would have run alone is marked "single".

| group | labels | result |
| --- | --- | --- |
| single | `world.lore.tests.test_anchors` | Ran 7, OK |
| single | `world.maps.tests.test_population_geometry` | Ran 28, OK |
| single | `commands.tests.test_localized.test_xyz_grid_and_help` | Ran 19, OK |
| single | `tests.test_map_core_contract` (unittest runner) | Ran 4, one `ImproperlyConfigured: CHANNEL_LOG_NUM_TAIL_LINES` import error — documented runner-shape red |
| single | `typeclasses.tests.test_exit_movement_cost` | Ran 22, OK |
| single | `typeclasses.tests.test_exits` | Ran 17, OK |
| single | `typeclasses.tests.test_map_discovery` | Ran 9, OK |
| single | `web.webclient.actions.tests.test_node_ids` | Ran 0, `SettlementNotLoaded` in `setUpClass` — documented registry-before-publish red |
| single | `web.webclient.actions.tests.test_travel_actions` | Ran 8, 6 `SettlementNotLoaded` errors, 2 passed — documented red |
| single | `web.webclient.actions.tests.test_exploration_actions.test_move_and_look` | Ran 37, OK |
| single | `web.webclient.presentation.tests.test_area_map` | Ran 62, OK (skipped=1) |
| 2 | `test_exploration_panel.test_presenter`, `test_exploration_panel.test_wilderness_and_npc_titles` | Ran 42, OK |
| 4 | `test_local_map.test_gate_capacity`, `test_gateway_resolution`, `test_grid_gateways`, `test_grid_helpers` | Ran 51, OK |
| 3 | `test_local_map.test_per_gate_footprint`, `test_local_map.test_presenter`, `test_local_map.test_wilderness` | Ran 43, OK |
| 2 | `test_map_quest_destinations`, `test_world_map` | Ran 28, OK |
| 5 | `world.lore.tests.test_anchor_placement`, `test_map_district_content`, `test_nations`, `test_sync`, `test_wilderness_entry` | Ran 45, OK |
| single | `world.lore.tests.test_settlements` | Ran 35, OK |
| single | `world.maps.tests.test_altoria_capital` | Ran 12, OK |
| single | `world.maps.tests.test_bootstrap` | Ran 46, OK — 348.860 s, also the second D9 timing line |
| 3 | `test_city_movement_cost`, `test_city_walkthrough`, `test_city_wilderness_roundtrip` | Ran 10, OK |