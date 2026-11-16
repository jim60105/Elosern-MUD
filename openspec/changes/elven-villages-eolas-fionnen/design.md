# Design

## Context

See `proposal.md` for the motivation. This document is self-contained: it repeats every table, coordinate and code block the work needs. Its source is the approved design `docs/superpowers/specs/2026-11-16-elven-villages-eolas-fionnen-design.md` at commit `58abb913` on branch `chore/elven-villages`. That file is not on `master`, and the worker does not need it.

Facts established while planning, by reading the code and by a throwaway run of the whole change with placeholder prose in a scratch clone:

- A settlement document needs no Python registration. `location_ref` is the only link. Both locations already exist in `content/maps/locations.yaml` at cells (1410, 2150) and (1465, 1237); all four neighbour cells of each are walkable.
- `world.narrative.player_correspondence.branch_available` is the only consumer of `letter_service`. It needs one `PLACE_REGISTRY` row whose key equals the interior room ID. `validate_place_registry` requires the row's `settlement_key` to be in `SETTLEMENT_REGISTRY`.
- `elven_village` locations are already hidden by `world/rules/wilderness_disclosure.py`.
- With the coordinates, directions and bends below, `python -m tools.settlement_synthesis lint` reports `fit: 0 errors, 0 warnings` for all three village maps, and `check_map_sources.py` reports no structure error and no cross-file problem.
- Adding a settlement document makes two generated artifacts stale: `world/maps/data/district_partition.json` and `world/maps/data/road_network.json`. Adding the Python rows makes `content/map-reference-context.json` stale. In the scratch run the road network regenerated with only its `source_signature` line changed.
- The five test assertions rewritten in Decision 9 (9a to 9d and 9f) are the only failures found among the lore, correspondence, service-host-roster, quest-definition, bootstrap, adoption and interior suites run in the scratch clone. With the rewrites applied, those suites and `tools.contract_gate` passed there. The one addition made after that run, the `anchors()` assertion in 9d, was not run. Task groups 7 and 10 rerun everything.
- Every 暗影谷村 road must be straight: `test_village_ciaran.test_every_segment_length_is_its_meter_endpoint_distance` requires each road's length to equal the distance between its endpoints. A trial road with a bend failed it.
- `world/maps/tests/test_settlement_sources.py` and `world/maps/tests/test_settlement_reload.py` bind a synthetic document to `elven_village_eolas`. Both compose that document in isolation, without the shipped settlement files, so the real 幽月谷村 map does not collide with them.

Existing rules the new content must satisfy, each already enforced by an existing test:

- `world.lore.tests.test_room_prose_language`: every node `desc` and room `desc_zh` is Traditional Chinese prose, the name and the description are in the same language, and no description carries an authoring note or the character `§`.
- `world.maps.tests.test_village_ciaran`, for 暗影谷村 only: the graph is a tree; no road has bends; every node `key` has at least 2 Han characters and every `desc` at least 4; no `key` or `desc` contains an ASCII word or any of `wall`, `gate`, `guard`, `marketplace`, `shop`, `store`, `城牆`, `城門`, `衛兵`, `市集`, `市場`, `店`.

## Goals / Non-Goals

**Goals:**

- Both new villages can be entered from the wilderness, every node is reachable, every shared interior can be entered, and a letter can be sent from each new courier station.
- No existing test names a node, room or place added by this change.
- The three generated artifacts are current when the work ends.

**Non-Goals:**

- Personal homes, residents' names, service hosts, assortments, commerce offers, dialogue.
- Room artwork. No new interior sets `art_key`.
- Any edit to `content/maps/locations.yaml`, `content/maps/continent.yaml` or `content/maps/districts.yaml`.
- Any new test, any new requirement, any edit under `openspec/specs/`.
- `PLACE_REGISTRY` rows for the six non-courier interiors. A standalone interior needs none.
- Editor layout files under `content/map-editor-layouts/`.
- Renaming or moving any existing node, room, interior or place.

## Decisions

### Decision 1: No specification delta and no new test

