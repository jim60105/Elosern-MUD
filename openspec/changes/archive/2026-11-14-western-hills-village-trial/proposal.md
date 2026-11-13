# Proposal

## Why

The Altoria Kingdom has no settlement below a town in the trial rectangle of the western hills around `town_scarp`: region `western_hills_valleys`, cells x 1000 to 1340 and y 501 to 950, both inclusive. This is wave 3 of the village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §9). Measured on the committed road artifact at planning time: 758 road cells, 436 of them more than 75 km by road from any settlement, the worst 234 km; it holds `town_scarp` and `town_honey_vale`.

## What Changes

- **Data.** New `village` and `hamlet` locations in `content/maps/locations.yaml`, 10 to 15 in total (about 4 villages and about 8 hamlets; these are targets, not limits), each with its `ANCHOR_LORE` row in `world/lore/anchors.py`.
- **Data.** One generated settlement map per new location under `content/maps/settlements/`, with zh-TW prose for every node.
- **Data.** The completed-area list `tools/settlement_spacing_areas.json` gains this area, so road coverage is enforced here from now on.
- **Regenerated.** `world/maps/data/road_network.json` (each village gains a spur), `world/maps/data/district_partition.json` and `content/map-reference-context.json`.
- **Working material.** The placement script and its candidate files live in this change's `snippets/` directory. They have no tests, no stable interface and no developer documentation.
- **Trial hand-off.** A findings file, `openspec/changes/western-hills-village-trial/trial-findings.md`, records whether a spacing value, a node count or the naming style should change. The user decides on any revision of the tiers design before `altoria-hills-village-placement` starts. This change itself changes no rule.

- Spec-less: game data only. `tools.settlement_spacing` and `tools.settlement_synthesis lint` check the result.

Human-reviewed, not tested: each site's geographic reason, the names, the prose, and how the new markers read on the world map. They are reviewed against `docs/lore/settlement-locations.md` 〈人類聚落的層級差異〉 and `docs/development/settlement-synthesis.md` § Human review.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- `content/maps/locations.yaml`, `world/lore/anchors.py`, new files under `content/maps/settlements/`, `tools/settlement_spacing_areas.json`, three regenerated artifacts, `docs/lore/settlement-locations.md`.
- Each village adds 4 or more grid rooms and each hamlet 2 or more. The test-suite cost is recorded in the hand-off and never blocks (design D9).
- Road regeneration runs several times in this change. Each run takes minutes and about 2.5 GB of memory.

## Batch:

- depends-on: village-hamlet-kinds
- depends-on: single-cell-footprint-entry
- depends-on: settlement-spacing-validation
- depends-on: road-spur-stage
- depends-on: single-cell-size-budget
- depends-on: single-cell-settlement-layout
- next: altoria-hills-village-placement
- conflicts: `content/maps/locations.yaml`, `world/lore/anchors.py`, `tools/settlement_spacing_areas.json`, `world/maps/data/road_network.json`, `world/maps/data/district_partition.json` and `content/map-reference-context.json` are changed by every placement change. The six placement changes are strictly serial, in the order trial, Altoria hills, Altoria coast, Grandia south, Grandia north, Valhalla. A spur or a hamlet written here is an input of the next change.
