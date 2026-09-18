## 1. Magnitude derivation

- [x] 1.1 Derive the three magnitudes by reading the `stimulus_applied` pleasure delta band from `world/rules/rulebook/sexual.yaml` — its floor, midpoint, and ceiling — and record the resulting values in this change's notes. Do not hard-code `8`, `11`, `14` anywhere outside the authored profiles.
- [x] 1.2 Add a behavior test that a synthetic usable item declaring a positive pleasure adjustment settles through the shared intimacy writer with no status key in the profile, and that the reported amount is the gauge delta actually applied rather than the declared amount. Annotate with `covers_requirement` for the shared-writer requirement. Verify with `world.rules.tests.test_item_use`.

## 2. Consuming devices

- [ ] 2.1 Register `aphrodisiac_bath_salts`, `slime_lube_gel`, `hot_kiss_potion` — `ItemKind.TOY`, `ItemIconKey.TOY`, `uncommon`, `intimacy_tool` band, sellable, `ItemUseMechanics(consumable=True, combat_allowed=False)`. Verify the registry imports and the item-effect loader fails, naming the three missing profiles — confirming the two-sided close is live.
- [ ] 2.2 Add their three `item_effects.yaml` profiles, each `stat: pleasure` with the gentle amount and no explicit scope. Verify the loader now closes cleanly.
- [ ] 2.3 Register `spark_candy` (`uncommon`, consuming) with the moderate amount, and verify the loader closes.

## 3. Reusable devices

- [ ] 3.1 Register `embracing_vine` (`rare`, `consumable=False`) with the moderate amount, and verify the loader closes.
- [ ] 3.2 Register `kiss_of_goddess_mist` and `censer_of_desire` (`rare`, `consumable=False`) with the intense amount, and verify the loader closes with all seven profiles bound.
- [ ] 3.3 Add a behavior test that a synthetic usable item declaring no combat use is refused at combat submission, naming the combat restriction, with no gauge movement and the item still in inventory. Annotate for the combat-bar requirement. Verify with `world.rules.tests.test_item_combat_turn`.
- [ ] 3.4 Add a behavior test for the non-consuming shape on a synthetic item: a successful out-of-combat use settles, leaves the inventory count unchanged, and advances the clock by the standard item-use duration; a consuming item removes exactly one copy. Annotate for the non-consuming requirement. Verify with `world.rules.tests.test_item_use`.
- [ ] 3.5 Add the rollback case: force a failure partway through a synthetic non-consuming use and assert every touched gauge, status, and intimate surface is restored with the inventory count unchanged. Verify with `world.rules.tests.test_item_use`.
- [ ] 3.6 Add all four tests to existing test modules so `.github/evennia-shards.json` needs no edit, confirm the annotation IDs against `uv run --locked python -m tools.spec_traceability list`, and verify with `uv run --locked python -m tools.spec_traceability check`.

## 4. Existing roster assertions

- [ ] 4.1 Move the exact key set in the existing registered data-contract test `world/lore/tests/test_items.py` to the new roster. Literal update only. Verify with `world.lore.tests.test_items`.
- [ ] 4.2 Move the literal registry count in `world/rules/tests/test_guild_config.py` to match. Verify with `world.rules.tests.test_guild_config`.
- [ ] 4.3 Move any existing literal pinning the shipped usable-item set, including in `world/rules/tests/test_shipped_item_use_regression.py`, and verify the bi-directional close still reports no missing profile and no orphan with `world.rules.tests.test_item_effects_rulebook`.
- [ ] 4.4 Run `uv run --locked python -m tools.test_data_lint check` and verify the gate passes with no new ledger entry.

## 5. Unmaterialised-state check

- [ ] 5.1 Use a synthetic pleasure-raising item on an entity whose intimacy state has never been materialised, and verify the preflight's fail-closed read does not reject it and the gauge rises through the shared writer. Verify with `world.rules.tests.test_item_use`.
- [ ] 5.2 Use a synthetic pleasure-raising item on an entity whose gauge is already at its ceiling, and verify the use is rejected with the full-gauge reason and the item is not consumed. Verify with `world.rules.tests.test_item_use`.

## 6. Gate

- [ ] 6.1 Run the focused labels touched by this change — `world.lore.tests.test_items`, `world.rules.tests.test_item_use`, `world.rules.tests.test_item_effects_rulebook`, `world.rules.tests.test_item_combat_turn`, `world.rules.tests.test_shipped_item_use_regression`, `world.rules.tests.test_guild_config` — plus `uv run --locked python -m tools.spec_traceability check`. Do not run the full suite.
- [ ] 6.2 Run `openspec validate land-usable-intimacy-items --strict` and verify it reports the change as valid.
