# Proposal: Companion field item use

## Why

Design §4.4 and §6.2 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: out-of-combat item use takes an actor; the bag tab's 使用 must act for the viewed member. Today `inventory.use` and `使用` act only for the puppet.

## What Changes

- New rules entry `world/rules/party_inventory.py::use_member_item(acting, member_id, item_key, target)`: member boundary (acting purpose), then the existing `use_item(member, item_key, target=...)`; the settlement scope from `party-field-settlement-scope` settles the present party.
- **BREAKING (pre-release)** `inventory.use` payload becomes `{actor_id, item_key[, target_key]}`; target resolution stays room-relative to the user. Active combat still rejects the action.
- `使用 <物品> [目標] [= <成員>]`: outside combat the member uses the item; inside an active session it saves that member's item command through the existing actor command path (`combat command <token> item ...`).
- Transitional client: the current bag drawer sends the controlled figure's id.
- Both player command documents updated.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `companion-field-actions`: adds explicit-user item use.
- `inventory-item-actions`: `inventory.use` payload with `actor_id`; `使用` names a member.
- `webclient-service-menus`: the service-action allowlist admits the use's exact `actor_id`.

## Impact

- `world/rules/party_inventory.py`, `web/webclient/actions/service_actions.py`, `commands/items.py` (`CmdUseItem`), `web/webclient-app/composables/intents.js`, `components/InventoryPanel.vue`.
- Docs: both player command documents.
- Tests: `world/rules/tests/test_companion_field_item_use.py` (sharded), service action tests, `commands/tests` item command tests, Vitest intents.

## Effort

**5.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **9 of 31**.

- depends-on: party-field-settlement-scope
- depends-on: party-member-equipment
- depends-on: companion-field-cast-rule

### Code and spec conflicts within the new batch

- `webclient-service-menus` requirement "Service actions are exact, allowlisted, and server-authoritative" is re-modified in order by `party-member-equipment`, `companion-field-item-use` and `shop-party-recipient-seller`; each later delta preserves the earlier member references (S, ordered).

- `party-member-equipment`: shared files `service_actions.py`, `commands/items.py`, `intents.js`, `InventoryPanel.vue`; shared spec `inventory-item-actions` (F; that change first; this delta preserves its toggle wording).
- `companion-field-cast-rule`: shared spec `companion-field-actions` (S; that change creates it) and both command docs (F).
- `party-inventory-panel`: consumes the use descriptor shape (D).
- `webclient-party-bag-retire`: removes `InventoryPanel.vue` (F; ordered).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
