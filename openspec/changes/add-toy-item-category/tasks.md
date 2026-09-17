## 1. Presentation vocabulary

- [x] 1.1 Add a Python-side cross-language test that extracts the `ITEM_ICONS` keys from `web/webclient-app/components/item-icons.js` with a narrow regex over the object literal and asserts the extracted set equals `{member.value for member in ItemIconKey}`. Make the extractor fail loud — an unparseable file or zero extracted keys is a failure, never an empty pass. Verify it passes against the current nine-member vocabulary before any member is added.
- [x] 1.1a Verify the new test actually catches the failure it exists for: add `TOY` to `ItemIconKey` alone and confirm the Python test fails naming `toy`, then continue with 1.2. Note in the test docstring that `ICON_KEYS` in `item_icons.test.js` is a third hand-maintained mirror that must be updated alongside the map.
- [x] 1.2 Add `TOY = "toy"` to `ItemKind` and `ItemIconKey` in `world/lore/items.py`, and verify `test_presentation_vocabularies_are_closed` fails until its expected sets are updated — confirming the closed-vocabulary assertion is live.
- [x] 1.3 Update the expected vocabulary sets in `world/lore/tests/test_items.py` and verify the test passes.
- [x] 1.4 Add a `toy` entry to `ITEM_ICONS` in `web/webclient-app/components/item-icons.js` with an inline 24×24 stroke path in the existing idiom and the label `情趣道具`, add `"toy"` to the `ICON_KEYS` array in `web/webclient-app/tests/world/item_icons.test.js`, and verify both the JavaScript alignment test and the Python cross-language test pass, and that `KIND_LABELS` derives the new label without a second edit.
- [x] 1.5 Add a Vitest case rendering one payload with a mapped icon key and one with an absent presentation, asserting the first shows that key's own glyph and label and only the second shows the fallback. Verify with the focused Vitest file for the inventory panel.

## 2. Price band

- [x] 2.1 Add an `intimacy_tool` `PriceEntry` (`情趣器具`, 50–20000 copper) to `PRICE_TABLE` in `world/lore/economy.py`, and verify the currency tests still pass.
- [x] 2.2 Add a behavior test that a synthetic usable item and a synthetic equipment item naming the same band both resolve the same `PriceEntry`, covering the one-band-two-shapes requirement. Verify with `world.rules.tests.test_guild_config`.

## 3. Wearable devices

- [x] 3.1 Add `EquipmentModifierKey` members and `ItemDefinition` entries for `nymph_buds_clamp`, `warm_honey_orb`, `hyperesthesia_charm` — `ItemKind.TOY`, `ItemIconKey.TOY`, `uncommon`, `EquipmentSlot.ACCESSORY`, `intimacy_tool` band, sellable. Verify the registry imports.
- [x] 3.2 Add the three matching `equipment_effects.yaml` entries — clamp `pleasure_gain: "+8%", sp_cost: "+5%"`, orb `defense: -1, pleasure_gain: "+8%"`, charm `pleasure_gain: "+8%", sp_cost: "+5%"`. Verify the rulebook loads and the budget test confirms all values sit inside the `uncommon` ceilings of soft-percent 15 and percent 8.
- [x] 3.3 Add `warmth_rune_egg` (`uncommon`, `pleasure_gain: "+8%"`) and `tremor_crystal` (`rare`, `pleasure_gain: "+10%"`) the same way, and verify the crystal loads inside the `rare` soft-percent ceiling of 20.
- [x] 3.4 Confirm by review that none of the five entries declares an attached buff, immunity, or status key, so the retired 催情霧 status is not reintroduced. No test: a rulebook entry's own fields are registry content, and the loader already rejects an attached buff naming an undefined status.

## 4. Church doctrine

- [x] 4.1 Update the `Doctrine coverage for the named Church set` test to check the vestment-and-emblem sub-set (`sister_vestments`, `radiant_holy_emblem`, `saintess_vestments`, `pilgrim_medallion`) for non-negative bias and pleasure plus healing-or-immunity, and verify it passes unchanged against the shipped four.
- [x] 4.2 Add sanctuary-device coverage for `nymph_buds_clamp`, `warm_honey_orb`, `hyperesthesia_charm` — non-negative bias, positive `pleasure_gain`, no suppression, no healing obligation — and verify it passes.
- [x] 4.3 Add the negative case: a deviant copy that moves a vestment key into the sanctuary sub-set still fails, proving membership comes from the named list and not from the rulebook.
- [x] 4.4 Verify `warmth_rune_egg` and `tremor_crystal` are excluded from both sub-sets, matching their Imperial and elven provenance.

## 5. Existing roster assertions

- [x] 5.1 Move the exact key set in the existing registered data-contract test `world/lore/tests/test_items.py` to the new roster, alongside the vocabulary literals from 1.3. Verify with `world.lore.tests.test_items`.
- [x] 5.2 Move the literal registry count in `world/rules/tests/test_guild_config.py` to match. Verify with `world.rules.tests.test_guild_config`.
- [x] 5.3 Move any literal bound-key set in the equipment-effect rulebook tests, and verify the two-sided close reports no unbound key and no orphan with `world.rules.tests.test_equipment_effect_rulebook`.
- [x] 5.4 Run `uv run --locked python -m tools.test_data_lint check` and verify the gate passes with no new ledger entry.

## 6. Verification

- [ ] 6.1 Using two synthetic accessory-slot items carrying pleasure adjustments, assert both equip at once and both adjustments reach the shared accessor against the five-slot cap. Verify with `world.skills.tests.test_equipment`.
- [ ] 6.2 Run the focused Vitest file for `item-icons.js` and the inventory panel — not the whole Vitest suite — and verify both the alignment case and the fallback case pass.
- [ ] 6.3 Run the focused Python labels touched by this change — `world.lore.tests.test_items`, `world.lore.tests.test_economy`, `world.rules.tests.test_equipment_effect_rulebook`, `world.rules.tests.test_guild_config`, `world.skills.tests.test_equipment` — plus `uv run --locked python -m tools.spec_traceability check`. Do not run the full suite.
- [ ] 6.4 Run `openspec validate add-toy-item-category --strict` and verify it reports the change as valid.
