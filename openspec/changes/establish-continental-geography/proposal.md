# Proposal

## Why

Declare frozen mainland, nine anchor cells, six reserved harbor sites and demographic/units contracts without runtime scale activation. The approved world-scale design requires this bounded ownership seam before the coordinated runtime cutover.

## What Changes

- **BREAKING** Declare frozen mainland, nine anchor cells, six reserved harbor sites and demographic/units contracts without runtime scale activation.
- Deliver one engineer-day of implementation with scenario evidence; no backwards-compatibility layers or database migrations.

## Capabilities

### New Capabilities
- `continental-geography`: Declare frozen mainland, nine anchor cells, six reserved harbor sites and demographic/units contracts without runtime scale activation.

### Modified Capabilities
None.

## Impact

world/lore/nations.py, world/lore/anchors.py, world/lore/wilderness_regions.py; add frozen geographic declarations alongside existing lore registries.

## Non-goals

No vehicles, mounts, shipping, fast travel, enhancement abilities, active-monster encounters, survival/carrying system, party-capacity changes, planet inference, further continents or automatic long-distance route execution. Companion physiology internals are external.

## Batch:

depends-on: none
code-conflicts: none; declarations consumed by downstream changes

Worker: luna
Branch: `feat/establish-continental-geography`
Worktree: `.worktrees/establish-continental-geography`

Source: `docs/superpowers/specs/2026-10-21-world-map-scale-design.md`. Companion dependency: `docs/superpowers/specs/2026-10-21-party-fatigue-and-sleep-design.md`; content is outside this batch.

## Dependency and conflict matrix

| Change | Direct prerequisites | Shared code conflicts |
| --- | --- | --- |
| `establish-continental-geography` | none | lore declarations |
| `implement-sparse-settlement-graphs` | none | world/maps/bootstrap.py::sync_grid, world/maps/map_data.py::XYMAP_DATA_LIST, typeclasses/rooms.py::GridRoom; sparse graph route adapter replacing dense allocation |
| `project-metric-local-maps` | establish-continental-geography | web/webclient/presentation/local_map/validate.py::validate_local_map, web/static/webclient/js/elosern/protocol/panels/local_map.js::requireCoord, web/static/webclient/js/elosern/local_map.js::layoutNodes, web/webclient-app/components/LocalMap.vue, web/webclient-app/components/MapLattice.vue |
| `charge-distance-based-travel` | establish-continental-geography | world/rules/movement.py::charge_movement, typeclasses/exits.py::MovementCostMixin.at_traverse/at_post_traverse and after_successful_movement, WildernessGateExit.at_traverse, WildernessReturnExit.at_traverse, world/maps/wilderness_destination.py::wilderness_neighbor, world/rules/movement_settlement.py::settle_movement |
| `integrate-fatigue-aware-traversal` | charge-distance-based-travel, external:party-fatigue-and-sleep | world/rules/movement.py::charge_movement, world/rules/party.py::follow_scope, typeclasses/exits.py traversal preflight, world/rules/movement_settlement.py::_snapshot_movement_state/_compensate, world/rules/clock.py::build_advance_snapshot_registry |
| `rescale-wilderness-geography` | establish-continental-geography, project-metric-local-maps, charge-distance-based-travel, integrate-fatigue-aware-traversal, implement-sparse-settlement-graphs | world/maps/wilderness_provider.py::ElosernWildernessMapProvider/region_for_coordinates, world/maps/wilderness_destination.py, world/lore/wilderness_entry.py::validate_wilderness_entries/_iter_map_extents, world/maps/bootstrap.py::sync_wilderness |
| `activate-metric-settlements` | establish-continental-geography, implement-sparse-settlement-graphs, project-metric-local-maps, charge-distance-based-travel, integrate-fatigue-aware-traversal, rescale-wilderness-geography | world/maps/altoria_capital.py, world/maps/village_ciaran.py, world/maps/map_data.py, world/maps/bootstrap.py::sync_grid/_sync_grid_room_art, world/maps/city_gates.py::CITY_GATE_REGISTRY, world/lore/anchor_placement.py, world/lore/settlements/places.py and place declaration modules, world/maps/room_art.py::grid_scene_identity, world/rules/map_knowledge.py::encode_grid, world/quests/definitions.py::KNOWN_GRID_MAP_KEYS |