`AGENTS.md` records the project rule: requirements and tests define logic, never game data, and a change that is only game data may ship without a spec. `.openspec.yaml` therefore sets `skip_specs: true`. The alternative, a delta listing the villages' nodes and rooms, would pin game data and is rejected.

### Decision 2: Hand-written YAML, shaped like `elven_village_ciaran`

Follow `.agents/skills/map-data-authoring/SKILL.md`. Do not use `tools.settlement_synthesis generate`; it produces a generated national-settlement layout, and these villages have an approved hand-drawn one.

Every settlement document starts with this header, with `<map_id>` replaced:

```yaml
version: 1
kind: settlement
id: <map_id>
location_ref: <map_id>
options:
  map_visual_range: 2
  map_mode: nodes
exit_prototype:
  prototype_parent: xyz_exit
  typeclass: typeclasses.exits.CostedXYZExit
```

Every node carries all eight fields, in this order:

```yaml
  <node_id>:
    x_m: <int>
    y_m: <int>
    prototype_parent: grid_room      # anchor_room for the one anchor node
    key: <name>
    desc: <zh-TW prose>
    anchor_key:                      # <map_id> for the one anchor node, else empty
    typeclass:
    scene_archetype: <archetype>
```

Every road in the tables below is two-way and is written as two directed entries: the listed direction from the first node to the second, and the listed return direction back. A road with bends lists its points from source to destination; the return entry lists the same points in reverse order:

```yaml
  - source: brook_head
    destination: valley_floor
    direction: s
    bends:
      - {x_m: 338, y_m: 418}
```

Coordinates are integer metres in the map's own frame; `y_m` grows north.

### Decision 3: 幽月谷村, `content/maps/settlements/elven_village_eolas.yaml`

A small valley running north to south that feeds and clothes itself. Villagers garden, keep spiders for silk and fire pottery. They practise magic on the proving ground and walk the game trail north to fight monsters.

Nodes (9). `valley_floor` is the anchor node: `prototype_parent: anchor_room`, `anchor_key: elven_village_eolas`.

| Node ID | `key` | `x_m` | `y_m` | `scene_archetype` | What the description covers |
| --- | --- | --- | --- | --- | --- |
| `forest_trail` | 深林獸徑 | 372 | 655 | `forest_path` | The only way in or out, leading to the northern deep forest. Monster horns and claws the villagers brought back hang beside it. |
| `brook_head` | 溪源 | 318 | 512 | `mountain_path` | The village's drinking water and its stone trough. The brook runs south across the valley floor. |
| `proving_ground` | 試法坪 | 96 | 548 | `mountain_path` | All magic practice and experiment happens here. The ground is scorched, frozen and cracked in patches. Far from the dwellings, near the trail. |
| `hot_spring` | 溫泉浴場 | 497 | 468 | `mountain_path` | An open-air hot spring under the valley wall, with stone-ringed pools. The village washes itself and its clothes here and talks. |
| `valley_floor` | 谷底空地 | 286 | 322 | `city_street` | Where the village gathers. |
| `silk_grove` | 蛛絲林 | 72 | 268 | `forest_path` | Spiders kept for silk, the cloth of the white traditional dress. |
| `cliff_dwellings` | 岩屋坡 | 468 | 297 | `mountain_path` | Dwellings cut into the valley wall, laundry at the doors. |
| `terrace_gardens` | 石階菜畦 | 241 | 148 | `mountain_path` | Terraces of roots, beans and herbs. |
| `kiln_yard` | 窯場 | 412 | 121 | `mountain_path` | The shared kiln for pottery and glass, also used to bake flatbread. |

Roads (9 two-way roads, 18 entries):

| From | To | Direction | Return | Bends, from → to |
| --- | --- | --- | --- | --- |
| `forest_trail` | `brook_head` | `s` | `n` | none |
| `brook_head` | `proving_ground` | `w` | `e` | none |
| `brook_head` | `hot_spring` | `e` | `w` | none |
| `brook_head` | `valley_floor` | `s` | `n` | (338, 418) |
| `hot_spring` | `cliff_dwellings` | `s` | `n` | (521, 383) |
| `valley_floor` | `cliff_dwellings` | `e` | `w` | none |
| `valley_floor` | `silk_grove` | `w` | `e` | none |
| `valley_floor` | `terrace_gardens` | `s` | `n` | none |
| `valley_floor` | `kiln_yard` | `se` | `nw` | (371, 236) |

