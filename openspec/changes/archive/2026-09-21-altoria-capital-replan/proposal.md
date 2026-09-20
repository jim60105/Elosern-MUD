## Why

`docs/lore/settlement-locations.md` line 7 says the current capital map is scaffolding: 「目前的聖潔王都地圖只是開發初期為了跑通地圖系統而搭建的測試骨架」, and line 500 says to rebuild it from the document rather than patch it cell by cell, because 「落差是全面性的，補丁式修改只會讓兩份資料都不乾淨」.

The concrete blocker is arithmetic. The capital has thirteen nodes, five are already taken by landed places, and two of the remainder are the gates. Twelve location types are still unbuilt. There is nowhere to put them.

The deeper problem is that the thirteen-node cross has no in-world reason to be that shape. It is a plus sign. A capital of 600,000 that is the seat of both the crown and the Church of Light should read as a place that grew, and its map should answer the question "why is the street here".

## What Changes

- Replace `world/maps/altoria_capital.py`'s map with a twenty-one node layout on three terraces, with an in-world reason for its shape: **the city is a river town that climbed a rock.** The lower city hugs the north bank, the middle city runs along the line of the old wall the city outgrew, and the upper city sits on the terrace above, reached by the 聖階 steps. The main street is the pilgrim road from the south gate to the cathedral door.
- The layout is deliberately not a lattice: diagonal links where streets cut the corner, dead-end spurs, and a ring in the lower city that is the old wall line. Twenty-one nodes, twenty-six links, six cycles — **the tree requirement is retired**, because a city where every route is the only route is a corridor, not a city.
- Seven of the twenty-one nodes carry no interior at all. 碼頭埠, 舊城牆遺跡, 中央廣場, 聖階, 上城門, 東門 and 大道北段 are walkable scenery: the parts of a capital that exist to be moved through and looked at.
- Add 王宮: the palace forecourt is a grid node at the top of the climb, and the palace itself lands later as a plot-gated interior.
- Re-point the five landed places at their new exteriors. **Their identities, hosts, goods, prices and interiors are untouched** — only `exterior_xy` changes. 鍛造鋪 and 裁縫坊 now share 工匠巷, which is what a craft alley is.
- Move the three geography registries onto the new coordinates: the anchor plaza, the Limbo bridging gate, and the wilderness gates. The second wilderness gate becomes 東門 on the east edge and stops being the reserved dead end it is today.
- **BREAKING** for anything pinned to the old coordinates: every node coordinate changes. There are no users and no saved games; developer databases converge on the next startup sync.

## Capabilities

### Modified Capabilities
- `sample-city-altoria`: the node count, coordinate list, link count, tree topology and AnchorRoom coordinate all change; the interiors requirement restates which exteriors the landed places attach to.
- `limbo-one-way-gates`: the capital's bridging gate coordinate and exit key change.
- `wilderness-gateway`: the capital's two gate `grid_xy` values and one `return_direction` change.

## Impact

- `world/maps/altoria_capital.py` — new `MAPSTR` and twenty-one prototypes.
- `world/lore/anchor_placement.py`, `world/maps/city_gates.py`, `world/lore/wilderness_entry.py` — one row each.
  `anchor-placement` needs no spec delta: its scenarios compare the registry against the spawned AnchorRoom
  rather than naming a coordinate, so they keep holding as both move together.
- `world/lore/settlements/places_altoria.py` — five `exterior_xy` values, nothing else. The three-way terrace split and the doorway-collision rule are `altoria-place-slices`, which lands next.
- `world/maps/tests/`, `world/lore/tests/` — the coordinate and count assertions.
- `docs/lore/settlement-locations.md` — line 7 and line 500 stop describing the map as unbuilt scaffolding.
- `world/maps/map_data.py`, `world/maps/bootstrap.py`, `world/rules/` — untouched. The assembly imports the map; nothing reads a capital coordinate outside the three registries.
