# Proposal

## Why

The Altoria Kingdom has 19 national settlements besides its capital: 6 cities, 6 ports and 7 towns. None has a local map. The settlement tooling can now author them deterministically, sized from population and fitted to the western hills, valleys and south-west coast.

## What Changes

- **Data.** Generate `content/maps/settlements/<location_id>.yaml` with `generate --missing --nation altoria`. `capital_altoria` already has a map, so the generator skips it and never overwrites it. Roster, largest first: `port_white_sail`, `city_confluence`, `port_south_tide`, `port_west_ore`, `city_greyrock`, `city_border_bridge`, `city_east_river`, `city_salt_ferry`, `city_salt_road`, `town_olive_ferry`, `town_ruins_gate`, `port_fishers_cove`, `town_honey_vale`, `port_hills_mouth`, `town_vineyard`, `town_west_ferry`, `port_westwind`, `town_east_ferry`, `town_scarp`.
- **Data, only where needed.** A port that the generator refuses with `water_gap` may be moved by at most 3 cells toward its water. The relocation rule is in design D2, and the likely candidates are `port_west_ore` and `port_westwind`, each about 3 cells from the sea. Every move is listed in the hand-off.
- **Data.** Write zh-TW prose for every generated node.
- **Regenerated.** `world/maps/data/district_partition.json`.
- Spec-less: game data only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- 19 new settlement documents, possibly a few edited cells in `content/maps/locations.yaml`, and the regenerated partition.
- About 170 new grid rooms, subject to the same test-cost gate as `grandia-settlement-maps` (design D4).
- Human-reviewed, not tested: layout appearance, prose tone and lore fit, and whether each relocation is acceptable. Reviewed against `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: grandia-settlement-maps
- depends-on: altoria-capital-river-rework
- depends-on: settlement-rework-and-prose
- conflicts: `world/maps/data/district_partition.json` and `content/maps/locations.yaml` are also changed by `grandia-settlement-maps` (before this change) and `valhalla-settlement-maps` (after it). The footprints written here are blocked cells for `valhalla-settlement-maps`, especially along the border river.
