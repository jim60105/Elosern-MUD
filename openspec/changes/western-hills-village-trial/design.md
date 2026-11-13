# Design

## Context

The tools exist after wave 2:

| Tool | Command | Role here |
| --- | --- | --- |
| Road generator | `uv run --locked python -m tools.road_network` | Stage one is unchanged by villages and hamlets. Stage two gives each village one spur from its cell. |
| Settlement generator | `uv run --locked python -m tools.settlement_synthesis generate --missing --nation altoria --kind <village or hamlet>` | Writes a one-cell map whose gates are the road cells touching the location cell. A village with no road is refused. |
| Terrain-fit lint | `uv run --locked python -m tools.settlement_synthesis lint` | Reports `fit_entrance_mismatch` when a map's gates no longer match the roads. |
| Spacing validation | `uv run --locked python -m tools.settlement_spacing` | Minimum spacing, road gaps inside completed areas, and placement identity. |
| Site check | `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/place_sites.py CANDIDATES.json` | Walkability, water, region and nation of candidate cells. |

Scope of this change: the trial rectangle of the western hills around `town_scarp`: region `western_hills_valleys`, cells x 1000 to 1340 and y 501 to 950, both inclusive.

## Goals / Non-Goals

**Goals:**

- Every road gap that lies wholly inside the completed areas after this change is at most 75 km.
- Every new village has a spur, a map and prose; every new hamlet has a map and prose.
- All checks of D7 pass.

**Non-Goals:**

- No code change under `tools/`, `packages/`, `world/` (except `ANCHOR_LORE` rows), `web/` or `typeclasses/`. If a tool looks wrong, stop and report.
- No service host, interior, shop, guild branch or church.
- No district, no landmark, no change to an existing location's cell or kind, no edit to an existing settlement map.
- No feature nodes beyond what the generator emits.
- No settlement outside the scope above, except the boundary rule of D2.
- No settlement of another people, and none in a region with no nation.
- No tests for the placement script, and no documentation of it.

## Decisions

### D1. Placement script

Write the placement script in `openspec/changes/western-hills-village-trial/snippets/` (for example `place.py`), together with its candidate JSON files. Start from nothing. It is a working tool: it reads `content/maps/locations.yaml`, `world/maps/data/road_network.json` and the terrain through `elosern_map_core`, and prints candidates. It never writes a map source; the implementing agent writes approved rows.

The script should rank candidates by the distribution targets of the tiers design §5, which are targets and not limits:

- villages: about 70% on a trunk road cell or within 5 km of one, about 30% between 20 and 60 km from a trunk at a site with a geographic reason;
- hamlets: about 80% on a road cell, spurs included; about 20% with no road, 15 to 30 km from a village or town;
- about one village to two hamlets.

### D2. Where a settlement may stand

- Inside the scope of this change. Exception: to close a road gap that crosses the boundary into an area completed earlier, a hamlet may be placed on the earlier side of the boundary when no site on this side works. Name each such hamlet in the hand-off.
- On a walkable cell that is not water, not another location's cell, not a footprint cell or gate approach cell of an existing map, not a harbour site and not a district landmark cell.
- An on-road hamlet stands on a cell of `road_network.json`. It must be an inner cell of a road, not the first or last cell of any road (those are gate approach cells of other settlements).
- A village on a trunk stands on an inner trunk cell under the same rule.

### D3. Approval criteria

Before writing a candidate, confirm all four criteria of the tiers design §8.2:

1. Spacing. A hamlet is at least 15 km in a straight line from every capital, city, town, port, village and hamlet. A village is at least 40 km from every capital, city, town, port and village. Use `spacing_exemption` only for a site whose design requires it, and write the reason in English.
2. Geographic reason. Each site has one: a valley floor, a ford, a road junction, a lake shore, a mine, a pass foot. It goes into `geographic_constraint`.
3. Name. Names follow the terrain, waterway and neighbours of the site: a ford, a slope, a mill, a mine, for example 柳渡村 `village_willow_ford` or 石坡 `hamlet_stone_slope`. Never reuse the name of an existing location, and never use beastfolk or elven vocabulary. The display name and the ID are unique across all locations. An ID is fixed once written.
4. Monster habitats. The cell and its 8 neighbours lie in no rectangle of any `EcologyZone.rectangles` and on no `MonsterSite.coordinates` of `world/lore/monster_placement.py`, and the world still composes (D7, step 1). Resolve a conflict by moving the settlement. Adjust a habitat only when no site within 10 km works, and then stop and report first: a habitat edit is outside this change's file list.

### D4. Row formats

`content/maps/locations.yaml`, appended after the last existing location:

```yaml
  village_willow_ford:
    kind: village
    display_name_zh: 柳渡村
    description: Farming village at a ford of the upper hills river.
    cell:
      cell_x: 1200
      cell_y: 640
    geographic_constraint: Valley floor at a river ford on the trunk road
    scene_archetype:
```

The example values are illustrative, not a site to place. `description` and `geographic_constraint` are English. IDs use the prefix `village_` or `hamlet_`.

`world/lore/anchors.py`, appended to `ANCHOR_LORE` after the last row, under one new comment line `# Altoria Kingdom villages and hamlets: western-hills-village-trial.`:

```python
    "village_willow_ford": AnchorLore("altoria", 1_200, None),
```

- The nation is `altoria` for every row of this change.
- Population: 300 to 2,000 for a village and 50 to 300 for a hamlet, higher where the site is better (a valley floor, a road junction), rounded to 10.
- Do not edit the existing comment lines that count settlements and people. Settlement populations are a sample and are never reconciled.

### D5. Order of work

The order is fixed, because hamlet sites depend on spurs and maps depend on roads:

