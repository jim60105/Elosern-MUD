# Tasks

Read `design.md` first. Every table and YAML block named below is in it.

Rules that hold for every task:

- Add no test and no assertion that names an item, value or count from this change.
- Rename, move or reorder no existing item row, enum member or rulebook entry.
- Do not edit `world/lore/economy.py`, any assortment, any commerce slice, or any file under `openspec/specs/`.
- Run every Evennia test command alone, exactly as written, with nothing before or after it.

## 1. Baseline

- [ ] 1.1 Run `git status`, then `uv run --locked python -c "from world.lore.items import ITEM_REGISTRY; print(len(ITEM_REGISTRY), list(ITEM_REGISTRY)[-1])"`. Verify by noting the count and last key in the working notes; the last key is expected to be `guild_limit_b`.

## 2. Item rows

- [ ] 2.1 Add the four members of design Decision 3 to `EquipmentModifierKey` in `world/lore/items/vocab.py`. Verify with `uv run --locked python -c "from world.lore.items.vocab import EquipmentModifierKey as K; print(K.EOLAS_PROVING_WAND.value, K.FIONNEN_LEAFWEAVE_GARB.value)"` printing `eolas_proving_wand fionnen_leafweave_garb`.
- [ ] 2.2 Create `world/lore/items/data_elven_village_goods.py` with the eight rows of design Decision 1 in table order, and register the slice last in `world/lore/items/assembly.py` as in Decision 2. Write each `summary_zh` from its "Summary covers" cell. Verification runs in 3.3, because the rulebook loaders reject the registry until the matching entries exist.

## 3. Rulebooks

- [ ] 3.1 Add the four entries of design Decision 4 to `effects:` in `world/rules/rulebook/equipment_effects.yaml`, verbatim.
- [ ] 3.2 Add the two entries of design Decision 5 to `items:` in `world/rules/rulebook/item_effects.yaml`, verbatim.
- [ ] 3.3 Verify with `uv run --locked python -c "from world.lore.items import ITEM_REGISTRY as R; print(len(R), list(R)[-8:])"`: the count is the baseline plus 8 and the last eight keys are the eight keys of Decision 1 in table order.

## 4. Focused tests

- [ ] 4.1 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_items world.rules.tests.test_item_use world.rules.tests.test_equipment_toggle world.rules.tests.test_equipment_effect_rulebook world.rules.tests.test_shop_economy`. Verify it ends with `OK`. If the test guard refuses the command for discovering more than 100 tests, run the labels as separate commands.
- [ ] 4.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb commands.tests.test_items`. Verify it ends with `OK`.
- [ ] 4.3 If a test in 4.1, 4.2 or 6.1 fails: when the failing assertion compares against a literal roster, count, last key or value of shipped items, rewrite that assertion to the logic it stands for and append no new key; rerun the command. For any other failure, run the same label on `master`; if `master` passes, stop and report the failure with its output. Verify by recording in the working notes either "no failure" or each rewritten assertion with its file and method name.

## 5. Documents

- [ ] 5.1 Add the eight rows to `docs/lore/items.md` as in design Decision 6. Verify with `grep -c "eolas_kiln_flatbread\|eolas_herb_tonic\|eolas_glass_pendant\|eolas_proving_wand\|fionnen_wildflower_honey\|fionnen_beeswax_salve\|fionnen_archer_bracer\|fionnen_leafweave_garb" docs/lore/items.md` printing `8`.
- [ ] 5.2 Create `docs/lore/elven-village-goods-review.md` as in design Decision 7. Verify the file has one line for each of the eight keys.
- [ ] 5.3 Run `sh /home/jim60105/.agents/skills/chinese-content-writing-guideline/scripts/lint.sh world/lore/items/data_elven_village_goods.py`. Verify it reports 0 errors in the `summary_zh` and `display_name_zh` strings; findings on Python code are not errors of this task.

## 6. Integration

- [ ] 6.0 Run `uv run --locked python -m tools.map_reference_context`, then `uv run --locked python -m tools.map_reference_context --check`. Verify the check prints `is up to date`. Do this after the last edit under `world/lore/` or `world/rules/`; repeat it if either changes again.
- [ ] 6.1 Run `uv run --locked python -m tools.contract_gate`. Verify it ends with `contract gate passed`.
- [ ] 6.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.spec_traceability check`. Verify both exit 0.
- [ ] 6.3 Run `openspec validate elven-village-local-goods --strict`. Verify it reports the change valid.

## Workflow follow-up

- A person reads `docs/lore/elven-village-goods-review.md` and the eight names and summaries before the change is archived.
