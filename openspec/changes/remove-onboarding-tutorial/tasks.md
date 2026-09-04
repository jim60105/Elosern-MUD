# Tasks: remove-onboarding-tutorial

## 1. Delete the core subsystem

- [ ] 1.1 Delete `world/rules/onboarding.py` (state machine, `GUARD_NPC_KEY`/`GUARD_NPC_TAG`, `sync_guard_npc`, `relocate_to_starting_location`, `maybe_play_arrival`, `observe_room_entry`, `run_scripted_talk`, `set_onboarded`).
- [ ] 1.2 Delete the whole `world/onboarding/` package (`guide.py`, `guide_dialogue.py`, `scenes.py`, `tests/test_onboarding_data.py`, `world/onboarding/tests/`).
- [ ] 1.3 Remove the `sync_guard_npc` startup step from `server/conf/at_server_startstop.py` (import at ~line 364 + the `STARTUP_STEP_ORDER` entry).
- [ ] 1.4 Delete the `OnboardingGuide` component class from `typeclasses/components.py`.
- [ ] 1.5 Delete the 新手引導 help-entry dict from `world/help_entries.py` (entry at :27-52, key 「新手引導」, aliases `["onboarding", "新手指引"]` — the guided-route text is retired per the `onboarding-guide` REMOVED requirement "A help entry explains onboarding afterwards"; every other entry in `HELP_ENTRY_DICTS` stays). Its only test consumer is `world/rules/tests/test_onboarding_journey.py:345-359`, deleted by task 6.1 — grep-verified no surviving test or module names the entry.
- [ ] 1.6 Remove the `world.rules.onboarding.sync_guard_npc` entry from the expected-startup-callable list in `server/conf/tests/test_startup_observability.py:39` (the test asserts the exact step roster; it fails the moment task 1.3 lands).

## 2. Move guild_staff dialogue into the read-only runtime

- [ ] 2.1 Move `GUILD_STAFF_DIALOGUE_KEY`, `GUILD_STAFF_TURNIN_KEYWORD`, `GUILD_STAFF_RESPONSES` and the `guild_staff` `DialogueDefinition` from `world/onboarding/guide_dialogue.py` into `world/rules/dialogue.py`; delete the cross-package import.
- [ ] 2.2 Drop the `OnboardingGuide` branch from `world/rules/dialogue.py::resolve_dialogue_component` (keep `ScriptedDialogue` only).
- [ ] 2.3 Rewrite `commands/talk.py`: delete the guide-prompt branch (`is_guide_host`/`current_guide_prompt`) and the `run_scripted_talk`/onboarding imports; every scripted answer resolves through `world/rules/dialogue.py`; drop the `onboarding_completed` echo in the 回報 turn-in path.
- [ ] 2.4 Repoint every surviving importer of the moved table from `world.onboarding.guide_dialogue` to `world.rules.dialogue`: `web/tests/browser/seed.py:193` (`GUILD_STAFF_DIALOGUE_KEY`; the host keeps the ordinary `ScriptedDialogue.create(...)` fixture idiom at :195), `typeclasses/tests/test_npc_dialogue.py:38`, `web/webclient/presentation/tests/test_art_panel.py:40`, and `world/rules/tests/test_dialogue.py:17-22` (+ the function-local `DIALOGUE_TABLE` import at :260) for the `GUILD_STAFF_*` names. In `commands/tests/test_talk_turnin_branch.py:13-16` and `commands/tests/test_talk_turnin_commands.py:17-20` repoint the `GUILD_STAFF_*` names but DELETE the `GUARD_DIALOGUE_KEY` import (the guard table dies) and the `ScriptedTalkResult` import at `test_talk_turnin_branch.py:23` — the methods consuming them are retired by task 6.5's migration table.

## 2b. Browser seed de-onboarding

