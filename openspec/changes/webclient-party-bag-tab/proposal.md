# Proposal: Party window 背包 tab (browse, give, use, equip)

## Why

Design §6.2 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 背包 tab shows the viewed member's equipment doll and bag, the holdings strip with 交給 X, a quantity stepper, and 使用… or 裝備 naming the replaced item. This change builds the exploration tab; `webclient-party-bag-retire` adds its combat behaviour and deletes `InventoryPanel`/`EquipmentDoll` (split after review to keep each change well under 8 hours).

## What Changes

- New `PartyBagTab.vue` in the party window: doll with slot filter, bag rows, item detail (ribbon, name, summary) with `HoldingsStrip`, `ActionBar` with stepper, per-cell 交給 X, 使用… (labelled confirmation) and 裝備 (naming the replaced item); dispatches `party.view_member` (item selection), `party.transfer`, `inventory.use` and `inventory.toggle_equip` with the viewed member.
- In combat this change renders the tab's committed counts only and disables its controls with their committed reasons; the full combat behaviour lands in `webclient-party-bag-retire`.
- `InventoryPanel` stays reachable until the retire change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-window`: adds the bag browse, give and use/equip requirements.

## Impact

- `web/webclient-app/components/PartyBagTab.vue`, `PartyWindow.vue`, `composables/intents.js`, stories, manifest (adds the tab component), Vitest.

## Effort

**5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **24 of 32**.

- depends-on: webclient-party-window-member-tab
- depends-on: party-inventory-panel
- depends-on: item-holdings-panel
- depends-on: shop-party-recipient-seller

### Code and spec conflicts within the new batch

- `webclient-party-window-member-tab`: shared `PartyWindow.vue`, `AppClient.vue`, manifest (F; that first).
- `webclient-party-bag-retire`: extends this tab and its spec file (F/S; ordered next).
- `party-member-equipment`, `companion-field-item-use`: shared `intents.js` (F; those first).

### Active change coordination

No active OpenSpec change.
