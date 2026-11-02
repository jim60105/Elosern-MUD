# Proposal

## Why

The Valhalla Beast Kingdom has 18 national settlements, the 400,000-person tribal capital (咆哮王城), 8 cities and 9 towns, and none has a local map. Valhalla's settlements follow the beast-folk archetype in `docs/lore/settlement-locations.md`. A tribal hall replaces the palace and the manor. The training and assembly grounds rank high. The ancestral altar replaces the church. There is no academy, alchemist or inn. The generator's `tribal_ring` morphology and its beast-class role catalogue produce exactly this.

## What Changes

- **Data.** Generate `content/maps/settlements/<location_id>.yaml` with `generate --missing --nation valhalla`, in this order: `capital_valhalla`, `city_iron_claw`, `city_mutual_market`, `city_horn_plain`, `city_moon_howl`, `city_shadow_wood`, `city_fox_fire`, `city_swift_wind`, `city_tiger_roar`, `town_pine_ferry`, `town_stag_ferry`, `town_ancestor_shrine`, `town_falcon`, `town_grizzly`, `town_west_ford_camp`, `town_frost_wind`, `town_shaman_cave`, `town_east_ford_camp`.
- No relocation. Valhalla has no ports, and no Valhalla settlement's lore requires a river. `capital_valhalla` stays about 13 km from `highland_river` on purpose. Its lore reads "highland forest and tribal routes", and the matrix gives beast cities only a simple ferry landing when they happen to sit on a river.
- **Data.** Write zh-TW prose for every generated node.
- **Regenerated.** `world/maps/data/district_partition.json`.
- No `content/maps/locations.yaml` edit. The change is spec-less.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- 18 new settlement documents and the regenerated partition.
- About 170 new grid rooms, subject to the same test-cost gate as the other batches.
- Human-reviewed, not tested: layout appearance, beast-folk prose tone and lore fit. Reviewed against `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: altoria-settlement-maps
- depends-on: settlement-rework-and-prose
- conflicts: rewrites `world/maps/data/district_partition.json` after `altoria-settlement-maps`. The Altoria border-river footprints are blocked cells here.
