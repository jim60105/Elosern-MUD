# Tasks

Ground rules for every task:
- Edit ONLY the test files a task names, plus the extra modules that task 9.3 identifies. Do NOT touch production code, `content/` (except the temporary canary in group 9, which you revert), `docs/`, `tools/`, `.github/` or `openspec/specs/`.
- Keep each `@covers_requirement(...)` ID exactly as it is. Never change the first docstring line of a `Data-contract test:` module.
- Run Evennia tests as ONE standalone command with no pipes, redirects or env prefixes. For example: `uv run evennia test --keepdb --settings settings.py world.maps.tests.test_city_walkthrough`. Without `--settings settings.py` the run fails with a misleading prototype `KeyError`. If output is truncated, read the log artifact path the tool prints.
- Expected values come from the authored documents (design D1) or are checked by the bracketing relation in design D2. Never copy a number from the current YAML into a test.
- Keep the indentation exactly as shown. Methods are indented 4 spaces inside their class.

## 1. Baseline

- [x] 1.1 Run each module below once on the clean tree. Record pass or fail in a scratch note.
  - `world.lore.tests.test_anchor_placement`
  - `world.lore.tests.test_wilderness_entry`
  - `world.maps.tests.test_bootstrap`
  - `world.maps.tests.test_city_walkthrough`
  - `world.maps.tests.test_city_movement_cost`
  - `world.maps.tests.test_city_wilderness_roundtrip`
  - `world.maps.tests.test_geography_source`

  Check: you have one recorded result per module. Any failure here was inherited; mention it in the hand-off and do not fix it.

## 2. Anchor placement registry (`world/lore/tests/test_anchor_placement.py`)

- [x] 2.1 In `test_registry_has_one_entry_per_built_settlement`, replace the method body (keep the decorator and `def` line) with:
  ```python
          from world.maps.map_data import current

          documents = current().settlements
          self.assertEqual(
              set(ANCHOR_PLACEMENT_REGISTRY),
              {document.location_ref for document in documents.values()},
          )
          for map_id, document in documents.items():
              with self.subTest(map_id=map_id):
                  placement = ANCHOR_PLACEMENT_REGISTRY[document.location_ref]
                  self.assertEqual(placement.anchor_key, document.location_ref)
                  self.assertEqual(placement.zcoord, map_id)
                  self.assertEqual(placement.node.object_id, document.anchor_node.node_id)
                  self.assertEqual(
                      anchor_entrance_xyz(placement),
                      (*document.anchor_node.coordinate, map_id),
                  )
  ```
- [x] 2.2 In `test_geographic_declarations_do_not_extend_grid_placement`, replace the statement `self.assertEqual(list(ANCHOR_PLACEMENT_REGISTRY), ["capital_altoria", "village_ciaran"],)` with:
  ```python
          from world.maps.map_data import current

          self.assertEqual(
              set(ANCHOR_PLACEMENT_REGISTRY),
              {document.location_ref for document in current().settlements.values()},
          )
  ```
- [x] 2.3 In `test_local_anchor_bindings_transform_to_absolute_metre_positions`:
  - Replace the literal dict `{"capital_altoria": (3500, 2850), "village_ciaran": (479, 305)}` with `{document.location_ref: document.local_anchor_m for document in current().settlements.values()}`. Add `from world.maps.map_data import current` as the first line of the method body.
  - Replace the three literal `world_position_m(...)` assertions, including the "south gate sits 450 m west" comment, with a loop over every document and every node:
    ```python
            from world.maps import geography

            for document in current().settlements.values():
                cell_x, cell_y = geography.current().locations.locations[document.location_ref].cell
                anchor_x, anchor_y = document.local_anchor_m
                for node in document.nodes.values():
                    with self.subTest(map=document.location_ref, node=node.node_id):
                        x, y = node.coordinate
                        self.assertEqual(
                            world_position_m(document.location_ref, (x, y)),
                            (1000 * cell_x + 500 + x - anchor_x, 1000 * cell_y + 500 + y - anchor_y),
                        )
    ```
  - Keep every other assertion in the method (the frozen-dataclass check and the rest).

  Check: `grep -nE "3500|2850|3050|479, 305|850_500|1_024_500" world/lore/tests/test_anchor_placement.py` prints nothing, and `uv run evennia test --keepdb --settings settings.py world.lore.tests.test_anchor_placement` passes.

