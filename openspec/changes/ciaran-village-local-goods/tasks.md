# Tasks

Read `design.md` first. Every table and YAML block named below is in it.

Rules that hold for every task:

- IDs are permanent. Rename no assortment key, item key, topic ID or scene ID. Delete no item row.
- Do not edit place rows, the capital's commerce slice, or any file under `openspec/specs/`.
- Add no test and no assertion that names an item, price or line from this change.
- Use the keys, names, prices and stock figures of `design.md` exactly.
- Before writing any card, room prose or dialogue, read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (by this absolute path; it is not in a worktree), `.agents/skills/npc-dialogue-content/SKILL.md` with its `references/scene-schema.md`, and the `chinese-content-writing-guideline` and `writing-style-guideline` skills.
- Run every Evennia test command alone, exactly as written, with nothing before or after it. If the test guard refuses a command for discovering more than 100 tests, run its labels as separate commands.

## 1. Baseline

- [ ] 1.1 Run `git status`. Confirm the dependencies are applied: `uv run --locked python -c "from world.lore.settlements.assortments import ASSORTMENT_REGISTRY as A; print('eolas_silkwork' in A, 'fionnen_attire' in A, 'fionnen_fare' in A)"` prints `True True True`, and `ls world/lore/items/data_elven_village_goods.py` lists the file.
- [ ] 1.2 Confirm the item keys are free: `grep -rn "ciaran_nightbloom_preserve\|ciaran_ember_mushroom_skewer\|ciaran_indigo_dye\|ciaran_crystal_sand\|ciaran_antivenom_tincture" world content docs` prints nothing.

## 2. Items

- [ ] 2.1 Append the five rows of design Decision 1 to `ROWS` in `world/lore/items/data_elven_village_goods.py`.
- [ ] 2.2 Add the entry of design Decision 2 to `items:` in `world/rules/rulebook/item_effects.yaml`, verbatim.
- [ ] 2.3 Verify with `uv run --locked python -c "from world.lore.items import ITEM_REGISTRY as R; print(list(R)[-5:])"` printing the five keys of Decision 1 in table order.

## 3. Shelves and prices

- [ ] 3.1 Change the four `item_keys` tuples in `world/lore/settlements/assortments.py` as in design Decision 3 and rewrite the comment block it names.
- [ ] 3.2 Replace the four `offers` blocks in `world/rules/rulebook/commerce/ciaran.yaml` as in design Decision 4.
- [ ] 3.3 Verify with `grep -n "elven_traditional_robe\|elven_forest_veil\|elven_candied_blossom\|elven_spider_silk" world/rules/rulebook/commerce/ciaran.yaml` printing nothing, and `uv run --locked python -c "from world.lore.settlements.assortments import ASSORTMENT_REGISTRY as A; print([A[k].item_keys for k in ('elven_attire','elven_fare','elven_sundries','elven_remedies')])"` printing the four "after" tuples of Decision 3.

## 4. Cards and room prose

- [ ] 4.1 Edit the four cards as in design Decision 5 in `world/lore/npc_profiles/ciaran_homes_a.py` and `world/lore/npc_profiles/ciaran_homes_b.py`. Verify with `grep -n "蛛絲\|蜜漬花蕊\|輕紗" world/lore/npc_profiles/ciaran_homes_a.py world/lore/npc_profiles/ciaran_homes_b.py` printing nothing, and `uv run --locked python -c "from world.lore.npc_profiles import NPC_PROFILE_REGISTRY as R; print(len(R))"` printing a number without an error.
- [ ] 4.2 Edit `content/maps/interiors/ciaran_valwyn_home.yaml` as in design Decision 6. Verify with `git diff --stat content/maps/interiors/` showing that one file with one changed line.

## 5. Dialogue

