## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §2 item 6, §8.1) fixes the requester's most visible flow break: pressing 交談 does not open a conversation. Today a scripted host's 交談 opens an `exploration.keywords` child frame that asks for a topic first, a generative host offers a separate 自由交談 row that borrows the command line, and the dialogue view appears only after the first topic or speech is sent. Nothing on the server can open a conversation without a topic.

This change adds the server action `explore.talk_open`. It opens the dialogue session with the host's authored greeting, or with a fixed server-authored line when the host has no greeting. Each dialogue host then gets exactly one 交談 affordance, and the dock's 交談 row dispatches that action. Once C8c (`webclient-retire-exploration-submenus`) is archived, the keyword frame is the last client-side exploration path that picks a topic outside the dialogue, and this change deletes it. The project is unreleased, so the old path is removed, not kept.

## What Changes

- **Server, new action.** `web/webclient/actions/exploration_actions.py` gains `validate_talk_open_payload` (exactly `{npc_id}`) and `_talk_open_adapter`. `web/webclient/actions/registry.py` registers `explore.talk_open` with a full-snapshot publish (`affected_panels=()`). The adapter:
  - rejects a possessed actor with the possession code
  - re-resolves the NPC from the actor's current location (`_resolve_npc`)
  - applies the talk schedule gate (`interaction_reason(npc, "talk")`)
  - requires a conversable host (new `world.rules.dialogue.opens_dialogue(npc)`: an `LLMNPC`, or a `ScriptedDialogue` host whose authored table resolves)
  - records the session through `open_or_refresh_dialogue`, with the line from `greeting_for(npc)` or the new fallback `dialogue_open_fallback_line(name)` in `world/rules/player_messages.py` (`「{name}看向你，等你開口。」` without the corner brackets, see design D3)

  Rejections reuse `talk_scripted`'s codes and messages. The action makes no LLM call, never advances the clock, and changes no affinity or memory. It is not added to the dispatcher's `_DIALOGUE_TRIGGER_ACTION_IDS`, so it schedules no action-options generation.
- **Shared vocabulary.** `explore.talk_open` joins `ACTION_CODE_ALLOWLIST` in `web/webclient/presentation/affordances.py`. `SUGGESTIBLE_ACTION_IDS` subtracts it, so no suggestion card or AI proposal can name it. `options.py` `_ACTION_PAYLOAD_VALIDATORS` registers its validator, which the lockstep test requires. The canonical vocabulary (`exploration_affordances`) does not emit it: the per-keyword `talk_scripted` entries and the `talk_freeform` entry stay, because the `context_actions` form, the suggestion cards, and the AI proposal ladder still use them (design D2).
- **BREAKING (protocol): exploration panel version 3.** In `web/webclient/presentation/exploration.py` the version becomes 3 (`EXPLORATION_SCHEMA_VERSION = 3`):
  - Every host that `opens_dialogue` gets exactly one `{kind: "action", action_id: "explore.talk_open", label: "交談"}` affordance, listed first. It is disabled with the possession reason when the actor is a possessed NPC.
  - A `ScriptedDialogue` host whose table does not resolve keeps a disabled 交談 carrying the existing `dialogue_unavailable` reason.
  - The panel no longer emits `explore.talk_scripted` or `explore.talk_freeform` affordances, and the target descriptor's `keywords` field is deleted. The panel's `ACTION_IDS` becomes the shared allowlist minus those two codes.

  The client mirror `web/static/webclient/js/elosern/protocol/panels/exploration.js` follows: version 3, no `keywords`, and `EXPLORATION_ACTION_IDS` swaps those two codes for `explore.talk_open`. The three exploration keyword constants and their `tests/test_exploration_parity_contract.py` pairs are deleted. `protocol/constants.js` `CONTEXT_ACTIONS_ACTION_CODES` gains `explore.talk_open`, and `panels/skill_descriptor.js` gains its `{npc_id}` params branch.
- **Client dock.** `web/static/webclient/js/elosern/exploration_menu.js` `targetMenuFor` replaces its `explore.talk_scripted` and `explore.talk_freeform` branches with one `explore.talk_open` branch. The row is `talk-open`, with payload `{npc_id}` and `commandDisplay.npcLabel`. `keywordMenuFor` and `scriptedAffordanceFor` are deleted.
  - `stores/frame-resolvers.js` deletes the `exploration.keywords` source.
  - `stores/elosern/frames.js` drops it from the `gridCols = 1` list. `settleFrameStack` gains one more rule: when the committed mode turns `dialogue`, the stack resets to the overview (design D6).
  - `stores/elosern/interaction.js` `handleExplorationItem` deletes the `openKeywords` and `freeform` branches. The dialogue variant's free row keeps `borrowDialogueCommand`.
  - `components/dock-panes.js` deletes the `nav` pane kind (its last producer was the keyword frame) and the `explore.talk_freeform` clause of the `affordance` test. `components/DockMenu.vue` deletes the `nav` template, its sizing branch, its CSS, and the `openKeywords` chevron clause.
- **Echo.** `web/static/webclient/js/elosern/command_echo.js` gains an `explore.talk_open` resolver, `talk <NPC>`. `stores/elosern/combat.js` `fillDisplayFor` fills its `npcLabel`.
- **Tests.**
  - Server: adapter, validator, registry pin, session writer, presenter (v3 shape, one 交談 per host, no keywords), allowlist and lockstep pins.
  - Node: protocol, exploration menu, command echo.
  - Vitest: resolvers, panes, store, dialogue, echo surfaces.
  - Browser: dialogue, nav, input-narrative, services, tiles, and contextual-hud dock journeys, re-pointed so 交談 dispatches `explore.talk_open` and the conversation continues in the dialogue variant.