1. Villages: propose, approve, write rows.
2. Regenerate (D6). Each new village now has a spur.
3. Hamlets: propose against the new road cells, approve, write rows.
4. Regenerate (D6). The roads do not move, because hamlets are not road nodes; this refreshes the signature.
5. Generate maps: villages first, then hamlets, with the two `generate --missing --nation altoria --kind …` commands. Run each with `--plan-only` first.
6. Prose for every new map (D5a).
7. Regenerate (D6), then add this change's area and validate (D7).

### D5a. Prose

For each new map run `uv run --locked python -m tools.settlement_synthesis brief <map_id>`, write `<scratchpad>/prose_<map_id>.json` and apply it with `uv run --locked python -m tools.settlement_synthesis prose <map_id> <file>`. Follow `docs/development/settlement-synthesis.md` § Prose pass. In addition:

- a village has a green with a well and a church front; a hamlet has a crossing and one farmstead;
- an entrance node names the road it meets, by the direction or the neighbour it leads to;
- shops, the guild branch and services are not mentioned as usable places: they do not exist yet.

Never hand-edit prose into the YAML.

### D6. Regeneration

Run in this order every time step D5 says "Regenerate":

1. `uv run --locked python -m tools.map_district_partition`
2. `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py --check`
3. `uv run --locked python -m tools.road_network --preview <scratch>/roads.png`, with `<scratch>` outside the repository
4. `uv run --locked python -m tools.map_reference_context`

If road generation fails naming a village, that village's cell is unusable or cut off: move it. If the world does not compose because an ecology zone lost its usable birth interval, that is a habitat conflict under D3.

Between the regeneration of step 2 and the one of step 4 of D5, compare the trunk rows: `git diff world/maps/data/road_network.json` must show changes only in `nodes`, `fingerprint`, `source_signature` and rows that carry `spur_of`. A changed row without `spur_of` means stage one moved; stop and report.

### D7. Validation

Replace the content of `tools/settlement_spacing_areas.json`:

Before:

```json
{"areas": []}
```

After:

```json
{"areas": [
  {"id": "western_hills_trial", "region": "western_hills_valleys", "bounds": [1000, 501, 1340, 950]}
]}
```

Then all of these must hold:

1. `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` exits 0.
2. `uv run --locked python -m tools.settlement_spacing` prints `spacing: 0 problems`.
3. `uv run --locked python -m tools.settlement_synthesis lint` exits 0.
4. `uv run --locked python -m tools.road_network --check` and `uv run --locked python -m tools.map_reference_context --check` exit 0.

A `road_gap` problem is fixed by placing a hamlet on that road stretch (or a village, where the stretch is long), then repeating D5 from the matching step. Never fix a problem by removing the area entry, by adding an exemption without a design reason, or by editing a tool.

### D8. Lore marks

`docs/lore/settlement-locations.md` is Traditional Chinese. This change places the first human villages and hamlets, so these 〔提案〕 marks change. The wording is human-reviewed against that document; no test reads it.

- 〈聚落原型〉 table, rows 人類村莊 and 人類小村莊: remove the leading `〔提案〕` from the 代表範例 cell.
- 〈原型與地圖層級的對應〉 table, rows 人類村莊 and 人類小村莊: the 現況 cell becomes `〔已實作〕陸續建置中；尚無服務宿主`.
- The sentence above that table ending 「村莊與小村莊尚未落地，人口是設計目標。」 becomes 「村莊與小村莊的人口是 `world/lore/anchors.py` 現行資料必須落在的範圍。」
- 〈人類聚落的層級差異〉, first paragraph: 「村莊與小村莊兩層都是〔提案〕，尚未有地圖與服務宿主。」 becomes 「村莊與小村莊兩層的地圖〔已實作〕並陸續建置中，服務宿主仍是〔提案〕。」

Leave the beastfolk rows (獸王國部族村寨, 獸王國氏族營地) as 〔提案〕.

### D9. Test-suite timing record (never blocks)

At the start, run `uv run --locked --env-file=/tmp/mud-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap` and record `Ran N tests in X s`. Run it again at the end. Report both lines in the hand-off. The timing never stops the commit and is never asserted by a test. If the guard refuses the package label for discovering more than 100 tests, time `world.maps.tests.test_bootstrap_sync` instead, both times.

### D10. Trial findings

This is the trial of the tiers design. Write `openspec/changes/western-hills-village-trial/trial-findings.md` with these headings and a short factual answer under each:

1. Spacing values: could the 15 km, 40 km and 75 km rules all be met? Name every site where one could not, and why.
2. Node counts: did any generated map need more than the minimum?
3. Naming style: list every name that needed a second attempt, and the reason.
4. Monster habitats: list every conflict found and how it was resolved.
5. Tools: every refusal, lint finding or validation problem that looked wrong, with the command and its output.
6. Counts: villages, hamlets, on-road and off-road, and kilometres of spur added.

Do not change a rule, a threshold or a tool in this change. A finding that needs one is reported in the hand-off for the user, who revises the tiers design before the next placement change starts.

## Risks / Trade-offs

- [A village whose ID sorts before existing villages can move their spurs] → After every regeneration the lint reports any map whose gates no longer match (`fit_entrance_mismatch`). Fix by deleting that map's file, generating it again and redoing its prose. Prefer IDs that do not need this, but never rename an ID that an earlier change wrote.
- [A gap crossing the scope boundary stays over 75 km] → It is not checked until both sides are complete. The next change closes it under D2.
- [Hundreds of new public markers crowd the world map] → Human review item; capture the continent in task 5.3. No rule changes here.
- [Prose volume] → Each map has 2 to 5 nodes. Write the prose map by map, village maps first.
