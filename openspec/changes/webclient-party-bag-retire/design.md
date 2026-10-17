# Design: Bag tab combat behaviour and retirement of the old bag

## Context

See proposal.md. `InventoryPanel.vue` routes combat use to `store.useCombatItem`; `EquipmentDoll.vue` reads `character.equipment`; several main-spec requirements (contextual HUD bag/doll/wallet/empty guidance, inventory tiles/dialogs, showcase surfaces, service acceptance, possession hybrid) still describe the frameless bag.

## Goals / Non-Goals

**Goals:** truthful combat behaviour in the tab; deletion with no residue; every requirement naming the old bag updated or removed.

**Non-Goals:** shop window, services schema (separate changes).

## Decisions

- **Combat**: counts only from `item_holdings`, give controls absent, reason 戰鬥中無法交換物品 in the action bar, 設為 X 本回合的行動… calls `useCombatItem` for the viewed member (opening the actor's item frame), toggles stay enabled per the committed descriptors.
- **Deletion** follows the governed-wave rule: files, stories, manifest titles, tests and duplicate `.elosern-root` rules together.
- **Possession hybrid**: the bag shows the viewed member (commander by default), identical with and without possession; the HUD `status` hybrid is untouched.

## Risks / Trade-offs

- [Many spec edits in one change] → Each is mechanical and cumulative with the chained changes listed in the proposal.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: combat counts-only, no give controls, draft route, free toggles, no `inventory.use`/`party.transfer` sent in combat; opener routing. In-combat story; Storybook build and showcase coverage; one browser method (give and equip a companion, then observe transfer disabled in combat) registered in `.github/browser-shards.json`; AGENTS.md. `tests.test_webclient_frozen_contract`, `tools.contract_gate`.