`brook_head`, `hot_spring`, `cliff_dwellings` and `valley_floor` form one loop.

Entrance and city gate, verbatim:

```yaml
wilderness_entry:
  shape:
    - "#"
  offset:
    dx: 0
    dy: 0
  gates:
    - return_direction: s
      destination_node: forest_trail
city_gate:
  node: forest_trail
  exit_key: 深林獸徑
  exit_aliases: []
```

### Decision 4: 翠綠森林村, `content/maps/settlements/elven_village_fionnen.yaml`

A village in a forest of giant trees, lived in on two levels: the ground and the canopy. Its centre is a clearing where sunlight falls straight down. Villagers keep bees, garden and work wood. Archery and light magic are practised on the same range.

Nodes (11). `light_court` is the anchor node: `prototype_parent: anchor_room`, `anchor_key: elven_village_fionnen`.

| Node ID | `key` | `x_m` | `y_m` | `scene_archetype` | What the description covers |
| --- | --- | --- | --- | --- | --- |
| `leaf_veiled_path` | 葉隱小徑 | 742 | 388 | `forest_path` | The only way in or out. Hanging boughs hide the opening. |
| `light_court` | 林間光庭 | 428 | 352 | `city_street` | A gap in the canopy lets full sunlight down. Where the village gathers. |
| `archery_lane` | 靶道 | 618 | 566 | `forest_path` | Archery and light magic are both practised here. Targets nailed to trunks, swinging wooden tags further off. |
| `blossom_garden` | 花蕊蜜園 | 603 | 196 | `forest_path` | Beehives and flower beds, the source of candied blossom. |
| `forest_brook` | 林溪 | 478 | 178 | `forest_path` | Drinking water, laundry, washing vegetables. |
| `bathing_pool` | 林泉浴場 | 268 | 118 | `forest_path` | An open-air pool fed from the brook, ringed by sun-warmed stones. |
| `forest_plots` | 林間菜圃 | 446 | 38 | `forest_path` | Vegetable beds and fruit trees in the gaps between the giants. |
| `craft_glade` | 木作空地 | 236 | 22 | `forest_path` | The shared woodworking ground: bows, arrows, bridge repairs, weaving. |
| `root_dwellings` | 樹根屋 | 214 | 318 | `forest_path` | Ground-level dwellings built between buttress roots. |
| `canopy_walk` | 樹冠吊橋 | 392 | 548 | `forest_path` | Canopy-level dwellings, platforms joined by rope bridges. |
| `lookout_bough` | 瞭望枝 | 176 | 590 | `forest_path` | The top bough of the tallest tree, with a view of the eastern plain. Hunting parties read the weather here. |

Roads (11 two-way roads, 22 entries):

| From | To | Direction | Return | Bends, from → to |
| --- | --- | --- | --- | --- |
| `leaf_veiled_path` | `light_court` | `w` | `e` | (634, 412), (531, 371) |
| `light_court` | `archery_lane` | `ne` | `sw` | none |
| `light_court` | `blossom_garden` | `se` | `nw` | none |
| `light_court` | `canopy_walk` | `n` | `s` | none |
| `light_court` | `root_dwellings` | `w` | `e` | none |
| `light_court` | `forest_brook` | `s` | `n` | none |
| `canopy_walk` | `lookout_bough` | `w` | `e` | (287, 556) |
| `root_dwellings` | `bathing_pool` | `s` | `n` | none |
| `bathing_pool` | `forest_brook` | `e` | `w` | (372, 131) |
| `forest_brook` | `forest_plots` | `s` | `n` | none |
| `forest_plots` | `craft_glade` | `w` | `e` | none |

`light_court`, `forest_brook`, `bathing_pool` and `root_dwellings` form one loop.

Entrance and city gate, verbatim:

```yaml
wilderness_entry:
  shape:
    - "#"
  offset:
    dx: 0
    dy: 0
  gates:
    - return_direction: w
      destination_node: leaf_veiled_path
city_gate:
  node: leaf_veiled_path
  exit_key: 葉隱小徑
  exit_aliases: []
```

