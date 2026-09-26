## 1. Preconditions

- [x] 1.1 Confirm that C8c (`webclient-retire-exploration-submenus`) is archived and that its seams exist:
  - `openspec/specs/webclient-exploration-menu/spec.md` contains "The exploration panel is an exact read-only version-2 presentation panel" and "The exploration dock is keyboard-first and roots at the scene overview".
  - `grep -n "verbMenuFor\|targetMenuFor" web/static/webclient/js/elosern/exploration_menu.js` matches both, and `grep -n "explore.talk_scripted\|explore.talk_freeform" web/static/webclient/js/elosern/exploration_menu.js` matches the two `targetMenuFor` branches.
  - `grep -n "EXPLORATION_SCHEMA_VERSION = 2" web/webclient/presentation/exploration.py` matches.

  Stop and report if any of these is missing.

## 2. Server: rules, message, action

- [x] 2.1 `world/rules/dialogue.py`:
  - Add `opens_dialogue(npc) -> bool` (design D1). It is true for an `LLMNPC` (lazy `typeclasses.npcs` import) or for a `ScriptedDialogue` host whose `dialogue_key_for(npc)` resolves in `DIALOGUE_TABLE`.
  - Add `explore.talk_open` to the module docstring's session-writer list and to the `open_or_refresh_dialogue` docstring.

  `world/rules/player_messages.py`: add `DIALOGUE_OPEN_FALLBACK_TEMPLATE = "{name}看向你，等你開口。"` and `dialogue_open_fallback_line(name: str) -> str` (design D3).

  Add cases to `world/rules/tests/test_dialogue.py`:
  - `opens_dialogue` is true for a synthesized scripted host with a table row and for an `LLMNPC` without a component.
  - It is false for a component host whose key is absent from the table and for a plain NPC.
  - `dialogue_open_fallback_line("甲")` is `甲看向你，等你開口。`.

  Use synthesized keys only (`tools.test_data_lint` rules).
- [x] 2.2 `web/webclient/actions/exploration_actions.py`:
  - Add `validate_talk_open_payload`: exactly `{npc_id}`, positive int, raising `ExplorationActionError` otherwise.
  - Add `_talk_open_adapter` per design D1, with the rejection order possessed, `no_npc`, `schedule_blocked`, `not_dialogue_host`, the greeting or fallback line, `open_or_refresh_dialogue`, the narrative message, and `_success("dialogue_opened", message, AFFECTED_FULL)`.
  - Add both to `__all__` and to the module docstring's action list.

  `web/webclient/actions/registry.py`: register `ActionSpec(action_id="explore.talk_open", validate_payload=validate_talk_open_payload, adapter=_talk_open_adapter, affected_panels=())`, and update the docstring to "fourteen exploration adapters". Do not add the id to `dispatcher.py` `_DIALOGUE_TRIGGER_ACTION_IDS`.
- [x] 2.3 Add `web/webclient/actions/tests/test_exploration_actions/test_talk_open.py`, reusing `_support.py` (`_t_dialogue_scope`, `_T_DIALOGUE`, `_T_LODGE_GREETING`, `_T_LODGE_KEYWORD`) and synthesized NPCs. Annotate the cases with `webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting` (confirm the ID with `uv run --locked python -m tools.spec_traceability list` after 7.1). Cover:
  - A scripted host with a greeting: success `dialogue_opened`, the session line equals the greeting, `live_dialogue_session` names the host, and the narrative message is `{key}說：{greeting}`.
  - An `LLMNPC` without a component, and a scripted host whose row has `greeting=None`: the line is `dialogue_open_fallback_line(npc.key)`.
  - A departed NPC and a non-NPC id reject with `no_npc`. A plain NPC and a component host without a table row reject with `not_dialogue_host`. None of them writes `db.dialogue_session`.
  - A schedule-blocked host rejects with `schedule_blocked` (patch `interaction_reason` as `test_dialogue_talk.py` does).
  - A possessed actor rejects with `REASON_POSSESSED_TALK`.
  - A successful open leaves the world clock tick, the relations record, and the NPC's memory attributes unchanged, and makes no client call (a `FakeLLMClient` is never invoked).
  - An open while a session names another host replaces it.
