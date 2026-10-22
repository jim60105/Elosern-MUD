# Proposal

## Why

The approved drawer requires national borders derived from real traversable terrain. The current straight forest and western classifier boundaries do not match that geography.

## What Changes

- Author 界河 and exactly three fords.
- Replace straight forest/highland boundaries and derive nominal territory and displayed borders.
- Re-check region-keyed consumers and anchor/harbour reachability.
- **BREAKING**: replace the old Y2200/Y1700 geography without migrations.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `wilderness-terrain`: Amend terrain and political-control boundaries; add the river crossing contract.

## Impact

Touches `world/maps/wilderness_provider.py`, `world/lore/wilderness_regions.py`, geographic lore and region-keyed consumer tests. Conflicts with district partition and landmark generation; apply before them. Keep effective demographics in `continental-geography` unchanged.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 1 remains one change, budgeted as 4h geography, 2h consumer corrections and 2h tests/documentation. No implementation is authorized by this proposal.

## Batch:

depends-on: none

Code-conflict notes: Touches `world/maps/wilderness_provider.py`, `world/lore/wilderness_regions.py`, geographic lore and region-keyed consumer tests. Conflicts with district partition and landmark generation; apply before them. Keep effective demographics in `continental-geography` unchanged.
