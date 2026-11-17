# Elven villages map review

This document records the human judgement two parts of the change `elven-villages-eolas-fionnen` need, namely how the three village maps read when drawn, and whether the new Traditional Chinese prose keeps the register of the village that already shipped. No test reads this file.

## 1. Scope

Authored by the change:

- `content/maps/settlements/elven_village_eolas.yaml`, 幽月谷村, 9 nodes and 18 directed road entries.
- `content/maps/settlements/elven_village_fionnen.yaml`, 翠綠森林村, 11 nodes and 22 directed road entries.
- `content/maps/settlements/elven_village_ciaran.yaml`, one added leaf node `bathing_pool` (溪池浴場) and its two road entries, with no existing node, road or gate changed.
- `content/maps/interiors/eolas_shelter.yaml`, `eolas_silverfeather.yaml`, `eolas_library.yaml`, `eolas_storehouse.yaml`.
- `content/maps/interiors/fionnen_shelter.yaml`, `fionnen_silverfeather.yaml`, `fionnen_honey_house.yaml`, `fionnen_bow_shed.yaml`.

Neither new village moves a node from the planning coordinates, so this review records no correction. The terrain-fit lint reported `fit: 0 errors, 0 warnings` for all three maps, and `tools.settlement_spacing` reported `spacing: 0 problems`.

## 2. Map images

The capture runtime was prepared once from the map-authoring skill, then each map was drawn with the map id substituted:

```console
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view settlement --map <map_id> --format png \
    --output /tmp/elven-captures/<map_id>.png
```

The three images were captured after the last settlement edit and after the district partition, road network and reference context had been regenerated, so they show the shipped graph. Each PNG was opened and read, and the reading below compares it with the road table in the change design.

### 幽月谷村 (`elven_village_eolas`)

Nine nodes are drawn, each labelled in Traditional Chinese. 溪源 sits between the northern trail and the valley floor and is the only junction besides 谷底空地. The drawn connections are 深林獸徑 to 溪源, 試煉場 to 溪源, 溫泉浴場 to 溪源, 溪源 to 谷底空地, 溫泉浴場 to 岩屋坡, 谷底空地 to 岩屋坡, 谷底空地 to 蛛絲林, 谷底空地 to 石階菜畦, and 谷底空地 to 窯場. Nine connections for nine two-way roads, with no unlisted connection. Three bends are visible. The 溪源 to 谷底空地 road kinks slightly east before running south-west; the 溫泉浴場 to 岩屋坡 road turns east of the wall before dropping to the dwellings; the 谷底空地 to 窯場 road leaves south-east and then steepens. 溪源, 溫泉浴場, 岩屋坡 and 谷底空地 close the one loop the design names. The outline is a lopsided ring with three long spurs, and no part of it reads as a grid of rows and columns.

### 翠綠森林村 (`elven_village_fionnen`)

Eleven nodes are drawn. 林間光庭 is the hub and carries six of the eleven roads, spread at uneven angles rather than on a cross. The drawn connections are 葉隱小徑 to 林間光庭, 林間光庭 to 靶道, 林間光庭 to 花蕊蜜園, 林間光庭 to 樹冠吊橋, 林間光庭 to 樹根屋, 林間光庭 to 林溪, 樹冠吊橋 to 瞭望枝, 樹根屋 to 林泉浴場, 林泉浴場 to 林溪, 林溪 to 林間菜圃, and 林間菜圃 to 木作空地. Eleven connections for eleven two-way roads, with no unlisted connection. Three bends are visible. The entry road from 葉隱小徑 bends twice before reaching the court; the 樹冠吊橋 to 瞭望枝 road bends once; the 林泉浴場 to 林溪 road bends once at the brook's shoulder. 林間光庭, 林溪, 林泉浴場 and 樹根屋 close the one loop the design names. The two levels read as two clusters joined at the court, and no part of the drawing forms a grid.

### 暗影谷村 (`elven_village_ciaran`)

The existing ten nodes keep the positions and the straight roads they had, and the drawing still reads as an irregular chain. The new 溪池浴場 is a single leaf at the south-east end, hanging off 溪畔下游 with one straight road that runs south-east and has no bend. That is the only change in the picture, one extra node, one extra connection, and no new line between existing nodes. The graph stays a tree, and the new node shares no row or column with any other node.

## 3. Prose review

The guideline is the register of the shipped 暗影谷村 nodes and interiors, namely landscape, livelihood and daily life, with each place written as a lived-in scene in one to three sentences of Traditional Chinese, with no signboard, no shopkeeper wording and no building of worship. Every new description was checked against it; none needed a correction after the check.

### Nodes, 幽月谷村