- [ ] 5.1 Rewrite `world/lore/dialogue/content/ciaran_lareneth.yaml` as in design Decision 7.
- [ ] 5.2 Rewrite `world/lore/dialogue/content/ciaran_valwyn.yaml` as in design Decision 7.
- [ ] 5.3 Rewrite `world/lore/dialogue/content/ciaran_vethiel.yaml` as in design Decision 7.
- [ ] 5.4 Rewrite `world/lore/dialogue/content/ciaran_nireth.yaml` as in design Decision 7.
- [ ] 5.5 Verify the IDs survived: `git diff world/lore/dialogue/content/ | grep "^[-+] *\(- \)\?topic_id\|^[-+] *scene_id"` prints nothing. Verify the load: `uv run --locked python -c "from world.lore.dialogue import DIALOGUE_SNAPSHOT; print(len(DIALOGUE_SNAPSHOT))"` prints a number and raises no `DialogueSourceError`.
- [ ] 5.6 Run `uv run --locked python .agents/skills/npc-dialogue-content/scripts/npc_content_lint.py --places world/lore/dialogue/content/ciaran_lareneth.yaml world/lore/dialogue/content/ciaran_valwyn.yaml world/lore/dialogue/content/ciaran_vethiel.yaml world/lore/dialogue/content/ciaran_nireth.yaml`. Verify exit code 0; read every WARN line and either fix the line or record in the review document why it stands.
- [ ] 5.7 Run `sh /home/jim60105/.agents/skills/chinese-content-writing-guideline/scripts/lint.sh` on each of the four dialogue files, the two profile modules and the edited interior file. Verify 0 errors apart from the expected false positives the dialogue skill lists.
- [ ] 5.8 Verify no removed good is still offered in prose: `grep -n "蛛絲\|蜜漬花蕊\|輕紗\|白色" world/lore/dialogue/content/ciaran_lareneth.yaml world/lore/dialogue/content/ciaran_valwyn.yaml world/lore/dialogue/content/ciaran_vethiel.yaml world/lore/dialogue/content/ciaran_nireth.yaml` prints only the lines that point a guest to the making village (design Decision 7).

## 6. Documents and regeneration

- [ ] 6.1 Edit `docs/lore/items.md` as in design Decision 8. Verify with `grep -c "ciaran_nightbloom_preserve\|ciaran_ember_mushroom_skewer\|ciaran_indigo_dye\|ciaran_crystal_sand\|ciaran_antivenom_tincture" docs/lore/items.md` printing `5`.
- [ ] 6.2 Edit `docs/lore/settlement-locations.md` as in design Decision 8. Verify by listing in the working notes each grep hit and whether it was changed or left, with the reason.
- [ ] 6.3 Refresh the eight ledger rows in `docs/development/npc-editorial-review.md` as in design Decision 8.
- [ ] 6.4 Create `docs/lore/ciaran-local-goods-review.md` as in design Decision 8. Verify it has a section for each of the four hosts and lists every proper noun used in the rewritten dialogue with the registry row it resolves to.
- [ ] 6.5 Run `uv run --locked python -m tools.map_reference_context`, then `uv run --locked python -m tools.map_reference_context --check`. Verify the check prints `is up to date`. Then run `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` and verify it ends with `RESULT: game-ready as far as static checks can tell`.

## 7. Tests

- [ ] 7.1 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_items world.lore.tests.test_shops world.lore.tests.test_npc_editorial_review world.lore.tests.test_dialogue_assembly world.lore.tests.test_room_prose_language`. Verify it ends with `OK`.
- [ ] 7.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_item_use world.rules.tests.test_shop_economy world.rules.tests.test_npc_roster_validation world.rules.tests.test_dialogue_sources world.rules.tests.test_authored_dialogue_runtime world.rules.tests.test_guild_config`. Verify it ends with `OK`.
- [ ] 7.3 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`. Verify it ends with `OK`.
- [ ] 7.4 If any test in 7.1 to 7.3 or 8.1 fails: when the failing assertion compares against a literal item key, price, stock figure, roster or count of shipped goods, or expects one of the four removed goods on a 暗影谷村 shelf, rewrite that assertion to the logic it stands for and append no new key; rerun the command. For any other failure, run the same label on `master`; if `master` passes, stop and report the failure with its output. Verify by recording in the working notes either "no failure" or each rewritten assertion with its file and method name.

## 8. Integration

- [ ] 8.1 Run `uv run --locked python -m tools.contract_gate`. Verify it ends with `contract gate passed`.
- [ ] 8.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.spec_traceability check`. Verify both exit 0.
- [ ] 8.3 Run `openspec validate ciaran-village-local-goods --strict`. Verify it reports the change valid.

## Workflow follow-up

- In a running game on a reset database, a person visits the four homes in 暗影谷村, reads every topic, and buys and sells one item at each.
- A person reads `docs/lore/ciaran-local-goods-review.md` and the rewritten cards and dialogue before the change is archived.
