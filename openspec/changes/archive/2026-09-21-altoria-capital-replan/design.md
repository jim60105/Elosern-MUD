## Context

The thirteen-node cross was built to prove the xyzgrid worked, and it did. It was never a city. `docs/lore/settlement-locations.md` says so at line 7 and tells the next author to rebuild rather than patch at line 500.

Two forces make now the time. The arithmetic one: five of thirteen nodes are taken, two are gates, twelve location types remain. The design one: everything downstream — where the cathedral sits relative to the palace, whether the market is inside or outside the old wall, whether a player climbing to the temple passes the academy — is decided by this map, so it must be decided before the content changes, not discovered by them.

## Goals / Non-Goals

**Goals.** A layout with an in-world reason for every street. Room for all nineteen places. Scenery that is not a shopfront. A palace. The five landed places keep everything except their address.

**Non-Goals.** No change to any place's identity, host, goods or prices. No new location content — this change ships an empty, walkable, well-shaped city, and the locations arrive after it. No change to how interiors, doorways or gates work.

## The city, and why it is that shape

聖潔王都 is a river town that climbed a rock. That single fact produces the whole layout.

**The lower city (Y=0–2)** is where the southern road meets the north bank. It is the oldest part and the most crowded, because it is the part that existed when the city was a crossing rather than a capital: a quay, a riverside road, the inn lane where travellers who arrive after the upper gates close have to stay, and the bathhouse that a river town gets before it gets anything else. The south gate at `(3,0)` is where the road from the wilderness enters.

**The middle city (Y=3)** is a belt, not a grid, because it follows the line of **the wall the city outgrew**. 舊城牆遺跡 at `(2,2)` is the surviving stub. When the wall came down the cleared strip along it became the widest continuous ground inside the city, so that is where the market went, and after the market the guild, the craft alley and the east market. This is the one long east–west street, and it is long for a reason that is visible in the ruin standing on it.

**The upper city (Y=4–6)** is the terrace above, reached by 聖階 — the steps that are also the last stretch of the pilgrim road. Everything that wanted height and distance is up here: the cathedral facing the top of the steps, the academy and the drill yard on either shoulder, the noble quarter behind, and the palace forecourt at the very top, above even the church. That ordering is a political statement and should read as one.

**The main street** is the pilgrim road: south gate → 南大道 → 大道北段 → 中央廣場 → 聖階 → 大神殿前. A player who walks straight in and keeps going arrives at the cathedral door, which is what the road was built for.

### The map

```
+ 0 1 2 3 4 5 6

6         #              (4,6) 王宮前庭
          |
5       #-#-#            (3,5) 貴族區前   (4,5) 上城門   (5,5) 學院前
        | |
4     #-#-#              (2,4) 校場外     (3,4) 聖階     (4,4) 大神殿前
     /  | |\
3   #-#-#-#-#-#          (1,3) 工匠巷 (2,3) 市場街 (3,3) 中央廣場
      | |                (4,3) 公會前 (5,3) 東市   (6,3) 東門
2     #-#                (2,2) 舊城牆遺跡 (3,2) 大道北段
      | |
1   #-#-#-#-#            (1,1) 碼頭埠 (2,1) 河岸道 (3,1) 南大道
        |                (4,1) 客棧巷 (5,1) 浴場前
0       #                (3,0) 南門

+ 0 1 2 3 4 5 6
```

Twenty-one nodes, twenty-six links, six cycles, verified against `XYMap.parse()`.

The two diagonals are shortcuts, and each has a reason. `(1,3)–(2,4)` is the path apprentices wear from the craft alley up to the drill yard. `(4,4)–(5,3)` is the pilgrims' slope from the east market to the cathedral, which exists because the proper route via the plaza and the steps is twice as long.

The silhouette is a teardrop: wide across the market belt, narrowing as it climbs, one node at the top. That is what a hill town looks like from above, and it is the reason the map is not a lattice.

### Where the landed five move

