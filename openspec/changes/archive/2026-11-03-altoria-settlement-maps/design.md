# Design

## Context

See proposal.md (Why). The tools are the same as in `grandia-settlement-maps`, and all are landed: the `tools.settlement_synthesis` commands `site`, `budget`, `lint`, `generate`, `brief` and `prose`, plus `place_sites.py`, `check_map_sources.py`, `regenerate_partition.py` and `capture_map.py`. Footprints already written for Grandia and for `capital_altoria` are blocked cells for this batch.

The site probe at proposal time gives these distances. They are Euclidean cells and only a guide, because the generator's reach test decides:

- `port_white_sail`: river 1, sea 3
- `port_south_tide`: sea 2
- `port_west_ore`: sea 3
- `port_fishers_cove`: river 1, sea 3
- `port_hills_mouth`: river 1, sea 3
- `port_westwind`: sea 3

Three of these sit on rivers: white_sail and hills_mouth near their river mouths, fishers_cove at about a 1-cell distance. The generator gives a port a waterside layout on a river when the sea is out of reach, which is correct for a river-mouth port.

## Goals / Non-Goals

**Goals:** every Altoria non-capital national settlement has a lint-clean local map with complete prose.

**Non-Goals:**
- `capital_altoria`, which `altoria-capital-river-rework` owns;
- city gates;
- interiors;
- Python lore;
- fine fitting;
- the other nations.

## Decisions

### D1. Order of work

Plan, relocate, generate, write prose, verify. This is the same order as `grandia-settlement-maps` D1.

### D2. Relocation rule (explicit; no other location edit is allowed)

There are three triggers:

- (a) `generate <id> --plan-only` fails with `water_gap` for a port;
- (b) `generate <id> --plan-only` fails with `anchor_outside_footprint`. A
  two-cell footprint whose nearest water cell is diagonal forces a five-cell
  path to the water, so the footprint's bounding-box midpoint falls on a cell
  it does not contain. This trigger was added during implementation: the
  proposal expected only ports to fail, but no port does, and
  `city_border_bridge`, `city_east_river` and `town_east_ferry` hit (b).
- (c) a generated footprint contains an authored ford. The district contract
  requires a ford to stay walkable wilderness that joins the banks, and a
  `river_crossing` plan reaches its ford cell. `town_west_ferry` consumed the
  western border ford at 450,1345 and moved three cells west to a
  waterside layout that leaves the ford free.

Let `L` be the failing location. The target `T` is `site L --radius 12`'s
`sea.nearest_cell`, or, when no sea is reported, `rivers[0].nearest_cell`.

Reject any candidate cell that:

- `place_sites.py`, run on a candidate file `[{"id": "<L>", "cell": [x, y]}]`
  (the cell is a two-item JSON list), reports `walkable=False` or
  `water_cell=True` for;
- has a region or nation different from `L`'s;
- equals any location cell or harbour cell;
- under trigger (b) or (c), would put an authored ford inside its generated
  footprint, because the district contract requires the principal border ford
  to stay reachable wilderness that joins the banks.

Try candidates in this order, and accept the first whose rerun of
`generate L --plan-only` no longer fails the trigger:

1. For `k = 1, 2, 3`, the ray candidate
   `c_k = L.cell + round_away(k * (T - L.cell) / max(|T.x - L.x|, |T.y - L.y|))`.
2. If the ray is exhausted under trigger (b) or (c), every other cell within
   Chebyshev 3 of `L.cell` that passes the rejections, ordered by displacement
   then `y` then `x`. For a border-river town the cell must stay on the
   Altoria (south) bank; a candidate that crosses the border river is rejected
   even when its nominal nation classifier still says Altoria.

The user approved this extension, including the exact cells below. The ray
dead-ends for the two border towns: `k = 1` still fails, `k = 2` is the river
cell, and `k = 3` crosses into Valhalla. The approved cells therefore come
from step 2 and stay on the Altoria bank.

If no candidate is accepted, restore the cell and report the location as
unresolved without generating it. Record every accepted move as
`id: old → new`.

**Generator precondition: a town's own wilderness landmark must not sit on
its location cell.** `tools/settlement_synthesis/workspace.py::blocked_cells`
reserves every `wilderness_cell` district landmark, so a landmark on the
settlement's own cell blocks the mandatory anchor cell and `generate` refuses
with `location cell not walkable`. Rebinding is not the remedy: the shipped
contract (`world/lore/tests/test_map_district_content.py`) requires a
wilderness landmark cell to stay valid wilderness, which a settlement
footprint destroys. Two Altoria landmarks collide this way:
`western_ore_hills` on `city_greyrock` and `vineyard_slopes` on
`town_vineyard`. Each moves three cells north to a walkable, dry, same-region
cell that stays over 100 km from every other Voronoi landmark.

**Accepted moves in this change:**

- `city_greyrock`: unchanged; its landmark moved instead.
- `town_vineyard`: unchanged; its landmark moved instead.
- `city_border_bridge`: 822,1363 → 819,1363.
- `city_east_river`: 1054,1072 → 1053,1073.
- `town_east_ferry`: 1149,1360 → 1148,1360.
- `town_west_ferry`: 450,1343 → 447,1343.

### D3. Prose

Follow `docs/development/settlement-synthesis.md` § Prose pass. Altoria's flavour comes from `docs/lore/settlement-locations.md`:

- a church-centred human kingdom;
- the western hills hold mining and market towns, where the lord's seat is a manor;
- the south-west ports are fishing and trading harbours;
- the border-river towns (`city_border_bridge`, `town_west_ferry`, `town_east_ferry`) face Valhalla across fords.

One prose JSON per map is applied with `prose`.

### D4. Test-suite timing record (never blocks)

Use the same rule as `grandia-settlement-maps` D4, with the baseline taken at the start of this change. The timing is reported in the hand-off and never stops the commit.

## Risks / Trade-offs

- [The border-river towns' footprints compete with the cells that `valhalla-settlement-maps` will need on the other bank] → This batch runs first, so its footprints become blocked cells for Valhalla. A Valhalla site that cannot grow is reported there.
- [A generation failure other than a water gap] → Report it and leave the location ungenerated.

## Migration Plan

None. The project is pre-release. To roll back, revert the commit and regenerate the partition.
