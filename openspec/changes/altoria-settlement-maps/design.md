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

The rule is triggered only when `generate <id> --plan-only` fails with `water_gap`. Let `L` be the failing location. The target `T` is `site L --radius 12`'s `sea.nearest_cell`, or, when no sea is reported, `rivers[0].nearest_cell`.

For `k = 1, 2, 3`:

1. Compute `c_k = L.cell + round_away(k * (T - L.cell) / max(|T.x - L.x|, |T.y - L.y|))`.
2. Reject `c_k` in any of these cases:
   - `place_sites.py`, run on a candidate file `[{"id": "<L>", "cell": [c_k.x, c_k.y]}]` (the cell is a two-item JSON list), reports `walkable=False` or `water_cell=True` for it;
   - its region or nation differs from `L`'s;
   - it equals any location cell or harbour cell.
3. Otherwise set the cell and rerun `generate L --plan-only`. Accept `c_k` once the plan succeeds. If it still fails, restore the cell and try the next `k`.

If no `c_k` is accepted, restore the cell and report the location as unresolved without generating it. Record every accepted move as `id: old → new`.

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