- [x] 2.4 Extend the existing server suites:
  - `test_exploration_actions/test_validators.py`: `validate_talk_open_payload` accepts `{npc_id: 1}` and rejects extra keys (`keyword_id`, `speech`), a missing key, `0`, `True`, and a string.
  - `test_exploration_actions/test_dialogue_session_recording.py`: add a talk_open writer case annotated `webclient-dialogue-session::the-dialogue-session-is-deterministic-core-only-character-state`.
  - `test_dispatcher/test_registry.py`: the pinned id list gains `explore.talk_open`.
  - `test_dispatcher/test_dialogue_trigger.py`: add "a successful talk_open schedules nothing".
  - `web/static/webclient/js/tests/command_echo_coverage_manifest.json`: `registeredMutationActionIds` gains `explore.talk_open` (pinned by `web/webclient/actions/tests/test_action_catalog_coverage.py`; the Node and Vitest halves of this lockstep are tasks 4.2 and 5.1).

  Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests world.rules.tests.test_dialogue world.rules.tests.test_dialogue_session`. It must pass.

## 3. Server: vocabulary and exploration panel v3

- [x] 3.1 `web/webclient/presentation/affordances.py`:
  - Insert `"explore.talk_open"` into `ACTION_CODE_ALLOWLIST` after `"explore.look"`, and update the comment ("twelve action codes; talk_open is never emitted by the vocabulary").
  - Subtract `"explore.talk_open"` in `SUGGESTIBLE_ACTION_IDS`.

  `web/webclient/presentation/options.py`: add `"explore.talk_open": validate_talk_open_payload` to `_ACTION_PAYLOAD_VALIDATORS`.

  Update the pins:
  - `presentation/tests/test_affordances/test_contract.py`: the allowlist test is renamed to "…the_twelve_actions", and the suggestible subtraction gains talk_open.
  - `test_affordances/test_vocabulary.py`: add a case where the vocabulary for a room with a scripted host and an `LLMNPC` contains no `explore.talk_open` entry, annotated `exploration-affordances::the-canonical-affordance-vocabulary-is-shared-and-read-only`.
  - `test_combat_panel/test_presenter.py` (the maximal-room id set also subtracts `explore.talk_open`).
  - `test_combat_panel/test_options_and_validators.py`: the lockstep test passes unchanged, which confirms coverage.
- [x] 3.2 `web/webclient/presentation/exploration.py`, per design D4:
  - `EXPLORATION_SCHEMA_VERSION = 3`.
  - `ACTION_IDS` is the allowlist minus `explore.talk_scripted` and `explore.talk_freeform`.
  - Delete `_validate_keyword`, `_require_keyword_id`, the `keywords` branch of `_validate_interact_target` (the exact field set becomes `identity`, `display_name`, `portrait_ref`, `affordances`), `_scripted_keywords`, and the now-unused keyword imports.
  - `_interact_targets` emits the single 交談 `explore.talk_open` (enabled, possession-disabled, or `dialogue_unavailable`) before the vocabulary rows, and drops `explore.talk_freeform` from the accepted codes.
  - Replace the `is_dialogue_host` / `opens_dialogue` import accordingly, and rewrite the module docstring ("version 3", "one 交談 per conversable host").
- [x] 3.3 Exploration panel tests under `web/webclient/presentation/tests/test_exploration_panel/`:
  - `_support.py`: fixtures build v3 payloads with no `keywords`.
  - `test_schema.py`: v2, a `keywords` field, and `talk_scripted` / `talk_freeform` affordances are rejected.
  - `test_presenter.py`:
    - one enabled 交談 for a scripted host and for an `LLMNPC`, none of the old codes, and no `keywords`
    - disabled `dialogue_unavailable` for a component host without a table row
    - possession-disabled 交談 for a possessed actor
    - the `ACTION_IDS` test asserts the derived subset instead of `assertIs(…, ACTION_CODE_ALLOWLIST)`
  - `test_navigation_and_byte_stability.py`: expected payloads follow.

  Re-anchor the 8 `webclient-exploration-menu::the-exploration-panel-is-an-exact-read-only-version-2-presentation-panel` annotations in `test_presenter.py` to the version-3 ID, and annotate the new affordance cases `webclient-exploration-menu::exploration-affordances-are-server-authored-never-inferred-from-prose`. Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests`. It must pass.
- [x] 3.4 `tests/test_exploration_parity_contract.py`: delete the `MAX_SCRIPTED_KEYWORDS`, `MAX_KEYWORD_ID_CHARS`, and `MAX_KEYWORD_LABEL_CODE_POINTS` pairs from `_AFFORDANCE_CONSTANTS`. Run `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_exploration_parity_contract`. It must pass.

## 4. Client protocol mirror, echo resolver, and the 交談 branch (Node)

