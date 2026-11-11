# Proposal

## Why

`north_deep_forest` holds 1.00M valid wilderness cells and no monster placement at all. After the six Wave 1 species changes it has three low, two mid and one high species. The region forbids roads (`content/maps/road_network.yaml` `forbidden_regions`) and has one inhabited settlement, the hidden elven village 幽月谷村 (`village_eolas`). Expeditions enter it from 北林堡 and 虎嘯城 toward the dragon nest and the eternal-night dungeon. This change gives the forest a hinterland zone beside 幽月谷村, two forest-edge approach zones that replace the road-corridor belt at the expedition entry points, five 30×30 deep-wild zones along the expedition approaches, and six sites for the stronger variants and the high-tier stag.

## What Changes

- Eight ecology zones, their compositions, grounds and activities, and six monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Ordinary pools: low-tier ordinary variants (`rotlog_sprout`, `quill_forager`, `hollow_roost_flier`) in the hinterland and approach zones; mid-tier ordinary variants (`hush_wing_hunter`, `vine_weaver`) with low company in the deep-wild zones.
- The stronger variants (`ring_elder`, `den_sentry`, `colony_sentinel`, `old_hollow_owl`, `trail_netter`) appear only in recoverable sites. The high-tier `wood_crown_elder` appears only in one one-shot boss site with the individual name 蒼冠.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the forest dossiers and the expedition routes, and the light tone beside the elven village.

## Batch:

depends-on: highland-road-belts
depends-on: moss-crown-stag-species

Last link of the placement chain (`eastern-plains-near-belts` → `western-hills-near-belts` → `coastal-near-belts` → `highland-road-belts` → this change) and of the species chain (`spore-cap-mushroom-species` → … → `moss-crown-stag-species`). All six species must exist, because placement validation rejects unknown variants at import.

Code conflicts: same declaration tuples and review document as the earlier placement links. `content/map-reference-context.json` must be regenerated after rebase.
