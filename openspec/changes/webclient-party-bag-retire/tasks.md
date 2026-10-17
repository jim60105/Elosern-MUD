# Tasks

Total estimate: **5.5 hours**, including implementation, focused verification, documentation and integration.

## 1. Combat behaviour and routing (2h)

- [ ] 1.1 Implement the combat bag behaviour and route the combat-root `背包` row and old openers to the tab; verify Vitest counts-only, absent give controls, the 戰鬥中無法交換物品 reason, the draft route through `useCombatItem`, free toggles, and that no `inventory.use` or `party.transfer` is sent in combat.

## 2. Deletion (1.5h)

- [ ] 2.1 Delete `InventoryPanel.vue`, `EquipmentDoll.vue`, their stories, manifest titles, tests and duplicate `.elosern-root` rules; add the in-combat bag story; run `pnpm run build-storybook`, `pnpm run showcase-coverage` and `tests.test_webclient_frozen_contract`.

## 3. Browser evidence and integration (2h)

- [ ] 3.1 Add one browser method (give potions to a companion, equip a companion, enter combat and observe transfer disabled), registered in `.github/browser-shards.json`; update `web/webclient-app/AGENTS.md`; annotate canonical IDs; run `tests.test_evennia_test_optimization_contract`, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-bag-retire --strict`.
