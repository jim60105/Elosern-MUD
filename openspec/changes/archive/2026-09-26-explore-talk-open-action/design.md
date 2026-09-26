## Context

See proposal.md (Why). The state below was checked in code, assuming C1 to C8c are archived. C9 was split along the server/client seam: this change (C9a) owns the server action, the v3 wire contract with its client mirror, and the one dock branch that must follow the wire; `webclient-talk-open-dock` (C9b) owns the client dock cleanup that the wire change leaves dead.

- **Server talk paths** (`web/webclient/actions/exploration_actions.py`):
  - `_talk_scripted_adapter` rejects in this order:
    - `REASON_POSSESSED_TALK` (a possessed actor)
    - `no_npc` / 這裡沒有這個對象。 (`_resolve_npc` misses)
    - `schedule_blocked` (`interaction_reason(npc, "talk")`)
    - `not_dialogue_host` / 對方無法交談。
    - `unregistered_keyword`, `dialogue_failed`, `no_response`

    Its success path calls `open_or_refresh_dialogue(actor, npc, response)`, sends `{npc.key}說：{response}` through `actor.msg`, and returns `_success("talked", …, AFFECTED_FULL)`. With `affected_panels=()`, the dispatcher publishes one full snapshot at a newer revision, and that snapshot carries mode `dialogue` together with the `dialogue` panel.
  - `_talk_freeform_adapter` resolves `LLMNPC` only (`no_npc` / 這裡沒有可以自由交談的對象。).
  - `dispatcher.py` `_DIALOGUE_TRIGGER_ACTION_IDS` schedules action-options (LLM) generation after `talk_scripted` and `talk_freeform`.
- **`world/rules/dialogue.py`**:
  - `is_dialogue_host(npc)` means a `ScriptedDialogue` component. `greeting_for(npc)` returns the authored greeting or `None`.
  - The session helpers (`open_or_refresh_dialogue`, `clear_dialogue_session`, `live_dialogue_session`) are the only writers of `db.dialogue_session`. `open_or_refresh_dialogue` only reads the clock.
  - The text `talk <npc>` command (`commands/talk.py`) greets without a keyword and deliberately does not open a session.
- **Shared vocabulary** (`web/webclient/presentation/affordances.py`):
  - `ACTION_CODE_ALLOWLIST` holds eleven codes. It gates three things: the `context_actions` affordance validator (`combat_panel.py`), suggestion cards (`options.py`), and the exploration panel's `ACTION_IDS` (`exploration.py`), which aliases it.
  - `_target_affordance_entries` emits one `talk_scripted` entry per authored keyword and one `talk_freeform` entry per `LLMNPC`. The `context_actions` form, `suggestible_candidates`, `default_cards`, and the AI situation (`server/option_proposal_service/situation.py`) consume these entries.
- **Exploration panel v2** (`web/webclient/presentation/exploration.py` `_interact_targets`):
  - Before the vocabulary rows, it emits one `explore.talk_scripted` 交談 per `ScriptedDialogue` host. It is enabled with a target-level `keywords` list, or disabled with `dialogue_unavailable` when the table does not resolve.
  - Then it emits `talk_freeform` (自由交談), `deliver`, party, `engage`, `possess`, and the navigate entries.
  - The `dialogue` presenter builds `choices` from `_scripted_keyword_descriptors(npc)` directly, never from the exploration panel.
- **Client** (after C8c):
  - `verbMenuFor` delegates to `targetMenuFor`. That function's `talk_scripted` branch sets `openKeywords`, which makes `handleExplorationItem` push `exploration.keywords` (`keywordMenuFor` rows `kw-*`, frame `gridCols = 1`). Its `talk_freeform` branch sets `freeform`, which makes `handleExplorationItem` set `ctx.freeformTarget` and bump `drawerRequest`.
  - The dialogue variant's free row uses `borrowDialogueCommand`, a separate entry that also sets `freeformTarget`.
  - `sendText` reads the NPC label from `panel.interact`, which still lists every host.
  - `classifyPane` returns `nav` only for `kw-*` rows, rows that are all `explore.look`, or `target-*` navigation cells. After C8c, only the keyword frame still produces one of these. The `affordance` kind (rows carrying `explore.engage`, `explore.party_invite`, or `explore.talk_freeform`) has had no producer since C8b moved target menus into `DockVerbPopover`.

## Goals / Non-Goals

**Goals:**
- 交談 on any conversable host enters the dialogue variant with one dispatch. The line is the host's greeting or the fixed fallback, and the choices and free row are already available.
- The exploration panel offers one 交談 per host, so keyword choice and free-form speech happen only inside the dialogue.
- The server and the client validator agree on panel version 3 in the same change, and the dock keeps a working 交談 row.

