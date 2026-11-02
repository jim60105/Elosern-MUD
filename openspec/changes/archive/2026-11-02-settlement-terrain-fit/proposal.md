# Proposal

## Why

Elosern has 3 capitals, 19 cities, 27 towns and 11 ports, but only `capital_altoria` and one elven village have local maps. Authoring the rest needs three things before any street graph is generated:

1. a terrain reading of each site: rivers, coast, fords, harbours, slope and neighbours;
2. a research-based size budget;
3. a check that a street graph actually fits its terrain.

There is no fit check today. Altoria's authored quay and riverbank nodes stand about 13 km from the nearest river (`capital_river`), and no tool notices. The map editor's hand edits need the same guard.

The two scales stay separate:

- The wilderness is a grid of 1 km cells. A cell centre lies at `(1000X+500, 1000Y+500)` m.
- Settlement streets are integer-metre graphs. Their polyline lengths drive walking time at 1.25 m/s.

A 3.5 km-wide capital therefore means about 45 minutes of walking. The footprint, in cells, and the street extent, in metres, both come from the same built-up area.

## What Changes

- New game-side tool package `tools/settlement_synthesis/` with three read-only commands run through `uv run --locked python -m tools.settlement_synthesis`:
  - `site <location>`: prints a site-context record. It lists each river and the sea within the search radius with distance and 8-way bearing. A river also gets its downstream bearing, taken from source-to-mouth route order. The record also lists fords, harbour sites, uphill bearing and relief, the nearest national settlements and the bearing to the settlement's own capital.
  - `budget <location>`: prints the size budget. Built-up area comes from the Cesaretti et al. (2016) population–area relation, area ∝ population^0.714, anchored at a stated reference density. Footprint cells are `max(2, ceil(area km²))`, which keeps every settlement multi-gate and never a concealed 1-cell entry. The envelope radius gives the metre extent. Node, gate and loop targets come from a log-scaled gameplay tier table: capital 28 nodes, then 18, 12, 10, 8 and 6 nodes at populations of 100k, 50k, 25k, 10k and below 10k.
  - `lint [map ...]`: the terrain-fit lint, in world metres:
    - errors: a water-edge node (an id with the word `quay`, `wharf`, `dock`, `docks`, `pier`, `landing`, `riverbank` or `waterfront`) more than 600 m from water; a road crossing inland water or sea with no `bridge`, `ford` or `ferry` endpoint; a node outside its multi-cell footprint; a node in water; a gate approach that is not walkable;
    - warnings: a gate node on the wrong side of the anchor; a road direction more than one octant from its geometry.
- The fantasy capitals (800k, 600k and 400k) are constraints the budget explains. It does not recompute them. The constants live in one `BudgetConfig`, and tests use synthetic configurations only.
- Skill documentation: the `map-data-authoring` skill (`SKILL.md`, `references/settlements.md` and `references/verification.md`) gains the commands, the scale rule and "run the lint after every settlement edit".
- The lint reports Altoria's existing quay mismatch on master. That is expected, and `altoria-capital-river-rework` resolves it. The lint is a workflow tool. This change adds no CI gate over shipped data.

## Capabilities

### New Capabilities

- `settlement-terrain-fit`: site-context derivation, the population-based size budget and the terrain-fit lint with its read-only command contract.

### Modified Capabilities

None.

## Impact

- New: `tools/settlement_synthesis/{__init__,geometry,terrain_view,site,budget,fit_lint,workspace,__main__}.py` and `tests/test_settlement_terrain_fit.py`. The test is synthetic only and registered in `.github/top-level-shards.json`.
- Docs: `.agents/skills/map-data-authoring/SKILL.md`, `references/settlements.md` and `references/verification.md`, plus a new `docs/development/settlement-synthesis.md`. That page records the scale rule, the density assumption with its sources, the tier table and the human-review checklist.
- Reads `world.lore.anchors.ANCHOR_LORE` for nation and population. A `--lore FILE` JSON override lets tests stay off shipped lore. It runs in the game environment and needs no Django setup.
- No map data, runtime code or dependency changes. Pure Python, no numpy.
- Human-reviewed, not tested: whether the chosen reference density and tier sizes *feel* right in play. They are reviewed against `docs/development/settlement-synthesis.md` § Human review (design D2).

## Batch:

- depends-on: none
- conflicts: `.github/top-level-shards.json`, `docs/development/settlement-synthesis.md` and `.agents/skills/map-data-authoring/**` are also edited by `settlement-graph-generator` and `settlement-rework-and-prose`. Those changes depend on this one, so the edits are serial.