### Decision 5: `return_direction` is `s` for 幽月谷村 and `w` for 翠綠森林村

The source design says 幽月谷村's entrance faces north and 翠綠森林村's faces east, and leaves the value to be confirmed with the check script. The check script and the lint accept every direction for these two cells, so they cannot confirm it. The code decides it: `world/maps/bootstrap.py` computes the outward direction as `face = OPPOSITE_DIRECTION[gate.return_direction]` and gives the gate room's wilderness exit that direction as an alias. A north-facing entrance therefore has `return_direction: s`: the traveller stands on the village cell and steps south to enter, and leaves `forest_trail` by going north. An east-facing entrance has `return_direction: w`.

This also keeps the exit names clear: `forest_trail` has one road, direction `s`, so the outward alias `n` is free; `leaf_veiled_path` has one road, direction `w`, so the outward alias `e` is free. The alternative values `n` and `e` would give the gate rooms an outward alias equal to their only road direction.

The `city_gate` blocks come from the source design and have a player-visible effect, the same one 暗影谷村 has today. `world/maps/bootstrap.py` creates a one-way exit from the starting room 虛境 for every city gate row, so 虛境 gains the exits 深林獸徑 and 葉隱小徑. The first time a character takes one, that gate room becomes the character's `home` (`world/rules/city_gates.py`). No character-creation code reads the registry. This change keeps the city gates, following the 暗影谷村 precedent, and the review document states the effect so the human reviewer can confirm it is wanted.

### Decision 6: Eight host-less interiors, one room each

Each interior file is `content/maps/interiors/<interior_id>.yaml`. The room ID equals the interior ID. No `art_key` line. Shape, verbatim except the placeholders:

```yaml
version: 1
kind: interior
id: <interior_id>
rooms:
  <interior_id>:
    name_zh: <name_zh>
    desc_zh: <zh-TW prose>
    scene_archetype: <scene_archetype>
connections: []
exterior:
  settlement: <settlement>
  node: <node>
  room: <interior_id>
  doorway_key: <doorway_key>
  doorway_aliases:
  - <alias>
```

| Interior and room ID | `name_zh` | `settlement` | `node` | `doorway_key` | `doorway_aliases` | `scene_archetype` | What the description covers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `eolas_shelter` | 共食棚 | `elven_village_eolas` | `valley_floor` | 共食棚 | `shelter`, `communal shelter` | `tavern_interior` | Where the whole village eats. |
| `eolas_silverfeather` | 銀羽驛站・幽月谷分站 | `elven_village_eolas` | `valley_floor` | 銀羽驛站 | `courier` | `tavern_interior` | Letters are sent and collected here. |
| `eolas_library` | 圖書館 | `elven_village_eolas` | `cliff_dwellings` | 圖書館 | `library` | `tavern_interior` | Centuries of experiment notes and copied texts. Nobody runs it; anyone may read. |
| `eolas_storehouse` | 儲糧窖 | `elven_village_eolas` | `terrace_gardens` | 儲糧窖 | `storehouse`, `cellar` | `cave_interior` | The village's stored food and seed. |
| `fionnen_shelter` | 共食棚 | `elven_village_fionnen` | `light_court` | 共食棚 | `shelter`, `communal shelter` | `tavern_interior` | Where the whole village eats. |
| `fionnen_silverfeather` | 銀羽驛站・翠綠森林分站 | `elven_village_fionnen` | `light_court` | 銀羽驛站 | `courier` | `tavern_interior` | Letters are sent and collected here. |
| `fionnen_honey_house` | 蜜漬房 | `elven_village_fionnen` | `blossom_garden` | 蜜漬房 | `honey house` | `tavern_interior` | Shared candying room and food store. |
| `fionnen_bow_shed` | 弓棚 | `elven_village_fionnen` | `archery_lane` | 弓棚 | `bow shed` | `tavern_interior` | Shared bows, arrows and strings. Anyone takes what they need. |

