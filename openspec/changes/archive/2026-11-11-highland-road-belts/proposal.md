# Proposal

## Why

Players almost never meet monsters in the wilderness. The shipped ecology zones cover 0.07% of the land and sit hundreds of cells from settlements and roads. The near-settlement programme adds a hinterland belt beside every inhabited settlement, a road-corridor belt, a deep-wild belt and sites. In Wave 1, the ten existing species move into the near belts. `northwest_highland_forest` holds 0.65M valid cells and the longest trunk-road network after the plains, but its only species is the mid-tier 霧鬃山貓. This change adds eight remote road-corridor zones, each at least 80 cells from every settlement, where the lynx meets travellers on the trunk roads.

## What Changes

- 8 new ecology zones for `northwest_highland_forest`, with their compositions, grounds and activities, transcribed verbatim from `snippets/monster_placement_rows.txt` and `snippets/monster_activity_rows.txt` in this change directory (design D1).
- Pools use only existing ordinary variants. No stronger or high-tier variant joins any pool, and every pooled species already lists the zone's region in `habitat_tags`.
- A new human-review subsection in `docs/development/regional-monster-population.md` records the belt rationale with no coordinate, density or count.
- `content/map-reference-context.json` is regenerated, so the map editor's monster layer shows the new zones.
- Deferred: None of the region's 18 settlements gets a hinterland zone in Wave 1. Hinterland pools are low-tier only, and the region has no low-tier species until its own species wave. Corridor points within 80 cells of a settlement are left unused for the same reason.

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

depends-on: coastal-near-belts

Serial placement chain: `eastern-plains-near-belts` → `western-hills-near-belts` → `coastal-near-belts` → `highland-road-belts` → `north-deep-forest-placement`. Every link appends to the same four declaration tuples and the same review document, so running them in order avoids textual conflicts. The rectangles of all five were probed together and do not overlap.

Code conflicts: `content/map-reference-context.json` conflicts mechanically with every Wave 1 species change. After a rebase, rerun `uv run --locked python -m tools.map_reference_context`. No other file is shared with the species chain.
