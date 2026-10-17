# Proposal: Member item transfer rule and action

## Why

Design §4.1 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md` (amending §2 of the 2026-10-15 party combat design): players must move items between any present party members outside combat, for free and all-or-nothing. Today only `給` moves items one way from the caller, and nothing exposes a bilateral transfer to the WebClient.

## What Changes

- New rule `world/rules/party_inventory.py::transfer_item(acting, giver_id, receiver_id, item_key, quantity)`: out-of-combat only (`transfer_in_combat`), both members authorized for the organizing purpose, distinct members (`transfer_same_member`), equipped (`item_equipped`), locked (`item_locked`: guild property, exam-kit restriction) and missing (`item_not_held`) rejections, composition of two `plan_inventory_delta` plans in one transaction with containment synchronized, no time, no affinity.
- New exact WebClient action `party.transfer` `{giver_id, receiver_id, item_key, quantity}`; full canonical snapshot on success.
- **BREAKING (pre-release)** `webclient-action-dispatch` identity rule widens from combat-only subordinate references to exact party member-scoped schemas; registry allowlist gains `party.transfer`.
- Text commands (`給`, `取回`) are owned by `party-transfer-text-commands`.

## Capabilities

### New Capabilities

- `party-item-transfer`: the transfer rule, its rejections, atomicity, and the `party.transfer` action.

### Modified Capabilities

- `webclient-action-dispatch`: identity requirement admits exact party member references; the registry allowlist adds `party.transfer`.

## Impact

- New `world/rules/party_inventory.py`; new adapter/validator in `web/webclient/actions/party_actions.py` registered in `web/webclient/actions/registry.py`.
- Reuses `world/rules/equipment.py::plan_inventory_delta`, `apply_inventory_plan` internals, `world/skills/restrictions.exam_restriction`, `is_in_active_session`.
- Tests: `world/rules/tests/test_party_inventory_transfer.py`, `web/webclient/actions/tests/test_party_actions.py` (both sharded); registry-composition test updated.
- Observability: new `party_transfer` info event; lint runs.

## Effort

**6 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **4 of 30**.

- depends-on: party-member-authority

### Code and spec conflicts within the new batch

- `party-transfer-text-commands`: shared file `world/rules/party_inventory.py` (consumer), shared spec `party-item-transfer` (S; ordered).
- `party-panel-v3-view-member`, `item-holdings-panel`: shared spec `webclient-action-dispatch` registry requirement (S; each later change re-modifies the allowlist preserving `party.transfer`); shared file `web/webclient/actions/registry.py` (F).
- `party-member-equipment`, `companion-field-item-use`, `companion-field-cast-actions`, `party-practice-booking`, `shop-party-recipient-seller`: shared file `web/webclient/actions/registry.py` only through ordinary registration lines (F, trivial), and they rely on this change's identity wording (D).
- `party-inventory-panel`: consumes `transfer_item` preflight for row descriptors (D).
- `.github/evennia-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change.
