# Proposal: party_inventory panel

## Why

Design §5 and §6.2 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 背包 tab shows the viewed member's equipment doll and bag rows with toggle, use and transfer descriptors plus the party purse. Today the bag reads `services.inventory` (the puppet's rows) and the doll reads `character.equipment`.

## What Changes

- New presenter/validator `web/webclient/presentation/party_inventory.py` (`party_inventory` v1) for the viewed member, available in exploration and combat: purse (commander wallet), normalized equipment with accessory limit, bag rows with presentation, `equipped_count`, `slot`, and `use`/`toggle`/`give` descriptors computed by the existing preflights (`preflight_equipment_toggle`, item-use preflight, transfer preflight from `party-item-transfer`).
- In combat `give` is disabled with 「戰鬥中無法交換物品。」 and `use` is a combat-draft descriptor (the bag tab saves the member's v7 draft entry through `combat.command`).
- `party.view_member` affected panels add `party_inventory`. JS mirror, parity, allowlist and fixtures.
- `services.inventory` is not removed here; it is dropped by `services-shop-structured-rows` after the bag tab deletes its last consumer.

## Capabilities

### New Capabilities

- `webclient-party-inventory-panel`: the `party_inventory` panel contract.

### Modified Capabilities

None.

## Impact

- New `web/webclient/presentation/party_inventory.py`; rules read helper `world/rules/party_inventory.py::inventory_view(member, *, in_combat)`; `registry.py`; `party_actions.py`; JS mirror, allowlists, fixtures.
- Tests: `web/webclient/presentation/tests/test_party_inventory_panel.py`, rules view tests (sharded), mirror tests.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **18 of 30**.

- depends-on: party-panel-v3-view-member
- depends-on: party-item-transfer
- depends-on: companion-field-item-use

### Code and spec conflicts within the new batch

- `party-item-transfer`, `party-member-equipment`, `companion-field-item-use`: shared file `world/rules/party_inventory.py` (F; those first); descriptor semantics consumed (D).
- `item-holdings-panel`: shares the rules view module and `party_actions.py` affected tuple (F; this first).
- `webclient-party-bag-tab`: consumes this panel (D).
- Protocol registry/allowlists/fixtures shared with every protocol change (F, conditional).

### Active change coordination

No active OpenSpec change.