| Node | Name | Review |
| --- | --- | --- |
| `forest_trail` | 深林獸徑 | A forest trail with the horns and claws of hunted monsters hung beside it; the village's only way in and out, so it reads as a path with a story rather than a gate. |
| `brook_head` | 溪源 | The spring, its stone trough and the barrels set down beside it; water and the sound of the brook carry the scene. |
| `proving_ground` | 試煉場 | Scorched, frozen and cracked ground far from the dwellings; magic practice is present as wear on the land, with no signboard and no instructor. |
| `hot_spring` | 溫泉浴場 | Steam, stone-ringed pools, washing and laundry; described as the day's washing place where talk finishes. |
| `valley_floor` | 谷底空地 | Trodden ground where the village meets, divides the day's work and children run; a lived-in gathering place. |
| `silk_grove` | 蛛絲林 | Spiders kept for silk and the white cloth woven from it, plus the quiet walk that keeps the webs intact. |
| `cliff_dwellings` | 岩屋坡 | Dwellings cut into the rock, laundry at the doors and lamps on the slope at dusk. |
| `terrace_gardens` | 石階菜畦 | Stone terraces of roots, beans and herbs with the stones picked out of the beds piled at the edge. |
| `kiln_yard` | 窯場 | One shared kiln for pottery and glass, flatbread baked against its wall, bread broken and shared. |

### Nodes, 翠綠森林村

| Node | Name | Review |
| --- | --- | --- |
| `leaf_veiled_path` | 葉隱小徑 | Hanging boughs hide the opening and the path shows itself only after pushing through; the entrance reads as forest, not as a gate. |
| `light_court` | 林間光庭 | A gap in the canopy, full sunlight on the ground, the village gathering and children chasing the light. |
| `archery_lane` | 靶道 | Targets nailed to trunks, swinging wooden tags further off, worn fletching on the ground; archery and light magic share one practice ground. |
| `blossom_garden` | 花蕊蜜園 | Flower beds, hives in the shade, honey and petals boiled down into candied blossom; work and food in one place. |
| `forest_brook` | 林溪 | Drinking water upstream, washing downstream, one wooden basin left on the stones. |
| `bathing_pool` | 林泉浴場 | A pool below the brook ringed by sun-warmed stones, washing and soaking with the day's talk. |
| `forest_plots` | 林間菜圃 | Vegetable beds between the giants, fruit trees mixed in, the surplus dried for winter. |
| `craft_glade` | 木作空地 | Low stools, stacked timber and shavings; bows, arrows, bridge boards and mending share the ground. |
| `root_dwellings` | 樹根屋 | Houses built between buttress roots, lamps inside at dusk and children's clothes on the roots. |
| `canopy_walk` | 樹冠吊橋 | Plank and rope bridges between doors, the sway in wind and the habit of walking without holding the rope. |
| `lookout_bough` | 瞭望枝 | The top bough of the tallest tree, the eastern plain in view, hunting parties reading cloud and wind before setting out. |

### Node, 暗影谷村

| Node | Name | Review |
| --- | --- | --- |
| `bathing_pool` | 溪池浴場 | A shallow pool where the stream widens below the village, rounded stones, washing and children in the shallows, lamps reflected at dusk; no ASCII text and none of the words the 暗影谷村 text rule forbids. |

### Rooms

| Room | Name | Review |
| --- | --- | --- |
| `eolas_shelter` | 共食棚 | Long table, low stools, dried herbs under the eaves; people bring their share and put the bowl back. No keeper and no price. |
| `eolas_silverfeather` | 銀羽驛站・幽月谷分站 | Letters sorted by destination, wax and paper on a low cabinet, nobody guarding the shelves. A working courier room written as a common shelf. |
| `eolas_library` | 圖書館 | Two rooms cut into the rock, centuries of experiment notes and copies, paper soft from use; unmanaged, anyone may read. A reading room, not an academy or a shrine. |
| `eolas_storehouse` | 儲糧窖 | A cool cellar with grain, roots and seed set out on shelves, take recorded by the taker; the smell of dry earth and husks. |
| `fionnen_shelter` | 共食棚 | A woven roof in the shade, a long table whose feet are sunk in the soil, people with their own share, never empty. |
| `fionnen_silverfeather` | 銀羽驛站・翠綠森林分站 | A letter rack against the trunk, pigeonholes for near and far post, wax and paper at the bottom, unlocked. |
| `fionnen_honey_house` | 蜜漬房 | Sealed jars of candied petals and fruit, the boiling pot still on the hearth, sweetness soaked into the wood. |
| `fionnen_bow_shed` | 弓棚 | Bows and bundled arrows on the wall, string on a spool, anyone takes what is needed and hangs the bow back; the repair corner holds old bows. No counter and no keeper. |

## 4. Lore checks

No temple. No node or room describes worship, an altar, a shrine or a priest. 幽月谷村's library is a room of written experiments that anyone may read, and 翠綠森林村 has no religious building at all.

No signboard. None of the new descriptions names a shop, a storefront, a counter or a keeper. The two courier rooms say outright that the shelves are unguarded, the storehouse records what the taker takes, and the bow shed lets anyone take what is needed. Trading in these villages stays in private homes, which this change does not author.

One magic practice spot per village. 幽月谷村 practises at 試煉場 and nowhere else; 翠綠森林村 practises at 靶道, where archery and light magic share the lane. No description invents a site per element, and 暗影谷村's existing 練刀場 is untouched.

Entrances that do not read as gates. 深林獸徑 is a monster trail whose branches carry trophies, 葉隱小徑 is an opening hidden by hanging boughs, and 暗影谷村's new 溪池浴場 is a leaf off 溪畔下游 at the water. None of the three contains a wall, a gate room or a guard, and the 暗影谷村 text rule that forbids those words still passes.
