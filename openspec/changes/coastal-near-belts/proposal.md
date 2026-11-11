# Proposal

## Why

Players almost never meet monsters in the wilderness. The shipped ecology zones cover 0.07% of the land and sit hundreds of cells from settlements and roads. The near-settlement programme adds a hinterland belt beside every inhabited settlement, a road-corridor belt, a deep-wild belt and sites. In Wave 1, the ten existing species move into the near belts. The two coastal regions hold 0.66M valid cells and six ports. Their one shipped zone and two boss sites all lie far from the ports, and their only low-tier species is the shore animal 潮燈蟹 (`tide_lamp_crab`). This change adds one hinterland zone beside each of the six ports, each on a rectangle with at least 12 water-adjacent cells. It also adds two crab corridors on the coastal road between 漁人灣 and 白帆港, and one remote south-east corridor where 吞潮鱷 joins the crab.

## What Changes

- 9 new ecology zones for `southwest_coast` and `southeast_coast`, with their compositions, grounds and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pools use only existing ordinary variants. No stronger or high-tier variant joins any pool, and every pooled species already lists the zone's region in `habitat_tags`.
- A new human-review subsection in `docs/development/regional-monster-population.md` records the belt rationale with no coordinate, density or count.
- `content/map-reference-context.json` is regenerated, so the map editor's monster layer shows the new zones.
- Deferred: The inland coastal settlements `city_salt_ferry`, `city_salt_road` and `town_olive_ferry` get no hinterland zone in Wave 1. The probe found no rectangle beside them with at least 12 water-adjacent cells, and the region has no inland low-tier species yet. Their zones arrive with the south-west coast species wave. No near-settlement south-east corridor qualified either, because no south-east road rectangle near a settlement had water cells.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. This is placement data, executed by the existing `regional-ecology`, `regional-population`, `monster-field-activity` and `wilderness-monster-population` contracts. Shipped-registry tests already validate every reference, habitat tag, bound and recovery path. No test pins any coordinate, density or count.

## Impact

Files: `world/lore/monster_placement.py` (`_ENCOUNTER_COMPOSITION_DECLARATIONS`, `_ECOLOGY_ZONE_DECLARATIONS`), `world/lore/monster_activity.py` (`_ACTIVITY_AREA_DECLARATIONS`, `_ACTIVITY_DECLARATIONS`), `docs/development/regional-monster-population.md`, and the regenerated `content/map-reference-context.json`. No test, shard or mechanism changes.

Runtime: a fresh world provisions more individuals, and an existing development database needs the reset in `docs/development/database-reset.md`. The standing population this change adds is about the sum of its zones' lower bounds (design D2).

Human-reviewed document: the subsection added by design D4 to `docs/development/regional-monster-population.md`. Review covers whether each belt's species fit the settlements and roads it borders, and whether the ground near towns keeps the light-adventure tone.

## Batch:

depends-on: western-hills-near-belts

Serial placement chain: `eastern-plains-near-belts` → `western-hills-near-belts` → `coastal-near-belts` → `highland-road-belts` → `north-deep-forest-placement`. Every link appends to the same four declaration tuples and the same review document, so running them in order avoids textual conflicts. The rectangles of all five were probed together and do not overlap.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every Wave 1 species change. After a rebase, rerun `uv run --locked python -m tools.map_reference_context`. No other file is shared with the species chain.
