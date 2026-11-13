# Proposal

## Why

Nothing exists below a town: the closed location-kind list has no value for a village or a hamlet, so none can be authored. The village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §3) adds the two kinds, shared by humans and beastfolk, before any tool or content can use them.

## What Changes

- The closed location-kind vocabulary gains `village` (村莊) and `hamlet` (小村莊), in the map schema and in `AnchorKind`.
- Both kinds are public settlements: they draw as `settlement` on the world map, they are distant-sighting sources, and the sight rulebook gains one silhouette row for each.
- Both kinds are inhabited settlement categories for the automatic monster birth exclusion, with the same one-cell minimum buffer as the existing kinds.
- A village or hamlet joins nation and population lore like a city, town or port.
- The map editor's kind dropdown lists both kinds.
- Documentation of the kind list and the ID prefixes (`village_`, `hamlet_`).
- No location of either kind is added. Tools that size, route or validate them are separate changes.

Human-reviewed, not tested: the four silhouette sentences in `world/rules/rulebook/sight.yaml` (design D3), reviewed against `docs/lore/settlement-locations.md` 〈人類聚落的層級差異〉.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `regional-ecology`: the inhabited settlement categories that exclude automatic births now include villages and hamlets.
- `lore-registries`: the national settlement lore join covers villages and hamlets.

## Impact

- `packages/map-core/elosern_map_core/schema.py`, `world/lore/anchors.py`, `world/maps/population_geometry.py`, `world/rules/sight.py`, `world/rules/rulebook/sight.yaml`, `tools/map-editor/frontend/src/components/ContinentInspector.vue`.
- Tests: `world/maps/tests/test_population_geometry.py`, `world/lore/tests/test_anchors.py`, `web/webclient/presentation/tests/test_world_map.py`.
- Documentation: `.agents/skills/map-data-authoring/SKILL.md`, `.agents/skills/map-data-authoring/references/locations-and-districts.md`, `docs/development/map-authoring-documents.md`, `docs/development/regional-monster-population.md`.
- Regenerated: `content/map-reference-context.json`.
- The design's instruction to correct any test that reconciles settlement populations against the world total finds nothing to correct (design D5).

## Batch:

- depends-on: elven-village-id-cutover
- conflicts: `world/lore/anchors.py`, `.agents/skills/map-data-authoring/references/locations-and-districts.md` and `content/map-reference-context.json` are also changed by `elven-village-id-cutover`.
- conflicts: `packages/map-core/elosern_map_core/schema.py` is also changed by `single-cell-footprint-entry` and `settlement-spacing-validation`, in other declarations.
