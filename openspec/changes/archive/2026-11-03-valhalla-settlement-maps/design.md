# Design

## Context

See proposal.md (Why). This change uses the same tools as `grandia-settlement-maps`. All of them have landed. In `tools.settlement_synthesis.generate`, nation `valhalla` is in `GenerationConfig().beast_nations`, so it gets these classes:

- `beast_capital` for `capital_valhalla`;
- `beast_town` for every other Valhalla settlement.

Both classes use the `tribal_ring` morphology. The beast-class role rows of `DEFAULT_CATALOGUE` are `market_street`, `tribal_hall`, `assembly_ground`, `training_ground`, `guild_forecourt`, `ancestral_altar`, `tavern_lane`, `ferry_landing` (river only) and `craft_alley`.

## Goals / Non-Goals

**Goals:**
- every Valhalla national settlement has a local map that passes the lint and has complete prose.

**Non-Goals:**
- relocations beyond the three cells D4 accepts;
- city gates;
- interiors;
- Python lore;
- fine fitting.

## Decisions

### D1. Order of work

Plan, generate, write prose, then verify. There is no `water_gap` step:
`water_gap` only applies to ports, and Valhalla has none. The only accepted
placement remedies are the two in D4: a town whose own wilderness landmark sits
on its location cell moves that landmark, and a two-cell footprint whose
diagonal water reach puts the mask midpoint outside the mask moves its location
cell by one. Any other plan failure is reported, and that location is not
generated.

### D2. Prose

Follow `docs/development/settlement-synthesis.md` § Prose pass, with these beast-folk rules from `docs/lore/settlement-locations.md` § 聚落差異深論:

- **Society.** Tribal society, with a tribal hall (部族議事廳). Leaders are chosen by consensus among the tribes, never by inheritance.
- **Rites.** The training ground is where the coming-of-age hunt and the 獸魂 rites take place. The ancestral altar or totem ground honours nature and ancestor spirits.
- **What does not exist.** There is no church, no alchemist and no magic academy. Smithing is heavy and suited to each subspecies.
- **Trade.** Trade happens at markets and through barter, but currency is still in use.
- **Tone.** Write with a robust, frank tone. It is in-world prose only, never 武俠 vocabulary.

### D3. Test-suite timing record (never blocks)

Apply the same rule as `grandia-settlement-maps` D4. The baseline is taken at the start of this change. The timing is reported in the hand-off and never stops the commit.

### D4. Approved placement remedies

**Generator precondition: a town's own wilderness landmark must not sit on its
location cell.** `tools/settlement_synthesis/workspace.py::blocked_cells`
reserves every `wilderness_cell` district landmark, so a landmark on the
settlement's own cell blocks the mandatory anchor cell and `generate` refuses
with `location cell not walkable`. Rebinding is not the remedy: the shipped
contract (`world/lore/tests/test_map_district_content.py`) requires a
wilderness landmark cell to stay valid wilderness, which a settlement footprint
destroys. Seven Valhalla landmarks collide this way. Each moves three cells
north to a walkable, dry, same-region cell that stays over 100 km from every
other Voronoi landmark:

| District | Landmark cell | Moved to |
| --- | --- | --- |
| `bison_plateau` | 391,1661 | 391,1664 |
| `iron_vein_highlands` | 1175,1605 | 1175,1608 |
| `stag_call_highlands` | 469,1850 | 469,1853 |
| `ancestor_cairn_hills` | 729,1595 | 729,1598 |
| `falcon_rise` | 1093,1455 | 1093,1458 |
| `grizzly_vale` | 896,1489 | 896,1492 |
| `shaman_cave_woods` | 1168,1816 | 1168,1819 |

**Accepted location moves.** Three border-river towns refuse with
`anchor_outside_footprint`: a two-cell budget plus the mandatory reach path to
`border_river`, which lies 2.83 cells south, grows a three-cell L whose
bounding-box midpoint is the missing corner. No location, harbour, landmark,
mask or gate approach blocks those cells, so the landmark remedy cannot apply.
The same rule as `altoria-settlement-maps` accepts a one-cell move for each;
each stays walkable, dry, in Valhalla and `northwest_highland_forest`, three
cells from the border river, and keeps its authored ford outside the new mask.

| Location | Cell | Moved to |
| --- | --- | --- |
| `city_mutual_market` | 824,1370 | 823,1370 |
| `town_west_ford_camp` | 450,1348 | 449,1348 |
| `town_east_ford_camp` | 1150,1366 | 1149,1366 |

## Risks / Trade-offs

- [Footprints from `altoria-settlement-maps` along the border river block Valhalla cells such as `town_west_ford_camp` and `town_east_ford_camp`] → The generator grows around blocked cells. A `footprint_short` failure is reported, and that location is not generated.
- [A moved landmark is a blocked cell for every map, so it can nudge a neighbouring footprint] → The seven landmark moves and the three location moves are applied before the generation batch, so one batch sees the final reservations.

## Migration Plan

None, because the project is pre-release. To roll back, revert the commit and regenerate the partition.
