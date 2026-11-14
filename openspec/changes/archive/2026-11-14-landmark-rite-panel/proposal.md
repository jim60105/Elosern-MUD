# Proposal

## Why

The browser needs committed, server-owned data to present a landmark rite: which landmark and guardian this is, which ritual options exist, which the player already experienced, who may perform, and the scene of the last committed rite. Today the browser has only the action's one-off result. This change adds the `rite` presentation panel and its browser-side mirror so the interface change that follows reads validated panel data and never invents it.

No visible surface changes: the panel is published and validated, and no component reads it yet.

## What Changes

- New eager presentation panel `rite`, schema version 1: the district and whether it is lit, the guardian, a nullable artwork descriptor, the options with a `companion` flag, the eligible performers, the nullable delivery of the last committed rite at this node, and the experienced option keys.
- The panel is available exactly when the record owner stands on a rite landmark's canonical node, lit or unlit, in the wilderness or in a settlement room; elsewhere it is the registered unavailable form.
- The `explore.landmark_rite` action stores its delivery as non-persistent presentation state bound to the node, and the panel carries it while the owner stays on that node.
- The browser protocol gains the exact mirror validator and the panel name; a malformed or oversize panel is rejected whole.
- `artwork` is always null in this change (`landmark-rite-art` fills it).

## Capabilities

### New Capabilities

- `landmark-rite-panel`: the `rite` panel's availability, shape, bounds and delivery, on both sides of the wire.

### Modified Capabilities

None.

## Impact

- New: `web/webclient/presentation/rite.py`, `web/webclient/presentation/tests/test_rite_panel.py`, `web/static/webclient/js/elosern/protocol/panels/rite.js`, `web/static/webclient/js/tests/rite_panel.test.js`.
- Edits: `web/webclient/presentation/registry.py` (registration and validator), `web/webclient/actions/rite_actions.py` (store the delivery), `web/static/webclient/js/elosern/protocol/constants.js`, `web/static/webclient/js/elosern/protocol/envelope.js`, `web/static/webclient/js/elosern/protocol.js`, `web/webclient-app/stores/elosern/shared.js` (panel name list), `tests/test_panel_schema_version_parity_contract.py`, `docs/development/webclient-synchronization.md`, `.github/evennia-shards.json`.
- The design's panel example is superseded in two details, recorded in the design: `art` is the existing artwork descriptor or null, and a performer name is bounded at 128 code points like every other member name on the wire.

## Batch:

- depends-on: landmark-rite-action
- conflicts: `landmark-rite-art` edits `web/webclient/presentation/rite.py`; it runs after this change.
