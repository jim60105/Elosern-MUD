## 1. Budget contract test

- [ ] 1.1 Hand-transcribe the codex's equipment adjustments into a literal test fixture of `(item_key, field, value, budget_column)` tuples covering all 45 shipped equipment items, taking each value from the codex row and each column from the field-to-column mapping in the codex's seventh layer. Do NOT parse the adjustment cells — the fixture is reviewed as data. Verify the fixture reproduces `equipment_effects.yaml` exactly for the 42 items where codex and rulebook agree.
- [ ] 1.2 Record the three known divergences (`sister_vestments`, `saintess_vestments`, `silver_feather_earring`) as an explicit allow-list in the fixture with a comment pointing at the codex's "rulebook is authoritative for tuned values" clause, and verify the test passes with exactly those three exempted and no others.
- [ ] 1.3 Add the assertion that every fixture value fits its budget column at the item's registered rarity, and verify it passes for all 45 shipped items.
- [ ] 1.4 Add a negative case: an over-budget synthetic tuple fails the assertion, proving the check is live.
- [ ] 1.5 Extend the fixture with the 12 new items' tuples as each group lands in section 2-4, and verify the fixture stays exhaustive — an item in the rulebook with no fixture tuple fails the test.

## 2. Beastfolk weapons

- [ ] 2.1 Add `EquipmentModifierKey` members and `ItemDefinition` entries for `beastfolk_warhammer`, `beastfolk_repeating_bow`, `beastfolk_war_spear` — `ItemKind.WEAPON`, `ItemIconKey.WEAPON`, `uncommon`, `EquipmentSlot.WEAPON_MAIN`, `mundane_weapon` band, sellable. Verify the registry imports.
- [ ] 2.2 Add the three matching `equipment_effects.yaml` entries — warhammer `atk_phys: 6, agility: "-6%"`, repeating bow `atk_phys: 3, agility: 4`, war spear `atk_phys: 5, defense: 2`. Verify the rulebook loads with no unbound key or orphan.
- [ ] 2.3 Add `beastfolk_twin_claws` and `beastfolk_spirit_wand` the same way — claws `atk_phys: 6, defense: -2`, wand `magic_power: 5, mp_cost: "-6%"` — and verify the budget test confirms both sit inside the `uncommon` ceilings of flat 6 and percent 8.

## 3. Elven and trophy weapons

- [ ] 3.1 Add `elven_longbow` — `rare`, `EquipmentSlot.WEAPON_MAIN`, `mundane_weapon` band — with `atk_phys: 6, agility: 3`, and verify it loads inside the `rare` flat ceiling of 8.
- [ ] 3.2 Add `dragon_lair_trophy_blade` — `epic`, `EquipmentSlot.WEAPON_MAIN`, `magic_weapon` band — with `atk_phys: 9, magic_power: 3`, and verify it loads inside the `epic` flat ceiling of 10.

## 4. Armor and accessories

- [ ] 4.1 Add `beastfolk_heavy_hide_armor` (`uncommon`, `EquipmentSlot.ARMOR`, `armor` band, `defense: 6, agility: "-8%"`) and `beastfolk_stalker_garb` (`uncommon`, `armor` band, `defense: 2, agility: "+6%"`). Verify both load and the budget test passes.
- [ ] 4.2 Add `elven_forest_veil` — `legendary`, `EquipmentSlot.ARMOR`, `armor` band — with `adjustments: {defense: 4, pleasure_gain: "+15%"}` and top-level `exposure_bias: 1`. Verify the bias is authored as a sibling of `adjustments`, not inside it, and that the load accepts it.
- [ ] 4.3 Add `beastfolk_tribal_totem` (`uncommon`, `EquipmentSlot.ACCESSORY`, `jewelry` band, `atk_phys: 2, defense: 2`) and `beastfolk_gale_earring` (`uncommon`, `jewelry` band, `agility: "+4%"`). Verify the earring's percent-typed `agility` is checked against the `percent` column, not `flat`.

## 5. Roster assertions

- [ ] 5.1 Update the exact key set in `world/lore/tests/test_items.py` to 94 keys and verify the metadata test passes.
- [ ] 5.2 Update the registry count in `world/rules/tests/test_guild_config.py` to 94 and verify its price-identity test passes.
- [ ] 5.3 Update any equipment-effect rulebook test that pins the bound key set, and verify the two-sided close still reports no unbound key and no orphan.
- [ ] 5.4 Add a test asserting none of the twelve regional keys appears in any shop's offered keys, and verify it passes.

## 6. Verification

- [ ] 6.1 Equip one item per slot from the new roster in a test — a main-hand weapon, the armor, and an accessory — and verify the adjustments reach the shared accessor with the expected values.
- [ ] 6.2 Run the full test suite and verify no regression in equipment toggle, inventory, presentation, or shop validation.
- [ ] 6.3 Run `openspec validate land-lore-regional-equipment --strict` and verify it reports the change as valid.