**Non-Goals:**
- Deleting the client code the wire change leaves dead (the keyword frame, the popover freeform borrow, the `nav` pane), the orphan `affordance` pane, and the dock reset when a conversation opens: C9b (`webclient-talk-open-dock`).
- The dialogue stage layout, the dock collapse in dialogue mode, and paging the dialogue line (C10b, C10c).
- Changes to the `context_actions` form, suggestion cards, or AI proposals. They keep the per-keyword and freeform entries.
- Changes to typed `talk`.

## Decisions

### D1. The adapter mirrors `talk_scripted`'s gates and adds one host predicate
The new helper in `world/rules/dialogue.py` is:

```python
def opens_dialogue(npc) -> bool:
    # LLMNPC, or a ScriptedDialogue host whose DIALOGUE_TABLE entry resolves
```

It uses a lazy `typeclasses.npcs` import, the `live_dialogue_session` precedent. `_talk_open_adapter(actor, payload, session=None)`:
1. Rejects a possessed actor with `REASON_POSSESSED_TALK`.
2. Resolves `npc = _resolve_npc(actor, npc_id)`. When it is `None`, rejects with `no_npc` / 這裡沒有這個對象。.
3. Rejects `interaction_reason(npc, "talk")` with `schedule_blocked` and that reason.
4. Rejects `not opens_dialogue(npc)` with `not_dialogue_host` / 對方無法交談。.
5. Computes `line = greeting_for(npc)`. When it is `None`, the line is `dialogue_open_fallback_line(npc.key)`.
6. Calls `open_or_refresh_dialogue(actor, npc, line)`.
7. Sends the narrative message `{npc.key}說：{greeting}` for a greeting, or the fallback line as-is.
8. Returns `_success("dialogue_opened", message, AFFECTED_FULL)`.

The adapter calls no `run_scripted_talk`, so there is no affinity gain. It calls no `at_talked_to`, so there is no LLM call and no memory write. It makes no clock call apart from the session helper's read-only `read_world_clock`.

`_talk_open_adapter` is not added to `_DIALOGUE_TRIGGER_ACTION_IDS`: scheduling action-options generation would be an LLM request caused by the action. The existing suggestions stay committed until the first choice or speech, and that trigger still fires.

*Why a new predicate instead of `is_dialogue_host`:* design §8.1 counts an `LLMNPC` as a dialogue host, and `is_dialogue_host` is component-only. A component host whose table does not resolve has no choices and no greeting. v2 already shows it as a disabled 交談 (`dialogue_unavailable`), and opening an empty conversation would be a dead end. Using one predicate for the adapter and the presenter keeps the render and the commit identical.

*Why `no_npc` covers a non-NPC identity:* `_resolve_npc` already treats "not a present NPC" as missing, exactly as `talk_scripted` does.

### D2. The allowlist gains the code, and the vocabulary stays per-keyword
`explore.talk_open` joins `ACTION_CODE_ALLOWLIST` (design §8.1). That lets the panel's action-id check derive from the shared list, and it keeps every validator of the shared vocabulary total:
- `options.py` `_ACTION_PAYLOAD_VALIDATORS` registers `validate_talk_open_payload`, so the lockstep test holds.
- `SUGGESTIBLE_ACTION_IDS` subtracts it. A suggestion card is already a direct action, and a card that opens a conversation would duplicate the 交談 row.

`exploration_affordances()` does not emit it. The keyword entries are what the suggestion ladder and the AI proposals choose from (`talk <NPC> <話題>` cards). Replacing them would change the `context_actions` form, the eligible digest, and the AI situation in the same change, and those consumers gain nothing from it. The exploration panel is a projection of the vocabulary, as it already was for talk: v2 merged all keyword entries into one 交談 row. The shared-vocabulary requirement states this projection explicitly.

*Alternative:* keep `talk_open` out of the allowlist and give the panel a private action list. Rejected: design §8.1 names the allowlist, and the current exploration-panel requirement forbids a private duplicate.

### D3. The fallback line
`world/rules/player_messages.py` gains `DIALOGUE_OPEN_FALLBACK_TEMPLATE = "{name}看向你，等你開口。"` and `dialogue_open_fallback_line(name: str) -> str`. The template has no corner brackets: authored greetings are narration that quotes speech inside 「」 (for example the `world/lore/dialogue/` rows), and this line is narration, not speech. `name` is `npc.key`, the name the `talk_scripted` narrative message uses. The `dialogue` panel's name plate shows the composed display name separately. The line is 11 code points plus the name, well inside `MAX_DIALOGUE_SESSION_LINE_CODE_POINTS`.

