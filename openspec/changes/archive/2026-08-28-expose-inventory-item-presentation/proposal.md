## Why

The item-presentation registry is not visible to the browser: `services.inventory.rows` exposes only an item key, name, quantity, and equipped flag. The inventory redesign needs an authoritative per-row visual identity and must preserve the current safe handling of valid but unregistered inventory keys.

## What Changes

- **BREAKING**: Raise the `services` panel schema from version 1 to version 2 and add a required nullable `presentation` field to each inventory row.
- Project the immutable registry metadata as an exact, read-only object for registered inventory keys; project `presentation: null` for syntactically valid keys absent from `ITEM_REGISTRY`.
- Extend the Python presenter validator, dependency-free browser protocol validator, Vue fixtures, and transport/store tests to reject malformed, unknown, overlong, or extra presentation fields before the UI consumes them.
- Preserve the 32-row bound, aggregate counts, canonical equipment-derived flag, unavailable forms, and the absence of use, consume, equip, drag, or drop actions.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-service-menus`: the read-only inventory row contract gains validated registry presentation metadata and advances the services panel schema version.

## Impact

- `world/rules/service_view.py`, `web/webclient/presentation/services.py`, and their focused tests gain a read-only projection from `ITEM_REGISTRY`.
- `web/static/webclient/js/elosern/protocol.js`, its Node tests, Vue fixture data, and store/transport tests adopt services schema version 2.
- The change depends on `add-item-presentation-metadata`; it does not change inventory persistence, item mechanics, OOB actions, text-client behavior, or the visual layout. No compatibility or migration layer is required before release.
