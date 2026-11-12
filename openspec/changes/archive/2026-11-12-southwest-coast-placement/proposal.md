# Proposal

## Why

`southwest_coast` is Altoria's craft shore: small harbours with finely built wooden ships, shipwright workshops, sea cliffs, fishing villages, salt pans and merchant ships carrying fine craft goods, plus three inland ferry settlements on its rivers (鹽津城, 鹽道城 and 橄欖津). Wave 1 (`coastal-near-belts`, landed) gave each of its three ports (漁灣鎮, 南潮港, 白帆港) a hinterland zone that holds only the shore crab, and two corridors with the same crab pool. It deferred the hinterland of the three inland settlements, because no rectangle beside them touches enough water for the crab and the region had no dry-ground species. The region has no deep-wild belt and no site. After the five Wave 4 south-west species changes it has two new low species (the salt-road ant and the rock-pool sea star), two new mid species (the mantis shrimp and the marine iguana) and one new high species (the giant octopus). This change adds the deferred inland hinterland belt, five road corridors, five 30×30 deep-wild zones on the remote shore and six sites.

## What Changes

- 15 new ecology zones (5 hinterland, 5 road corridors, 5 deep-wild) with their compositions, grounds and activities, and 6 monster sites with their compositions, grounds, defended extents and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pool edits on 5 landed rows of `coastal-near-belts`: each of `port_fishers_cove_hinterland`, `port_south_tide_hinterland` and `port_white_sail_hinterland` gains `oyster_rack_creeper` and `salt_hauler` compositions, and each of `southwest_road_01` and `southwest_road_02` gains a `salt_hauler` composition, with their activities over the existing grounds (design D1, block 4). Rectangles, densities, capacities and timing stay unchanged. This change does not edit the archived `coastal-near-belts` directory.
- The deferred hinterland: two zones beside each city (鹽津城, 鹽道城) and one beside the town 橄欖津, each with the dry-ground ant alone in three compositions.
- Ordinary pools: the low-tier `salt_hauler` and `oyster_rack_creeper` beside settlements and as company; the ant alone on the five new corridors, whose rectangles hold no water-adjacent cell (a recorded deviation: the three remote corridors carry no mid-tier composition, because both south-west mid-tier ordinary variants are shore animals); the mid-tier ordinary `reef_burrow_striker` and `seacliff_basker` with low company in the deep-wild zones, every one of which holds at least 12 water-adjacent cells.
- The stronger variants (`salt_mound_soldier`, `tide_pool_elder`, `seawall_den_holder`, `salt_dike_holder` and the shipped `reef_warden` 守礁型) appear only in recoverable sites. The high-tier `wreck_den_elder` appears only in one one-shot boss site with the individual name 沉錨.
- A human-review subsection in `docs/development/regional-monster-population.md`, and a regenerated `content/map-reference-context.json`.
- Expected standing population (planning probe, not a contract): the fifteen new zones initialize to the sum of their lower bounds, 101 individuals, and may hold up to 211; the sites add up to 14 more, so about 115..225 in total. The pool edits change the composition mix of the five existing zones, not their bounds.
- Deviations recorded for human review (design D3, D4): the remote corridors without a mid-tier composition, and a corridor belt sparser than one corridor per 40–60 km of trunk road.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-site-placement`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound, capacity, life cycle and individual-name rule. No test pins coordinates, densities or counts.

## Impact

Files: `world/lore/monster_placement.py` (`_SITE_DECLARATIONS`, `_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`, including the 5 landed south-west rows), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. Existing development databases need the reset in `docs/development/database-reset.md`, because the pool edits change existing zones and the new zones need initialization.

Human-reviewed document: the new subsection of `docs/development/regional-monster-population.md` (design D4). It covers whether each belt and site fits the species dossiers, the salt road, olive groves, oyster racks, boatyard slipways, sea cliffs and salt pans of the shore, whether the ground beside the towns keeps the light-adventure tone, and the two recorded deviations.

## Batch:

depends-on: southeast-coast-placement
depends-on: wreck-arm-octopus-species

Placement chain (strictly serial): `north-deep-forest-placement` → `central-mountains-placement` → `northwest-highland-placement` → `eastern-plains-deep-placement` → `southeast-coast-placement` → this change → `western-hills-deep-placement`. Every link appends to the same declaration tuples and review document. The species chain must have landed through `wreck-arm-octopus-species` (the last south-west species; the chain runs `salt-column-ant-species` → `stiff-arm-starfish-species` → `shell-crack-shrimp-species` → `salt-snort-iguana-species` → `wreck-arm-octopus-species`), because placement validation rejects unknown variants at import. The western species `shaft-leap-cricket-species` and `pit-sand-antlion-species` are not needed by this change.

Code conflicts: same declaration tuples and review document as the other placement links. The 5 edited rows belong to `coastal-near-belts` only; no other open change edits them. `content/map-reference-context.json` must be regenerated after rebase. Every new rectangle and site ground keeps an edge distance of at least 2 cells from every landed and open-change zone, area and site ground.