- [ ] 2b.1 Strip ALL onboarding seeding from `web/tests/browser/seed.py`: delete the `OnboardingGuide`/`LOOK_BEAT_ID`/`sync_guard_npc` imports (:430, :438, :440), the `sync_guard_npc()` call (:447), the four deleted-attribute writes `character.onboarded`/`onboarding_beat`/`guide_progress`/`first_arrival_seen` (:452-455), and the `OnboardingGuide.name` guard search + affinity-seeding block (:459-474). Keep the `sync_grid()`/`sync_service_interiors()` calls, the `character.location = south_gate` placement, and the `record_arrival(character)` call (the exploration browser fixtures still need the character in the South Gate with map knowledge recorded). The `ScriptedDialogue`-backed dialogue host at :193-195 (and the 「吟遊詩人」 bard at :477-479, which already uses `dialogue_key="guild_staff"` through `ScriptedDialogue`) stay as ordinary fixtures — guild-staff dialogue is now an ordinary `ScriptedDialogue` table, not onboarding state. The :464-465 deleted-component search has no surviving consumer: the guard affinity seeding it feeds existed only for guard-focused browser assertions, retired with the guard (task 6.2).

## 3. Trim production callers

- [ ] 3.1 `commands/character_creation.py`: remove the post-creation relocate-to-南門 + arrival calls (character stays in 虛境 at birth).
- [ ] 3.2 `typeclasses/accounts.py`: remove the `maybe_play_arrival` call.
- [ ] 3.3 `typeclasses/characters.py`: remove the `advance_beat` onboarding hook from `at_look`.
- [ ] 3.4 `typeclasses/exits.py`: remove the `observe_room_entry` call from the movement completion path.
- [ ] 3.5 `world/rules/movement_settlement.py`: remove the `first_arrival_seen` snapshot field from the settlement snapshot/restore surfaces.
- [ ] 3.6 `world/rules/guild.py`: remove the claim-hook `if record.definition_key == "introductory_hunt" and not actor.onboarded: set_onboarded(...); onboarding_completed = True` block (claim bookkeeping and the `introductory_hunt` quest itself stay unchanged).
- [ ] 3.7 `web/webclient/actions/service_actions.py`: remove the `result["onboarding_completed"]` welcome echo branch.
- [ ] 3.8 `web/webclient/actions/exploration_actions.py`: retarget `explore.talk_scripted` from `world.rules.onboarding.talk_response`/`run_scripted_talk` to the `world/rules/dialogue.py` seam; remove onboarding look hooks.
- [ ] 3.9 `web/webclient/actions/creation_actions.py`: remove the activation relocation-to-南門 and its failure-degradation branch; hand off to exploration with the character still in 虛境.
- [ ] 3.10 `web/webclient/presentation/affordances.py`: resolve `ScriptedDialogue` only for `explore.talk_scripted`; remove `OnboardingGuide` handling.
- [ ] 3.11 Grep-sweep the repo for residual references (`onboarding`, `guide_progress`, `first_arrival_seen`, `onboarding_beat`, `observe_room_entry`, `sync_guard_npc`, `OnboardingGuide`, `run_scripted_talk`, `set_onboarded`, `relocate_to_starting_location`, `maybe_play_arrival`) and fix every non-test caller.
- [ ] 3.12 `commands/guild.py::CmdGuildTurnIn`: remove the third `onboarding_completed` welcome echo (the `if result.get("onboarding_completed"):` branch at :329-332) — the sibling surfaces `commands/talk.py:157-160` and `web/webclient/actions/service_actions.py:347-349` are covered by tasks 2.3/3.7; all three echo surfaces must lose the branch together with the producer at `world/rules/guild.py`.

## 4. Remove character attributes

- [ ] 4.1 Delete the `onboarded`, `guide_progress`, `onboarding_beat`, `first_arrival_seen` AttributeProperties from `typeclasses/characters.py` (dev-database residue handled by reset — no migration).

## 5. HelpOverlay dead-prop trim (merged webclient-static-help-overlay scope)

