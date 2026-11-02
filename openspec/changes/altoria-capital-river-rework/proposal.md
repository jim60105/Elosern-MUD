# Proposal

## Why

The local map of `capital_altoria` is unresearched development data:

- **Water.** Its `quay` (碼頭埠) and `riverbank_road` (河岸道) nodes describe a working river port. The location cell (850, 1024) is about 13 km from the nearest river, `capital_river`. `settlement-terrain-fit`'s lint therefore reports both nodes as `fit_water_role_dry`.
- **Size.** The footprint is a hand-drawn 40-cell mask. The 600,000-person budget is 13 cells, and the street extent is about 5 × 6 km. The tier wants 28 nodes, but the map has 21.

The lore supports moving the town to the river. Its `geographic_constraint` reads "riverfront below northern terraces". The south gate's own description says the town began as a crossing (渡口) and climbed the rock behind it. `capital_river` also has a ford at (861, 1040), 2 cells south of the proposed cell.

## What Changes

- **Data.** Move `locations.capital_altoria.cell` from (850, 1024) to (861, 1042). That cell is on the north bank, 2 cells north of the `capital_river` ford at (861, 1040). `place_sites.py` reports it as walkable, in `western_hills_valleys`, nominal nation `altoria`. This is the default answer to the quay-versus-river question and is flagged for user confirmation; see design D1 for the alternatives.
- **Data.** Regenerate `content/maps/settlements/capital_altoria.yaml` with `generate capital_altoria --replace --bind … --gates s,e`. The result is a `river_crossing` layout:
  - a 13-cell footprint that reaches the ford;
  - 28 nodes, among them a new `ford_crossing` node, two more neighbour-facing gates, approach streets and lanes;
  - new positions, roads and directions.
  - All 21 existing node ids are bound, so every interior doorway, the district landmark (`central_plaza`), the city gate (`south_gate`) and the `n`/`w` wilderness gates on `south_gate`/`east_gate` keep their ids. The places and service hosts keep their attachments, and existing prose is kept.
- **Data.** Write zh-TW prose for the new nodes with the `prose` command. Correct a kept description only where the brief shows that its site cue is now false.
- **Docs.** In `docs/lore/settlement-locations.md` (zh-TW), lines 7 and 501, replace the room and road counts ("二十一間房", "二十六條連結") and the fixed walking chain with count-free wording.
- **Regenerated.** `world/maps/data/district_partition.json`.
- Spec-less. `unpin-settlement-map-data` has already removed every spec and test pin this rework would break.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a game-data change, and `skip_specs: true` is set.

## Impact

- `content/maps/locations.yaml`, which changes one cell.
- `content/maps/settlements/capital_altoria.yaml`, which is rewritten through the codec with its header comments kept.
- `world/maps/data/district_partition.json`, which is regenerated.
- `docs/lore/settlement-locations.md`, two sentences.
- No Python lore, interiors, `content/map-reference-context.json` or specs change. Tests change only when task 4.2 finds a residual copied-data pin, which it rewrites with the derivation recipe, keeping the module's requirement IDs.
- The district landmark moves with the location. Its ≥100 km Voronoi spacing is checked by `check_map_sources.py`.
- `docs/development/sparse-settlement-graphs.md` quotes the old coordinates as historical design examples. They are left unchanged and noted there with one sentence.
- Human-reviewed, not tested: the editor look, the prose tone and whether the relocation is acceptable lore-wise. The checklist is `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: unpin-settlement-map-data
- depends-on: settlement-rework-and-prose
- depends-on: settlement-sync-cost-probe
- conflicts: `world/maps/data/district_partition.json` and `content/maps/locations.yaml` are also rewritten by `grandia-settlement-maps`, `altoria-settlement-maps` and `valhalla-settlement-maps`. Each of those depends on this change, so they land one after another.
