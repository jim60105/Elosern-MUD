# Proposal

## Why

`central_mountains` covers about 0.38M cells of the continent's spine and holds no monster placement at all. After the five Wave 2 central-mountain species changes it has two low, two mid and one high species. No road enters the region (`world/maps/data/road_network.json` has no road cell in it), and its two inhabited settlements are the hidden elven villages 暗影谷村 (`village_ciaran`) and 翠綠森林村 (`village_fionnen`). Foot traffic climbs in from the foothill settlements 斷崖鎮, 銀嶺鎮, 楓麓鎮 and 狐火城. This change gives the mountains a hinterland zone beside each elven village, four mountain-path approach zones that replace the road-corridor belt where the foothill traffic climbs in, five 30×30 deep-wild zones along the spine, and five sites for the stronger variants and the high-tier serpent.

## What Changes

- Eleven ecology zones, their compositions, grounds and activities, and five monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Ordinary pools: low-tier ordinary variants (`seep_sipper`, `ledge_basker`) in the hinterland and approach zones; mid-tier ordinary variants (`updraft_glider`, `lamp_seeker`) with low company in the deep-wild zones.
- The stronger variants (`spring_keeper`, `vent_crack_dweller`, `crag_nest_vulture`, `old_veil_moth`) appear only in recoverable sites. The high-tier `white_rime_coil` appears only in one one-shot boss site with the individual name 霜環.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the zones initialize to the sum of their lower bounds, 77 individuals, and may hold up to 168; the sites add up to 7 more, so about 84..175 in total.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers and the mountain paths, and the light tone beside the elven villages.

## Batch:

depends-on: north-deep-forest-placement
depends-on: rime-scale-serpent-species

Placement chain (strictly serial): the five Wave 1 placement changes ending with `north-deep-forest-placement` → this change → `northwest-highland-placement`. Every link appends to the same declaration tuples and review document. The species chain must have landed through `rime-scale-serpent-species`, because placement validation rejects unknown variants at import.

Code conflicts: same declaration tuples and review document as the other placement links. `content/map-reference-context.json` must be regenerated after rebase. The probe placed every rectangle clear of the Wave 1 rectangles, including `town_scarp_hinterland`, `town_silver_ridge_hinterland` and `eastern_road_10` near the mountain foot.
