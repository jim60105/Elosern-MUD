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
| single | `world.maps.tests.test_editor_final_yaml_adoption` | Ran 1, OK — 136.054 s |
| 3 | `test_geography_source`, `test_limbo_room`, `test_movement_roundtrip` | Ran 47, OK |
| 2 | `world.maps.tests.test_population_geometry`, `test_sparse_graph` | Ran 41, OK |
| 3 | `test_runtime_adoption`, `test_settlement_reload`, `test_static_map_references` | Ran 20, OK — 136.931 s |
| 3 | `test_village_ciaran`, `test_wilderness_destination`, `test_wilderness_geography_contract` | Ran 51, OK |
| 2 | `test_wilderness_population`, `test_wilderness_provider` | Ran 37, OK |
| 2 | `world.quests.tests.test_compile_blueprint`, `test_compile_offline` | Ran 49, OK |
| 2 | `world.quests.tests.test_definitions`, `test_scene_builder_offline` | Ran 62, OK |
| 2 | `world.quests.tests.test_compile_registration`, `test_encounter_activation` | Ran 45, OK |
| 2 | `world.quests.tests.test_encounter_dispatch`, `test_generated_dialogue_scenes` | Ran 52, OK |
| 2 | `world.quests.tests.test_package_proposal`, `test_quests_observability` | Ran 24, 9 `SettlementNotLoaded` errors through the `_anchor_key` fixture lookup, 15 passed — documented red |
| 4 | `test_room_observation`, `test_scene_smoke`, `test_story_dialogue`, `test_story_effects` | Ran 41, OK |
| 3 | `test_dialogue_refresh_lifecycle`, `test_guild_config.test_price_scaling`, `test_guild_config.test_service_host_roster` | Ran 61, OK |
| 2 | `test_map_knowledge_integration`, `test_sight` | Ran 67, OK — 131.037 s |
| 3 | `test_movement`, `test_movement_settlement`, `test_party_follow` | Ran 74, OK — 192.044 s |
| 3 | `test_party_follow_possession`, `test_party_time_settlement`, `test_travel_plan` | Ran 80, 1 failure and 1 skip — the one failure is the inherited baseline red described below |
| single | `world.lore.tests.test_anchors` (rerun on the final data) | Ran 7, OK |

## The one non-red failure, and why it is not this change's

`world.rules.tests.test_party_follow_possession.PossessedWildernessSettlementTests.test_falsy_wilderness_return_compensates_the_whole_party`
fails on its own in this worktree with
`{...settled population...} != {...start population...}` and a 6010-character
state difference. It is inherited from the baseline, not caused by this
change:

- this branch changes nothing in `world/rules/tests/test_party_follow_possession.py`
  (`git log c70b1eac..HEAD -- <file>` is empty);
- upstream `master` already fixes exactly this failure in
  `16bd6484 test(population): keep the possessed-wilderness fixture's cursors
  current`, whose message records the same test failing on its own in a
  throwaway checkout of an earlier merge point with the identical assertion
  and the identical 6010-character difference, caused by a catch-up settling
  world state between the two snapshots;
- that fix (+25 lines) is not in this change's baseline `c70b1eac`, and the
  fix belongs to the `population-writer-guards` change, not to a data change's
  file list.

Recorded under Spec deviations in the hand-off; no residual-pin rewrite was
made, and no test file was touched.