- [x] 4.1 `web/static/webclient/js/elosern/protocol/panels/exploration.js`:
  - The version check becomes `!== 3`.
  - `EXPLORATION_ACTION_IDS` is `talk_open`, `party_invite`, `party_leave`, `engage`, `possess`, `possess_release`, `deliver`.
  - Delete `validateExplorationKeyword`, the `keywords` branch (the exact field set loses `keywords`), and the three keyword constants and their exports.
  - Update the header comment.

  `web/static/webclient/js/elosern/protocol.js`: drop the three constant exports. `protocol/constants.js`: `CONTEXT_ACTIONS_ACTION_CODES` gains `"explore.talk_open"` after `"explore.look"`. `protocol/panels/skill_descriptor.js` `validateContextActionsAffordanceParams`: add an `explore.talk_open` branch accepting exactly `{npc_id}`.
- [x] 4.2 `web/static/webclient/js/elosern/command_echo.js`: add the `explore.talk_open` resolver (`talk <NPC>` from `npcLabel`, `null` without it), design D5.
- [x] 4.3 `web/static/webclient/js/elosern/exploration_menu.js` `targetMenuFor` (design D6): one `explore.talk_open` branch (`talk-open`, `actionId`/`payload` only while enabled, `commandDisplay: {npcLabel: target.display_name}`, the disabled reason as the other rows) replaces the `talk_scripted` and `talk_freeform` branches. Change nothing else in this file: `keywordMenuFor`, `scriptedAffordanceFor`, and their exports stay for C9b to delete.
- [x] 4.4 Node tests under `web/static/webclient/js/tests/`:
  - `protocol_fixtures.js`: v3 exploration fixtures without `keywords`, with 交談 as `explore.talk_open`.
  - `protocol_exploration_a.test.js`, `protocol_exploration_b.test.js`:
    - version 3
    - rejection of `keywords`, of `talk_scripted` / `talk_freeform` target affordances, and of v2
    - the pinned `EXPECTED_ACTION_CODES` (twelve) and `EXPECTED_EXPLORATION_ACTION_IDS` lists
    - the talk_open params vectors
  - `protocol_context_actions_a.test.js`: the code-list pin gains talk_open.
  - `exploration_menu.test.js`: add `targetMenuFor` cases: enabled 交談 → `{actionId: "explore.talk_open", payload: {npc_id}, commandDisplay: {npcLabel}}`, and disabled 交談 → no action and the reason. Replace any `targetMenuFor` case that asserted the `talk-scripted` or `talk-freeform` row. Leave the `keywordMenuFor` / `scriptedAffordanceFor` cases (C9b deletes them with their functions).
  - `hud_dock_menus.test.js`: follow if it builds a talk row.
  - `command_echo.test.js`: the resolver, its null case, and the `REGISTERED_MUTATION_ACTIONS` coverage fixture entry (`{payload: {npc_id: 7}, display: {npcLabel: …}}`).

  Run `node --test web/static/webclient/js/tests/*.test.js`. It must pass.

## 5. Vitest and story fixtures the wire change turns red

- [x] 5.1 Under `web/webclient-app/tests/` (design D7):
  - `store/protocol_fixtures.js`: v3 exploration panel, 交談 as `explore.talk_open`, no `keywords`.
  - `store/command_echo_surfaces.test.js`: add one behavioral table row "exploration popover 交談 (row descriptor forwarded)" with `ids: ["explore.talk_open"]`, dispatching `explore.talk_open` with `{npc_id: 7}` and `{npcLabel: "店長"}` and expecting `talk 店長`. The "exercises every registered mutation id" test must pass.
  - `frame-resolvers.test.js`: the `exploration.target` cases assert the `talk-open` row (`actionId: "explore.talk_open"`, payload `{npc_id}`). Leave the `exploration.keywords` cases for C9b.
  - `dialogue_store.test.js`, `dialogue_dock.test.js`: open conversations by activating the popover's `talk-open` row and committing a `dialogue` panel, instead of the keyword frame. Assert that the free row still borrows the command line through `borrowDialogueCommand`. Assert nothing about the popover's depth (C9b adds the reset).
  - `store/declarative_frames.test.js`: the room-change case that opened a keywords frame through 交談 opens the popover instead.

  Find every remaining v2 exploration fixture with `git grep -n "schema_version: 2" web/webclient-app/tests web/webclient-app/stories` and check whether it is an exploration panel. Run `pnpm test`. It must pass.
- [x] 5.2 Story fixtures fed through `store.receive`:
  - `web/webclient-app/stories/Core/AppShell.stories.js`: the exploration fixtures use v3, 交談 as `explore.talk_open`, and no `keywords` or `talk_scripted` / `talk_freeform` affordance.
  - `stories/fixtures/scene_overview.js` (C8a): `explorationPanelFixture` emits v3 targets.

  `pnpm run build-storybook` and `pnpm run showcase-coverage` (repository root) must pass.

