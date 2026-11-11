# Proposal

## Why

`northwest_highland_forest` holds 0.65M valid wilderness cells and 18 inhabited settlements of the beastfolk kingdom: 咆哮王城, eight cities and nine towns. Wave 1 (`highland-road-belts`) gave it eight remote road-corridor zones that hold only the mid-tier 霧鬃山貓, and deferred every hinterland zone because the region had no low-tier species. After the five Wave 2 northwest species changes it has three low, one mid and one high new species. This change delivers the deferred hinterland belt (two zones beside the capital and each city, one beside each town), adds low company to the eight Wave 1 corridors, and adds five 30×30 deep-wild zones and five sites for the stronger variants and the high-tier griffin.

## What Changes

- 32 new ecology zones (27 hinterland, 5 deep-wild) with their compositions, grounds and activities, and five monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Corridor low company: two new compositions and activities for each of `highland_road_01` … `highland_road_08`, and an edit of the `pool` tuple of those eight `EcologyZone` rows that `highland-road-belts` will have landed (design D1, block 4). Their rectangles, densities, capacities and timing stay unchanged. This change does not edit the `highland-road-belts` change directory.
- Ordinary pools: low-tier ordinary variants (`pine_floor_grouse`, `dam_builder`, `vein_digger`) in the hinterland zones and as corridor company; mid-tier ordinary variants (`trapline_raider` and the shipped `wood_stalker`) with low company in the deep-wild zones.
- The stronger variants (`lek_master_cock`, `old_dam_keeper`, `deep_seam_mole`, `winter_den_glutton`) appear only in recoverable sites. The high-tier `windcrest_elder` appears only in one one-shot boss site with the individual name 金翎.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the new zones initialize to the sum of their lower bounds, 261 individuals, and may hold up to 520; the sites add up to 9 more, so about 270..529 in total. The corridor edit changes the corridors' composition mix, not their bounds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`, including the eight landed `highland_road_*` rows), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`, because the pool edit changes existing zones and the new zones need initialization.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers, the beastfolk hunting grounds, fords and ore diggings, and whether the ground beside towns keeps the light-adventure tone.

## Batch:

depends-on: central-mountains-placement
depends-on: ore-nest-griffin-species

Placement chain (strictly serial): `eastern-plains-near-belts` → `western-hills-near-belts` → `coastal-near-belts` → `highland-road-belts` → `north-deep-forest-placement` → `central-mountains-placement` → this change. Every link appends to the same declaration tuples and review document, and this link edits the eight corridor rows `highland-road-belts` lands. The species chain must have landed through `ore-nest-griffin-species`, because placement validation rejects unknown variants at import.

Code conflicts: same declaration tuples and review document as the other placement links. `content/map-reference-context.json` must be regenerated after rebase. `city_fox_fire`'s two zones sit on its northwest-region side, clear of `fox_fire_pass_approach` from `central-mountains-placement`.
