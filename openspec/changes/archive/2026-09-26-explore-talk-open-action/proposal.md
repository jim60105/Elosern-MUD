## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §2 item 6, §8.1) fixes the requester's most visible flow break: pressing 交談 does not open a conversation. Today a scripted host's 交談 opens an `exploration.keywords` child frame that asks for a topic first, a generative host offers a separate 自由交談 row that borrows the command line, and the dialogue view appears only after the first topic or speech is sent. Nothing on the server can open a conversation without a topic.

This change (C9a) adds the server action `explore.talk_open` and the wire contract that carries it. The action opens the dialogue session with the host's authored greeting, or with a fixed server-authored line when the host has no greeting. Each dialogue host then gets exactly one 交談 affordance in exploration panel version 3, which no longer carries `keywords` or the in-conversation talk codes. The client protocol mirror changes in the same change, because a v3 panel is a protocol error to a v2 validator. So does the one client branch that turns the 交談 affordance into a dock row, because without it the popover would silently drop 交談 and the dock could no longer open a conversation. The client dock cleanup that this leaves dead (the keyword frame, the popover freeform borrow, the `nav` and `affordance` pane kinds, and the dock reset on entering dialogue) is C9b (`webclient-talk-open-dock`). The project is unreleased, so the old wire shape is removed, not kept.

**Implementation profile:** logic — a server action, a panel schema bump, its client validator mirror, and one dock branch swap; server, Node, Vitest, and browser tests fully decide correctness.

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
- **Client protocol mirror (same wire, same change).** `web/static/webclient/js/elosern/protocol/panels/exploration.js` follows: version 3, no `keywords`, and `EXPLORATION_ACTION_IDS` swaps those two codes for `explore.talk_open`. The three exploration keyword constants and their `tests/test_exploration_parity_contract.py` pairs are deleted. `protocol/constants.js` `CONTEXT_ACTIONS_ACTION_CODES` gains `explore.talk_open`, and `panels/skill_descriptor.js` gains its `{npc_id}` params branch.
- **Echo resolver (forced by the registry lockstep).** Registering an action adds it to `command_echo_coverage_manifest.json`, which `web/webclient/actions/tests/test_action_catalog_coverage.py`, the Node catalog gate in `command_echo.test.js`, and the Vitest behavioral table in `tests/store/command_echo_surfaces.test.js` all pin. So `web/static/webclient/js/elosern/command_echo.js` gains the `explore.talk_open` resolver `talk <NPC>` here, with its Node fixture and one Vitest "row descriptor forwarded" table row. The store's central `npcLabel` fill (`fillDisplayFor`) is C9b.
- **Client dock: the minimal branch swap.** `web/static/webclient/js/elosern/exploration_menu.js` `targetMenuFor` replaces its `explore.talk_scripted` and `explore.talk_freeform` branches with one `explore.talk_open` branch. The row is `talk-open`, with payload `{npc_id}` and `commandDisplay.npcLabel`. This is the only client source change beyond the protocol mirror and the echo resolver. Decision (design D6): C9a alone leaves the client working. After C9a, 交談 in the verb popover dispatches `explore.talk_open` and the conversation continues in the dialogue variant of the message window (C6b/C6c), with its choices and its free row. What C9a leaves behind is dead but harmless client code (`keywordMenuFor`, `scriptedAffordanceFor`, the `exploration.keywords` source, the `openKeywords` and `freeform` branches of `handleExplorationItem`, the `nav` pane kind), and the verb popover stays open over the conversation until C9b adds the reset.
- **Tests.**
  - Server: adapter, validator, registry pin, session writer, presenter (v3 shape, one 交談 per host, no keywords), allowlist and lockstep pins, parity contract.
  - Node: protocol, the `targetMenuFor` talk row, and the command echo.
  - Vitest: only what the wire change and the branch swap turn red: the v3 protocol fixtures, the `exploration.target` resolver cases, the dialogue tests that opened a conversation through the keyword frame, the declarative-frames room-change case, and the echo table row. The v3 fixtures of the Storybook stories that go through `store.receive` also follow, because those stories throw on a rejected panel.
  - Browser: the dialogue, nav, input-narrative, state, and tiles journeys that walked 交談 → keyword frame or 自由交談 are re-pointed so 交談 dispatches `explore.talk_open` and the conversation continues in the dialogue variant. The fixed-column nav-pane journey, whose only frame was the keyword frame, moves to the combat skill frame.
- No component is added or deleted.

