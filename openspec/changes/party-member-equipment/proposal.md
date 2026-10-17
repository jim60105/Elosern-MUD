# Proposal: Equipment toggle for any present member

## Why

Design §4.2 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the toggle action must take an actor and accept any present party member, free in exploration and in combat. Today `inventory.toggle_equip` accepts only `{item_key}` and toggles the puppet; `裝備` is commander-only.

## What Changes

- New rules entry `world/rules/party_inventory.py::toggle_member_equipment(acting, member_id, item_key)`: member boundary (organizing purpose, knocked-out admitted), then the unchanged `toggle_equipment(member, item_key)`.
- **BREAKING (pre-release)** `inventory.toggle_equip` payload becomes exactly `{actor_id, item_key}`; the current client sends the viewed/controlled member id (the current bag drawer sends the controlled figure's id until the bag tab lands).
- `裝備 <物品> [= <成員>]`; both player command documents updated.
- In combat the toggle stays free; the member's saved draft entry is revalidated at submission (existing preflight), and previews refresh through the full snapshot.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `inventory-item-actions`: exact toggle payload with `actor_id`; text `裝備` names a member.
- `equipment-inventory`: adds the any-present-member requirement.
- `webclient-service-menus`: the service-action allowlist admits the toggle's exact `actor_id`.

## Impact

- `world/rules/party_inventory.py`, `web/webclient/actions/service_actions.py` (validator/adapter), `commands/items.py` (`CmdToggleEquip`), `web/webclient-app/composables/intents.js` and `components/InventoryPanel.vue` (send `actor_id` of the controlled figure), JS action tests.
- Docs: `docs/game/commands.md`, `docs/game/command-reference.md`.
- Tests: `world/rules/tests/test_party_member_equipment.py` (sharded), updated service action tests, Vitest for the drawer payload.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **6 of 31**.

- depends-on: party-member-authority
- depends-on: party-transfer-text-commands

### Code and spec conflicts within the new batch

- `webclient-service-menus` requirement "Service actions are exact, allowlisted, and server-authoritative" is re-modified in order by `party-member-equipment`, `companion-field-item-use` and `shop-party-recipient-seller`; each later delta preserves the earlier member references (S, ordered).

- `party-transfer-text-commands`: shared files `commands/items.py`, both command docs (F; that change first, hence the ordering dependency).
- `companion-field-item-use`: shared files `web/webclient/actions/service_actions.py`, `commands/items.py`, `web/webclient-app/composables/intents.js`; shared spec `inventory-item-actions` both requirements (F; this change first, the later one re-modifies preserving `actor_id` on the toggle).
- `party-inventory-panel`: consumes the toggle descriptor shape (D).
- `webclient-party-bag-retire`: removes `InventoryPanel.vue` edited here (F; ordered).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
