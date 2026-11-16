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
- **No elven temple.** Neither village has a building of worship. The lore
  keeps elven faith unknown to outsiders.
- **Places are life scenes, not service buildings.** No signboards, no
  shopkeeper wording.
- **幽月谷村 prose stays non-sexual.** The Eolas look like children for life.
  Every node and room description in that village, the bath included, covers
  only daily life, work and magic practice.

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

| Node ID | Name | Content |
| --- | --- | --- |
| `forest_trail` | 深林獸徑 | The only way in or out, leading to the northern deep forest. Monster horns and claws the villagers brought back hang beside it. |
| `brook_head` | 溪源 | The village's drinking water and its stone trough. The brook runs south across the valley floor. |
| `proving_ground` | 試法坪 | All magic practice and experiment happens here. The ground is scorched, frozen and cracked in patches. Far from the dwellings, near the trail. |
| `hot_spring` | 溫泉浴場 | An open-air hot spring under the valley wall, with stone-ringed pools. The village bathes, washes clothes and talks here. |
| `valley_floor` | 谷底空地 | Anchor room. Where the village gathers. |
| `silk_grove` | 蛛絲林 | Spiders kept for silk, the cloth of the white traditional dress. |
| `cliff_dwellings` | 岩屋坡 | Dwellings cut into the valley wall, laundry at the doors. Personal homes attach here later. |
| `terrace_gardens` | 石階菜畦 | Terraces of roots, beans and herbs. |
| `kiln_yard` | 窯場 | The shared kiln for pottery and glass, also used to bake flatbread. |

`valley_floor` is the single `anchor_room` with `anchor_key:
elven_village_eolas`. Scene archetypes: `city_street` for `valley_floor`,
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
loop. The map spans about 600 m by 600 m, the same scale as 暗影谷村.

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

| Node ID | Name | Content |
| --- | --- | --- |
| `leaf_veiled_path` | 葉隱小徑 | The only way in or out. Hanging boughs hide the opening. |
| `light_court` | 林間光庭 | Anchor room. A gap in the canopy lets full sunlight down. Where the village gathers. |
| `archery_lane` | 靶道 | Archery and light magic are both practised here. Targets nailed to trunks, swinging wooden tags further off. |
| `blossom_garden` | 花蕊蜜園 | Beehives and flower beds, the source of candied blossom. |
| `forest_brook` | 林溪 | Drinking water, laundry, washing vegetables. |
| `bathing_pool` | 林泉浴場 | An open-air pool fed from the brook, ringed by sun-warmed stones. |
| `forest_plots` | 林間菜圃 | Vegetable beds and fruit trees in the gaps between the giants. |
| `craft_glade` | 木作空地 | The shared woodworking ground: bows, arrows, bridge repairs, weaving. |
| `root_dwellings` | 樹根屋 | Ground-level dwellings built between buttress roots. |
| `canopy_walk` | 樹冠吊橋 | Canopy-level dwellings, platforms joined by rope bridges. |
| `lookout_bough` | 瞭望枝 | The top bough of the tallest tree, with a view of the eastern plain. Hunting parties read the weather here. |

`light_court` is the single `anchor_room` with `anchor_key:
elven_village_fionnen`. Scene archetypes: `city_street` for `light_court`,
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
loop. The map spans about 800 m by 700 m.

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
`bathing_pool`, 溪池浴場, joined to `stream_bend` by one two-way road. No
existing ID, coordinate or direction changes. The existing contract test
requires the village graph to stay a tree; a single leaf keeps that true.

### Courier stations

`world.narrative.player_correspondence` grants the letter service to a room
through a `PlaceDefinition` with `letter_service=True`. Each new station
therefore needs:

- a `SETTLEMENT_REGISTRY` row for the village (`ELVEN_VILLAGE` archetype);
- a `PLACE_REGISTRY` row of kind `COURIER_STATION`, joined to the interior
  room, written beside the two existing station rows.

Existing tests list every place key (`world/lore/tests/test_settlements.py`,
`world/rules/tests/test_guild_config/test_service_host_roster.py`). They are
updated with the two new keys. The other shared interiors get no place row:
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

The change is hand-written data, following the `map-data-authoring` skill. It
adds no OpenSpec change, no specification and no new test: specifications and
tests in this project define logic, not game data.

Work happens in a worktree under `.claude/worktrees/`, not the primary
checkout. Order:

1. Run the check script once for a baseline.
2. 幽月谷村: settlement document, then its four interiors.
3. 翠綠森林村: settlement document, then its four interiors.
4. 暗影谷村: the bath node.
5. Python rows for the two courier stations; update the listing tests.
6. Regenerate the partition after the last source edit, then the reference
   context.
7. Revise the lore document.

One commit per village, one for the courier rows, one for the documents.

## 9. Verification

- `check_map_sources.py` exits 0.
- `python -m tools.settlement_synthesis lint <map_id>` reports no error for
  the three village maps.
- Captured images of both new maps are read and match the sketches above.
- Tests that load the world and the place registry pass: the map tests, the
  settlement lore tests and the service host roster tests.
- In a running game, each village can be entered from the wilderness, every
  node reached, every shared interior entered, and a letter sent from each
  new courier station.