Out of scope:
- The client dock cleanup, the dock reset on entering dialogue (C9b D1), the `nav` and orphan `affordance` pane deletion, the store's `npcLabel` fill, the dock-only stories, the new one-step keyboard journey, and the dock-root exploration-menu, contextual-hud, and pointer-activation deltas: `webclient-talk-open-dock` (C9b).
- The dialogue stage layout (both portraits, dimming, the collapsed command panel, choices after the last page, `↦ 移動…`): C10b (`webclient-dialogue-stage-actors`) and C10c (`webclient-dialogue-choices-overlay`).
- The text `talk <npc>` command is unchanged: it still greets without opening a session (design D5).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-exploration-menu`:
  - REMOVED "The exploration panel is an exact read-only version-2 presentation panel".
  - ADDED "The exploration panel is an exact read-only version-3 presentation panel".
  - MODIFIED "Exploration affordances are server-authored, never inferred from prose": one 交談 `explore.talk_open` per conversable host.
  - ADDED "explore.talk_open opens a conversation with the host's greeting".
  - The dock requirement ("The exploration dock is keyboard-first and roots at the scene overview", C8b's text) is replaced by C9b.
- `webclient-dialogue-session`: MODIFIED "The dialogue session is deterministic-core-only character state". The writer list gains the `explore.talk_open` success path.
- `webclient-action-dispatch`: MODIFIED "Action registries are allowlisted and duplicate-safe". Fourteen exploration adapters.
- `exploration-affordances`: MODIFIED "The canonical affordance vocabulary is shared and read-only". The allowlist gains `explore.talk_open`, which the vocabulary never emits, and the exploration panel projects talk as one entry per host.
- `webclient-context-actions`: MODIFIED "The exploration context form enumerates the complete canonical affordance list": the client code lists.

## Impact

- Server source:
  - `world/rules/dialogue.py` (`opens_dialogue`, module docstring writer list), `world/rules/player_messages.py`
  - `web/webclient/actions/exploration_actions.py`, `registry.py` (docstring and registration)
  - `web/webclient/presentation/affordances.py`, `options.py`, `exploration.py`
- Client source:
  - `web/static/webclient/js/elosern/protocol/constants.js`, `protocol/panels/exploration.js`, `protocol/panels/skill_descriptor.js`, `protocol.js` (export list)
  - `web/static/webclient/js/elosern/command_echo.js` (the `explore.talk_open` resolver)
  - `web/static/webclient/js/elosern/exploration_menu.js` (`targetMenuFor` talk branch only)
  - Story fixtures fed through `store.receive`: `web/webclient-app/stories/Core/AppShell.stories.js`, `stories/fixtures/scene_overview.js` (C8a)
- Server tests:
  - `web/webclient/actions/tests/test_exploration_actions/` (new `test_talk_open.py`, `test_validators.py`, `test_dialogue_session_recording.py`)
  - `web/webclient/actions/tests/test_dispatcher/test_registry.py`, `test_dialogue_trigger.py`
  - `web/webclient/presentation/tests/test_exploration_panel/{_support,test_presenter,test_schema,test_navigation_and_byte_stability}.py`
  - `web/webclient/presentation/tests/test_affordances/{test_contract,test_vocabulary}.py`, `test_combat_panel/{test_presenter,test_options_and_validators}.py`
  - `world/rules/tests/test_dialogue.py` (`opens_dialogue`, fallback line)
  - `tests/test_exploration_parity_contract.py`
  - `web/static/webclient/js/tests/command_echo_coverage_manifest.json` (pinned by `web/webclient/actions/tests/test_action_catalog_coverage.py`)
- Node tests: `web/static/webclient/js/tests/{protocol_exploration_a,protocol_exploration_b,protocol_context_actions_a,exploration_menu,hud_dock_menus,command_echo}.test.js`, `protocol_fixtures.js`.
- Vitest (under `web/webclient-app/`): `tests/store/protocol_fixtures.js`, `tests/frame-resolvers.test.js` (the `exploration.target` cases), `tests/{dialogue_store,dialogue_dock}.test.js`, `tests/store/declarative_frames.test.js` (the room-change case), `tests/store/command_echo_surfaces.test.js` (one row).
- Browser: `web/tests/browser/_journey_support.py`, `browser_helpers.py`, `test_browser_exploration_{dialogue,nav,state,tiles}.py`, `test_browser_input_narrative.py`, `test_browser_combat_skills.py`.
- Spec traceability: the panel requirement ID moves from version-2 to version-3 (8 annotations in `test_presenter.py`). The C8b exploration-dock ID stays until C9b.
- Dependencies: archive order C8c (`webclient-retire-exploration-submenus`) → C9a (this change) → C9b (`webclient-talk-open-dock`) → C10a (`dialogue-panel-host-portrait`).
