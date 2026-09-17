## 1. Price band

- [ ] 1.1 Add a `specialty_food` `PriceEntry` (`特產食品`, 10–100 copper) to `PRICE_TABLE` in `world/lore/economy.py`, and verify `world/lore/tests/` currency tests still pass with `max_copper >= min_copper` and integer bounds.
- [ ] 1.2 Add a `lore-registries` test asserting every `ItemDefinition.price_table_key` in `ITEM_REGISTRY` resolves to a `PriceEntry`, and verify it passes against the current roster before any item is added.

## 2. Catalog contract test

- [ ] 2.1 Add a codex parser helper to the lore test package that reads `docs/lore/items.md` and yields, per item row, the key, display name, and the section it sits in — accepting only table rows whose first cell contains exactly one backticked key. Verify it returns exactly 106 keys (58 shipped + 48 catalogued) against the current document.
- [ ] 2.2 Add the catalog contract test asserting every `ITEM_REGISTRY` key is catalogued by the codex and that display names agree. Verify it passes against the current 58-item roster.
- [ ] 2.3 Extend the contract test with a negative case: a synthetic registry entry whose key the codex does not list fails the assertion.

## 3. Inspect-only registry entries

- [ ] 3.1 Register the 6 foods — `kingdom_rye_hardtack` / `adventurer_field_ration` on the `meal` band, and `imperial_candied_fruit` / `beastfolk_smoked_jerky` / `harbor_lobster_bisque` / `elven_candied_blossom` on `specialty_food` — each `ItemKind.FOOD` + `ItemIconKey.FOOD`, sellable, with the codex summary. Verify the catalog contract test covers all six.
- [ ] 3.2 Register the 5 non-mechanical remedies — `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught` on `potion`; `spirit_dew`, `elven_tear` on `material` — each `ItemKind.POTION` + `ItemIconKey.POTION`, sellable, and each declaring neither `use_mechanics` nor `equipment_slot`. Verify the contract test covers all five.
- [ ] 3.3 Register the 4 tools — `enchanted_compass`, `dungeon_flare_talisman`, `beastfolk_signal_conch`, `camp_ward_kit` — on the `tool` band as `ItemKind.TOOL` + `ItemIconKey.TOOL`, sellable. Verify the contract test covers all four.
- [ ] 3.4 Register the 6 materials — `goblin_ear`, `slime_residue`, `earth_drake_scale`, `troll_fang`, `elven_essence`, `ancient_dragon_heart` — on the `material` band as `ItemKind.MATERIAL` + `ItemIconKey.MATERIAL`, sellable. Verify the contract test covers all six.
- [ ] 3.5 Register the 3 curios — `family_crest_token`, `ancient_mystery_key`, `elven_child_toy` — as `ItemKind.MISC` + `ItemIconKey.MISC`, `sellable=False` on the `relic` band. Verify a test asserts all three are non-sellable and carry the keepsake band.
- [ ] 3.6 Verify every new summary passes `ItemPresentation` validation unchanged (non-empty, ≤128 code points, single line, no markup, no URL form, no emoji) by constructing the registry at import time — a violation raises before any test runs.

## 4. Roster assertions

- [ ] 4.1 Update the exact key set in `world/lore/tests/test_items.py` to the 82-key roster and verify `test_every_registered_item_resolves_complete_metadata` passes.
- [ ] 4.2 Update `len(ITEM_REGISTRY) == 58` to `82` in `world/rules/tests/test_guild_config.py` and verify `test_initial_items_have_lore_price_identity_without_numbers` passes.
- [ ] 4.3 Add a test asserting no inspect-only catalogue item declares `use_mechanics`, `equipment_slot`, or `modifier_key`, and verify it passes.

## 5. Shop stock

- [ ] 5.1 Add the 18 stocked keys to `altoria_general_store.offered_item_keys` in `world/lore/shops.py` — the 6 foods, the 3 `potion`-band remedies plus `spirit_dew`, the 4 tools, and the 4 materials other than `elven_essence` and `ancient_dragon_heart`. Verify `world/lore/shops.py` still imports (its module-level validators run at import).
- [ ] 5.2 Add the 18 matching offers to `shops.altoria_general_store.offers` in `world/rules/rulebook/guild_economy.yaml` using the codex reference prices, with `max_stock`/`restock_quantity` deep for `common` and 1/1 for `rare` and above. Verify `validate_shop_configs` accepts the rulebook.
- [ ] 5.3 Add a test asserting `elven_tear`, `elven_essence`, and `ancient_dragon_heart` are registered but absent from every shop's offered keys, and verify it passes.
- [ ] 5.4 Verify the two-sided join rejects a one-sided edit: temporarily remove one offer from the YAML and confirm loading raises naming the missing key, then restore it.

## 6. Documentation and gate

- [ ] 6.1 Add one line to the 雜物 section of `docs/lore/items.md` recording that the category lands as `sellable = false` on the `relic` band, mirroring 公會見習徽記, and verify the catalog contract test still parses the section.
- [ ] 6.2 Run the full test suite and verify no existing consumer of `ITEM_REGISTRY` regressed — in particular the quest, starting-kit, preset, scenario-director, and gallery-prompt validators that iterate the registry.
- [ ] 6.3 Run `openspec validate land-lore-inspect-only-items --strict` and verify it reports the change as valid.