- [ ] 5.1 `web/webclient-app/components/HelpOverlay.vue`: delete the dead `guide` prop and its template section (component already renders static `controlsReferenceSection()` from `lib/controls-reference.js`).
- [ ] 5.2 `web/webclient-app/AppClient.vue`: remove the `:guide="{}"` binding.
- [ ] 5.3 Prune `guide` fixtures/stories/tests in `web/webclient-app/stories/Overlays/HelpOverlay.stories.js`, `stories/OverlayHost.stories.js`, `stories/fixtures.js`, `tests/overlays/help_overlay.test.js`.

## 6. Tests and CI bookkeeping

- [ ] 6.1 Delete `world/rules/tests/test_onboarding.py`, `world/rules/tests/test_onboarding_journey.py`, and `world/onboarding/tests/`.
- [ ] 6.2 Delete/retune webclient and browser tests whose only payload was onboarding behavior (incl. `web.tests.browser.test_browser_exploration.ExplorationBrowserTest.test_look_at_room_preserves_the_onboarding_beat`); where a surviving trimmed requirement lost its sole carrier, move its `@covers_requirement` anchor onto a surviving test.
- [ ] 6.3 `.github/evennia-shards.json`: remove `world.rules.tests.test_onboarding`, `world.rules.tests.test_onboarding_journey`, `world.onboarding` entries; rename shard `quests-skills-art-ai-onboarding-lore` without the `onboarding` word (update any consumer of the key).
- [ ] 6.4 `.github/browser-shards.json`: remove the onboarding look-beat entry.
- [ ] 6.5 Migrate every surviving test that imports deleted symbols or asserts removed behavior, per this verified migration table (line numbers verified against current source). Rule: onboarding-only methods are deleted; mixed-purpose methods are rewritten to `ScriptedDialogue`/ordinary display while preserving EVERY non-onboarding `@covers_requirement` assertion they carry:
  - `commands/tests/test_localized.py:815-832` — `LocalizedLookOnboardingIntegrationTests` (file tail, onboarding look-beat class, no `@covers_requirement` anchor): DELETE the whole class.
  - `typeclasses/tests/test_appearance.py:359-375` — `test_onboarding_look_beat_still_completes_with_the_block_present` (anchored `displayed-stats-view::look-target-appends-the-displayed-stats-block-room-look-never-does`): REWRITE — keep the 「攻擊：60」 stats-block assertion through the ordinary `at_look` seam, drop the beat/attribute assertions.
  - `typeclasses/tests/test_exits.py:255-262` — `test_guided_player_entering_wilderness_is_marked_skipped` (anchored `onboarding-guide::deviation-detection-applies-to-every-room-type`, a REMOVED requirement): DELETE.
  - `typeclasses/tests/test_exits.py:264-278` — `test_wilderness_step_and_return_are_noops_for_ended_guide` (onboarding-only `snapshot_for` payload, no anchor): DELETE (the shared-completion-helper source-inspection tests at :281+ stay).
  - `world/rules/tests/test_guild_dialogue_turnin.py:253-254` — `assertTrue(result["onboarding_completed"])` / `assertTrue(self.player.onboarded)` inside the successful-turn-in assertions: DELETE both lines (the copper/merit/items/claims assertions carry the turn-in contract). Also drop the `self.player.onboarded` field from the rollback-snapshot tuples at :317 and :337.
  - `world/rules/tests/test_dialogue.py` — delete the guard-host/onboarding-beat methods and the `onboarding-guide::talk-behaves-predictably-for-any-npc` anchors (capability REMOVED); repoint the guild_staff/`DIALOGUE_TABLE` references per task 2.4; drop the `guide_progress`/`onboarded` keys from `_player_state` (:358-359); every `guild-registration`/`scripted-dialogue`-anchored method survives with its non-onboarding assertions intact.
  - `commands/tests/test_talk_turnin_branch.py:63` — `test_turnin_reports_onboarding_completion_line` (mocks the `onboarding_completed` result key): DELETE; the remaining mocked-branch tests keep their guild-turnin assertions with the key removed from the fake payloads (:55).
  - `commands/tests/test_talk_turnin_commands.py:91-102` — `test_talk_turnin_with_quest_id_settles_once_and_completes_onboarding`: REWRITE as settle-once coverage (drop 「你的第一個日子在這裡圓滿結束」 and `assertTrue(self.char1.onboarded)`, keep the 「你回報了任務」/wallet/second-attempt assertions); :122-128 `test_turnin_keyword_on_the_guard_is_an_unknown_keyword` (builds an `OnboardingGuide` guard): DELETE; :183-184 `guide_progress` seen-keywords assertion: DELETE the assertion line (busy-host assertions stay).