| Place | Was | Now | Why |
| --- | --- | --- | --- |
| 冒險者公會 | `(3,1)` 冒險者公會外 | `(4,3)` 公會前 | On the market belt, one block east of the plaza |
| 雜貨店 | `(1,2)` 市場街 | `(2,3)` 市場街 | The same street, kept by name |
| 鍛造鋪 | `(0,2)` 鐵匠鋪外 | `(1,3)` 工匠巷 | The west end of the belt, where the noisy trades went |
| 裁縫坊 | `(2,3)` 北大道 | `(1,3)` 工匠巷 | Shares the craft alley with the forge — that is what a craft alley is |
| 餐館 | `(2,1)` 南大道 | `(3,1)` 南大道 | The same street, kept by name |

Nothing else about them changes. Their keys, hosts, titles, goods, prices, interiors, descriptions and doorway names are untouched.

## Decisions

### The tree requirement is retired, deliberately

`sample-city-altoria` currently requires exactly twelve links forming a tree with no cycle. That was the right pin for scaffolding — it made the map trivially verifiable — and it is the wrong pin for a city. A tree means every pair of rooms has exactly one route, which is the topology of a corridor.

Nothing depends on acyclicity. `calculate_path_matrix` handles cycles; movement cost is charged per exit traversed, not per path; the wilderness and quest layers read coordinates, not topology. What replaces the pin is a specific cycle count, so the map is still exactly verifiable — six cycles, not "some".

### Two exteriors carry two doors

The craft alley hosts the forge and the tailor; the cathedral square hosts the sanctuary and its shop; the inn lane hosts the tavern and the inn; the east market hosts the alchemist and the merchant hall; the market street hosts the general store, the jeweller and the stalls. `_ensure_interior_doorways` already supports this: each interior gets its own 外 exit, and the exterior gets one doorway per place keyed by that place's authored doorway name.

The registry does not currently check that two places on one exterior have distinct doorway names. They would collide into one exit. This change **creates** that hazard — the forge and the tailor share 工匠巷 from here on — and gives the tailor a distinct name by hand. The guard that makes it impossible to get wrong is `altoria-place-slices`, which lands next; splitting it out keeps this change to the map and the registries that index into it, which are the part that cannot be separated.

### Scenery is grid rooms, not host-less places

Seven nodes carry no interior. They are ordinary `GridRoom`s with authored descriptions and nothing to enter. Making them place records with no host was considered and rejected: a place is a *location you go inside*, and a quayside is somewhere you stand. The `hostless-places` capability exists for interiors without a host — the palace, the market stalls, the village's communal shelter — not for open ground.

### The second gate moves and becomes real

Today's 北門 at `(2,4)` is a documented dead end reserved for a future wilderness link. The replan gives the capital an east gate at `(6,3)` at the far end of the market belt, which is where a road from a second direction would actually meet a river town's high street, and wires it as the second wilderness gate.

Its `return_direction` becomes `w`: a traveller approaching from the east travels west to enter. That follows the existing convention — the capital's south gate is `n` because you travel north into it — and it moves the approach cell from `(60, 103)` to `(63, 100)`.

## Risks

**The wilderness approach cell must be provider-valid and outside every footprint.** `(63, 100)` sits one cell east of the capital's 5×5 footprint. The village footprint is far away, so disjointness is not in doubt, but the provider rectangle bound is, and `validate_wilderness_entries` runs at every startup — a bad cell fails the whole lore load, not just the gate. The first task verifies the cell against `_in_provider_rect` before anything else is written.

**Coordinate churn is broad and shallow.** Every capital coordinate changes, so every test that names one fails. That is loud rather than dangerous: the failures are assertions, not silent behaviour changes, and the three registries plus five `exterior_xy` values are the complete set of production references — verified by grep, recorded in the tasks.

**Descriptions are authored in English.** Every existing room `desc` and every `room_desc_zh` in this codebase holds English prose despite the field name, so this change matches that. It is an inconsistency worth a change of its own; introducing Chinese descriptions here would leave the capital half in each language.
