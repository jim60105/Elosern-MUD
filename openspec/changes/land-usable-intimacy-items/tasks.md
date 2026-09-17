## 1. Magnitude derivation

- [ ] 1.1 Add a test asserting the three intimacy magnitudes are the floor, midpoint, and ceiling of the `stimulus_applied` pleasure delta band declared in `world/rules/rulebook/sexual.yaml`, reading the band from the rulebook rather than hard-coding `8`, `11`, and `14`. Verify it passes.
- [ ] 1.2 Extend the catalog contract test to assert each codex device's stated tier (溫和／中等／強烈) matches the magnitude its profile declares, and verify it fails when a tier and an amount are deliberately mismatched.

## 2. Consuming devices

- [ ] 2.1 Register `aphrodisiac_bath_salts`, `slime_lube_gel`, `hot_kiss_potion` — `ItemKind.TOY`, `ItemIconKey.TOY`, `uncommon`, `intimacy_tool` band, sellable, `ItemUseMechanics(consumable=True, combat_allowed=False)`. Verify the registry imports and the item-effect loader fails, naming the three missing profiles — confirming the two-sided close is live.
- [ ] 2.2 Add their three `item_effects.yaml` profiles, each `stat: pleasure` with the gentle amount and no explicit scope. Verify the loader now closes cleanly.
- [ ] 2.3 Register `spark_candy` (`uncommon`, consuming) with the moderate amount, and verify the loader closes.

## 3. Reusable devices

- [ ] 3.1 Register `embracing_vine` (`rare`, `consumable=False`) with the moderate amount, and verify the loader closes.
- [ ] 3.2 Register `kiss_of_goddess_mist` and `censer_of_desire` (`rare`, `consumable=False`) with the intense amount, and verify the loader closes with all seven profiles bound.
- [ ] 3.3 Add a test asserting every usable intimacy item declares `combat_allowed=False`, and verify it passes.

## 4. Roster assertions

- [ ] 4.1 Update the exact key set in `world/lore/tests/test_items.py` to 106 keys and verify the metadata test passes.
- [ ] 4.2 Update the registry count in `world/rules/tests/test_guild_config.py` to 106 and verify its price-identity test passes.
- [ ] 4.3 Update any test pinning the shipped usable-item set — including the shipped item-use regression suite — and verify the bi-directional close assertion covers all eleven usable items.
- [ ] 4.4 Add a test asserting none of the seven usable intimacy keys appears in any shop's offered keys, and verify it passes.

## 5. Behaviour verification

- [ ] 5.1 Use a consuming device on an entity whose intimacy state has never been materialised, and verify the pleasure gauge rises by the declared amount, the arousal-coupled state follows, and exactly one copy is removed.
- [ ] 5.2 Use a reusable device out of combat and verify the effect settles, the inventory count is unchanged, and the world clock advances by the standard item-use duration.
- [ ] 5.3 Use a device on an entity whose pleasure gauge is at 100 and verify the use is rejected with the full-gauge reason and the item is not consumed.
- [ ] 5.4 Submit a usable intimacy device as a combat action and verify it is rejected for the combat restriction with no gauge movement.
- [ ] 5.5 Force a rollback partway through a reusable device's settlement and verify the intimacy surface is restored and the inventory count is still unchanged.

## 6. Gate

- [ ] 6.1 Run the full test suite and verify no regression in item use, combat submission, intimacy state, inventory, or shop validation.
- [ ] 6.2 Run `openspec validate land-usable-intimacy-items --strict` and verify it reports the change as valid.
