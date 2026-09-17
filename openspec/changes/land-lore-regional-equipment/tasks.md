## 1. Unstocked-equipment behavior

- [ ] 1.1 Using a synthetic equipment item that no synthetic shop offers, assert the rulebook loads with no unbound key and no orphan, that no validator reports a missing offer, and that granting and equipping it applies its adjustments through the shared accessor. Annotate with `covers_requirement` for the registration-and-tradeability requirement. Verify with `world.rules.tests.test_equipment_effect_rulebook` and `world.skills.tests.test_equipment`.
- [ ] 1.2 Add a negative case proving the budget gate is live: a synthetic rulebook entry whose value exceeds its rarity's ceiling must fail the load naming the field and the ceiling. Verify with `world.rules.tests.test_equipment_effect_rulebook`.
- [ ] 1.3 Add both tests to existing test modules so `.github/evennia-shards.json` needs no edit, and confirm the annotation IDs against `uv run --locked python -m tools.spec_traceability list`. Verify with `uv run --locked python -m tools.spec_traceability check`.

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

## 5. Existing roster assertions

- [ ] 5.1 Move the exact key set in the existing registered data-contract test `world/lore/tests/test_items.py` to the new roster. Literal update only, no added assertions. Verify with `world.lore.tests.test_items`.
- [ ] 5.2 Move the literal registry count in `world/rules/tests/test_guild_config.py` to match. Verify with `world.rules.tests.test_guild_config`.
- [ ] 5.3 Move any literal bound-key set in the equipment-effect rulebook tests, and verify the two-sided close reports no unbound key and no orphan with `world.rules.tests.test_equipment_effect_rulebook`.
- [ ] 5.4 Run `uv run --locked python -m tools.test_data_lint check` and verify the gate passes with no new ledger entry.

## 6. Verification

- [ ] 6.1 Run the focused labels touched by this change — `world.lore.tests.test_items`, `world.rules.tests.test_equipment_effect_rulebook`, `world.rules.tests.test_guild_config`, `world.skills.tests.test_equipment`, `world.rules.tests.test_equipment_toggle`. Do not run the full suite.
- [ ] 6.2 Run `openspec validate land-lore-regional-equipment --strict` and verify it reports the change as valid.
