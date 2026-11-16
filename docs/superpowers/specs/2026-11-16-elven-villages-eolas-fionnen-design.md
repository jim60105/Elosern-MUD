# Elven villages: 幽月谷村 and 翠綠森林村

Date: 2026-11-16

## 1. Purpose

Two of the three elven villages exist only as a continent cell and a
population: `elven_village_eolas` (幽月谷村, 80 people) and
`elven_village_fionnen` (翠綠森林村, 120 people). Only `elven_village_ciaran`
(暗影谷村) has a local map.

This design gives both villages a local map and their shared interiors, adds a
public bath to all three villages, and revises
`docs/lore/settlement-locations.md` to match.

## Status

This design became the OpenSpec change `elven-villages-eolas-fionnen`. The
change's own `design.md` is the authority for implementation. Planning found
facts this document did not have, and where the two differ the change is
right:

- **Tests.** Five existing assertions pin shipped data, not three. The two
  this document missed are in `world/quests/tests/test_definitions.py`, which
  names `elven_village_fionnen` as a location without a map, and in
  `world/maps/tests/test_bootstrap/test_bootstrap_selection.py`, which walks
  every place after syncing two maps. All five become logic assertions.
- **Entrance directions.** `return_direction` is `s` for 幽月谷村 and `w` for
  翠綠森林村. The check script accepts any direction, so it cannot confirm
  the choice as sections 4 and 5 say; the outward exit is the opposite of
  `return_direction`.
- **Regeneration.** `world/maps/data/road_network.json` goes stale as well as
  the partition and the reference context.
- **暗影谷村 bath node.** It sits at (781, 14), direction `se` from
  `stream_bend`, on a straight road. An existing test requires every road in
  that village to be straight.
- **City gates.** Each new `city_gate` adds a one-way exit from the starting
  room 虛境, and a character's first traversal sets `home` to that village.
  暗影谷村 already works this way, and the user confirmed both new villages
  keep it.
- **Other documents.** One sentence each in
  `docs/development/evennia-testing-guide.md` and
  `docs/development/narrative-memory-and-recall.md` counts gate maps or
  courier stations and is corrected by the change.

## 2. Scope

In scope:

- One settlement document per village: nodes, roads, wilderness entry, city
  gate.
- Shared interiors only: spaces the whole village uses. None has a host.
- A courier station in each new village, the one functional shared place
  暗影谷村 has. This needs Python lore rows (section 6).
- One new bath node in the existing 暗影谷村 map.
- Lore document revisions (section 7).

Out of scope, left for a later design:

- Personal homes and their residents' names.
- Service hosts, shop assortments, commerce offers and dialogue.
- Room artwork. No new interior sets `art_key`.
- Any change to `locations.yaml`. Both cells stay where they are.

## 3. Design rules for both villages

- **Lived in and self-sufficient.** Each village shows where its people get
  water, grow or gather food, make cloth and tools, wash, and sleep.
- **No functional place missing.** Every functional shared place 暗影谷村 has
  must exist. Today that is one: the courier station.
- **Elements have no places.** Magic is practised in one spot per village, not
  at a site per element.
- **No grid.** Neither map is laid out on a grid. Nodes sit at irregular
  positions, roads differ in length, and no two roads run parallel or meet at
  right angles by design. Roads that follow a brook, a valley wall or a line
  of trunks carry `bends`. The diagrams below show which places connect; they
  are drawn in text and look squarer than the maps are. The coordinate tables
  give the shape.
- **No elven temple.** Neither village has a building of worship. The lore
  keeps elven faith unknown to outsiders.
- **Places are life scenes, not service buildings.** No signboards, no
  shopkeeper wording.
- **Prose register.** Node and room descriptions follow the existing 暗影谷村
  nodes and interiors: landscape, livelihood and daily life.

## 4. 幽月谷村 (`elven_village_eolas`)

A small valley that feeds and clothes itself. Villagers garden, keep spiders
for silk and fire pottery. In spare hours they try magic on the proving
ground, and when they want an opponent they walk the game trail into the
northern deep forest to fight monsters.