## 3. Wilderness entry registry (`world/lore/tests/test_wilderness_entry.py`)

- [x] 3.1 In `test_registry_has_two_v2_entries_keyed_by_settlement`, make these replacements and keep the method name and decorators:
  - The `list(WILDERNESS_ENTRY_REGISTRY) == [...]` assertion → `self.assertEqual(set(WILDERNESS_ENTRY_REGISTRY), {d.location_ref for d in current().settlements.values() if d.wilderness_entry is not None})`. Import `current` from `world.maps.map_data` inside the method.
  - `self.assertEqual(_capital().hash_cell_count, 40)` → `self.assertEqual(_capital().hash_cell_count, sum(row.count("#") for row in document.wilderness_entry.shape))`, where `document = current().settlements["capital_altoria"]`.
  - `self.assertEqual(_capital().origin_xy, (847, 1020))` → compute `cell_x, cell_y = geography.current().locations.locations["capital_altoria"].cell` and `dx, dy = document.wilderness_entry.offset`, then assert `origin_xy == (cell_x + dx, cell_y + dy)`. Use `from world.maps import geography`.
  - The capital gate list literal `[("n", "capital_altoria", "south_gate"), ("w", "capital_altoria", "east_gate")]` → `[(g.return_direction, "capital_altoria", g.destination_node) for g in document.wilderness_entry.gates]`.
  - Leave the village assertions unchanged.

- [x] 3.2 In `test_derived_geometry_matches_the_authored_mask`, keep the footprint-cells comprehension, the point-shape check and the 4-connectivity walk. Replace the literal assertions as follows, with these definitions at the top of the method:

  ```python
  document = current().settlements["capital_altoria"]
  cell = geography.current().locations.locations["capital_altoria"].cell
  geometry = document.wilderness_geometry(cell)
  ```

  Import `gate_approach_cell` from `elosern_map_core.authoring`.
  - The 7×9 `shape` tuple literal → `self.assertEqual(_capital().shape, document.wilderness_entry.shape)`.
  - `hash_cell_count == 40` → `== geometry.hash_cell_count`.
  - `anchor_cell == (850, 1024)` → `== geometry.anchor_cell`.
  - The two `approach_cell(...)` literals `(850, 1021)` and `(854, 1024)` become a loop over `document.wilderness_entry.gates`. For each gate, assert `_capital().approach_cell(_capital().gate_for(g.return_direction)) == gate_approach_cell(geometry, g.return_direction)`.
  - Rewrite the leading comment so that it no longer states "40 km²" or "7x9".
- [x] 3.3 In `test_gate_lookup_by_return_direction`:
  - Keep the `gate_for("n")` and `gate_for("w")` destination assertions.
  - Replace the two `assertIsNone(...gate_for("s"/"e"))` lines and their comment with:

    ```python
    from world.maps.map_data import current

    authored = {g.return_direction for g in current().settlements["capital_altoria"].wilderness_entry.gates}
    for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
        with self.subTest(direction=direction):
            if direction in authored:
                self.assertIsNotNone(_capital().gate_for(direction))
            else:
                self.assertIsNone(_capital().gate_for(direction))
    ```

  Check: `grep -nE "847, 1020|, 40\)|850, 102|854, 1024|#\.\.\.\.\.#" world/lore/tests/test_wilderness_entry.py` prints nothing, and the module passes.

## 4. Bootstrap sync (`world/maps/tests/test_bootstrap.py`)

