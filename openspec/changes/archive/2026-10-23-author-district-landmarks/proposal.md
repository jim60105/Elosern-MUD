# Proposal

## Why

The frozen partition needs the full approved exploration roster rather than the small initial registry or prototype cyclic names.

## What Changes

- Author approximately 110–130 real district/landmark pairs.
- Keep the one deep-forest region district and validate spacing/reachability.
- Regenerate committed ownership and outlines.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `map-districts`: Complete authored district/landmark content and regenerated partition.

## Impact

Edits `world/lore/map_districts.py` and generated partition/outline data from the tool. Conflicts with establish-map-districts and compute-map-district-partition on those files. World panel payload sizing must use this final roster.

## Sizing

Estimated implementation effort: 8 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 3 remains one content-authoring change, budgeted as 5h roster/name authoring, 1h regeneration and 2h focused integrity/reachability verification. No implementation is authorized by this proposal.

## Batch:

depends-on: compute-map-district-partition

Code-conflict notes: Edits `world/lore/map_districts.py` and generated partition/outline data from the tool. Conflicts with establish-map-districts and compute-map-district-partition on those files. World panel payload sizing must use this final roster.
