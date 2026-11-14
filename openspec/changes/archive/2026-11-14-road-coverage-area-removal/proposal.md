# Proposal

## Why

Road coverage was enforced area by area while the villages and hamlets were placed. After `valhalla-village-placement` the completed-area list covers every region that has roads, so the list no longer narrows anything. The village and hamlet tiers design (`docs/superpowers/specs/2026-11-13-village-hamlet-tiers-design.md` §9) says the list is then removed.

## What Changes

- **BREAKING (tool input).** The spacing validation checks every road gap on every road. The completed-area list, its file `tools/settlement_spacing_areas.json`, its loader and the `--areas` option are removed.
- A gap that crosses a region boundary, deferred until now, is checked. Any such gap still over 75 km is closed in this change by placing one hamlet on it (design D3).
- Documentation loses the description of completed areas.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `settlement-spacing`: road coverage applies to every road; the completed-area requirement is removed.

## Impact

- `tools/settlement_spacing.py`, `tests/test_settlement_spacing.py`; `tools/settlement_spacing_areas.json` is deleted.
- Documentation: `.agents/skills/map-data-authoring/references/locations-and-districts.md`.
- Only if a boundary gap remains: new hamlet rows and maps, and the regenerated road network, partition and reference context, under the rules of `valhalla-village-placement`.

## Batch:

- depends-on: valhalla-village-placement
- depends-on: settlement-spacing-validation (archived, so that `openspec/specs/settlement-spacing/spec.md` exists; `openspec validate` reports this as an informational note until then)
- conflicts: `tools/settlement_spacing_areas.json` is changed by every placement change. This change runs last.