- [x] 4.1 Rename `test_capital_sparse_graph_spawns_twenty_one_rooms_and_fifty_two_exits` to `test_capital_sparse_graph_spawns_one_room_per_node_and_one_exit_per_road`. Keep its decorator. Replace the literals `21` and `52` with `len(current().settlements["capital_altoria"].nodes)` and `len(current().settlements["capital_altoria"].roads)`, importing `from world.maps.map_data import current` inside the method.
- [x] 4.2 In `MetricCutoverTests._seed_precutover_rooms`, replace the two loop header lines `for map_id, graph in SETTLEMENT_GRAPHS.items():` and `for node_id in graph.nodes:` with the lines below, and keep the loop body unchanged:
  ```python
          for map_id, old_coordinates in OLD_COORDINATES.items():
              ids[map_id] = {}
              for node_id in SETTLEMENT_GRAPHS[map_id].nodes:
                  if node_id not in old_coordinates:
                      continue
                  coordinate = old_coordinates[node_id]
  ```
  Delete the original `ids[map_id] = {}` and `coordinate = OLD_COORDINATES[map_id][node_id]` lines that these new lines replace. The cutover still has to converge every declared node: the existing `_declared_node_count()` assertions stay unchanged.
- [x] 4.3 Replace each of the three string keys `"grid:capital_altoria:3500:2850"` in `test_cutover_preserves_identity_references_and_knowledge` (two occurrences) and in `test_real_startup_converges_places_scene_art_and_quest_targets` (one occurrence). Replace each one with a call to `_plaza_key()`. Add this function once at module level, directly below `OLD_COORDINATES`:
  ```python
  def _plaza_key():
      x, y = SETTLEMENT_GRAPHS["capital_altoria"].node("central_plaza").coordinate
      return f"grid:capital_altoria:{x}:{y}"
  ```
  Call `_plaza_key()` at each use site. A module-level constant would read the published view at import time, so use the function. Leave the compact keys `"grid:capital_altoria:3:3"`, `"grid:capital_altoria:3:0"` and `"grid:village_ciaran:1:1"` unchanged.

- [x] 4.4 In `WildernessBootstrapTests`:
  - In `test_sync_wilderness_provisions_one_gate_exit_per_authored_gate` and `test_sync_wilderness_is_idempotent`, replace `WildernessGateExit.objects.all().count(), 3` with:

    ```python
    WildernessGateExit.objects.all().count(),
    sum(len(d.wilderness_entry.gates) for d in current().settlements.values() if d.wilderness_entry is not None),
    ```

    Import `current` from `world.maps.map_data` inside each method.
  - In `test_provisioned_gates_are_immediately_traversable`, replace `(854, 1024)` with `_approach("w")` and `(850, 1021)` with `_approach("n")`. Add a module-level function:

    ```python
    def _approach(return_direction):
        from elosern_map_core.authoring import gate_approach_cell
        from world.maps import geography
        from world.maps.map_data import current

        document = current().settlements["capital_altoria"]
        cell = geography.current().locations.locations["capital_altoria"].cell
        return gate_approach_cell(document.wilderness_geometry(cell), return_direction)
    ```

  - In the same test, replace `self._gate_exits()[1][0]` with `next(e for e in self._gate_exits()[1] if e.db.gate_direction == "w")`, and the south one with the same pattern using `"n"`.
  - In `test_sync_wilderness_provisions_one_gate_exit_per_authored_gate`, the per-room `len(gates) == 1` checks hold only while each of those rooms carries one gate. Replace them with `len([g for g in gates if g.db.gate_direction == "w"]) == 1`, and the south check with the same pattern using `"n"`.

  Check: `grep -nE "3500:2850|twenty_one|fifty_two|854, 1024|850, 1021|count\(\), 3\)" world/maps/tests/test_bootstrap.py` prints nothing, and the module passes. Run it class by class if the guard reports more than 100 tests.

## 5. City walkthrough (`world/maps/tests/test_city_walkthrough.py`)

