# Tasks: first-quest-starter-epithet

## 1. Lore flavor rewrite

- [ ] 1.1 Rewrite `STARTER_EPITHET.origin_basis` in `world/lore/titles.py` to the guard-free first-turn-in narrative: 「你在公會完成第一次任務回報，成為阿爾托利亞冒險者中的新面孔。」 (display 「南門新客」 unchanged).
- [ ] 1.2 Reword the `StarterEpithet` class docstring from the onboarding framing to the first-reward-claim framing.

## 2. titles.py writer refactor

- [ ] 2.1 Add `grant_first_quest_epithet(actor)` in `world/rules/titles.py`: `bank_epithet(actor, STARTER_EPITHET.display, STARTER_EPITHET.origin_basis, get_world_clock().tick)`; returns the 「獲得異名：南門新客」 notification tuple on a real bank, `()` on the dedupe no-op.
- [ ] 2.2 Delete `grant_starter_pair` entirely (no alias, no shim); update the "Guild pairing grants (D3/D8 §6.5)" section comment to reflect that registration grants the rank title only and the epithet moved to the claim path.

## 3. guild.py transaction hooks

- [ ] 3.0 Rebase precondition (ordering: `remove-onboarding-tutorial` lands FIRST): implement tasks 3.1-3.4 and 4.1-4.3 against the post-removal result shape — the `turn_in_quest` result dict no longer carries `"onboarding_completed"` (sibling deletes the producer at `world/rules/guild.py:441-446` + :474), and none of the three echo sites (`commands/guild.py:329-332`, `commands/talk.py:157-160`, `web/webclient/actions/service_actions.py:347-349`) still holds the welcome branch. The `title_notifications` loop added here must be the ONLY extra echo line on every claim path (jointly-owned files: the four listed in proposal Impact — if landing in parallel instead, one owner applies both changes' hunks together).
- [ ] 3.1 `register_adventurer` (`world/rules/guild.py`): replace the `grant_starter_pair(actor)` call with `grant_rank_title(actor, "F")`; keep `title_notifications` in the returned record; update the D8 §6.5 comment.
- [ ] 3.2 `turn_in_quest`: capture `first_claim = not claims` from the already-parsed `claims` list (pre-append); in `writer()`, when `first_claim`, call `grant_first_quest_epithet(actor)` and collect the lines. Land after `remove-onboarding-tutorial` removes the `set_onboarded` hook from the same closure, or coordinate both hunks with one owner.
- [ ] 3.3 Add `title_collection` and `title_equipped` to the `snapshot_attributes(...)` tuple and the `restore()` loop so a failed first claim revokes the epithet.
- [ ] 3.4 Add `"title_notifications"` to the `turn_in_quest` result dict.

## 4. Claim-surface echoes

- [ ] 4.1 `commands/guild.py::CmdGuildTurnIn`: echo each `result["title_notifications"]` line after the reward summary (same loop idiom as `CmdGuildRegister`).
- [ ] 4.2 `commands/talk.py::_turn_in_quest`: echo the same lines on the dialogue turn-in surface.
- [ ] 4.3 `web/webclient/actions/service_actions.py` guild claim adapter: append the notification lines to the actor message / success payload for the webclient claim response.
- [ ] 4.4 Add the three-surface first-claim notification assertion set: on a FIRST-ever successful claim, the 「獲得異名：南門新客」 line must appear on all three surfaces — CLI `guild turnin` (`CmdGuildTurnIn` — extend the existing claim-command carriers `commands/tests/test_guild_economy_commands.py` / `test_command_branch_behaviour.py`, the modules already exercising it), the CLI `talk 回報` keyword path (`commands/tests/test_talk_turnin_commands.py` pattern), and the webclient claim action (`web/webclient/actions/tests/test_service_actions.py` guild claim adapter); on second-and-later claims the line must be ABSENT on every surface; and on all three surfaces assert NO claim response still contains 「你的第一個日子在這裡圓滿結束」 (the sibling's deleted welcome must not resurface through this change's echo code).

## 5. Tests

- [ ] 5.1 `world/rules/tests/test_titles.py`: replace `grant_starter_pair` pairing tests with — registration grants F fixed title only (no epithet entry, full title 「F級冒險者」); `grant_first_quest_epithet` banks + auto-equips + emits 「獲得異名：南門新客」; a second `grant_first_quest_epithet` is silent and inert (dedupe); mechanical sweep of remaining `grant_starter_pair` fixture calls (`grant_rank_title` + `grant_first_quest_epithet`, or direct `bank_epithet` where dedupe is the subject).
- [ ] 5.2 `world/rules/tests/test_guild_registration.py`: registration record's `title_notifications` is the F-rank line only; rejected registration still grants nothing.
- [ ] 5.3 `world/rules/tests/test_guild_rewards.py`: first-ever claim of any definition grants the epithet inside the transaction (composed title 「F級冒險者　南門新客」 after the claim, response carries the notification); second and later claims are inert (no re-grant, no line); fault-injection on the first claim restores `title_collection`/`title_equipped` with every other surface; non-`introductory_hunt` first claim grants identically.
- [ ] 5.4 Mechanical fixture sweep in the remaining importers: `world/rules/tests/test_title_view.py`, `commands/tests/test_title_command.py`, `typeclasses/tests/test_appearance.py`, `typeclasses/tests/test_npc_dialogue.py`, `server/conf/tests/test_title_nomination_service.py`, `web/webclient/actions/tests/test_title_actions.py`, `web/webclient/presentation/tests/test_character_panel.py`, `web/webclient/presentation/tests/test_title_codex_panel.py`; assert `grep -r grant_starter_pair` returns nothing.

## 6. Traceability anchors

- [ ] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and confirm the ids for the touched capabilities: `title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically`, `title-system::slot-non-empty-is-an-invariant-with-auto-equip-and-no-unequip`, `guild-registration::guild-registration-grants-the-paired-starter-titles-atomically`.
- [ ] 6.2 Keep `@covers_requirement` on the rewritten registration/pairing/invariant tests pointing at those ids; add `@covers_requirement("quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically")` on the new first-claim grant tests (re-run the `list` command if the slug differs after sync).

## 7. Gates

- [ ] 7.1 Focused suites green: `world.rules.tests.test_titles`, `world.rules.tests.test_title_view`, `world.rules.tests.test_guild_registration`, `world.rules.tests.test_guild_rewards`, `commands.tests.test_guild`, `web.webclient.actions.tests.test_title_actions`, `web.webclient.presentation.tests.test_character_panel`, `web.webclient.presentation.tests.test_title_codex_panel`, `typeclasses.tests.test_appearance`, `typeclasses.tests.test_npc_dialogue`, `commands.tests.test_title_command`, `server.conf.tests.test_title_nomination_service`.
- [ ] 7.2 `uv run --locked python -m tools.spec_traceability check` — 0 uncovered, 0 errors.
- [ ] 7.3 `openspec validate first-quest-starter-epithet --strict` green.
