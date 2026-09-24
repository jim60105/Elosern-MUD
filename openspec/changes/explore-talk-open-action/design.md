## Context

See proposal.md (Why). The state below was checked in code, assuming C1 to C8c are archived.

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
  - `classifyPane` returns `nav` only for `kw-*` rows, rows that are all `explore.look`, or `target-*` navigation cells. After C8c, only the keyword frame still produces one of these.

## Goals / Non-Goals

**Goals:**
- 交談 on any conversable host enters the dialogue variant with one dispatch. The line is the host's greeting or the fixed fallback, and the choices and free row are already available.
- The exploration panel offers one 交談 per host, so keyword choice and free-form speech happen only inside the dialogue.
- The keyword frame, the popover freeform borrow, and the `nav` pane that only the keyword frame fed are deleted.

**Non-Goals:**
- The dialogue stage layout, the dock collapse in dialogue mode, and paging the dialogue line (C10).
- Changes to the `context_actions` form, suggestion cards, or AI proposals. They keep the per-keyword and freeform entries.
- Changes to typed `talk`.
- The `affordance` pane of `DockMenu`, which has had no producer since C8b (reported for C8c).

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
- Its only consumer was `keywordMenuFor` and the `exploration.keywords` frame, which this change deletes.
- The dialogue panel's `choices` come from `_scripted_keyword_descriptors(npc)`, not from the exploration panel.
- Keeping the field would ship up to 16 unused descriptors per host, and it would keep the validator rule "keywords require a talk_scripted affordance", which no longer has a subject.

The client mirror deletes `validateExplorationKeyword`, the keywords branch, and `EXPLORATION_MAX_SCRIPTED_KEYWORDS` / `EXPLORATION_MAX_KEYWORD_ID` / `EXPLORATION_MAX_KEYWORD_LABEL`. The three matching pairs leave `tests/test_exploration_parity_contract.py`, because the Python constants still bound the vocabulary and the dialogue panel, which have their own mirrors. There is no compatibility window: server and client ship together.

`ACTION_IDS` in `exploration.py` becomes `tuple(code for code in ACTION_CODE_ALLOWLIST if code not in ("explore.talk_scripted", "explore.talk_freeform"))`, still derived from the shared list. A v3 target carrying either code is therefore a protocol error. JS `EXPLORATION_ACTION_IDS` becomes `talk_open`, `party_invite`, `party_leave`, `engage`, `possess`, `possess_release`, `deliver`.

`_interact_targets` builds 交談 before the vocabulary rows, in the same position as v2:
- If `opens_dialogue(obj)`: an enabled 交談, or a disabled one with the possession reason when `is_possessed_actor(actor)`. This matches how the vocabulary's own talk entries gate.
- Otherwise, if `is_dialogue_host(obj)`: a disabled 交談 with `_DIALOGUE_UNAVAILABLE_REASON`.

The row loop drops `explore.talk_freeform` from its accepted codes. An `LLMNPC` that is also a companion therefore shows 交談, 解散, and 附身, where it used to show 自由交談.

### D5. Typed `talk` is unchanged; the echo is `talk <NPC>`
The command-line catalog prefers "the canonical typed command". `talk <npc>` is the typed command that presents the same greeting, so the resolver returns `join(["talk", npcLabel])`, or `null` without a label. `fillDisplayFor` adds `explore.talk_open` to its `npcLabel` family. The dock row also carries `commandDisplay.npcLabel`.

The line heads the conversation's response. C6a's dispatch mark would start a response even for a silent action, so the echo is chosen for the log's readability ("what did I do"), not for segmentation.

The typed command keeps its greet-without-session behaviour. Making it open a session would change Telnet behaviour with no Telnet surface to show a session, and no exploration spec requires Telnet parity for dialogue (only `webclient-combat-menu` does, for combat).

### D6. The dock returns to the overview when a conversation opens
Without a new rule, the verb popover stays open after a successful `talk_open`: dialogue mode keeps the exploration form, and the target is still present. `settleFrameStack` records `ctx.lastMode`. When the committed mode changes from `exploration` to `dialogue` and `router.depth() > 1`, it resets to `EXPLORATION_ROOT_DESCRIPTOR` inside the `inStackMutation` window, reusing C8b's room-change reset path. The first settle and every other transition never reset.

