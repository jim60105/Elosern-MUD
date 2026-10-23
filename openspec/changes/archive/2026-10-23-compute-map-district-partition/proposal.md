# Proposal

## Why

A reproducible offline partition is needed to reveal districts without recomputing walking-distance geometry at runtime.

## What Changes

- Compute barrier-aware 5 km Voronoi ownership after region districts.
- Store RLE ownership and smoothed outlines; expose frozen runtime lookup.
- Add an exact recomputation test.

## Capabilities

### New Capabilities
- `map-district-partition`: Offline reproducible ownership, outlines and frozen runtime lookup.

### Modified Capabilities
- None.

## Impact

Owns new offline partition tool, frozen generated map data and `world/maps/` read adapter. Conflicts with landmark authoring regenerating the same data. Geography and registry must already be applied.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 2 partition sub-change, split from establish-map-districts to keep deterministic routing, outline generation and recomputation testing within 8h. No implementation is authorized by this proposal.

## Batch:

depends-on: establish-map-districts

Code-conflict notes: Owns new offline partition tool, frozen generated map data and `world/maps/` read adapter. Conflicts with landmark authoring regenerating the same data. Geography and registry must already be applied.
