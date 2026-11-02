# Proposal

## Why

The Grandia Empire has 22 national settlements in `content/maps/locations.yaml` and `ANCHOR_LORE`: the 800,000-person capital, 5 cities, 5 ports and 11 towns. None has a local map, so travellers cannot enter any of them. The tooling from `settlement-terrain-fit`, `settlement-graph-generator` and `settlement-rework-and-prose` can now author them deterministically, sized from population and fitted to the terrain.

## What Changes

- **Data.** Generate `content/maps/settlements/<location_id>.yaml` for every Grandia national settlement without one, using `generate --missing --nation grandia`. The roster, largest first: `capital_grandia`, `port_golden_sheaf`, `city_twin_currents`, `port_south_cape`, `port_east_bay`, `city_starglow`, `city_wheatwave`, `city_imperial_ferry`, `port_dawnlight`, `city_spice_road`, `town_east_pasture`, `town_emerald_lake`, `town_crystal`, `port_tide_wind`, `town_black_soil`, `town_silver_ridge`, `town_steed_plain`, `town_maple_foot`, `town_orange_blossom`, `town_north_wood_keep`, `town_sunken_bell`, `town_sunrise`.
- **Data, only where needed.** Move a location cell by at most 3 cells toward its water, under the explicit relocation rule in design D2, in two cases:
  - a port the generator refuses with `water_gap`;
  - `capital_grandia`, whose lore constraint is "major river supply". It sits about 4–5 cells from `imperial_river` and its ford (1953, 1268), which is beyond the 3-cell reach of a 16-cell footprint.

  Each move is listed in the hand-off.
- **Data.** Write zh-TW prose for every generated node with `brief` and `prose`.
- **Regenerated.** `world/maps/data/district_partition.json`.
- No city gate from the starting room (`city_gate:` stays empty), no interiors and no Python lore.
- Spec-less: game data only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- 22 new settlement documents, possibly a few edited cells in `content/maps/locations.yaml`, and the regenerated partition.
- Runtime: about 230 new grid rooms and their exits, spawned by `sync_grid()` at start-up and in every test that calls it on shipped data. Design D4 records the test-suite cost without blocking the change.
- Human-reviewed, not tested: layout appearance, prose tone and lore fit, and whether each relocation is acceptable. The checklist is `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: altoria-capital-river-rework
- depends-on: settlement-rework-and-prose
- depends-on: unpin-settlement-map-data
- conflicts: `world/maps/data/district_partition.json` and `content/maps/locations.yaml` are also rewritten by `altoria-settlement-maps` and `valhalla-settlement-maps`. Those come after this change and depend on it. Footprints written here also become blocked cells for the later nations.