The rule covers any opener: dock, typed `talk X kw`, or a suggestion card. It is the dock-side half of "交談 enters the dialogue immediately". C10 then collapses the command panel in dialogue mode.

### D7. Client deletions
- `exploration_menu.js`:
  - Delete `keywordMenuFor` and `scriptedAffordanceFor`, and both exports.
  - `targetMenuFor` maps `explore.talk_open` to `{key: "talk-open", label: affordance.label || "交談", actionId: enabled ? "explore.talk_open" : null, payload: enabled ? {npc_id: target.identity} : null, commandDisplay: {npcLabel: target.display_name}, description / disabledReason as the other rows}`.
  - The header comment drops "scripted keyword buttons, free-form dialogue".
- `frame-resolvers.js`: delete `exploration.keywords`. It becomes an unregistered source, so a stray push pops, as in C8c D2.
- `interaction.js`: delete the `openKeywords` and `freeform` branches, and update the `borrowDialogueCommand` comment, which names the deleted 互動 → 自由對話 row.
- `dock-panes.js`: `classifyPane` loses the `nav` kind (the `kw-*`, all-look, and `target-*` clauses) and the `explore.talk_freeform` clause of the affordance test.
- `DockMenu.vue`: loses the nav template, `dock-menu__nav*` CSS, and the `nav` `sizeFn` branch.
- `dialogue-view.js`: its comment stops citing `keywordMenuFor`.

### D8. Spec strategy
- The panel requirement's title names the version, so it is REMOVED and ADDED (version-3), with 8 annotations in `test_presenter.py` re-anchored.
- C8b's dock requirement has a scenario, "交談 keeps the scripted keyword frame", that becomes false, and a MODIFIED block cannot drop it. That requirement is also REMOVED and ADDED ("The keyboard-first exploration dock roots at the scene overview and opens dialogue directly"), and every annotation C8b and C8c anchored to it is re-anchored.
- Every other block is MODIFIED with all scenario titles kept:
  - "Exploration affordances are server-authored" keeps "A scripted host exposes its authored keywords" and "A generative NPC offers free-form talk", with bodies that now say where the keywords and speech are offered.
  - The contextual-hud and pointer-activation blocks are written on C8c's text.
  - The dialogue-session, action-dispatch, exploration-affordances, and context-actions blocks are written on the main specs. No series change modifies them.
- At sync, the `webclient-exploration-menu` Purpose paragraph is edited from "version-2 … thirteen exact allowlisted exploration adapters" to "version-3 … fourteen".

## Risks / Trade-offs

- [A suggestion card still offers `talk <NPC> <話題>` from the exploration root] → Intended. Cards are direct actions from the suggestions frame, and design §8.1 removes only the target-level keyword rows. A card opens the conversation through `talk_scripted`, and D6 returns the dock to the overview.
- [Opening a conversation no longer refreshes suggestions] → Accepted (D1). The first choice or speech triggers generation as today.
- [A host whose schedule blocks talk still shows an enabled 交談] → Same as v2's `talk_scripted` row: the presenter never checks the schedule gate, and the adapter rejects with the schedule reason. Pinned by a test.
- [Browser journeys already rewritten by C8b and C6c are edited again] → The edits only replace the 交談 → keyword or 自由交談 steps with 交談 → dialogue pick or free row. Section 6 of tasks.md lists the files from `git grep`.
- [An LLM-only host opens with the fallback line and zero choices] → Intended: the dialogue offers the free row and the exit row. C10 lays them out.

## Migration Plan

None: the client is unreleased and the server and client ship together.

Archive order: **C8a → C8b (`webclient-scene-overview-swap`) → C8c (`webclient-retire-exploration-submenus`) → C9 (this change) → C10 (`webclient-dialogue-stage`)**.
- The dock requirement this change removes and restates is C8b's.
- The contextual-hud and pointer-activation blocks are written on C8c's text.
- If C8c is amended to retire the `affordance` pane, this change's pointer-activation block must be rebased on that text.
