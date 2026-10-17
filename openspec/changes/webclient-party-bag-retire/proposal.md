# Proposal: Bag tab combat behaviour and retirement of the old bag

## Why

Design §6.2 and §9 of `docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`: in combat the holdings strip shows counts only, transfer controls are absent, the action bar shows 戰鬥中無法交換物品, 使用 becomes 設為 X 本回合的行動… (the member's v7 draft entry) and equipment toggles stay available for every member; `InventoryPanel` and `EquipmentDoll` are removed once their replacement lands, with stories, manifest entries and duplicate rules.

## What Changes

- `PartyBagTab.vue` combat behaviour through the existing `useCombatItem` flow for the viewed member.
- The combat dock root's `背包` row and every old bag opener open the party window on 背包.
- **BREAKING (pre-release)** delete `InventoryPanel.vue`, `EquipmentDoll.vue`, their stories, manifest titles (`World/InventoryPanel`, `Data/EquipmentDoll`), tests and `.elosern-root` duplicate rules; remove the bag and doll HUD requirements; move the wallet requirement to the party purse; update inventory-action, showcase, service acceptance, possession-hybrid and empty-guidance requirements that named the old bag.
- `web/webclient-app/AGENTS.md` drops "there is no companion equipment surface" and documents the bag routing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-party-window`: adds the combat bag requirement.
- `webclient-contextual-hud`: removes the bag and doll requirements, renames the wallet requirement to the party purse, updates empty guidance.
- `inventory-item-actions`: tile and dialog requirements move to the bag tab.
- `webclient-component-showcase`: surfaces and breakdown-story requirements name the bag tab.
- `webclient-service-menus`: browser acceptance names the bag tab.
- `webclient-possession-presentation`: the inventory hybrid scenarios read `party_inventory` for the viewed member.

## Impact

- `PartyBagTab.vue`, `AppClient.vue`, `stores/elosern/combat.js` (`useCombatItem` reuse), stories, manifest, Vitest; deletions above; one browser method.

## Effort

**5.5 hours total, strictly less than 8 hours**, including implementation, focused verification, documentation and integration.

## Batch: party member management

Declared implementation order: **25 of 32**.

- depends-on: webclient-party-bag-tab

### Code and spec conflicts within the new batch

- `party-member-equipment`, `companion-field-item-use`: last edited `InventoryPanel.vue` and `inventory-item-actions` requirements (F/S; those first; this deletes the panel and preserves their member fields).
- `webclient-component-showcase` "The map, art, and services surfaces…" (re-modified by `webclient-shop-window`), "The status, character, and skill surfaces…" and "Breakdown-state stories…" (re-modified by `webclient-party-status-tab`, `webclient-party-skill-tab`) (S; ordered, cumulative).
- `webclient-service-menus` "Service browser acceptance…": modified by `shop-party-recipient-seller` before and `webclient-shop-window` after (S; cumulative).
- `webclient-contextual-hud` purse requirement: re-modified by `webclient-shop-window` (S).
- `services-shop-structured-rows`: drops `services.inventory` after this change deletes its last consumer (D).
- `.github/browser-shards.json`: conditional manifest conflict.

### Active change coordination

No active OpenSpec change. The v7 combat item flow is reused unchanged.