- [x] 5.1 In `test_walk_from_limbo_to_central_plaza_and_render`, replace the three `next(...)` lookups by key (南大道, 大道北段, 中央廣場) with a breadth-first walk over spawned exits from `south_gate` that stops at the first `AnchorRoom`:
  ```python
          plaza = None
          seen, frontier = {south_gate}, [south_gate]
          while frontier and plaza is None:
              room = frontier.pop(0)
              for exit_obj in room.exits:
                  nxt = exit_obj.destination
                  if isinstance(nxt, AnchorRoom):
                      plaza = nxt
                      break
                  if isinstance(nxt, GridRoom) and nxt not in seen:
                      seen.add(nxt)
                      frontier.append(nxt)
  ```
  Keep the following assertions (`assertIsInstance(plaza, AnchorRoom)`, the `anchor_key` check, the render).
- [x] 5.2 In `test_every_room_is_reachable_from_south_gate`, replace `21` with `len(current().settlements["capital_altoria"].nodes)` and import `current` from `world.maps.map_data`.

  Check: `grep -n "南大道\|大道北段\|, 21)" world/maps/tests/test_city_walkthrough.py` prints nothing, and the module passes.

## 6. City movement cost (`world/maps/tests/test_city_movement_cost.py`)

- [x] 6.1 Add `_polyline_metres` and the `assertChargedFor` mixin method from design D2. The mixin is a small class `_ChargeAssertions` that the test class also inherits. Delete `SOUTH_GATE_TO_AVENUE_SECONDS` and its comment line (`南門 (3050,150) -> ...`), and keep `HIDDEN_PATH_TO_PLAZA_SECONDS`.
- [x] 6.2 In `test_fresh_intra_city_traversal_advances_clock_by_move`:
  - Replace the `"南大道"` lookup with `city_exit = next(e for e in south_gate.exits if isinstance(e, CostedXYZExit))`.
  - Compute `document = current().settlements["capital_altoria"]`.
  - Find the road: `road = next(r for r in document.roads if r.source == south_gate.sparse_node_id and r.destination == city_exit.destination.sparse_node_id)`.
  - Build `points = [document.nodes[road.source].coordinate, *[(b.x_m, b.y_m) for b in road.bends], document.nodes[road.destination].coordinate]`.
  - Assert `self.char1.location == city_exit.destination` instead of comparing keys.
  - With `delta = tick - before`, assert `self.assertChargedFor(delta, _polyline_metres(points))` and `assertNotEqual(delta, MOVE)`.

  Check: `grep -n "724\|南大道" world/maps/tests/test_city_movement_cost.py` prints nothing, and the module passes.

## 7. City–wilderness roundtrip (`world/maps/tests/test_city_wilderness_roundtrip.py`)

- [x] 7.1 Add `_polyline_metres` and the `_ChargeAssertions` mixin (design D2), and make `CityWildernessRoundTripTests` inherit the mixin. Replace the constant `GATE_APPROACH_SECONDS = 811` and its comment with a function:
  ```python
  def _gate_approach_metres():
      from world.maps import geography
      from world.maps.map_data import current

      document = current().settlements["capital_altoria"]
      cell_x, cell_y = geography.current().locations.locations[document.location_ref].cell
      anchor_x, anchor_y = document.local_anchor_m
      gate_x, gate_y = document.nodes[_EAST_GATE.destination.object_id].coordinate
      gate_world = (1000 * cell_x + 500 + gate_x - anchor_x, 1000 * cell_y + 500 + gate_y - anchor_y)
      approach_world = (1000 * EAST_APPROACH[0] + 500, 1000 * EAST_APPROACH[1] + 500)
      return _polyline_metres([gate_world, approach_world])
  ```

  In `test_full_round_trip_leaves_no_leaked_bookkeeping`, replace the `assertEqual(advances, [...])` and the total-tick assertion with these assertions:
  - `advances[1] == advances[2] == WILDERNESS_STEP_SECONDS`;
  - `advances[0] == advances[3]`;
  - `self.assertChargedFor(advances[0], _gate_approach_metres())`;
  - `get_world_clock().tick == before + sum(advances)`.

  Apply the same pattern to every other use of `GATE_APPROACH_SECONDS`: the charged delta of a gate crossing must satisfy `assertChargedFor(delta, _gate_approach_metres())`. Keep `WILDERNESS_STEP_SECONDS`.
