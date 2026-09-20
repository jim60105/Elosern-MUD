Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. The band

- [ ] 1.1 Add the `masterwork_gear` entry to `PRICE_TABLE` in `world/lore/economy.py` with floor
  100, ceiling 500,000 and a note stating that price follows scarcity rather than materials.
  Verify the ceiling is strictly below the `relic` floor with a behavior test over
  `PRICE_TABLE` bounds rather than a recital of the row's values.
- [ ] 1.2 Do NOT add the keepsake-offer rejection here. `commerce-assortment-registry` rewrites
  `validate_shop_configs` wholesale, so an enforcement edit in this change would have to be
  re-applied over that restructuring. The rule is stated in this change's spec and enforced there;
  keep this change free of `world/rules/guild_config.py` so the two share no file.

## 2. Authored item rows

- [ ] 2.1 Move `dark_elf_kimono`, `shadow_blade`, `shadow_blade_echo`, `dark_elf_ninja_garb`,
  `crescent_earring` and `elven_traditional_robe` in `world/lore/items/data_named_equipment.py`
  to `masterwork_gear` with `sellable=True`, leaving rarity untouched. All six live in this file
  — `elven_traditional_robe` is at line 71. Verify the registry still imports and its own
  load-time checks stay green.
- [ ] 2.2 In `world/lore/items/data_regional_equipment.py`, move `elven_forest_veil` from `armor`
  to `masterwork_gear` and raise `elven_longbow` to `EPIC`.
- [ ] 2.3 Raise `prism_charm` to `RARE` in `world/lore/items/data_armor_accessories_materials.py`
  and `elven_candied_blossom` to `RARE` in `world/lore/items/data_inspect_only_codex.py`.
- [ ] 2.4 Confirm the nine remaining `relic` rows are untouched, and verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_items`.

## 3. Handoff

- [ ] 3.1 Run `uv run --locked python -m tools.test_data_lint check` and confirm no new tagged
  data-contract test was introduced by this change.
- [ ] 3.2 Run `openspec validate masterwork-gear-price-band --strict` and the focused labels above.
