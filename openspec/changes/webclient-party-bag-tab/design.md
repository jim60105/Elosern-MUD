# Design: Party window 背包 tab

## Context

See proposal.md. `InventoryPanel.vue` renders `services.inventory` tiles, a confirmation dialog for use, direct toggles, and in combat routes use to `store.useCombatItem`; `EquipmentDoll.vue` renders `character.equipment`. The prototype `tabs/BagTab.vue` defines the approved layout (doll above rows, detail with ribbon, holdings strip, action bar).

## Goals / Non-Goals

**Goals:** a complete bag tab for any member, in both modes, from committed panels only; deletion of the two old components.

**Non-Goals:** shop comparison (shop window), the services schema change (next protocol change).

## Decisions

- **Item selection is server state** through `party.view_member {member_id, tab: "bag", item_key}`; the detail waits for `item_holdings` for that key and shows the committed unavailable reason otherwise.
- **Stepper** bounds: 1..`give.max_quantity`, forced to 1 for equipment rows; the quantity resets when the viewed member or item changes.
- **Use** keeps the existing labelled confirmation dialog in exploration (now inside the window); in combat it calls the existing `useCombatItem` for the viewed member, which already opens the actor's item frame.
- **Equip label** names the replaced singleton occupant from the doll (`party_inventory.equipment`), never a client-chosen accessory.
- **Deletion** follows the governed-wave rule: component files, stories, manifest titles, tests and duplicate `.elosern-root` rules removed together; specs edited so no requirement names them.

## Risks / Trade-offs

- [Combat flow coupling] → Reuses the existing tested store path; Vitest asserts no `inventory.use` in combat.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: slot filter, item selection payload, holdings rendering without invention, stepper bounds, give payload, disabled receive reason, use confirmation, equip label, combat counts-only/no-give/draft route/free toggles, possession-identical rendering. Stories (consumable, equipment, in-combat) at both sizes; Storybook build and showcase coverage. One browser method (give and equip a companion) registered in `.github/browser-shards.json`. `web/webclient-app/AGENTS.md` updated. `tools.contract_gate`.
