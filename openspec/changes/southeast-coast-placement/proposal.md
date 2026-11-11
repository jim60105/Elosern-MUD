# Proposal

## Why

`southeast_coast` is Grandia's trading shore, with 0.26M valid wilderness cells and three ports (金穗港, 東灣港, 南岬港). Wave 1 (`coastal-near-belts`, landed) gave each port a hinterland zone that holds only the shore crab, and one remote corridor where the crocodile joins the crab. The region has no deep-wild belt and no site for the crab's and the crocodile's stronger variants. After the three Wave 3 south-east species changes it has two new low species (the mudskipper and the harbour gull) and one new mid species (the harbour seal). This change adds the new low species to the port hinterlands, two gull corridors on the trunk road to 金穗港, five 30×30 deep-wild zones on the remote shore, and five sites for the stronger variants.

## What Changes

- 7 new ecology zones (2 road corridors, 5 deep-wild) with their compositions, grounds and activities, and 5 monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pool edits on 4 landed rows of `coastal-near-belts`: each of `port_east_bay_hinterland`, `port_golden_sheaf_hinterland` and `port_south_cape_hinterland` gains `mudflat_skipper` and `mast_circler` compositions, and `southeast_road_01` gains a `mast_circler` composition, with their activities over the existing grounds (design D1, block 4). Rectangles, densities, capacities and timing stay unchanged. This change does not edit the archived `coastal-near-belts` directory.
- No deferred hinterland applies here. The three south-east settlements are ports and each already has its Wave 1 hinterland zone. The inland coastal settlements that Wave 1 deferred (`city_salt_ferry`, `city_salt_road`, `town_olive_ferry`) belong to `southwest_coast` and stay deferred.
- Ordinary pools: the low-tier `mudflat_skipper` and `mast_circler` beside the ports and as company; the gull alone on the two new trunk-road corridors, whose rectangles hold no water-adjacent cell; the mid-tier ordinary `pier_basker` and the shipped `bank_lurker` with low company in the deep-wild zones, every one of which holds at least 12 water-adjacent cells.
- The stronger variants (the shipped `reef_warden` 守礁型 and `bay_warden` 守灣型, and `turret_keeper`, `stack_colony_elder`, `haulout_bull`) appear only in recoverable sites. The two shipped crocodile boss sites stay as they are.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the seven new zones initialize to the sum of their lower bounds, 52 individuals, and may hold up to 103; the sites add up to 12 more, so about 64..115 in total. The pool edits change the composition mix of the four existing zones, not their bounds.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`, including the 4 landed south-east rows), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`, because the pool edits change existing zones and the new zones need initialization.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers, the harbours, fish markets, breakwaters, estuaries and tidal marsh of the shore, and whether the ground beside the ports keeps the light-adventure tone.

## Batch:

depends-on: eastern-plains-deep-placement
depends-on: breakwater-seal-species

Placement chain (strictly serial): `north-deep-forest-placement` → `central-mountains-placement` → `northwest-highland-placement` → `eastern-plains-deep-placement` → this change (`highland-road-belts` has landed). Every link appends to the same declaration tuples and review document. The species chain must have landed through `breakwater-seal-species`, because placement validation rejects unknown variants at import.

Code conflicts: same declaration tuples and review document as the other placement links. The 4 edited rows belong to `coastal-near-belts` only; no other open change edits them. `content/map-reference-context.json` must be regenerated after rebase. Every new rectangle and site ground keeps at least 2 cells from every landed and open-change zone, area and site ground, including the grounds of the two shipped crocodile boss sites.
