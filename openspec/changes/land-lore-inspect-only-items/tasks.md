## 1. Price band

- [x] 1.1 Add a `specialty_food` `PriceEntry` (`特產食品`, 10–100 copper) to `PRICE_TABLE` in `world/lore/economy.py`. Verify with the focused label `world.lore.tests.test_economy`.
- [x] 1.2 Add a behavior test covering the absent-band refusal: build a synthetic item definition naming an undefined price-table key, run it through shop-catalog validation, and assert the load raises naming that item rather than accepting an unbounded price. Verify with `world.rules.tests.test_guild_config`.

## 2. Inspect-only registry entries

- [ ] 2.1 Register the 6 foods — `kingdom_rye_hardtack` / `adventurer_field_ration` on the `meal` band, and `imperial_candied_fruit` / `beastfolk_smoked_jerky` / `harbor_lobster_bisque` / `elven_candied_blossom` on `specialty_food` — each `ItemKind.FOOD` + `ItemIconKey.FOOD`, sellable, with the codex summary. Verify the registry imports, which runs `ItemPresentation` validation on every summary.
- [ ] 2.2 Register the 5 non-mechanical remedies — `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught` on `potion`; `spirit_dew`, `elven_tear` on `material` — each `ItemKind.POTION` + `ItemIconKey.POTION`, sellable, declaring neither `use_mechanics` nor `equipment_slot`. Verify the registry imports.
- [ ] 2.3 Register the 4 tools — `enchanted_compass`, `dungeon_flare_talisman`, `beastfolk_signal_conch`, `camp_ward_kit` — on the `tool` band as `ItemKind.TOOL` + `ItemIconKey.TOOL`, sellable. Verify the registry imports.
- [ ] 2.4 Register the 6 materials — `goblin_ear`, `slime_residue`, `earth_drake_scale`, `troll_fang`, `elven_essence`, `ancient_dragon_heart` — on the `material` band as `ItemKind.MATERIAL` + `ItemIconKey.MATERIAL`, sellable. Verify the registry imports.
- [ ] 2.5 Register the 3 curios — `family_crest_token`, `ancient_mystery_key`, `elven_child_toy` — as `ItemKind.MISC` + `ItemIconKey.MISC`, non-sellable on the `relic` band. Verify the registry imports.

## 3. Shape-derived behavior

- [ ] 3.1 Using a synthetic item that declares no mechanics, assert using it is refused with the not-usable reason with no gauge movement and no inventory change, and that equipping it is refused with the not-equipment reason with equipment state unchanged. Annotate with `covers_requirement` for the inert-item requirement. Verify with `world.rules.tests.test_item_use`.
- [ ] 3.2 Using a synthetic non-sellable item, assert selling it to a merchant is refused with wallet and inventory unchanged, and that the refusal still holds when a synthetic shop lists that key. Annotate for the non-sellable requirement. Verify with `world.rules.tests.test_guild_config` or the focused shop-command label, whichever owns merchant transactions.
- [ ] 3.3 Using a synthetic registered item that no synthetic shop offers, assert it can be granted into inventory and then inspected, equipped, or used per its shape, that buying it is refused for not being offered — distinct from the unknown-key refusal — and that catalog validation accepts the state. Annotate for the registration-does-not-entitle requirement. Verify with the same focused labels.
- [ ] 3.4 Add the three tests to existing test modules rather than creating new ones, so `.github/evennia-shards.json` needs no edit. If a new module proves unavoidable, register it in exactly one shard in this change and verify with `tests.test_evennia_test_optimization_contract`.
- [ ] 3.5 Obtain the canonical requirement IDs with `uv run --locked python -m tools.spec_traceability list` and confirm each annotation uses a literal ID. Verify with `uv run --locked python -m tools.spec_traceability check`.

## 4. Existing roster assertions

- [ ] 4.1 Move the exact key set in the existing registered data-contract test `world/lore/tests/test_items.py` to the new roster. Do not add assertions — this is a literal update to a test that already exists. Verify with `world.lore.tests.test_items`.
- [ ] 4.2 Move the literal registry count in `world/rules/tests/test_guild_config.py` to match. Verify with `world.rules.tests.test_guild_config`.
- [ ] 4.3 Run `uv run --locked python -m tools.test_data_lint check` and verify the gate still passes with no new ledger entry required.

## 5. Shop stock

- [ ] 5.1 Add the 18 stocked keys to `altoria_general_store.offered_item_keys` in `world/lore/shops.py` — the 6 foods, the 3 `potion`-band remedies plus `spirit_dew`, the 4 tools, and the 4 materials other than `elven_essence` and `ancient_dragon_heart`. Verify `world/lore/shops.py` imports, since its validators run at import.
- [ ] 5.2 Add the 18 matching offers to `shops.altoria_general_store.offers` in `world/rules/rulebook/guild_economy.yaml` using the codex reference prices, with stock depth deep for `common` and single-unit for `rare` and above. Verify with `world.rules.tests.test_guild_config`.
- [ ] 5.3 Verify the two-sided join rejects a one-sided edit: temporarily remove one offer from the YAML, confirm loading raises naming the missing key, then restore it.

## 6. Documentation and gate

- [ ] 6.1 Add one line to the 雜物 section of `docs/lore/items.md` recording that the category lands as non-sellable on the `relic` band, mirroring 公會見習徽記.
- [ ] 6.2 Run the focused labels touched by this change — `world.lore.tests.test_items`, `world.lore.tests.test_economy`, `world.rules.tests.test_guild_config`, `world.rules.tests.test_item_use` — plus the registry-iterating validators in `world.lore.tests.test_starting_kits` and `world.quests`. Do not run the full suite.
- [ ] 6.3 Run `openspec validate land-lore-inspect-only-items --strict` and verify it reports the change as valid.