- No component is added or deleted.

Out of scope:
- The dialogue stage layout (both portraits, dimming, the collapsed command panel, choices after the last page, `↦ 移動…`): `webclient-dialogue-stage` (C10). After this change 交談 enters the existing dialogue variant of the message window (C6b/C6c).
- The text `talk <npc>` command is unchanged: it still greets without opening a session (design D5).
- The `affordance` pane kind of `DockMenu`: no frame has produced it since C8b moved target menus into `DockVerbPopover`. Its retirement belongs with C8c's pane cleanup (reported to the coordinator), not here.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-exploration-menu`:
  - REMOVED "The exploration panel is an exact read-only version-2 presentation panel".
  - ADDED "The exploration panel is an exact read-only version-3 presentation panel".
  - MODIFIED "Exploration affordances are server-authored, never inferred from prose": one 交談 `explore.talk_open` per conversable host.
  - ADDED "explore.talk_open opens a conversation with the host's greeting".
  - REMOVED "The exploration dock is keyboard-first and roots at the scene overview" (C8b's text).
  - ADDED "The keyboard-first exploration dock roots at the scene overview and opens dialogue directly".
- `webclient-dialogue-session`: MODIFIED "The dialogue session is deterministic-core-only character state". The writer list gains the `explore.talk_open` success path.
- `webclient-action-dispatch`: MODIFIED "Action registries are allowlisted and duplicate-safe". Fourteen exploration adapters.
- `exploration-affordances`: MODIFIED "The canonical affordance vocabulary is shared and read-only". The allowlist gains `explore.talk_open`, which the vocabulary never emits, and the exploration panel projects talk as one entry per host.
- `webclient-context-actions`: MODIFIED "The exploration context form enumerates the complete canonical affordance list": the client code lists.
- `webclient-contextual-hud`, all on C8c's text:
  - MODIFIED "Dock panes render a per-kind vocabulary from backed fields only": no keyword navigation rows.
  - MODIFIED "A fixed-column dock pane sizes its columns to content": the scenario names the waiting cards instead of a nav pane.
- `webclient-pointer-activation`: MODIFIED, on C8c's text, "Every action-dock surface renders exactly the keyboard router's current menu frame". The form list loses the navigation row.

## Impact

- Server source:
  - `world/rules/dialogue.py` (`opens_dialogue`, module docstring writer list), `world/rules/player_messages.py`
  - `web/webclient/actions/exploration_actions.py`, `registry.py` (docstring and registration)
  - `web/webclient/presentation/affordances.py`, `options.py`, `exploration.py`
- Client source:
  - `web/static/webclient/js/elosern/exploration_menu.js`, `command_echo.js`, `protocol/constants.js`, `protocol/panels/exploration.js`, `protocol/panels/skill_descriptor.js`, `protocol.js` (export list)
  - `web/webclient-app/stores/frame-resolvers.js`, `stores/elosern/{frames,interaction,combat}.js`, `stores/dialogue-view.js` (comment)
  - `components/dock-panes.js`, `components/DockMenu.vue`
  - Stories `stories/Core/AppShell.stories.js`, `stories/fixtures/scene_overview.js`, `stories/Action/DockMenu.stories.js`
- Server tests:
  - `web/webclient/actions/tests/test_exploration_actions/` (new `test_talk_open.py`, `test_validators.py`, `test_dialogue_session_recording.py`)
  - `web/webclient/actions/tests/test_dispatcher/test_registry.py`, `test_dialogue_trigger.py`
  - `web/webclient/presentation/tests/test_exploration_panel/{_support,test_presenter,test_schema,test_navigation_and_byte_stability}.py`
  - `web/webclient/presentation/tests/test_affordances/test_contract.py`, `test_combat_panel/test_options_and_validators.py`
  - `world/rules/tests/test_dialogue.py` (`opens_dialogue`, fallback line)
  - `tests/test_exploration_parity_contract.py`
- Node tests: `web/static/webclient/js/tests/{exploration_menu,hud_dock_menus,command_echo,protocol_exploration_a,protocol_exploration_b,protocol_context_actions_a,keyboard_router_declarative}.test.js`, `protocol_fixtures.js`.
- Vitest (under `web/webclient-app/`): `tests/frame-resolvers.test.js`, `tests/components/dock_panes.test.js`, `tests/action/{dock_menu,dock_menu_panes}.test.js`, `tests/store/{declarative_frames,command_echo_surfaces}.test.js`, `tests/store/protocol_fixtures.js`, `tests/{dialogue_store,dialogue_dock}.test.js`.
- Browser: `web/tests/browser/test_browser_exploration_{dialogue,nav,state,tiles}.py`, `test_browser_input_narrative.py`, `test_browser_services_base.py`, `test_browser_contextual_hud_dock.py`, `_journey_support.py`, `browser_helpers.py`.
- Spec traceability: the panel requirement ID moves from version-2 to version-3 (8 annotations in `test_presenter.py`). The C8b exploration-dock ID moves to the new dock ID in the files C8b and C8c anchored to it.
- Dependencies: archive order C8a → C8b → C8c (`webclient-retire-exploration-submenus`) → C9 (this change) → C10. The contextual-hud and pointer-activation blocks are written on C8c's text, and the dock requirement replaces C8b's.