The doorway keys and aliases are a planning choice modelled on `ciaran_shelter.yaml` and `ciaran_silverfeather.yaml`; the source design names only the rooms. Two interiors open from `valley_floor` and two from `light_court`; their doorway keys differ, as the game requires.

### Decision 7: One leaf node in 暗影谷村

Add to `content/maps/settlements/elven_village_ciaran.yaml`, after the last existing node:

```yaml
  bathing_pool:
    x_m: 781
    y_m: 14
    prototype_parent: grid_room
    key: 溪池浴場
    desc: <zh-TW prose>
    anchor_key:
    typeclass:
    scene_archetype: wilderness_path
```

and append to `roads`:

```yaml
  - source: stream_bend
    destination: bathing_pool
    direction: se
  - source: bathing_pool
    destination: stream_bend
    direction: nw
```

`stream_bend` sits at (689, 85) and has one outgoing road, `w`. The new node shares no `x_m` or `y_m` with any existing node, so it lies off the map's existing lines. It is a leaf, so the graph stays a tree. The road has no bends, because every 暗影谷村 road must be straight (see Context). Its description is an open-air pool where the stream widens below the village and must satisfy the `test_village_ciaran` text rules listed in Context. The coordinate is a planning choice; the source design fixes only the ID, the name and the neighbour.

### Decision 8: Python rows for the courier stations

In `world/lore/settlements/settlements.py`, add two entries to `SETTLEMENT_REGISTRY` after the `elven_village_ciaran` entry:

```python
    "elven_village_eolas": SettlementDefinition(
        key="elven_village_eolas",
        archetype=SettlementArchetype.ELVEN_VILLAGE,
    ),
    "elven_village_fionnen": SettlementDefinition(
        key="elven_village_fionnen",
        archetype=SettlementArchetype.ELVEN_VILLAGE,
    ),
```

In `world/lore/settlements/places.py`, add two `PlaceDefinition` entries inside the `PLACE_REGISTRY` comprehension, directly after the `ciaran_silverfeather` entry:

```python
        PlaceDefinition(
            key="eolas_silverfeather",
            settlement_key="elven_village_eolas",
            kind=PlaceKind.COURIER_STATION,
            room=interior_room_ref("eolas_silverfeather", "eolas_silverfeather"),
            letter_service=True,
        ),
        PlaceDefinition(
            key="fionnen_silverfeather",
            settlement_key="elven_village_fionnen",
            kind=PlaceKind.COURIER_STATION,
            room=interior_room_ref("fionnen_silverfeather", "fionnen_silverfeather"),
            letter_service=True,
        ),
```

No new slice module is created: the two rows sit beside the two existing courier rows. The alternative, `places_eolas.py` and `places_fionnen.py` slices, is deferred to the later host design, which is when those villages get rows of their own.

### Decision 9: Five data-dependent assertions become logic assertions

Each test keeps its name and its `@covers_requirement` decorators. Only the method body changes. No new key is appended anywhere.

**9a.** `world/lore/tests/test_settlements.py`, `PlaceRegistryTests.test_place_iteration_order_is_the_load_bearing_slice_order`. Replace the whole method, including its comment block and the literal key list, with:

```python
    def test_place_iteration_order_is_the_load_bearing_slice_order(self):
        # The derived roster and shop registry iterate this dict, and the
        # roster processes rows in dict order (sync_service_content). The
        # registry is therefore the per-settlement slices concatenated in
        # their declared order, each slice in its authored tuple order, with
        # the courier stations after the last slice. Which rows a slice holds
        # is game data and is not pinned here.
        from world.lore.settlements.places_altoria_lower import ROWS as lower
        from world.lore.settlements.places_altoria_middle import ROWS as middle
        from world.lore.settlements.places_altoria_upper import ROWS as upper
        from world.lore.settlements.places_ciaran import ROWS as village

        slice_keys = [row.key for row in (*lower, *middle, *upper, *village)]
        keys = list(PLACE_REGISTRY)
        self.assertEqual(keys[: len(slice_keys)], slice_keys)
        trailing = keys[len(slice_keys):]
        self.assertTrue(trailing)
        for key in trailing:
            with self.subTest(place=key):
                self.assertIs(PLACE_REGISTRY[key].kind, PlaceKind.COURIER_STATION)
```

