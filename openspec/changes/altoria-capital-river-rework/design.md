# Design

## Context

See proposal.md (Why). Facts verified on master at proposal time:

- `capital_river` flows westward. Its route starts at (1150, 1060) and runs toward (830, 1031). Near the city its raster occupies (862–867, 1040) and (856–860, 1039), with the ford at (861, 1040). The cells (861, 1041) and (861, 1042) are land on the north bank. (861, 1039) is land on the south bank. The elevation bands around the city are 5–6, which is mild relief.
- `place_sites.py` reports (861, 1042): `walkable=True water_cell=False region=western_hills_valleys nation=altoria river=2`.
- The default budget for `capital_altoria` gives 13 footprint cells, envelope radius about 1,987 m, 28 nodes, 4 gates and loop ratio 0.35. The reach is `ceil(sqrt(13)/2)+1 = 3`, so the ford is within reach and the morphology is `river_crossing`.
- Nodes that something joins on:
  - interior doorways: `academy`, `bath_forecourt`, `craft_alley`, `east_market`, `great_temple`, `guild_forecourt`, `inn_lane`, `market_street`, `noble_quarter`, `palace_forecourt`, `south_avenue`, `south_gate`, `training_ground`;
  - the district landmark `central_plaza`;
  - the city gate `south_gate`;
  - the wilderness gates `n → south_gate` and `w → east_gate`.

  `content/map-reference-context.json` has no `settlement_node:` incoming references.

## Goals / Non-Goals

**Goals:**
- Altoria passes the terrain-fit lint, its quay and riverbank stand on the river, and it matches the research size budget.
- Every id and attachment is preserved.

**Non-Goals:**
- new interiors or places;
- changing Python lore;
- fine fitting such as bends or district shaping, which is a later editor pass by the user;
- Valhalla, whose capital needs no river: its lore says "highland forest and tribal routes".

## Decisions

### D1. Relocate the capital to the north bank (default; confirm with the user)

These are the options for the quay-versus-river mismatch:

| Option | Effect | Verdict |
| --- | --- | --- |
| A. Move the cell to (861, 1042), on the north bank by the ford | The river is south, the terraces climb north, and the ford feeds the south gate. This matches "riverfront below northern terraces", the south gate's 渡口 origin and the existing "從碼頭沿著北岸向東" riverbank prose. | **Default** |
| B. Move to the south bank, around (850, 1034) | The river lies north, which contradicts "below northern terraces". | Rejected |
| C. Keep the cell and redraw `capital_river` north of it | This edits continent terrain: elevation, partition, every river consumer and the ford. | Rejected as out of scope |
| D. Keep the cell and drop the water roles | This contradicts the lore and the existing quay interior prose. | Rejected |

Option A changes the world position of everything in Altoria by about (+11 km, +19 km), and the district partition is regenerated. If the user rejects A before this change is applied, stop. The change has to be re-proposed with the user's chosen option.

### D2. Binding table (exact file content)

Write `<scratchpad>/altoria_bind.json` with exactly this content. The order matters for `nearest:`.

```json
{"bindings": {
  "central_plaza": "central_plaza",
  "south_gate": "south_gate",
  "east_gate": "east_gate",
  "quay": "river_quay",
  "riverbank_road": "riverbank",
  "market_street": "market_street",
  "guild_forecourt": "guild_forecourt",
  "craft_alley": "craft_alley",
  "east_market": "exchange_forecourt",
  "inn_lane": "inn_lane",
  "bath_forecourt": "bath_forecourt",
  "great_temple": "temple_forecourt",
  "palace_forecourt": "palace_forecourt",
  "noble_quarter": "noble_quarter",
  "training_ground": "training_ground",
  "academy": "academy",
  "south_avenue": "nearest:south_gate",
  "north_avenue": "nearest:central_plaza",
  "holy_steps": "nearest:temple_forecourt",
  "upper_gate": "nearest:palace_forecourt",
  "old_wall_ruins": "nearest:market_street"
}}
```

The roles match the existing meanings:
- `east_market` keeps the merchant hall and the alchemist, so it binds to `exchange_forecourt`;
- `quay` is a river quay;
- `south_avenue` is the first street inside the south gate.

The forced gates are `--gates s,e`. They keep the `n` return gate on `south_gate` and the `w` return gate on `east_gate`, which the residual test assumptions in `unpin-settlement-map-data` D4 rely on. The two other gates come from the generator's own capital, neighbour and ford rules.

### D3. Prose

After the replace, `brief capital_altoria` lists the slots that came with `desc_empty: true`:
- `ford_crossing`;
- the two generated gates;
- the approach streets;
- the lanes;
- any unbound catalogue slot.

Write prose for each of them to `<scratchpad>/altoria_prose.json`, following `docs/development/settlement-synthesis.md` § Prose pass. Also reread the kept descriptions of the 21 bound nodes against the brief's bearings, and rewrite only clauses that are now false. For example, a node described as uphill now lies downhill of the plaza. Apply everything with one `prose` run.

### D4. Lore document wording (zh-TW, exact replacements)

- In line 7, replace `重新建置為一座二十一間房的三層城市` with `重新建置為一座沿河北岸、由渡口向北層層攀升的三層城市`. Replace the sentence `旅人由南門入城、經南大道與大道北段抵中央廣場，東門則直接面向荒野。` with `旅人由南門渡河入城，沿大道上行抵中央廣場；其餘城門各自面向鄰近的城鎮與荒野。`.
- In line 501, replace `從零重建為三層、二十一間房、二十六條連結的王都第一版` with `從零重建為三層的王都第一版，其後再依河道與人口規模重新配置`.

## Risks / Trade-offs

- [`river_crossing` places the south gate's approach on the south bank (861, 1039) only if the reach path runs straight down x=861] → BFS from (861, 1042) to the ford (861, 1040) is a straight 2-step path, so this holds. Task 2.3 checks the written gate approach.
- [Moving 19 km changes which district owns surrounding wilderness] → The partition is regenerated, and `check_map_sources.py` verifies landmark spacing.
- [Kept prose conflicts with new geometry] → D3 covers it with a reread of the 21 kept descriptions. The user's editor review is the final check.
- [Tests that still assume Altoria data] → The canary in `unpin-settlement-map-data` ran exactly this kind of change. Task 4.2 reruns the same module list on the real data.

## Migration Plan

Pre-release, so no save migration is needed. Stored map knowledge for old Altoria coordinates falls back through the existing metric-cutover convergence by node identity. Rollback is `git revert` of the data commit plus partition regeneration.
