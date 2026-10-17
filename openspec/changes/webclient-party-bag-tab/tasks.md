# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration.

## 1. Bag tab (3h)

- [ ] 1.1 Implement `PartyBagTab.vue` (doll with slot filter, rows, detail, `HoldingsStrip`, `ActionBar` with stepper, give, use/equip) and route the combat-root `背包` row and old openers to it; verify Vitest item-selection payload, holdings without invention, stepper bounds, `party.transfer` payload, disabled receive reason, use confirmation, equip label naming the replaced item.
- [ ] 1.2 Implement combat behaviour (counts only, no give controls, 戰鬥中無法交換物品, 設為 X 本回合的行動… through `useCombatItem`, free toggles); verify Vitest that no `inventory.use` or `party.transfer` is sent in combat.

## 2. Deletion and specs (1.5h)

- [ ] 2.1 Delete `InventoryPanel.vue`, `EquipmentDoll.vue`, their stories, manifest titles, tests and duplicate `.elosern-root` rules; add bag stories (consumable, equipment, in-combat) at both sizes; run `pnpm run build-storybook` and `pnpm run showcase-coverage`.

## 3. Browser evidence and docs (1.5h)

- [ ] 3.1 Add one browser method that gives potions to a companion and equips a companion, registered in `.github/browser-shards.json`; update `web/webclient-app/AGENTS.md` (remove the no-companion-equipment statement, document bag routing).

## 4. Integration (1h)

- [ ] 4.1 Annotate canonical IDs for the added/modified/renamed requirements, run the touched Vitest files, `tests.test_evennia_test_optimization_contract`, `tests.test_webclient_frozen_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-bag-tab --strict`.
