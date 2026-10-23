# Proposal

## Why

District discovery needs a frozen declaration contract and a read-only interpretation of existing visits before geometry can be generated.

## What Changes

- Add the frozen district registry and canonical landmark validation.
- Derive lighting from the existing visited record with no new state.
- Define the single multi-nation deep-forest region district.

## Capabilities

### New Capabilities
- `map-districts`: Frozen landmark declarations and knowledge-derived district lighting.

### Modified Capabilities
- None.

## Impact

Owns new `world/lore/map_districts.py`, registry validation and a rules-side read-only lighting helper. Conflicts with author-district-landmarks in the registry; partition consumes this contract. Narrative emission belongs to publish-world-map-panel.

## Sizing

Estimated implementation effort: 5 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 2 is split: this 5h registry/lighting slice precedes the separate 8h partition slice; the combined row exceeds the 8h limit. No implementation is authorized by this proposal.

## Batch:

depends-on: author-border-river-and-forest-edge

Code-conflict notes: Owns new `world/lore/map_districts.py`, registry validation and a rules-side read-only lighting helper. Conflicts with author-district-landmarks in the registry; partition consumes this contract. Narrative emission belongs to publish-world-map-panel.
