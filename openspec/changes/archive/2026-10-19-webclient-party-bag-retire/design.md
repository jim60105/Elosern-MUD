# Design: Bag tab combat behaviour and retirement of the old bag

## Context

See proposal.md. `InventoryPanel.vue` routes combat use to `store.useCombatItem`; `EquipmentDoll.vue` reads `character.equipment`; several main-spec requirements (contextual HUD bag/doll/wallet/empty guidance, inventory tiles/dialogs, showcase surfaces, service acceptance, possession hybrid) still describe the frameless bag.

## Goals / Non-Goals

**Goals:** truthful combat behaviour in the tab; deletion with no residue; every requirement naming the old bag updated or removed.

**Non-Goals:** shop window, services schema (separate changes).

## Decisions

- **Combat**: counts only from `item_holdings`, give controls absent, reason 戰鬥中無法交換物品 in the action bar, 設為 X 本回合的行動… calls `useCombatItem` for the viewed member (opening the actor's item frame), toggles stay enabled per the committed descriptors.
- **Cross-member draft**: when the viewed member is not the commanded one, 設為 X 本回合的行動… first sends the actor selector's own read-only `combat.actor_choices` for that member, and the item frame opens only after that member's choices commit; the card stays on that member afterwards, exactly as an explicit actor switch would leave it. A refused or rejected switch drops the intent with visible feedback; a closed window, another member selection or another actor query drops it silently.
- **Openers**: every old bag opener funnels into `openHudDrawer("inventory")`, which the store aliases to the party window on 背包; the opener payloads in `web/static` are unchanged.
- **Breakdown stories**: `party_inventory` v1 carries no trait layers, so the layer and 16-layer-bound properties stay with the character fixture's drawer story; the bag tab's breakdown story is its equipment story, whose `item_holdings` delta changes are the server's adjustment strings.
- **Spec drift**: the requirements that still described the deleted drawer and are not re-modified by a later change of the batch (the reference-drawer frame scenarios, the required-component and held-item bag scenarios, the exploration acceptance list) are updated here.
- **Deletion** follows the governed-wave rule: files, stories, manifest titles, tests and duplicate `.elosern-root` rules together.
- **Possession hybrid**: the bag shows the viewed member (commander by default), identical with and without possession; the HUD `status` hybrid is untouched.

## Risks / Trade-offs

- [Many spec edits in one change] → Each is mechanical and cumulative with the chained changes listed in the proposal.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: combat counts-only, no give controls, draft route, free toggles, no `inventory.use`/`party.transfer` sent in combat; opener routing. In-combat story; Storybook build and showcase coverage; one browser method (give and equip a companion, then observe transfer disabled in combat) registered in `.github/browser-shards.json`; AGENTS.md. `tests.test_webclient_frozen_contract`, `tools.contract_gate`.
