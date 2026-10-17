# Proposal: Party window 背包 tab

## Why

Design §6.2 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: the 背包 tab shows the viewed member's equipment doll and bag, the holdings strip with 交給 X, a quantity stepper, 使用… or 裝備, and in combat counts only, no transfer, the 戰鬥中無法交換物品 reason, 設為 X 本回合的行動… and free equipment toggles. It replaces `InventoryPanel` and `EquipmentDoll`.

## What Changes

- New `PartyBagTab.vue` in the party window: doll (slot filter), bag rows, item detail with `HoldingsStrip`, `ActionBar` with stepper, give, use/equip, combat behaviour; dispatches `party.view_member` (item selection), `party.transfer`, `inventory.use`, `inventory.toggle_equip` with the viewed member, and the existing combat item flow in combat.
- The combat dock root's `背包` row and the old bag openers open the party window on 背包.
- **BREAKING (pre-release)** delete `InventoryPanel.vue`, `EquipmentDoll.vue`, their stories, manifest titles (`World/InventoryPanel`, `Data/EquipmentDoll`), tests and `.elosern-root` duplicate rules; remove the two drawer requirements and move the wallet requirement to the party purse.
- `web/webclient-app/AGENTS.md` drops "there is no companion equipment surface" and documents the bag tab routing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-window`: adds the bag tab requirements.
- `webclient-contextual-hud`: removes the bag and doll requirements; the wallet requirement becomes the party purse (renamed).
- `inventory-item-actions`: tile and dialog requirements move to the bag tab.
- `webclient-component-showcase`: the surfaces and breakdown-story requirements name the bag tab instead of the deleted components.

## Impact

- `web/webclient-app/components/PartyBagTab.vue`, `PartyWindow.vue`, `AppClient.vue`, `composables/intents.js`, `stores/elosern/combat.js` (`useCombatItem` reuse), stories, manifest, Vitest; deletions above; one browser method.

## Effort

**7 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **23 of 30**.

- depends-on: webclient-party-window-member-tab
- depends-on: party-inventory-panel
- depends-on: item-holdings-panel
- depends-on: shop-party-recipient-seller

### Code and spec conflicts within the new batch

- `party-member-equipment`, `companion-field-item-use`: last edited `InventoryPanel.vue` and `intents.js` (F; those first; this deletes the panel).
- `webclient-component-showcase` requirements "The map, art, and services surfaces…" (also re-modified by `webclient-shop-window`), "The status, character, and skill surfaces…" (also by `webclient-party-status-tab`, `webclient-party-skill-tab`) and "Breakdown-state stories…" (also by `webclient-party-status-tab`) (S; ordered, each preserving earlier edits).
- `webclient-contextual-hud` purse requirement: re-modified by `webclient-shop-window` (S; ordered).
- `services-shop-structured-rows`: drops `services.inventory` after this change deletes its last consumer (D; ordered).
- `webclient-party-window-member-tab`: shared `PartyWindow.vue`, `AppClient.vue`, manifest (F; that first).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The v7 combat item flow (`store.useCombatItem`) is reused unchanged.
