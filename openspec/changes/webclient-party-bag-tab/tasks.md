# Tasks

Total estimate: **5 hours**, including implementation, focused verification, documentation and integration.

## 1. Browse and select (2h)

- [ ] 1.1 Implement the doll with slot filter, bag rows and item detail with `HoldingsStrip` in `PartyBagTab.vue`; verify Vitest slot filtering, the item-selection payload, and holdings rendering without invention.

## 2. Give, use and equip (2h)

- [ ] 2.1 Implement the stepper, per-cell 交給 X, 使用… confirmation and 裝備 label; verify Vitest stepper bounds, `party.transfer` payload with the viewed member as giver, disabled receive reasons, use confirmation and `inventory.use`/`inventory.toggle_equip` payloads with the viewed member's `actor_id`.

## 3. Integration (1h)

- [ ] 3.1 Add bag stories (consumable, equipment) at both sizes with the manifest title, run `pnpm run build-storybook`, `pnpm run showcase-coverage`, the touched Vitest files, `uv run --locked python -m tools.contract_gate` and `openspec validate webclient-party-bag-tab --strict`.
