# Proposal

## Why

The three elven villages use the `village_` ID prefix, which the village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §3.1) reserves for human villages and beastfolk tribal villages. The prefix must be free before any `village` location is placed.

## What Changes

- **BREAKING (data identity).** Rename three location IDs in one cutover, with no alias and no migration:
  - `village_fionnen` → `elven_village_fionnen`
  - `village_ciaran` → `elven_village_ciaran`
  - `village_eolas` → `elven_village_eolas`
- The settlement map `content/maps/settlements/village_ciaran.yaml` becomes `elven_village_ciaran.yaml` with `id: elven_village_ciaran`, so its grid node IDs change from `grid:village_ciaran:…` to `grid:elven_village_ciaran:…`.
- Every current reference follows: location data, `ANCHOR_LORE`, the settlement registry, service host bindings, race home anchors, the commerce scale row, interior exteriors, tests and current documentation.
- Regenerated: the district partition, the road network and the reference context.
- `docs/lore/settlement-locations.md`: the 〔提案〕 note about the prefix becomes a statement of fact. The wording is human-reviewed against that document (design D4).
- Spec-less: this is an identity rename of authored data. No requirement names these IDs and no behaviour changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true` is set.

## Impact

- 36 files change by one substitution, one of them after a rename; 3 generated artifacts are rewritten.
- A development database created before this change holds rooms and map knowledge under the old IDs. The supported recovery is the reset in `docs/development/database-reset.md`.
- Ecology zone keys such as `village_eolas_hinterland` are zone identities, not location references, and keep their names (design D2).

## Batch:

- depends-on: none
- conflicts: `world/lore/anchors.py`, `content/maps/locations.yaml`, `.agents/skills/map-data-authoring/references/locations-and-districts.md` and `content/map-reference-context.json` are also changed by `village-hamlet-kinds`. Land this change first.
- conflicts: `world/maps/data/road_network.json` and `world/maps/data/district_partition.json` are regenerated here and by every placement change. Never merge them by hand; regenerate.
