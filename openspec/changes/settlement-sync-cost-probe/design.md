# Design

## Context

See proposal.md (Why). The tools are `tools.settlement_synthesis generate --missing --nation <n>`, `regenerate_partition.py` and the Evennia test runner. The runner prints `Ran N tests in X s` and accepts one standalone command per module, with at most 100 tests.

## Goals / Non-Goals

**Goals:** produce measured numbers and a mechanical decision, and publish the canonical module list.

**Non-Goals:** designing or implementing a mitigation, writing prose, committing data.

## Decisions

### D1. What is measured

- **Modules timed.** Each module runs once on the clean tree (*before*) and once with all generated data in place (*after*):
  - `world.maps.tests.test_bootstrap`
  - `world.maps.tests.test_city_walkthrough`
  - `world.maps.tests.test_runtime_adoption`
  - `world.lore.tests.test_wilderness_entry`
  - `web.webclient.presentation.tests.test_world_map`
- **Room and exit counts.** Read them with:

  ```
  uv run --locked python -c "from world.maps import runtime; runtime.adopt(); from world.maps.map_data import SETTLEMENT_GRAPHS as g; print(sum(len(x.nodes) for x in g.values()), sum(len(x.edges) for x in g.values()))"
  ```

  This command needs no Django setup. If it fails, record the error and use the node and road counts from the generated YAML files instead.
- **Generation outcome.** Record which locations failed generation and why.

### D2. Decision rule (mechanical)

Let `r` be the ratio *after / before* for `world.maps.tests.test_bootstrap`, and `t` the *after* time in seconds.

- **proceed** when `r ≤ 2.5` and `t ≤ 600`;
- **blocked** otherwise.

Write the decision word, the full table and the failed-location list into § Runtime cost. A **blocked** result is not a failure of this change. It is the evidence the user needs to choose a mitigation. Possible mitigations:

- test-scoped publication of a settlement subset;
- faster or lazy room synchronization;
- splitting the shipped-data tests.

### D3. Canonical settlement-sensitive module list

Write the following list verbatim as § "Settlement-sensitive test modules". It is the set of modules found by `grep -rlE "capital_altoria|south_gate|east_gate|central_plaza|SETTLEMENT_GRAPHS|WILDERNESS_ENTRY_REGISTRY|ANCHOR_PLACEMENT_REGISTRY"`, with browser tests excluded. Add a note that the `tests.` module runs under `unittest` and all others under `evennia test --settings settings.py`.

`commands.tests.test_localized.test_xyz_grid_and_help tests.test_map_core_contract typeclasses.tests.test_exit_movement_cost typeclasses.tests.test_exits typeclasses.tests.test_map_discovery typeclasses.tests.test_npc_dialogue web.webclient.actions.tests.test_exploration_actions.test_move_and_look web.webclient.actions.tests.test_node_ids web.webclient.actions.tests.test_travel_actions web.webclient.presentation.tests.test_area_map web.webclient.presentation.tests.test_exploration_panel.test_presenter web.webclient.presentation.tests.test_exploration_panel.test_wilderness_and_npc_titles web.webclient.presentation.tests.test_local_map.test_gate_capacity web.webclient.presentation.tests.test_local_map.test_gateway_resolution web.webclient.presentation.tests.test_local_map.test_grid_gateways web.webclient.presentation.tests.test_local_map.test_grid_helpers web.webclient.presentation.tests.test_local_map.test_per_gate_footprint web.webclient.presentation.tests.test_local_map.test_presenter web.webclient.presentation.tests.test_local_map.test_wilderness web.webclient.presentation.tests.test_map_quest_destinations web.webclient.presentation.tests.test_world_map world.lore.tests.test_anchor_placement world.lore.tests.test_map_district_content world.lore.tests.test_nations world.lore.tests.test_settlements world.lore.tests.test_sync world.lore.tests.test_wilderness_entry world.maps.tests.test_altoria_capital world.maps.tests.test_bootstrap world.maps.tests.test_city_movement_cost world.maps.tests.test_city_walkthrough world.maps.tests.test_city_wilderness_roundtrip world.maps.tests.test_editor_final_yaml_adoption world.maps.tests.test_geography_source world.maps.tests.test_limbo_room world.maps.tests.test_movement_roundtrip world.maps.tests.test_runtime_adoption world.maps.tests.test_settlement_reload world.maps.tests.test_sparse_graph world.maps.tests.test_static_map_references world.maps.tests.test_village_ciaran world.maps.tests.test_wilderness_destination world.maps.tests.test_wilderness_geography_contract world.maps.tests.test_wilderness_population world.maps.tests.test_wilderness_provider world.quests.tests.test_compile_blueprint world.quests.tests.test_compile_offline world.quests.tests.test_compile_registration world.quests.tests.test_definitions world.quests.tests.test_encounter_activation world.quests.tests.test_encounter_dispatch world.quests.tests.test_generated_dialogue_scenes world.quests.tests.test_package_proposal world.quests.tests.test_quests_observability world.quests.tests.test_room_observation world.quests.tests.test_scene_builder_offline world.quests.tests.test_scene_smoke world.quests.tests.test_story_dialogue world.quests.tests.test_story_effects world.rules.tests.test_dialogue_refresh_lifecycle world.rules.tests.test_guild_config.test_price_scaling world.rules.tests.test_guild_config.test_service_host_roster world.rules.tests.test_map_knowledge_integration world.rules.tests.test_movement world.rules.tests.test_movement_settlement world.rules.tests.test_party_follow world.rules.tests.test_party_follow_possession world.rules.tests.test_party_time_settlement world.rules.tests.test_sight world.rules.tests.test_travel_plan`

`world.maps.tests.test_editor_final_yaml_adoption` runs with `--settings test_settings.py` and an env file that contains `MUD_TEST_SETTINGS=1`.

Write the following "Residual pin rule" verbatim under that section:

> A failure is a residual pin when the module passes on the pre-change tree (`git stash`, rerun, `git stash pop`) and the cause is a copied settlement value: a literal coordinate, count, duration, node key, cell, roster or gate direction. To fix it:
> - rewrite only that assertion;
> - derive the expected value from `world.maps.map_data.current().settlements[...]`, `world.maps.geography.current().locations` or `elosern_map_core.authoring.gate_approach_cell`, never from a literal;
> - keep the module's `@covers_requirement` IDs and its `Data-contract test:` docstring line;
> - for durations, assert that the charged tick delta `d` satisfies `(d - 1) * 1.25 < metres <= d * 1.25`, where `metres` is the authored polyline length. Never recompute seconds.
>
> Any other failure stops the change.

## Risks / Trade-offs

- [The temporary data is left behind] → Task 3.2 ends with a `git status` check, and nothing but the doc may be staged.
- [The measurement varies from machine to machine] → The ratio, not the absolute time, decides the result. Absolute numbers are recorded only for context.

## Migration Plan

None.