```
          深林獸徑 (entrance, facing north)
               │
   試法坪 ─── 溪源 ─── 溫泉浴場
               │          │
   蛛絲林 ─ 谷底空地 ─── 岩屋坡
               │   ╲
          石階菜畦   窯場
```

### Nodes (9)

| Node ID | Name | `x_m`, `y_m` | Content |
| --- | --- | --- | --- |
| `forest_trail` | 深林獸徑 | 372, 655 | The only way in or out, leading to the northern deep forest. Monster horns and claws the villagers brought back hang beside it. |
| `brook_head` | 溪源 | 318, 512 | The village's drinking water and its stone trough. The brook runs south across the valley floor. |
| `proving_ground` | 試法坪 | 96, 548 | All magic practice and experiment happens here. The ground is scorched, frozen and cracked in patches. Far from the dwellings, near the trail. |
| `hot_spring` | 溫泉浴場 | 497, 468 | An open-air hot spring under the valley wall, with stone-ringed pools. The village bathes, washes clothes and talks here. |
| `valley_floor` | 谷底空地 | 286, 322 | Anchor room. Where the village gathers. |
| `silk_grove` | 蛛絲林 | 72, 268 | Spiders kept for silk, the cloth of the white traditional dress. |
| `cliff_dwellings` | 岩屋坡 | 468, 297 | Dwellings cut into the valley wall, laundry at the doors. Personal homes attach here later. |
| `terrace_gardens` | 石階菜畦 | 241, 148 | Terraces of roots, beans and herbs. |
| `kiln_yard` | 窯場 | 412, 121 | The shared kiln for pottery and glass, also used to bake flatbread. |

`valley_floor` is the single `anchor_room` with `anchor_key:
elven_village_eolas`. Coordinates are metres in the local frame, north up. If the settlement lint
objects to a position, the implementer moves the node and keeps the layout
irregular. Scene archetypes: `city_street` for `valley_floor`,
`forest_path` for `forest_trail` and `silk_grove`, `mountain_path` for the
rest.

### Roads

All roads are two-way, written as two directed entries.

| From | To | Direction (return) |
| --- | --- | --- |
| `forest_trail` | `brook_head` | s (n) |
| `brook_head` | `proving_ground` | w (e) |
| `brook_head` | `hot_spring` | e (w) |
| `brook_head` | `valley_floor` | s (n) |
| `hot_spring` | `cliff_dwellings` | s (n) |
| `valley_floor` | `cliff_dwellings` | e (w) |
| `valley_floor` | `silk_grove` | w (e) |
| `valley_floor` | `terrace_gardens` | s (n) |
| `valley_floor` | `kiln_yard` | se (nw) |

`brook_head`, `hot_spring`, `cliff_dwellings` and `valley_floor` form one
loop. The map spans about 430 m by 530 m, a narrow valley running north to
south.

Bends: `brook_head` to `valley_floor` follows the brook through (338, 418);
`hot_spring` to `cliff_dwellings` follows the valley wall through (521, 383);
`valley_floor` to `kiln_yard` skirts the terraces through (371, 236). Each
return road carries the same points in reverse.

### Entrance

A concealed point entry: `shape: ['#']`, `offset: {dx: 0, dy: 0}`, one gate
with `destination_node: forest_trail`. `city_gate.node` is `forest_trail`,
`exit_key` 深林獸徑. The entrance faces north. The implementer picks the
`return_direction` value that puts the approach on the north side and confirms
it with the check script; all four neighbour cells of (1410, 2150) are
walkable.

### Shared interiors (4)

| Interior and room ID | Name | Opens from | Notes |
| --- | --- | --- | --- |
| `eolas_shelter` | 共食棚 | `valley_floor` | Where the whole village eats. |
| `eolas_silverfeather` | 銀羽驛站・幽月谷分站 | `valley_floor` | Functional: send and collect letters. |
| `eolas_library` | 圖書館 | `cliff_dwellings` | Centuries of experiment notes and copied texts. Nobody runs it; anyone may read. |
| `eolas_storehouse` | 儲糧窖 | `terrace_gardens` | The village's stored food and seed. `cave_interior`. |

The other three use `tavern_interior`. Each interior has one room whose ID
equals the interior ID.