**9b.** Same file, `PlaceRegistryTests.test_every_shipped_kind_describes_its_location`. Keep its two decorator lines. Replace the method body, including the `expected` table, with:

```python
    def test_every_shipped_kind_describes_its_location(self):
        # Each shipped row's kind is a member of the closed vocabulary. Which
        # kind a given row carries is game data and is not pinned here.
        for key, place in PLACE_REGISTRY.items():
            with self.subTest(place=key):
                self.assertIsInstance(place.kind, PlaceKind)
        # The worked example for the kind rule: a dwelling whose occupant
        # trades is still a home. Reclassifying such a row to its host's
        # capability leaves no trading home and fails here.
        trading_homes = [
            place
            for place in PLACE_REGISTRY.values()
            if place.kind is PlaceKind.HOME and place.assortment_keys
        ]
        self.assertTrue(trading_homes)
        for place in trading_homes:
            with self.subTest(place=place.key):
                self.assertIsNotNone(place_shop_identity(place))
                self.assertTrue(place_capabilities(place, "merchant"))
```

**9c.** `world/rules/tests/test_guild_config/test_service_host_roster.py`, `ServiceHostRosterTests.test_every_shipped_place_authors_a_complete_host_except_the_sanctioned_emptiness`. Keep its decorator. Replace the method body, including the literal key set, with:

```python
    def test_every_shipped_place_authors_a_complete_host_except_the_sanctioned_emptiness(self):
        # hostless-places neutrality gate: a shipped place is host-less
        # exactly when it declares none of the host identity fields, and every
        # other shipped place declares all of them. Which places are host-less
        # is game data and is not pinned here.
        for place in PLACE_REGISTRY.values():
            declared = [
                field
                for field in HOST_IDENTITY_FIELDS
                if getattr(place, field) is not None
            ]
            with self.subTest(place=place.key):
                if place_is_hostless(place):
                    self.assertEqual(declared, [])
                else:
                    self.assertEqual(declared, list(HOST_IDENTITY_FIELDS))
        # Every hosted place still contributes exactly one matching row, and
        # the host-less places contribute none.
        self._assert_rows_follow_the_places(validate_service_hosts())
```

**9d.** `world/quests/tests/test_definitions.py`, `test_lore_known_but_unplaced_anchor_is_rejected`. This test is not in the source design. It asserts that `elven_village_fionnen` has no placement, which stops being true when the village gets a map. Add `from unittest import mock` under the existing `import unittest` line, and add `from world.lore.anchors import anchors` under the existing `from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY` line. Keep the decorator. Replace the method body with:

```python
    def test_lore_known_but_unplaced_anchor_is_rejected(self):
        # The anchor is lore-known; its placement row is removed from the
        # registry the validator reads, so the case never depends on which
        # locations ship a local map.
        unplaced_key = anchor_locator().anchor_key
        self.assertIn(unplaced_key, anchors())
        self.assertIn(unplaced_key, ANCHOR_PLACEMENT_REGISTRY)
        remaining = {
            key: row
            for key, row in ANCHOR_PLACEMENT_REGISTRY.items()
            if key != unplaced_key
        }
        unplaced = QuestDefinition(
            key="anchor-unplaced",
            display_name="未落錨",
            quest_type=QuestType.EXPLORE,
            rank="F",
            stages=(
                QuestStage(
                    0,
                    reach(RoomLocator(DestinationKind.ANCHOR, anchor_key=unplaced_key)),
                ),
            ),
        )
        with mock.patch(
            "world.quests.definitions.ANCHOR_PLACEMENT_REGISTRY", remaining
        ):
            with self.assertRaises(QuestDefinitionError) as caught:
                register(unplaced)
        self.assertIn(unplaced_key, str(caught.exception))
        self.assertNotIn("anchor-unplaced", QUEST_DEFINITION_REGISTRY)
```

**9e.** `world/maps/tests/test_settlement_sources.py`: the comment above `_THIRD` says the synthetic settlement is "bound to an authored location that has no shipped local map". Replace that three-line comment with:

```python
#: A synthetic third settlement bound to an authored location. Each candidate
#: here is composed without the shipped settlement documents. Its ids
#: deliberately differ from the location it binds, so the location-derived
#: (not identity-derived) reverse navigation is exercised.
```

No assertion in that file changes.

**9f.** `world/maps/tests/test_bootstrap/test_bootstrap_selection.py`, `MetricCutoverTests.test_real_startup_converges_places_scene_art_and_quest_targets`. This test is not in the source design. It starts the world with only the capital and 暗影谷村 selected and then expects every `PLACE_REGISTRY` row to have a room. That stops being true when a place sits in another settlement. Change only the head of the final loop. Replace:

```python
        # Every service place's exterior resolves to its converged room and
        # every interior keeps its bidirectional doorway.
        for place in PLACE_REGISTRY.values():
            exterior = GridRoom.objects.filter_xyz(xyz=place_exterior_xyz(place)).first()
```

with:

```python
        # Every service place of a selected settlement resolves its exterior
        # to the converged room and keeps its bidirectional doorway. A place
        # whose settlement was not selected has no room to resolve.
        for place in PLACE_REGISTRY.values():
            if place_exterior_xyz(place)[2] not in CAPITAL_VILLAGE_MAP_IDS:
                continue
            exterior = GridRoom.objects.filter_xyz(xyz=place_exterior_xyz(place)).first()
```

The rest of the loop body is unchanged. `CAPITAL_VILLAGE_MAP_IDS` and `place_exterior_xyz` are already imported in that file.

Other pins of shipped data in these files (for example `PRE_SPLIT_PLACE_CAPTURE`) keep passing and are left alone: this change removes a pin only where the pin breaks.

### Decision 10: Regeneration order

After the last map source edit and the last Python lore edit, in this order:

1. `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py`
2. `uv run --locked python -m tools.road_network` (about 95 seconds, about 2.5 GiB of memory)
3. `uv run --locked python -m tools.map_reference_context`

The road network is not in the source design; the scratch run showed it goes stale. Any later edit to a settlement file, including a moved node, makes steps 1 and 2 stale again. Prose-only edits to a settlement file also count, because the partition signature covers file content. Interior files are not partition inputs.

### Decision 11: Prose guideline and the human-reviewed review document

Node and room descriptions in both new villages, and the new 暗影谷村 node, follow the register of the existing 暗影谷村 nodes and interiors (`content/maps/settlements/elven_village_ciaran.yaml`, `content/maps/interiors/ciaran_*.yaml`): landscape, livelihood and daily life, with each place written as a lived-in scene, not a service building. No signboards, no shopkeeper wording, no building of worship. Each description is one to three sentences of Traditional Chinese, written with the `chinese-content-writing-guideline` and `writing-style-guideline` skills. Magic is practised in one spot per village (試法坪, 靶道); no description invents a site per element.

Whether the prose reads well and whether the maps look irregular are human judgements. They are recorded in `docs/lore/elven-villages-map-review.md`, written in English, with these five sections:

1. **Scope**: the files this change authored.
2. **Map images**: for each of the three village maps, the capture command used, and what the image shows when read: which nodes connect, where the bends are, and whether any part reads as a grid.
3. **Prose review**: for each new node and room, one line confirming it follows the guideline above, or the correction made.
4. **Lore checks**: no temple, no signboard, one magic practice spot per village, entrances that do not read as gates.
5. **For the reviewer's decision**: one paragraph stating that the two new city gates add the exits 深林獸徑 and 葉隱小徑 to the starting room 虛境 and that the first traversal sets the character's `home` (Decision 5).

No test reads this document.

### Decision 12: Lore document edits in `docs/lore/settlement-locations.md`

All edits are Traditional Chinese, in the document's existing voice.

