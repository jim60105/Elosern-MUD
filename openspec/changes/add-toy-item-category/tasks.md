## 1. Presentation vocabulary

- [ ] 1.1 Add a Python-side cross-language test that extracts the `ITEM_ICONS` keys from `web/webclient-app/components/item-icons.js` with a narrow regex over the object literal and asserts the extracted set equals `{member.value for member in ItemIconKey}`. Make the extractor fail loud — an unparseable file or zero extracted keys is a failure, never an empty pass. Verify it passes against the current nine-member vocabulary before any member is added.
- [ ] 1.1a Verify the new test actually catches the failure it exists for: add `TOY` to `ItemIconKey` alone and confirm the Python test fails naming `toy`, then continue with 1.2. Note in the test docstring that `ICON_KEYS` in `item_icons.test.js` is a third hand-maintained mirror that must be updated alongside the map.
- [ ] 1.2 Add `TOY = "toy"` to `ItemKind` and `ItemIconKey` in `world/lore/items.py`, and verify `test_presentation_vocabularies_are_closed` fails until its expected sets are updated — confirming the closed-vocabulary assertion is live.
- [ ] 1.3 Update the expected vocabulary sets in `world/lore/tests/test_items.py` and verify the test passes.
- [ ] 1.4 Add a `toy` entry to `ITEM_ICONS` in `web/webclient-app/components/item-icons.js` with an inline 24×24 stroke path in the existing idiom and the label `情趣道具`, add `"toy"` to the `ICON_KEYS` array in `web/webclient-app/tests/world/item_icons.test.js`, and verify both the JavaScript alignment test and the Python cross-language test pass, and that `KIND_LABELS` derives the new label without a second edit.
- [ ] 1.5 Add a test asserting no registered item resolves to the unknown-item fallback through the client icon map, and verify it passes.

## 2. Price band

- [ ] 2.1 Add an `intimacy_tool` `PriceEntry` (`情趣器具`, 50–20000 copper) to `PRICE_TABLE` in `world/lore/economy.py`, and verify the currency tests still pass.
- [ ] 2.2 Extend the catalog contract test to assert every codex 性玩具 reference price — wearable and usable alike — falls inside the intimacy-device band, and verify it passes against all twelve codex rows even though only five land here.

## 3. Wearable devices

- [ ] 3.1 Add `EquipmentModifierKey` members and `ItemDefinition` entries for `nymph_buds_clamp`, `warm_honey_orb`, `hyperesthesia_charm` — `ItemKind.TOY`, `ItemIconKey.TOY`, `uncommon`, `EquipmentSlot.ACCESSORY`, `intimacy_tool` band, sellable. Verify the registry imports.
- [ ] 3.2 Add the three matching `equipment_effects.yaml` entries — clamp `pleasure_gain: "+8%", sp_cost: "+5%"`, orb `defense: -1, pleasure_gain: "+8%"`, charm `pleasure_gain: "+8%", sp_cost: "+5%"`. Verify the rulebook loads and the budget test confirms all values sit inside the `uncommon` ceilings of soft-percent 15 and percent 8.
- [ ] 3.3 Add `warmth_rune_egg` (`uncommon`, `pleasure_gain: "+8%"`) and `tremor_crystal` (`rare`, `pleasure_gain: "+10%"`) the same way, and verify the crystal loads inside the `rare` soft-percent ceiling of 20.
- [ ] 3.4 Add a test asserting no wearable intimacy entry declares an attached buff, immunity, or status key, and verify it passes — pinning that the retired 催情霧 status is not reintroduced.

## 4. Church doctrine

- [ ] 4.1 Update the `Doctrine coverage for the named Church set` test to check the vestment-and-emblem sub-set (`sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`, `pilgrim_medallion`) for non-negative bias and pleasure plus healing-or-immunity, and verify it passes unchanged against the shipped four.
- [ ] 4.2 Add sanctuary-device coverage for `nymph_buds_clamp`, `warm_honey_orb`, `hyperesthesia_charm` — non-negative bias, positive `pleasure_gain`, no suppression, no healing obligation — and verify it passes.
- [ ] 4.3 Add the negative case: a deviant copy that moves a vestment key into the sanctuary sub-set still fails, proving membership comes from the named list and not from the rulebook.
- [ ] 4.4 Verify `warmth_rune_egg` and `tremor_crystal` are excluded from both sub-sets, matching their Imperial and elven provenance.

## 5. Roster assertions

- [ ] 5.1 Update the exact key set in `world/lore/tests/test_items.py` to 99 keys and verify the metadata test passes.
- [ ] 5.2 Update the registry count in `world/rules/tests/test_guild_config.py` to 99 and verify its price-identity test passes.
- [ ] 5.3 Update any equipment-effect rulebook test pinning the bound key set, and verify the two-sided close reports no unbound key and no orphan.
- [ ] 5.4 Add a test asserting none of the five wearable intimacy keys appears in any shop's offered keys, and verify it passes.

## 6. Verification

- [ ] 6.1 Equip two wearable devices at once in a test and verify both pleasure adjustments reach the shared accessor and both occupy accessory slots against the five-slot cap.
- [ ] 6.2 Run the JavaScript test suite and verify the inventory panel renders a `toy` item with its own glyph and label rather than the unknown-item fallback.
- [ ] 6.3 Run the full Python test suite and verify no regression in equipment, inventory, presentation, or shop validation.
- [ ] 6.4 Run `openspec validate add-toy-item-category --strict` and verify it reports the change as valid.