## 5. 翠綠森林村 (`elven_village_fionnen`)

A village in a forest of giant trees, lived in on two levels: the ground and
the canopy. Its centre is a clearing where sunlight falls straight down.
Villagers keep bees, garden and work wood. Archery and light magic are
practised on the same range.

```
   瞭望枝 ── 樹冠吊橋        靶道
               │           ╱
   樹根屋 ── 林間光庭 ──── 葉隱小徑 (entrance, facing east)
     │          │    ╲
  林泉浴場 ── 林溪     花蕊蜜園
               │
   木作空地 ─ 林間菜圃
```

### Nodes (11)

| Node ID | Name | `x_m`, `y_m` | Content |
| --- | --- | --- | --- |
| `leaf_veiled_path` | 葉隱小徑 | 742, 388 | The only way in or out. Hanging boughs hide the opening. |
| `light_court` | 林間光庭 | 428, 352 | Anchor room. A gap in the canopy lets full sunlight down. Where the village gathers. |
| `archery_lane` | 靶道 | 618, 566 | Archery and light magic are both practised here. Targets nailed to trunks, swinging wooden tags further off. |
| `blossom_garden` | 花蕊蜜園 | 603, 196 | Beehives and flower beds, the source of candied blossom. |
| `forest_brook` | 林溪 | 478, 178 | Drinking water, laundry, washing vegetables. |
| `bathing_pool` | 林泉浴場 | 268, 118 | An open-air pool fed from the brook, ringed by sun-warmed stones. |
| `forest_plots` | 林間菜圃 | 446, 38 | Vegetable beds and fruit trees in the gaps between the giants. |
| `craft_glade` | 木作空地 | 236, 22 | The shared woodworking ground: bows, arrows, bridge repairs, weaving. |
| `root_dwellings` | 樹根屋 | 214, 318 | Ground-level dwellings built between buttress roots. |
| `canopy_walk` | 樹冠吊橋 | 392, 548 | Canopy-level dwellings, platforms joined by rope bridges. |
| `lookout_bough` | 瞭望枝 | 176, 590 | The top bough of the tallest tree, with a view of the eastern plain. Hunting parties read the weather here. |

`light_court` is the single `anchor_room` with `anchor_key:
elven_village_fionnen`. Coordinates follow the same rule as 幽月谷村. Scene archetypes: `city_street` for `light_court`,
`forest_path` for the rest. Personal homes attach to `root_dwellings` and
`canopy_walk` later.

### Roads

| From | To | Direction (return) |
| --- | --- | --- |
| `leaf_veiled_path` | `light_court` | w (e) |
| `light_court` | `archery_lane` | ne (sw) |
| `light_court` | `blossom_garden` | se (nw) |
| `light_court` | `canopy_walk` | n (s) |
| `light_court` | `root_dwellings` | w (e) |
| `light_court` | `forest_brook` | s (n) |
| `canopy_walk` | `lookout_bough` | w (e) |
| `root_dwellings` | `bathing_pool` | s (n) |
| `bathing_pool` | `forest_brook` | e (w) |
| `forest_brook` | `forest_plots` | s (n) |
| `forest_plots` | `craft_glade` | w (e) |

`light_court`, `forest_brook`, `bathing_pool` and `root_dwellings` form one
loop. The map spans about 570 m by 570 m.

Bends: `leaf_veiled_path` to `light_court` winds between trunks through
(634, 412) and (531, 371); `bathing_pool` to `forest_brook` follows the water
through (372, 131); `canopy_walk` to `lookout_bough` sags like a rope bridge
through (287, 556). Each return road carries the same points in reverse.

### Entrance

A concealed point entry with one gate, `destination_node: leaf_veiled_path`.
`city_gate.node` is `leaf_veiled_path`, `exit_key` 葉隱小徑. The entrance
faces east. The implementer picks the matching `return_direction` and confirms
it with the check script; all four neighbour cells of (1465, 1237) are
walkable.

### Shared interiors (4)