- [x] 7.2 In `test_intra_city_grid_traversal_advances_clock_by_move`, apply the same rewrite as task 6.2: any `CostedXYZExit` of the south gate, checked with `assertChargedFor` against the document road's polyline metres. This replaces the `"南大道"` lookups and `before + 724`.

  Check: `grep -nE "811|724|6500,3010|南大道" world/maps/tests/test_city_wilderness_roundtrip.py` prints nothing, and the module passes.

## 8. Geography source (`world/maps/tests/test_geography_source.py`)

- [x] 8.1 In `test_retained_adapter_keeps_its_snapshot_coordinates`, replace the three `(3500, 2850)` arguments with `anchor_xy`. Define it at the top of the method as `anchor_xy = map_data.current().settlements["capital_altoria"].local_anchor_m`, using `from world.maps import map_data`. Check: the module passes.

## 9. Canary proof (temporary data, never committed)

- [x] 9.1 Apply the canary. Create `content/maps/settlements/town_scarp.yaml` with exactly this content:
  ```yaml
  version: 1
  kind: settlement
  id: town_scarp
  location_ref: town_scarp
  options:
    map_visual_range: 2
    map_mode: nodes
  exit_prototype:
    prototype_parent: xyz_exit
    typeclass: typeclasses.exits.CostedXYZExit
  nodes:
    central_plaza:
      x_m: 400
      y_m: 300
      prototype_parent: anchor_room
      key: 金絲雀廣場
      desc: 測試用的廣場。
      anchor_key: town_scarp
      typeclass:
      scene_archetype: city_street
    east_gate:
      x_m: 700
      y_m: 300
      prototype_parent: grid_room
      key: 金絲雀東門
      desc: 測試用的東門。
      anchor_key:
      typeclass:
      scene_archetype: city_street
    west_gate:
      x_m: 100
      y_m: 300
      prototype_parent: grid_room
      key: 金絲雀西門
      desc: 測試用的西門。
      anchor_key:
      typeclass:
      scene_archetype: city_street
  roads:
    - source: central_plaza
      destination: east_gate
      direction: e
    - source: east_gate
      destination: central_plaza
      direction: w
    - source: central_plaza
      destination: west_gate
      direction: w
    - source: west_gate
      destination: central_plaza
      direction: e
  wilderness_entry:
    shape:
      - "##"
    offset:
      dx: 0
      dy: 0
    gates:
      - return_direction: w
        destination_node: east_gate
      - return_direction: e
        destination_node: west_gate
  city_gate:
  ```
  Then make these edits in `content/maps/settlements/capital_altoria.yaml`:
  - set `south_gate.x_m` to `3090` and `east_gate.x_m` to `6540`;
  - add a node `canary_lane` with every node field: `x_m: 3620`, `y_m: 2960`, `prototype_parent: grid_room`, `key: 金絲雀巷`, `desc: 金絲雀測試。`, `anchor_key:` empty, `typeclass:` empty, `scene_archetype: city_street`;
  - append two roads: `central_plaza → canary_lane`, direction `ne`, and `canary_lane → central_plaza`, direction `sw`;
  - under `wilderness_entry.gates`, after the `w`/`east_gate` entry, append two gates: `return_direction: s` with `destination_node: palace_forecourt`, and `return_direction: e` with `destination_node: craft_alley`.

  In `content/maps/locations.yaml`, under `capital_altoria:` → `cell:`, change `cell_x: 850` to `cell_x: 851`.

  Run `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`. Check: `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` prints `district partition: current`, and it reports no structure error and no game-adoption problem.
