# Proposal: Item holdings query panel

## Why

Design §3.3, §6.2 and §7 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the bag's holdings strip and the shop's comparison strip need, for the selected item only, every member's held count and, for equipment, every member's stat delta against that member's current slot occupant; the client computes neither. No such read exists.

## What Changes

- New pure rules read `world/rules/party_inventory.py::item_holdings(acting, giver, item_key, *, in_combat)` and `equipment_delta(member, item_key)` (hypothetical swap through the breakdown read model; no write).
- New panel `item_holdings` v1 (`web/webclient/presentation/item_holdings.py`), available in exploration and combat, with per-member `held`, `equipped`, `delta` and `receive` facts.
- **BREAKING (pre-release)** `party.view_member` payload becomes `{member_id, tab, skill_key, item_key}` (nullable item; `skill_key` from `character-skill-growth-fields`); the selection stores the item; its affected panels add `item_holdings`. The design lists only `party.view_member` and `party.transfer` as new action identifiers, so the holdings query rides the existing selection action instead of adding a third identifier (recorded as a planning interpretation).
- JS mirror, parity, allowlist and fixtures.

## Capabilities

### New Capabilities

- `webclient-item-holdings-panel`: the holdings query contract.

### Modified Capabilities

- `webclient-party-panel`: the `party.view_member` requirement carries the selected item.

## Impact

- `world/rules/party_inventory.py`, `world/rules/status_query/` (breakdown with an overridden equipment mapping), new `web/webclient/presentation/item_holdings.py`, `party_view_selection.py`, `party_actions.py`, `registry.py`, JS mirror, allowlists, fixtures.
- Tests: `world/rules/tests/test_item_holdings.py`, presenter tests (sharded), mirror tests, action schema tests.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **20 of 32**.

- depends-on: party-inventory-panel

### Code and spec conflicts within the new batch

- `party-panel-v3-view-member`: this delta modifies the `party.view_member` requirement that change adds (S; strict validation shows an informational archive-order notice until it is synced); shared files `party_view_selection.py`, `party_actions.py` (F; that first).
- `party-inventory-panel`: shared rules module and affected tuple (F; that first).
- `services-shop-structured-rows`: reuses `equipment_delta` for the viewed-member stock delta (D).
- `webclient-window-primitives` (`HoldingsStrip`), `webclient-party-bag-tab`, `webclient-shop-window`: consume this panel (D).
- Protocol registry/allowlists/fixtures (F, conditional).

### Active change coordination

No active OpenSpec change.