| Interior and room ID | Name | Opens from | Notes |
| --- | --- | --- | --- |
| `fionnen_shelter` | 共食棚 | `light_court` | Where the whole village eats. |
| `fionnen_silverfeather` | 銀羽驛站・翠綠森林分站 | `light_court` | Functional: send and collect letters. |
| `fionnen_honey_house` | 蜜漬房 | `blossom_garden` | Shared candying room and food store. |
| `fionnen_bow_shed` | 弓棚 | `archery_lane` | Shared bows, arrows and strings. Anyone takes what they need. |

All four use `tavern_interior`.

## 6. 暗影谷村 and the courier stations

### Bath node in 暗影谷村

Add one node to `content/maps/settlements/elven_village_ciaran.yaml`:
`bathing_pool`, 溪池浴場, joined to `stream_bend` by one two-way road, placed off the existing lines of
the map. No
existing ID, coordinate or direction changes. The existing contract test
requires the village graph to stay a tree; a single leaf keeps that true.

### Courier stations

`world.narrative.player_correspondence` grants the letter service to a room
through a `PlaceDefinition` with `letter_service=True`. Each new station
therefore needs:

- a `SETTLEMENT_REGISTRY` row for the village (`ELVEN_VILLAGE` archetype);
- a `PLACE_REGISTRY` row of kind `COURIER_STATION`, joined to the interior
  room, written beside the two existing station rows.

Three existing assertions pin the registry's contents and will fail when the
rows are added: the ordered key list and the key-to-kind table in
`world/lore/tests/test_settlements.py`, and the host-less key set in
`world/rules/tests/test_guild_config/test_service_host_roster.py`. These
assert game data. The new keys are not appended to them. Each is rewritten to
assert the logic it stands for:

- order: the registry is the per-settlement slices concatenated in their
  declared order, followed by the courier stations;
- kind: every place's kind is a member of the closed vocabulary, and a
  trading home is still `HOME`;
- host-less: a place is host-less exactly when it declares none of the host
  identity fields, and every other place declares all of them.

The other shared interiors get no place row:
a standalone interior needs none, and rows for them arrive with the host
design.

## 7. Lore document revisions

In `docs/lore/settlement-locations.md`:

- **Public bath.** Rewrite the elven paragraph: all three villages have a
  public bath, an open-air pool at a natural water source, with no separate
  areas and no keeper. Matrix cell 公共浴場 × 精靈村落 changes from 無 to 變.
- **Library.** 幽月谷村 alone keeps a library, because the Eolas write their
  experiments down. The other two villages pass knowledge by word of mouth.
  It is a room of notes, not an academy. Matrix cell 魔法學院與圖書館 ×
  精靈村落 changes from 無 to 變, with this note.
- **Deep-dive section.** Remove the bath from the list of facilities
  incompatible with elven society.
- **Status.** Update "3 座，其中暗影谷村有地圖" and the last item of 未來擴充
  方向 to say all three villages have maps and shared places, and that homes
  and service hosts for the two new villages are still to come.
- **Per-village cases.** Add a short case description of each new village,
  drawn from sections 4 and 5.

Other documents that count village maps or list elven places are corrected
where the implementer finds them stale.

## 8. Delivery

The change is hand-written game data, following the `map-data-authoring`
skill. It goes through OpenSpec as one proposal with no specification delta
and no new test: specifications and tests in this project define logic, not
game data. The only test edits are the three rewrites in section 6, which
remove data pins.

Order of work:

1. Run the check script once for a baseline.
2. 幽月谷村: settlement document, then its four interiors.
3. 翠綠森林村: settlement document, then its four interiors.
4. 暗影谷村: the bath node.
5. Python rows for the two courier stations; rewrite the three data-pinning
   assertions.
6. Regenerate the partition after the last source edit, then the reference
   context.
7. Revise the lore document.

One commit per village, one for the courier rows, one for the documents.

## 9. Verification

- `check_map_sources.py` exits 0.
- `python -m tools.settlement_synthesis lint <map_id>` reports no error for
  the three village maps.
- Captured images of all three village maps are read. They show the
  connections in sections 4 to 6 and no grid.
- The existing suites that load the world and the place registry still pass.
  No assertion names a node, room or place added by this design.
- In a running game, each village can be entered from the wilderness, every
  node reached, every shared interior entered, and a letter sent from each
  new courier station.