## 6. Browser journeys the wire change turns red

- [ ] 6.1 `web/tests/browser/_journey_support.py` and `browser_helpers.py`: every hand-built exploration panel is v3, with no `keywords` and 交談 as `explore.talk_open`. Locate them with `git grep -n "keywords\|talk_scripted\|talk_freeform\|schema_version" web/tests/browser/_journey_support.py web/tests/browser/browser_helpers.py`.
- [ ] 6.2 `web/tests/browser/test_browser_exploration_dialogue.py`:
  - `test_scripted_keyword_dialogue_completes` and `test_dialogue_surface_is_the_caption_and_the_dock_stays_ordinary`: overview chip → 交談 sends exactly one `explore.talk_open`. The dialogue variant shows the host's greeting (`_shipped_greeting()`) and its picks, and then digit `1` sends `explore.talk_scripted`. Do not assert the dock depth (C9b).
  - `test_freeform_dialogue_degrades_offline_through_the_command_line` and `test_cancelled_freeform_dialogue_cannot_capture_a_later_command`: bard chip → 交談 → the dialogue variant's `dialogue-freeform` row → command line. The offline assertion waits for the `explore.talk_freeform` result instead of the greeting text, which `talk_open` already shows.
- [ ] 6.3 `test_browser_input_narrative.py`: the two freeform tests find the bard through the fixture's `LLMNPC` identity (the panel no longer marks freeform), open it with 交談, and borrow from the dialogue free row. The echo assertions expect `talk <bard>` for the open, followed by exactly one `talk <bard> <speech>` for the send. The locked-send test disconnects after the open.
- [ ] 6.4 `test_browser_exploration_nav.py`: the intermediate-depth test (C8b: popover → keyword frame) becomes popover → Escape at depth 2, and the `talk-scripted` key assertions read `talk-open`. `test_browser_exploration_state.py`: add `explore.talk_open` to the zero-count assertions. `test_browser_exploration_tiles.py`: C8c's fixed-column nav-pane case (a keyword frame) has no reachable frame left, so move it into `test_browser_combat_skills.py` as a skill-frame case at 1280x720 with the same assertions (every row inside the pane's right edge, and ArrowRight reaching the second column of the fixed two-column mapping), keeping its `webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content` annotation.

  `git grep -n "talk-scripted\|talk-freeform\|自由交談" web/tests/browser` returns nothing. (`exploration.keywords` and `dock-menu__nav` references are C9b's to clear.)

## 7. Specs and traceability

- [x] 7.1 Sync this change's deltas into the main specs. Edit the `webclient-exploration-menu` Purpose paragraph: "version-2 `exploration` panel" becomes "version-3", and "the thirteen exact allowlisted exploration adapters" becomes "fourteen". Edit the `exploration-affordances` Purpose only if it names the allowlist size. It currently says "the eight emitted action codes", which stays true.
- [x] 7.2 Re-anchor the version-2 panel ID to the version-3 ID (task 3.3). Leave `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview` in place: that requirement survives until C9b.

  Confirm every ID with `uv run --locked python -m tools.spec_traceability list`, then run `uv run --locked python -m tools.spec_traceability check`. It must pass, and the new talk_open requirement must be covered by 2.3.

## 8. Validation

- [x] 8.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. All must pass.
- [x] 8.2 Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions.tests web.webclient.presentation.tests world.rules.tests.test_dialogue world.rules.tests.test_dialogue_session tests.test_exploration_parity_contract web.webclient.tests.test_node_suite_evidence commands.tests.test_talk_turnin_commands`. It must pass, and the last module confirms typed `talk` is unchanged.
- [ ] 8.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_exploration_nav web.tests.browser.test_browser_exploration_state web.tests.browser.test_browser_exploration_tiles web.tests.browser.test_browser_exploration_actions web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_services_base web.tests.browser.test_browser_contextual_hud_dock web.tests.browser.test_browser_combat_skills web.tests.browser.test_browser_options_surface`. It must pass. If `test_browser_contextual_hud_dock.py` or `test_browser_services_base.py` reached a keyword frame or a 自由交談 row through the popover, re-point that step here the same way as 6.2.
- [x] 8.4 Check the live client at 1920x1080 with `agent-browser`: 交談 on a scripted host shows the greeting and its choices in the message window in one press. Close the browser afterwards.
- [x] 8.5 Run `openspec validate explore-talk-open-action --strict` and `git diff --check`. Both must be clean.