| Where (current text) | Edit |
| --- | --- |
| Line 58, table cell `〔已實作〕3 座，其中暗影谷村有地圖` | Say all three villages have a local map and shared places. |
| Line 87, matrix row 公共浴場, last column `無` | Change to `變`. |
| Line 92, matrix row 魔法學院與圖書館, last column `無` | Change to `變`. |
| Line 393, 〈公共浴場〉 聚落差異, the sentences from `精靈村落完全沒有「公共浴場」這個概念` to the end of the paragraph | Rewrite: all three villages have a public bath. It is an open-air pool at a natural water source (hot spring, forest pool, stream pool), with no separate areas and no keeper; washing, laundry and talk happen there as part of the day. Name the three: 溫泉浴場, 林泉浴場, 溪池浴場. Keep the sentence about 獸王國城邑 unchanged. |
| Line 495, 〈魔法學院與圖書館〉 聚落差異 | Take 精靈村落 out of the "全部沒有" list and add: 幽月谷村 alone keeps a library, because the Eolas write their experiments down; it is a room of notes that nobody runs, not an academy. The other two villages pass knowledge by word of mouth. No elven village has an academy. Reword the paragraph's closing sentence about 獸人 and 精靈 so it says neither has a reason to found a formal academy (學院), which stays true beside the library. |
| Line 521, 〈聚落差異深論〉, the list `公會分會、商會、光明教會神殿、公共浴場、衛兵城門、魔法學院、港口` | Remove 公共浴場 from the list. Keep 魔法學院. |
| Line 521, same paragraph, after the sentence that ends `不套用單一「精靈村」模板。` | Add a short case description of each new village, drawn from Decisions 3 and 4: what the village lives on, its gathering place, its bath, its practice ground, and its shared rooms. |
| Line 591, last item of 〈未來擴充方向〉 | Rewrite: all three villages now have maps and shared places; personal homes and service hosts for 幽月谷村 and 翠綠森林村 are still to come. |

The line numbers are those on `master` at `6deac2f4`; find each passage by its quoted text.

Two other documents carry a count that this change makes false. Each gets a one-sentence edit, in Traditional Chinese:

| File and current text | Edit |
| --- | --- |
| `docs/development/evennia-testing-guide.md`, the sentence that begins `宣告推導自 registry，不是複製 roster：今日是兩個 gate map` | Say the gate maps are the starting city and the three elven villages, with no number that the next map would falsify. |
| `docs/development/narrative-memory-and-recall.md`, the sentence `兩個聚落各有一個無宿主（hostless）的銀羽驛站分部。` | Say every settlement that has a courier station has one host-less 銀羽驛站 branch, with no count. |

A search of `docs/`, `README.md` and the `AGENTS.md` files found no other statement that only 暗影谷村 has a map. The scenario title "The registry carries exactly two rows today" in `openspec/specs/limbo-one-way-gates/spec.md` is left alone: its body already says the row count follows the source documents, and this change edits no spec.

## Risks / Trade-offs

- [The partition or road network is regenerated before the last settlement edit and goes stale] → Task group 6 regenerates after all source edits, and task 10.1 rechecks freshness at the end. A stale partition makes every test that loads the world fail, which is a loud failure.
- [A description trips an existing prose rule, such as the character 店 in the 暗影谷村 node] → The rules are listed in Context and each authoring task names its test.
- [The lint objects to a coordinate after prose or other edits] → The scratch run was clean with these exact values. If the lint reports an error, move only the node it names by the smallest amount that clears it, keep the coordinate off the `x_m` and `y_m` values of every other node, and record the move in the review document.
- [Another existing test pins data this change alters and was not run in the scratch clone] → Task group 10 runs the wider map, sight and presentation suites, which were not run while planning. If one fails because it compares against a literal roster, count or name, or because it walks a whole registry after starting only some of the maps, rewrite it to its logic as in Decision 9 and never append a new key; if it fails for another reason, stop and report.
- [Rewriting 9a to 9c loosens three data guards, and 9c now restates the registry validator's all-or-nothing host rule] → Intended. The project rule is that tests do not pin game data; the mechanisms (slice order, closed kind vocabulary, all-or-nothing host group) stay asserted.
- [The browser fixtures derive their map set from the city gate registry, so browser journeys seed four gate maps where they seeded two] → Slower seeding only. Not run while planning; task 10.6 names the check.
- [`retire-classic-art-assets` moves `master` while this change is applied] → It touches only art code and art specs; no file overlaps.

## Migration Plan

None. The project is pre-release. A development database picks up the new rooms on the next bootstrap synchronisation.
