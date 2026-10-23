# Proposal

## Why

The prototype outlines already total about 73 KB, while both existing protocol validators reject generic envelopes over 64 KB and long lists.

## What Changes

- Measure real generated world payload sizes and enforce a bounded map-only exception.
- Confirm real WebSocket/browser round-trip delivery.
- Send bounded parts only if the measured transport cannot carry the chosen payload intact.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `webclient-oob-protocol`: Explicit measured world-map size/collection exception and end-to-end delivery contract.

## Impact

Touches presentation protocol/coordinator, browser protocol constants/validation/store and a focused managed transport test. Conflicts with publish-area-map-panel/world publication on protocol/coordinator and browser shards; serialize these changes. No global local_map budget increase.

## Sizing

Estimated implementation effort: 6 hours, including focused tests and documentation, for a gpt-luna-level worker. §9 row 5 is split: this 6h measurement/transport slice precedes the 8h world presenter/narrative slice; the combined work exceeds 8h. The shared codec/schema work is already complete upstream, so this 6h slice allocates 2h real-data measurement, 2h transport integration and 2h focused socket/parity verification/docs. No implementation is authorized by this proposal.

## Batch:

depends-on: define-map-panel-protocol
depends-on: author-district-landmarks
depends-on: publish-area-map-panel

Code-conflict notes: Touches presentation protocol/coordinator, browser protocol constants/validation/store and a focused managed transport test. Conflicts with publish-area-map-panel/world publication on protocol/coordinator and browser shards; serialize these changes. No global local_map budget increase.
