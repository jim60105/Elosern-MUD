# Proposal

## Why

`eastern_plains` is Grandia's farm heartland, with 1.34M valid wilderness cells and 19 inhabited settlements. Wave 1 (`eastern-plains-near-belts`, landed) gave every settlement a hinterland zone and placed twelve remote road corridors, all holding the same four low-tier compositions, because the region had no mid-tier species. The region still has no deep-wild belt and no site. After the four Wave 3 eastern species changes it has one new low, two new mid and one new high species. This change adds five 30×30 deep-wild zones, gives the twelve remote corridors mid-tier company, adds the new low beetle to every hinterland pool, and adds six sites for the stronger variants (including the shipped 領群型 and 護巢型) and the high-tier turtle.

## What Changes

- 5 new deep-wild ecology zones with their compositions, grounds and activities, and 6 monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pool edits on 37 landed rows of `eastern-plains-near-belts`: each of the 25 `*_hinterland` zones gains a `road_ball_roller` composition, and each of `eastern_road_01` … `eastern_road_12` gains `road_ball_roller`, `plain_runner` and `sluice_wader` compositions, with their activities over the existing grounds (design D1, block 4). Rectangles, densities, capacities and timing stay unchanged. This change does not edit the archived `eastern-plains-near-belts` directory.
- Ordinary pools: the low-tier `road_ball_roller` in the hinterland belt; the mid-tier ordinary `plain_runner` and `sluice_wader` with low company on the remote corridors and in the deep-wild zones.
- The stronger variants (`flock_leader`, `nest_guard`, `heap_brood_keeper`, `herd_stallion`, `heronry_elder`) appear only in recoverable sites. The high-tier `wide_mound_elder` appears only in one one-shot boss site with the individual name 白蘆.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the five new zones initialize to the sum of their lower bounds, 45 individuals, and may hold up to 88; the sites add up to 15 more, so about 60..103 in total. The pool edits change the composition mix of the 37 existing zones, not their bounds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`, including the 37 landed eastern rows), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`, because the pool edits change existing zones and the new zones need initialization.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers, the farm roads, irrigation canals, ranches and lake district of the plain, and whether the ground beside towns keeps the light-adventure tone.

## Batch:

depends-on: northwest-highland-placement
depends-on: lake-mound-turtle-species

Placement chain (strictly serial): `north-deep-forest-placement` → `highland-road-belts` → `central-mountains-placement` → `northwest-highland-placement` → this change → `southeast-coast-placement`. Every link appends to the same declaration tuples and review document. The species chain must have landed through `lake-mound-turtle-species`, because placement validation rejects unknown variants at import; the remaining Wave 3 species links (`flat-leap-goby-species`, `mast-wind-gull-species`, `breakwater-seal-species`) are not needed by this change.

Code conflicts: same declaration tuples and review document as the other placement links. The 37 edited rows belong to `eastern-plains-near-belts` only; no other open change edits them. `content/map-reference-context.json` must be regenerated after rebase. Every new rectangle and site ground keeps at least 2 cells from every landed and open-change zone, area and site ground.