- [ ] 9.2 With the canary applied, run every module below, one per command. Use `uv run evennia test --keepdb --settings settings.py <label>` for Evennia modules and `uv run --locked python -m unittest <label>` for the `tests.` module. Record each failure in a scratch note. Run a module class by class if the guard reports more than 100 tests.

  `commands.tests.test_localized.test_xyz_grid_and_help tests.test_map_core_contract typeclasses.tests.test_exit_movement_cost typeclasses.tests.test_exits typeclasses.tests.test_map_discovery typeclasses.tests.test_npc_dialogue web.webclient.actions.tests.test_exploration_actions.test_move_and_look web.webclient.actions.tests.test_node_ids web.webclient.actions.tests.test_travel_actions web.webclient.presentation.tests.test_area_map web.webclient.presentation.tests.test_exploration_panel.test_presenter web.webclient.presentation.tests.test_exploration_panel.test_wilderness_and_npc_titles web.webclient.presentation.tests.test_local_map.test_gate_capacity web.webclient.presentation.tests.test_local_map.test_gateway_resolution web.webclient.presentation.tests.test_local_map.test_grid_gateways web.webclient.presentation.tests.test_local_map.test_grid_helpers web.webclient.presentation.tests.test_local_map.test_per_gate_footprint web.webclient.presentation.tests.test_local_map.test_presenter web.webclient.presentation.tests.test_local_map.test_wilderness web.webclient.presentation.tests.test_map_quest_destinations web.webclient.presentation.tests.test_world_map world.lore.tests.test_anchor_placement world.lore.tests.test_map_district_content world.lore.tests.test_nations world.lore.tests.test_settlements world.lore.tests.test_sync world.lore.tests.test_wilderness_entry world.maps.tests.test_altoria_capital world.maps.tests.test_bootstrap world.maps.tests.test_city_movement_cost world.maps.tests.test_city_walkthrough world.maps.tests.test_city_wilderness_roundtrip world.maps.tests.test_geography_source world.maps.tests.test_limbo_room world.maps.tests.test_movement_roundtrip world.maps.tests.test_runtime_adoption world.maps.tests.test_settlement_reload world.maps.tests.test_sparse_graph world.maps.tests.test_static_map_references world.maps.tests.test_village_ciaran world.maps.tests.test_wilderness_destination world.maps.tests.test_wilderness_geography_contract world.maps.tests.test_wilderness_population world.maps.tests.test_wilderness_provider world.quests.tests.test_compile_blueprint world.quests.tests.test_compile_offline world.quests.tests.test_compile_registration world.quests.tests.test_definitions world.quests.tests.test_encounter_activation world.quests.tests.test_encounter_dispatch world.quests.tests.test_generated_dialogue_scenes world.quests.tests.test_package_proposal world.quests.tests.test_quests_observability world.quests.tests.test_room_observation world.quests.tests.test_scene_builder_offline world.quests.tests.test_scene_smoke world.quests.tests.test_story_dialogue world.quests.tests.test_story_effects world.rules.tests.test_dialogue_refresh_lifecycle world.rules.tests.test_guild_config.test_price_scaling world.rules.tests.test_guild_config.test_service_host_roster world.rules.tests.test_map_knowledge_integration world.rules.tests.test_movement world.rules.tests.test_movement_settlement world.rules.tests.test_party_follow world.rules.tests.test_party_follow_possession world.rules.tests.test_party_time_settlement world.rules.tests.test_sight world.rules.tests.test_travel_plan`

  Check: you have one recorded result per module.
- [ ] 9.3 For every module that failed in 9.2 but passed in a clean run (task 1.1, or a clean rerun of that module after a temporary revert), find the copied settlement value: a literal coordinate, count, duration, node key or roster. Rewrite it with the D1/D2 recipes in that module, keeping requirement IDs. A failure that has a real cause other than a copied settlement value is a finding to report, not something to fix here. Check: rerunning the module with the canary applied passes.
- [x] 9.4 Revert the canary: `rm content/maps/settlements/town_scarp.yaml` and `git checkout -- content/maps/settlements/capital_altoria.yaml content/maps/locations.yaml world/maps/data/district_partition.json`. Check: `git status --porcelain content world/maps/data` prints nothing, and `check_map_sources.py` exits 0 or prints the same result as before group 9.

## 10. Final checks

- [x] 10.1 Rerun every module edited in groups 2–9 on the clean tree. Check: each passes.
- [x] 10.2 Run `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.contract_gate`. Check: each exits 0, and traceability still reports `0 uncovered`.
- [x] 10.3 Run `openspec validate unpin-settlement-map-data --strict`. Check: it prints `is valid`.