### D4. Exploration panel version 3 drops `keywords`
`keywords` is deleted from the target descriptor, and the version becomes 3:
- Its only consumer was `keywordMenuFor` and the `exploration.keywords` frame, which this change makes unreachable (D6) and C9b deletes.
- The dialogue panel's `choices` come from `_scripted_keyword_descriptors(npc)`, not from the exploration panel.
- Keeping the field would ship up to 16 unused descriptors per host, and it would keep the validator rule "keywords require a talk_scripted affordance", which no longer has a subject.

The client mirror deletes `validateExplorationKeyword`, the keywords branch, and `EXPLORATION_MAX_SCRIPTED_KEYWORDS` / `EXPLORATION_MAX_KEYWORD_ID` / `EXPLORATION_MAX_KEYWORD_LABEL`. The three matching pairs leave `tests/test_exploration_parity_contract.py`, because the Python constants still bound the vocabulary and the dialogue panel, which have their own mirrors. There is no compatibility window: server and client ship together.

`ACTION_IDS` in `exploration.py` becomes `tuple(code for code in ACTION_CODE_ALLOWLIST if code not in ("explore.talk_scripted", "explore.talk_freeform"))`, still derived from the shared list. A v3 target carrying either code is therefore a protocol error. JS `EXPLORATION_ACTION_IDS` becomes `talk_open`, `party_invite`, `party_leave`, `engage`, `possess`, `possess_release`, `deliver`.

`_interact_targets` builds 交談 before the vocabulary rows, in the same position as v2:
- If `opens_dialogue(obj)`: an enabled 交談, or a disabled one with the possession reason when `is_possessed_actor(actor)`. This matches how the vocabulary's own talk entries gate.
- Otherwise, if `is_dialogue_host(obj)`: a disabled 交談 with `_DIALOGUE_UNAVAILABLE_REASON`.

The row loop drops `explore.talk_freeform` from its accepted codes. An `LLMNPC` that is also a companion therefore shows 交談, 解散, and 附身, where it used to show 自由交談.

### D5. Typed `talk` is unchanged; the echo is `talk <NPC>`
The command-line catalog prefers "the canonical typed command". `talk <npc>` is the typed command that presents the same greeting, so the resolver returns `join(["talk", npcLabel])`, or `null` without a label. The dock row carries `commandDisplay.npcLabel`, so the echo works from the popover without a store fill. The resolver lands here, not in C9b, because registering the action adds it to `command_echo_coverage_manifest.json`, and three gates pin that manifest in lockstep: the Python registry pin (`test_action_catalog_coverage.py`), the Node catalog gate (`command_echo.test.js`), and the Vitest behavioral table (`command_echo_surfaces.test.js`, one row per registered id). C9b adds `explore.talk_open` to `fillDisplayFor`'s `npcLabel` family for dispatch paths that carry no descriptor.

The line heads the conversation's response. C6a's dispatch mark would start a response even for a silent action, so the echo is chosen for the log's readability ("what did I do"), not for segmentation.

The typed command keeps its greet-without-session behaviour. Making it open a session would change Telnet behaviour with no Telnet surface to show a session, and no exploration spec requires Telnet parity for dialogue (only `webclient-combat-menu` does, for combat).

### D6. C9a alone leaves the client working, through one branch swap
The v3 panel carries no `keywords` and no `talk_scripted` / `talk_freeform` target affordance, and the client mirror rejects both. `targetMenuFor` silently drops an affordance whose `action_id` it does not map, so without a change the verb popover would lose 交談 and the dock could no longer open a conversation. The minimal fix is in this change:
- `targetMenuFor` maps `explore.talk_open` to `{key: "talk-open", label: affordance.label || "交談", actionId: enabled ? "explore.talk_open" : null, payload: enabled ? {npc_id: target.identity} : null, commandDisplay: {npcLabel: target.display_name}, description / disabledReason as the other rows}`.
- Its `explore.talk_scripted` and `explore.talk_freeform` branches are deleted in the same edit: those codes can no longer reach it, because the validator rejects a panel that carries them.

Nothing else in the client source changes here. The state after C9a:
- 交談 dispatches `explore.talk_open` through the ordinary action path. The committed `dialogue` panel shows the greeting or fallback line, its choices, and its free row in the dialogue variant of the message window (C6b/C6c). The free row still borrows the command line through `borrowDialogueCommand`.
- `keywordMenuFor`, `scriptedAffordanceFor`, the `exploration.keywords` resolver source, and the `openKeywords` / `freeform` branches of `handleExplorationItem` are unreachable. The `nav` pane kind has no producer, and the `affordance` pane kind already had none since C8b. They are dead but harmless until C9b deletes them.
- The verb popover stays open over the conversation after a successful open, because dialogue mode keeps the exploration form. C9b adds the reset (its D1). Journeys in this change therefore close the popover with Escape, or assert nothing about the dock depth, after opening a conversation.