- [ ] 6.6 Re-anchor stale requirement literals after main-spec sync (RENAME hazard): this change's `RENAMED Requirements` blocks rename `movement-settlement-atomicity` req 1 (`…-companion-following-and-onboarding-as-one-coherent-transaction` → the no-onboarding slug) and `webclient-exploration-menu`'s `explore.look` req (`…-and-preserves-onboarding-look-hooks` → `explore-look-reuses-the-command-appearance-path`). Every surviving test carrying the OLD literal breaks traceability at sync — verified sites: `world/rules/tests/test_movement_settlement.py:166`, `typeclasses/tests/test_exit_movement_cost.py:31`, `typeclasses/tests/test_exits.py:53,126,146`, `web/webclient/actions/tests/test_exploration_actions.py:479,521`, `web/tests/browser/test_browser_exploration.py:202`. After archive sync, run `uv run --locked python -m tools.spec_traceability list` and replace every stale literal with the post-sync id. Deleting the onboarding look-beat carriers (`test_exploration_actions.py:521`'s `test_look_at_room_advances_the_onboarding_look_beat`, `test_browser_exploration.py:202-…` `test_look_at_room_preserves_the_onboarding_beat` — task 6.2) drops one carrier of the renamed look requirement, but `test_look_at_present_entity_uses_ordinary_display` (anchored at `test_exploration_actions.py:479`) survives and MUST carry the renamed look requirement's post-sync id.
- [ ] 6.7 Add the reconnect regression assertion: `typeclasses/accounts.py::at_post_login` only played the arrival hook — it never relocated the character. With the hook gone, reconnecting must keep the character at its persisted location. Add a focused test (accounts/typeclasses suite): place a character in a non-birth room, log out/in (or call `at_post_login`), assert `location` is unchanged and no teleport occurs.

## 7. Spec-wording sync (applied by OpenSpec archive)

- [ ] 7.1 Confirm implementation matches the 14 delta files under `specs/` (REMOVED capability + 13 MODIFIED trim deltas; `grid-room-sync`/`limbo-room`/`sample-city-altoria` untouched — sibling `limbo-one-way-city-gates` owns them).
- [ ] 7.2 Confirm no player-command doc change needed: `docs/game/commands.md` and `docs/game/command-reference.md` carry no onboarding entries (verified); `tests/test_command_docs.py` stays green.

## 8. Gates

- [ ] 8.1 Targeted Evennia test runs: talk/dialogue (guild_staff 回報 still resolves), guild (`introductory_hunt` completes without `set_onboarded`), character creation (birth stays in 虛境), movement settlement + map knowledge, webclient exploration/creation.
- [ ] 8.2 Full non-browser Evennia suite once (`--parallel 16 --noinput`).
- [ ] 8.3 `uv run --locked python -m tools.spec_traceability check` → 0 uncovered / 0 errors (onboarding requirements leave the index at archive sync).
- [ ] 8.4 `uv run --locked python -m tools.observability_lint check` → violations shrink-only (`sync_guard_npc` startup-step events retired; freeze file currently carries no onboarding ids — verified).
- [ ] 8.5 npm gates: `npm test`, `npm run build-storybook`, `npm run showcase-coverage`.
- [ ] 8.6 `openspec validate --all --strict`.
