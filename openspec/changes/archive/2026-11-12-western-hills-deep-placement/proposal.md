# Proposal

## Why

`western_hills_valleys` is Altoria's mining and craft country: terraced stone fields, mine shafts, quarries, river valleys with workshops and mills, and scrub hills with grazing sheep. Wave 1 (`western-hills-near-belts`, landed) gave every inhabited settlement a hinterland zone and placed ten road corridors; nine remote corridors carry the goat as their only mid-tier animal. The region has no deep-wild belt, and its sites are the shipped hare nest, goat camp, transfer station and boar boss site. After the two Wave 4 western species changes it has one new low species (the cave cricket) and one new mid species (the antlion). This change adds five 30×30 deep-wild zones, adds the cricket to every hinterland and corridor pool and the antlion to every remote corridor pool, and adds three sites for the stronger variants.

## What Changes

- 5 new deep-wild ecology zones with their compositions, grounds and activities, and 3 monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pool edits on 29 landed rows of `western-hills-near-belts`: each of the 19 `*_hinterland` zones gains a `cellar_leaper` composition; each of the nine remote corridors (`western_road_01`, `western_road_02` and `western_road_04` … `western_road_10`) gains `quarry_pit_lurker` and `cellar_leaper` compositions; `western_road_03` gains a `cellar_leaper` composition. Their activities run over the existing grounds (design D1, block 4). Rectangles, densities, capacities and timing stay unchanged. This change does not edit the archived `western-hills-near-belts` directory.
- Ordinary pools: the low-tier `cellar_leaper` beside every settlement and as company; the mid-tier ordinary `quarry_pit_lurker` beside the shipped `cliff_stepper` on the remote corridors and in the deep-wild zones, with low company.
- The stronger variants (`old_shaft_leaper`, `spoil_heap_elder` and the shipped `pass_warden` 守隘型) appear only in recoverable sites. The shipped hare nest, goat camp, transfer station and boar boss site stay as they are.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the five new zones initialize to the sum of their lower bounds, 45 individuals, and may hold up to 90; the sites add up to 6 more, so about 51..96 in total. The pool edits change the composition mix of the 29 existing zones, not their bounds.
- Deviation recorded for human review (design D3): no corridor is added, so the western corridor belt stays sparser than one corridor per 40–60 km of road.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`, including the 29 landed western rows), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`, because the pool edits change existing zones and the new zones need initialization.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers, the mine shafts, quarries, spoil heaps, mill cellars and scrub hills of the region, whether the ground beside the towns keeps the light-adventure tone, and the recorded deviation.

## Batch:

depends-on: southwest-coast-placement
depends-on: pit-sand-antlion-species

Placement chain (strictly serial): `north-deep-forest-placement` → `central-mountains-placement` → `northwest-highland-placement` → `eastern-plains-deep-placement` → `southeast-coast-placement` → `southwest-coast-placement` → this change, the last placement link of the programme. Every link appends to the same declaration tuples and review document. The species chain must have landed through `pit-sand-antlion-species` (after `shaft-leap-cricket-species`), because placement validation rejects unknown variants at import.

Code conflicts: same declaration tuples and review document as the other placement links. The 29 edited rows belong to `western-hills-near-belts` only; no other open change edits them. `content/map-reference-context.json` must be regenerated after rebase. Every new rectangle and site ground keeps an edge distance of at least 2 cells from every landed and open-change zone, area and site ground, including the grounds of the shipped boar boss site.
