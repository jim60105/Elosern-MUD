## 1. Component template and script

- [ ] 1.1 In `CharacterStatusDrawer.vue`, add an `ATTRIBUTE_KEYS = ["atk_phys", "agility", "defense", "magic_level"]` allowlist and a computed `attributeRows` that filters+orders `traits` by that list; replace the `屬性` section's `v-for="row in traits"` with `v-for="row in attributeRows"`.
- [ ] 1.2 Fix the local `VITALS` constant's `mp`/`sp` labels from `氣力`/`精力` to `魔力`/`耐力`.
- [ ] 1.3 Add a local label override for the `屬性` row rendering `magic_level` as `魔階` (keep every other attribute's `row.label` from the server as-is); change the `計數・公會` rank row's hardcoded text (`CharacterStatusDrawer.vue:272`) from `階級` to `公會階級`.
- [ ] 1.4 Reorder the template's `<section>` blocks to: 生命量 → 屬性 → 裝備人偶(`EquipmentDoll`) → 計數・公會 → 狀態(conditions) → 偽裝 → 錢包 → 背景. Move markup only — do not change any section's internal content or `data-testid` values.

## 2. Tests and stories

- [ ] 2.1 Update `web/webclient-app/tests/data/character_status_drawer.test.js`: fix the hardcoded section-label order array (currently `:100-103`) to the new order; fix the trait-count assertion (currently `:105-115`, asserts DOM node count equals `CHARACTER_PANEL_SAMPLE.traits.length` = 8) to assert exactly the 4 filtered `atk_phys`/`agility`/`defense`/`magic_level` rows and never `hp`/`mp`/`sp`/`guild_merit`; assert the `magic_level` row's rendered text is `魔階` and the guild rank row's label is `公會階級`.
- [ ] 2.2 Re-run `npm run build-storybook` and visually confirm `Data/CharacterStatusDrawer`'s `Full`, `Undisguised`, and `Combat` stories render the new order (Combat: `character` unavailable — the reordered sections still degrade correctly per the existing "drawer is useful in combat" scenario).
- [ ] 2.3 Confirm `web/webclient-app/stories/fixtures.js`'s `CHARACTER_PANEL_SAMPLE`/`CHARACTER_PANEL_UNDISGUISED_SAMPLE` already include all eight trait keys (add any missing ones) so the showcase stories exercise the filter.
- [ ] 2.4 Add a case to `world/rules/tests/test_status_query.py` asserting `_STATIC_KEYS + _COUNTER_KEYS` minus `{"guild_merit"}` equals exactly `("atk_phys", "agility", "defense", "magic_level")` — a pinned contract test, not a cross-file check (see design.md's Decisions) — with a comment pointing at `CharacterStatusDrawer.vue`'s `ATTRIBUTE_KEYS` as the value that must be updated in lockstep if this test's expected tuple ever changes.

## 3. Verification

- [ ] 3.1 `npm test` (Vitest) green.
- [ ] 3.2 `npm run build-storybook` and `npm run showcase-coverage` green.
- [ ] 3.3 `uv run pytest world/rules/tests/test_status_query.py` (or the project's standard Python test invocation) green.
- [ ] 3.4 `openspec validate fix-webclient-character-status-drawer-order --strict` passes.