Alternative: keep `keywords` and the old codes in v3 so the old client path stays alive until C9b. Rejected: it would ship a wire contract that C9b immediately breaks again, and it would keep the validator rule "keywords require a talk_scripted affordance" for one more change.

### D7. Tests follow only what the wire change turns red
The v3 panel is rejected by any fixture still at v2, and the swapped branch turns every journey that walked 交談 → keyword frame or 自由交談 red. This change re-points exactly those:
- Node and Vitest protocol fixtures, and the Storybook fixtures that go through `store.receive` (`AppShell.stories.js` throws on a rejected panel; `stories/fixtures/scene_overview.js` builds the overview from a validated panel).
- Vitest: the `exploration.target` resolver cases (`talk-open` row), the dialogue store and dock tests that opened a conversation through the keyword frame (they now activate the popover's `talk-open` row and commit a `dialogue` panel), and the declarative-frames room-change case that opened a keyword frame (it opens the popover instead).
- Browser: the dialogue, input-narrative, and nav journeys; the state journey's zero-count list; and the tiles journey's fixed-column case, whose only frame was the keyword frame. That case moves to the combat skill frame with its existing assertions (in-pane bounds and the fixed two-column keyboard mapping) and its `webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content` annotation.

Deleting the dead-code tests (keyword cases, nav and affordance pane cases), the dock-reset cases (C9b D1), and the new one-step keyboard journey belong to C9b.

### D8. Spec strategy
- The panel requirement's title names the version, so it is REMOVED and ADDED (version-3), with 8 annotations in `test_presenter.py` re-anchored.
- "Exploration affordances are server-authored" is MODIFIED with all scenario titles kept: "A scripted host exposes its authored keywords" and "A generative NPC offers free-form talk" keep their titles, with bodies that now say where the keywords and speech are offered.
- The dialogue-session, action-dispatch, exploration-affordances, and context-actions blocks are written on the main specs. No series change modifies them.
- At sync, the `webclient-exploration-menu` Purpose paragraph is edited from "version-2 … thirteen exact allowlisted exploration adapters" to "version-3 … fourteen".
- The dock requirement ("The exploration dock is keyboard-first and roots at the scene overview", C8b's text) still describes the keyword frame after this change archives. Its scenario "交談 keeps the scripted keyword frame" is false between C9a and C9b. C9b REMOVES and ADDS it; the two changes archive back to back, so no other change reads the stale text.

## Risks / Trade-offs

- [A suggestion card still offers `talk <NPC> <話題>` from the exploration root] → Intended. Cards are direct actions from the suggestions frame, and design §8.1 removes only the target-level keyword rows. A card opens the conversation through `talk_scripted`, and C9b's reset returns the dock to the overview.
- [Opening a conversation no longer refreshes suggestions] → Accepted (D1). The first choice or speech triggers generation as today.
- [A host whose schedule blocks talk still shows an enabled 交談] → Same as v2's `talk_scripted` row: the presenter never checks the schedule gate, and the adapter rejects with the schedule reason. Pinned by a test.
- [Browser journeys already rewritten by C8b and C6c are edited again] → The edits only replace the 交談 → keyword or 自由交談 steps with 交談 → dialogue pick or free row. Section 6 of tasks.md lists the files from `git grep`.
- [The popover stays open over the conversation until C9b] → Accepted for one change (D6). The popover stays usable beside the dialogue variant, and Escape or its back row closes it. C9b archives immediately after this change.
- [Dead client code survives one change] → Accepted (D6). Nothing reaches it: the validator rejects every payload that could feed the keyword frame or the freeform row.
- [An LLM-only host opens with the fallback line and zero choices] → Intended: the dialogue offers the free row and the exit row. C10c lays them out.

## Migration Plan

None: the client is unreleased and the server and client ship together.

Archive order: **C8a → C8b (`webclient-scene-overview-swap`) → C8c (`webclient-retire-exploration-submenus`) → C9a (this change) → C9b (`webclient-talk-open-dock`) → C10a (`dialogue-panel-host-portrait`)**.
- This change is written on the main specs for every capability it touches, and on C8c's archived client state.
- C9b removes and restates C8b's dock requirement and writes the contextual-hud and pointer-activation blocks on C8c's text, so it must archive after this change.
- C10a adds nothing this change reads, but it keeps its archive slot after C9b.
