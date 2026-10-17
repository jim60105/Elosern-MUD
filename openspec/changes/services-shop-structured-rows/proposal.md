# Proposal: services v7 structured shop rows

## Why

Design §4.3, §5 and §7 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: stock rows gain the item presentation (kind, icon, rarity, summary) and the viewed member's delta or held count; sellable rows list the viewed member's unequipped items; each view shows one price (buy view buy prices, sell view sell prices); and the `inventory` section leaves `services`. Today `services` v6 stock rows carry both prices and no presentation, sellable rows come from the puppet, and the puppet's inventory rides `services`.

## What Changes

- **BREAKING (pre-release)** `services` v6 → v7: removes `inventory` and `pagination.inventory_total`; the shop section adds `member_id`; stock rows add `presentation` and `viewed {held, delta}` and drop `sell_copper`; sellable rows list the viewed member's unequipped copies with `presentation`. Python validator, JS mirror, parity and fixtures move together.
- `world/rules/service_view.py` drops the inventory section and builds shop facts for the viewed member, reusing `equipment_delta` (`item-holdings-panel`) for `viewed.delta` and the economy preflights from `shop-party-recipient-seller` for enablement.
- `party.view_member` affected panels add `services` (the shop rows follow the viewed member).
- Transitional `ShopPanel.vue` sends `services.shop.member_id` as recipient/seller (instead of the controlled figure) and renders the new rows (buy price in the buy list, sell price in the sell list) until the shop window replaces it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-service-menus`: the services panel, shop surface and reconnect requirements.

## Impact

- `web/webclient/presentation/services.py`, `world/rules/service_view.py`, `party_actions.py`, JS mirror, fixtures, `web/webclient-app/components/ShopPanel.vue`, `QuestDrawer.vue` (reads `services` only for guild sections; verified unaffected).
- Tests: services presenter/validator/parity tests, service view tests, Vitest ShopPanel.

## Effort

**6.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **26 of 32**.

- depends-on: webclient-party-bag-retire
- depends-on: item-holdings-panel
- depends-on: shop-party-recipient-seller

### Code and spec conflicts within the new batch

- `shop-party-recipient-seller`: shared files `ShopPanel.vue`, `service_actions.py` callers (F; that first); spec requirement "Service actions are exact…" is a different requirement (S).
- `webclient-party-bag-retire`: deletes the last `services.inventory` consumer (D; must land first).
- `party-inventory-panel`, `item-holdings-panel`: shared rules helpers (D).
- `webclient-shop-window`: consumes v7 and deletes `ShopPanel.vue` (F; ordered).
- Protocol fixtures/parity (F, conditional).

### Active change coordination

No active OpenSpec change.
