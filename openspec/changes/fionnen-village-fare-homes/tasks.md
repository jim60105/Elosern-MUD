# Tasks

Read `design.md` first. Every table, YAML block and code block named below is in it.

Rules that hold for every task:

- IDs are permanent. Rename, move or delete nothing that exists.
- Do not edit the settlement map document, `content/maps/locations.yaml`, the item registry or any file under `openspec/specs/`.
- Add no test and no assertion that names a place, host, item, price or line from this change.
- Use the names, keys, ages, prices and stock figures of `design.md` exactly.
- Before writing any card, room prose or dialogue, read `/var/home/jim60105/repos/MUD/tmp/story_settings/world_info.md` (`tmp/` is git-ignored, so the file exists only in the primary checkout, not in a worktree; read it by this absolute path), `.agents/skills/npc-dialogue-content/SKILL.md` with its `references/scene-schema.md`, and the `chinese-content-writing-guideline` and `writing-style-guideline` skills.
- The server refuses to start until every gate of a host is satisfied, so the registries load only after groups 2 to 6 are all done. Verification that loads them is in group 7.
- Run every Evennia test command alone, exactly as written, with nothing before or after it. If the test guard refuses a command for discovering more than 100 tests, run its labels as separate commands.

## 1. Baseline

- [ ] 1.1 Run `git status`, then `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py`. Verify by noting the result line in the working notes; the expected baseline ends with `RESULT: game-ready as far as static checks can tell`.
- [ ] 1.2 Confirm the IDs are free: `grep -rn "fionnen_elunwen" content world docs/development` prints nothing. Confirm the dependency is applied: `uv run --locked python -c "from world.lore.items import ITEM_REGISTRY as R; print('eolas_proving_wand' in R, 'fionnen_leafweave_garb' in R)"` prints `True True`.

## 2. Interiors

- [ ] 2.1 Create the 4 interior files of design Decision 2 under `content/maps/interiors/`, with no `art_key` line. Verify with `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py`: it reports no structure error and `game-adoption cross-file problems: 0`.

## 3. Places and shelves

- [ ] 3.1 Add the rows to `world/lore/settlements/places_fionnen.py` as in design Decision 3.
- [ ] 3.2 Add the 2 assortments of design Decision 4 to `world/lore/settlements/assortments.py`.
- [ ] 3.3 Append the offers and shop rows to `world/rules/rulebook/commerce/fionnen.yaml` as in design Decision 5, with the figures verbatim.

## 4. Profiles

- [ ] 4.1 Create `world/lore/npc_profiles/fionnen_homes_b.py` and register it as in design Decision 6. Write the 4 cards and `misunderstood` lines from their briefs.

## 5. Dialogue

- [ ] 5.1 Create the 4 dialogue files of design Decision 7: world/lore/dialogue/content/fionnen_elunwen.yaml world/lore/dialogue/content/fionnen_firwen.yaml world/lore/dialogue/content/fionnen_lumeth.yaml world/lore/dialogue/content/fionnen_sylara.yaml.

## 6. Inventory and ledger

- [ ] 6.1 Add the 8 `NpcSource` rows of design Decision 8 to `world/lore/npc_profiles/inventory.py`.
- [ ] 6.2 Add the 8 ledger rows of design Decision 8 to `docs/development/npc-editorial-review.md`.

## 7. Load and lint

- [ ] 7.1 Run `uv run --locked python -c "from world.lore.settlements.places import PLACE_REGISTRY as P; print([P[k].host_profile_key for k in 'fionnen_elunwen_home fionnen_firwen_home fionnen_lumeth_home fionnen_sylara_home'.split()])"`. Verify it prints the 4 profile keys of design Decision 1.
- [ ] 7.2 Run `uv run --locked python -c "from world.lore.dialogue import DIALOGUE_SNAPSHOT; print(len(DIALOGUE_SNAPSHOT))"`. Verify it prints a number and raises no `DialogueSourceError`.
- [ ] 7.3 Run `uv run --locked python .agents/skills/npc-dialogue-content/scripts/npc_content_lint.py --places world/lore/dialogue/content/fionnen_elunwen.yaml world/lore/dialogue/content/fionnen_firwen.yaml world/lore/dialogue/content/fionnen_lumeth.yaml world/lore/dialogue/content/fionnen_sylara.yaml`. Verify exit code 0; read every WARN line and either fix the line or record in the review document why it stands.
- [ ] 7.4 Run `sh /home/jim60105/.agents/skills/chinese-content-writing-guideline/scripts/lint.sh` on each dialogue file, on `world/lore/npc_profiles/fionnen_homes_b.py` and on each new interior file. Verify 0 errors apart from the expected false positives the dialogue skill lists.
- [ ] 7.5 Run `uv run --locked python -m tools.map_reference_context`, then `uv run --locked python -m tools.map_reference_context --check`. Verify the check prints `is up to date`. Then rerun `uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py` and verify it ends with `RESULT: game-ready as far as static checks can tell`.

## 8. Tests

- [ ] 8.1 Nothing to edit (design Decision 9). Verify with `git diff --stat` showing no test file.
- [ ] 8.2 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_settlements world.lore.tests.test_shops world.lore.tests.test_npc_profile_inventory world.lore.tests.test_npc_editorial_review world.lore.tests.test_dialogue_assembly world.lore.tests.test_room_prose_language`. Verify it ends with `OK`.
- [ ] 8.3 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_npc_roster_validation world.rules.tests.test_dialogue_sources world.rules.tests.test_authored_dialogue_runtime world.rules.tests.test_guild_config`. Verify it ends with `OK`.
- [ ] 8.4 Run `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_economy_sync`, then `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.maps.tests.test_service_interiors world.maps.tests.test_interior_sources world.maps.tests.test_static_map_references`, then `uv run --locked python -m unittest tests.test_map_runtime_contract`. Verify each ends with `OK`.
- [ ] 8.5 If any test in 8.2 to 8.4 or 10.1 fails: when the failing assertion compares against a literal roster, count or name of shipped places, hosts, shops, profiles or dialogue tables, or assumes there is exactly one village, one village subrace or one village host of some kind, rewrite that assertion to the logic it stands for and append no new key; rerun the command. For any other failure, run the same label on `master`; if `master` passes, stop and report the failure with its output. Verify by recording in the working notes either "no failure" or each rewritten assertion with its file and method name.

## 9. Documents

- [ ] 9.1 Create `docs/lore/fionnen-fare-homes-review.md` as in design Decision 10. Verify it has a section for each of the 4 hosts and lists every proper noun used in the dialogue with the registry row it resolves to.
- [ ] 9.2 Revise `docs/lore/settlement-locations.md` as in design Decision 10. Verify with `grep -n "幽月谷村與翠綠森林村的個人住宅與服務宿主尚未建置" docs/lore/settlement-locations.md` printing nothing, and `grep -c "埃倫溫‧斯威夫塔羅" docs/lore/settlement-locations.md` printing at least `1`.

## 10. Integration

- [ ] 10.1 Run `uv run --locked python -m tools.contract_gate`. Verify it ends with `contract gate passed`.
- [ ] 10.2 Run `uv run --locked python -m tools.test_data_lint check` and `uv run --locked python -m tools.spec_traceability check`. Verify both exit 0.
- [ ] 10.3 Run `openspec validate fionnen-village-fare-homes --strict`. Verify it reports the change valid.

## Workflow follow-up

- In a running game, a person walks into 翠綠森林村, enters each new home, talks through every topic and buys and sells one item at each trading home.
- A person reads `docs/lore/fionnen-fare-homes-review.md` and the new cards, room prose and dialogue before the change is archived.
