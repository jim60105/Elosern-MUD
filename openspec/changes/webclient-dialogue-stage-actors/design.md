## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C9 and C10a (`dialogue-panel-host-portrait`) are archived.

- **Stage anchors** (C4a D1/D4, C4b, C4c):
  - `HudFrame.vue` renders `.stage-band` (a two-column grid, `minmax(0, 2fr) minmax(0, 1fr)`) with `[data-anchor="band-message"]` and `[data-anchor="band-command"]`.
  - The portrait anchors `[data-anchor="actor-left"]` / `[data-anchor="actor-right"]` are `bottom: var(--band-h)`, `height: min(62vh, 680px, calc(100% - var(--header-h) - var(--band-h)))`, `aspect-ratio: 2 / 3`, `pointer-events: none`, z-index 2, and inset 6%.
  - `AppClient.vue` renders `<ReferenceArtwork :portrait="currentPortrait">` in `#actor-left` (`currentPortrait` = `store.view.rosterCharacters.find(c => c.current)?.portrait`); `actor-right` is empty.
  - Creation mode switches the band to one column and hides `band-message`.
- **`ReferenceArtwork.vue`** renders the image with `faceObjectPosition(portrait.face_rect)`, or a placeholder whose glyph is `placeholder.label.slice(0, 1)` and whose label defaults to `肖像生成中`. It is also used in `HudDrawer`'s `#art` slot (`AppClient.vue` line 322), so it stays.
- **Portrait data** (C10a):
  - `dialogueViewModel(panel).host.portraitRef` is the art catalog key or `null`.
  - The `art` panel's `portrait_catalog` entries carry `url`, `face_rect`, `alt`, `placeholder` (`{kind, label}` or null), and `context`.
  - `components/party-helpers.js` `portraitFor` drops url-less entries, so it cannot feed a placeholder card, and the stage needs the raw entry.
- **`MessageWindow.vue`** (C6b D6, C6c, C7):
  - While `mode === "dialogue"` and the view model exists, `data-variant="dialogue"` renders, unpaged and untyped, in the text area's scroll region: the residual response blocks, the `.dlg` box (`.av` avatar, `.who` / `.who-bond` / `.say`), and the `.choices` rows (`dialogue-pick`, `dialogue-freeform`, `dialogue-exit`).
  - The page surface `message-page` is focusable in the paged variant.
- **`AppShell.vue`** (current code plus C5 and C6c):
  - `restoreDockFocus()` focuses `#action-dock`. It is exposed, and it is called by `releaseCommandField`, by the mode watcher's pre-flush rescue (`HIDDEN_BY_MODE`, dialogue `""`), and by `composables/use-dock.js` `onNavigateHome`.
  - C5 routes Escape, `sent`, and the borrow's `drawerCloseRequest` into `releaseCommandField(true)`.
- **Keyboard**:
  - `bridge.js` `onDocumentKeydown` sends every non-editable, non-modified key to `store.focusPress`.
  - `stores/elosern/interaction.js` `focusPress` claims digits `1`–`9` (C8c), first through the caption retarget `handleCaptionDialoguePick` while `captionDialoguePresented()`, and passes every other key to `ctx.router.press`.
  - C9 D6 resets the router to the overview when the mode turns `dialogue`.
- **Dispatch**:
  - `stores/elosern/transport.js` `dispatchAction` stores `ctx.inFlight = { requestId, actionId, presentationRevision, handledResult }`, which is cleared once the result is handled and the declared revision is accepted, or on rejection.
  - `view.js` publishes `dispatch.inFlight` without `actionId`.
  - `_talk_freeform_adapter` returns a deferred that settles after the LLM reply, so the in-flight record spans the whole wait.

## Goals / Non-Goals

**Goals:**
- Both portraits stand on the stage in dialogue, with a truthful host source and a static speaking state.
- The command region collapses in dialogue, the message window spans the band, and a name plate names the host.
- Focus never lands on the hidden dock or the body, and no key drives the hidden router.

**Non-Goals:**
- Paging or typing the dialogue line, the choices over the stage, `↦ 移動…`, and the borrow and phase-gap work (C10c). The dialogue variant keeps its rows in the window here.
- Motion of any kind (C11). Combat `actor-right` (C13).

## Decisions

### D1. `StageActor` wraps `ReferenceArtwork`
`components/StageActor.vue`:
- Props: `portrait` (Object|null), `name` (String), `side` (`"left"` | `"right"`), and `dimmed` (Boolean).
- Root: `<div class="stage-actor" data-testid="stage-actor" :data-side="side" :data-speaking="String(!dimmed)">`, holding `<ReferenceArtwork :portrait="shown" />`.
- `shown` is `portrait` when it is non-null. Otherwise it is `{ placeholder: { kind: "missing", label: name } }` when `name` is set, so `ReferenceArtwork` draws the name's first grapheme and the name. With neither, it is `null`, so `ReferenceArtwork` shows its default `肖像生成中`.
- `ReferenceArtwork`'s glyph uses `label.slice(0, 1)`. For a surrogate-pair initial that splits the character, so `ReferenceArtwork` switches to `portraitGlyph(label)` (`components/character-identity.js`). This is the only edit to it.
- Dim: `.stage-actor[data-speaking="false"] { filter: brightness(var(--actor-dim)); }`, with `--actor-dim: 0.6` in `styles/tokens.css`. There is no transition property; C11 adds the motion token.
- `actor-left`'s `.reference-artwork { height: 100% }` rule moves to `.stage-actor` and its child, so both anchors share it. `actor-right` mirrors the horizontal mask.

*Why wrap, not replace:* the drawer's art slot needs a plain portrait frame with no side or speaking state, and the design's "Becomes `StageActor`" is met by the stage using only `StageActor`.

*Why `dimmed` and not `speaking`:* outside dialogue nothing is dimmed, and "not speaking" is not meaningful there. `AppClient` computes `dimmed` from the mode and the speaker.

### D2. Host source: the raw catalog entry by the committed key
`AppClient.vue` adds `hostPortrait = computed(() => { const ref = dialogueVm.value?.host.portraitRef; return ref == null ? null : (panel('art')?.portrait_catalog?.[ref] ?? null); })`. It uses the raw entry, not `portraitFor`, so a pending entry shows its own placeholder card (design §12, "truthful placeholder"). A missing entry falls to D1's name placeholder. `actor-right` renders `<StageActor v-if="store.view.mode === 'dialogue' && dialogueVm" side="right" :portrait="hostPortrait" :name="dialogueVm.host.displayName" :dimmed="store.view.dialogueSpeaker === 'player'" />`. `dialogueVm` is the same `dialogueViewModel(panel('dialogue'))` the window receives, computed once in `AppClient`.

### D3. `dialogueSpeaker` from the in-flight action
`view.js` publishes `dialogueSpeaker: ctx.inFlight && DIALOGUE_SPEECH_ACTIONS.has(ctx.inFlight.actionId) ? "player" : "host"`, with `DIALOGUE_SPEECH_ACTIONS = new Set(["explore.talk_scripted", "explore.talk_freeform"])`. `publishView` already runs on dispatch, on result, on revision acceptance, and on rejection, which are exactly the moments `inFlight` changes.

Why this matches "lit until the reply commits":
- The reply is the dialogue panel committed at the declared revision.
- `inFlight` is cleared only after that revision is accepted.
- The freeform deferred keeps the request open through the LLM call.

A `dialogue_leave` or a move is not speech, so the host stays lit and the stage clears on the mode change. The value is derived, never stored, so a reconnect (which clears `inFlight`) lands on `"host"`.

*Alternative:* a timer or a "line changed" watcher. Rejected. A scripted reply can repeat the same line, and a timer guesses.

### D4. Collapse by mode CSS; the dock stays mounted
In `HudFrame.vue`:
- `[data-elosern-mode="dialogue"] .stage-band { grid-template-columns: minmax(0, 1fr); }`
- `[data-elosern-mode="dialogue"] [data-anchor="band-command"] { display: none; }`

This is the mode-gating mechanism C4a already uses for creation. `#action-dock` stays in the DOM, so the "never remounted" rule holds, and C9 D6 has already reset its router to the overview.

In `AppShell.vue`:
- `HIDDEN_BY_MODE.dialogue = "[data-anchor='band-command']"`.
- The `command-line` anchor keeps `right: 33.3333%` in every mode. The row therefore stops at the old two-thirds line and never covers the host portrait. The spec's geometry wording changes from "the message region's right edge" to "the right edge of the band's left two thirds".

*Alternative:* `v-if` on the dock in dialogue. Rejected: it remounts `#action-dock`, loses the router's focus bookkeeping, and breaks the persistence scenario.

### D5. Focus home
`AppShell.vue` renames `restoreDockFocus()` to `restoreFocusHome()`:
- In dialogue mode (`props.mode === "dialogue"`) it calls `messageWindow.value?.focusHome()`.
- Otherwise it focuses `#action-dock`.

The exposed API and `use-dock.js` `onNavigateHome` follow the rename. `MessageWindow` exposes `focusHome()`:
- while the dialogue variant renders, it focuses its first row (`dialogue-pick`, else `dialogue-freeform`, else `dialogue-exit`)
- otherwise it focuses the page surface (`message-page`)
- both with `preventScroll`

The mode watcher's two phases:
- **Entering dialogue (pre-flush).** If focus is inside `band-command`, focus `message-page`, which is visible in both modes, before the attribute hides the dock. This avoids the browser's blur to body. Then, after `nextTick` (the variant is rendered), call `restoreFocusHome()`.
- **Leaving dialogue (post-flush).** Focus inside `band-message` is on a row that is about to disappear, and the body may already hold it. In a `nextTick` after the flush, if `document.activeElement` is the body or inside `band-message`, call `restoreFocusHome()`, which now focuses the rendered dock.

The command line's collapse paths (C5 D2) already end in `releaseCommandField(true)`, which now calls `restoreFocusHome()`. Escape and an accepted send in dialogue therefore land on the window.

### D6. The router is inert in dialogue
`focusPress(key, repeat)` starts with `const dialogueMode = ctx.reducer.getState().mode === "dialogue"`. When it is true:
- Digits run the existing caption retarget only.
- `/` goes to `ctx.router.press` (the router's `SLASH` → `toggle-drawer` → `drawerRequest` path).
- Every other key returns `false`.

Unclaimed keys reach the text path exactly as today, and a focused dialogue button keeps its native Enter (the bridge already skips Enter on buttons) and Space.

*Why in the store, not the bridge:* `focusPress` is the one entry point that already knows the dialogue retarget, and the bridge's claim is the return value. Nothing else changes.

### D7. The name plate
`MessageWindow` renders, while the dialogue variant is active:

```
<div class="message-window__plate" data-testid="message-name-plate">{{ vm.host.displayName }}<span v-if="vm.bondStage != null" class="message-window__plate-bond" data-testid="dialogue-bond">  ·  羈絆 {{ vm.bondStage }}</span></div>
```

It is placed as the first flex child of the window, above the text area, 30px tall, in the gold display face with the gold hairline border of the reference's `.who` treatment. The `.dlg` box loses `.av`, `.who`, and their CSS, and keeps `.say` (testid `dialogue-say`). The testid `dialogue-who` is deleted, and tests read `message-name-plate`.

*Why inside the window, not straddling its top edge:* a plate that straddles the border would sit in the stage strip that the expanded command-line row occupies, and would be covered while the player types a freeform line. Inside the window, the text area loses 30px in dialogue. The variant scrolls in C10b, and C10c's paging measures the text area's box through the ResizeObserver (C6b D2), so no constant changes.

Width: the window spans 1920px, but the page text keeps its `max-width: 42em` cap (C6b D1), so the measure stays ≤ 42 characters. The text column stays left-aligned under the plate, as in design §8.2's sketch.

### D8. Tests
- **Vitest.**
  - `tests/core/stage_actor.test.js`: image, pending placeholder, missing entry with a name, `portraitGlyph` initial for an astral-plane character, the `data-speaking` / dim class, and no focusable element.
  - `tests/hud_frame.test.js`: the dialogue band has one column and `band-command` is hidden.
  - `tests/app.test.js`:
    - the host actor renders only in dialogue with the catalog entry from the committed key
    - `dimmed` follows `dialogueSpeaker`
    - `#action-dock` is the same element across exploration → dialogue → exploration
    - focus lands on the first pick when entering dialogue, and on the dock when leaving it
  - `tests/message_window_dialogue.test.js`: the plate text with and without a bond stage, no `.av` / `dialogue-who`, and `focusHome()`.
  - `tests/dialogue_dock.test.js`: rewritten as "the command region collapses in dialogue mode". It asserts `focusPress` returns `false` for arrows, Enter, and Escape in dialogue, and that the router depth and focus are unchanged.
  - `tests/dialogue_store.test.js`: `dialogueSpeaker` through dispatch, result, revision, and rejection.
  - `tests/store/digit_row_picks.test.js`: dialogue digits still retarget.
- **Browser** (`web/tests/browser`):
  - `test_browser_exploration_dialogue.py` at 1920x1080:
    - After 交談, `[data-anchor="band-command"]` is hidden, the message region is 1920px (±1) wide at 300px, `actor-right` holds `stage-actor[data-side="right"]`, the host's `data-speaking="true"`, and the player's is `"false"`.
    - After a pick is sent, the player is lit until the reply commits (poll `data-speaking`).
    - Escape from `/` returns focus to the first pick.
    - After 結束對話, the dock is visible at the overview and focused.
  - `test_browser_contextual_hud_stage.py`: the band-height and split scenarios gain the dialogue state.
  - `test_browser_contextual_hud_anchors.py`: `actor-right` geometry in dialogue.
  - `test_browser_layout.py`: the required-surface list excludes `#action-dock` in dialogue.

### D9. Spec strategy, traceability, and archive order
Each MODIFIED block is written on the latest series text, keeping every scenario title:

| Requirement | Written on |
|---|---|
| contextual-hud "The WebClient renders a full-bleed cinematic stage…" | C8b `webclient-scene-overview-swap` |
| contextual-hud "Surface visibility is gated by the committed game mode" | C6c `webclient-message-window-swap` |
| contextual-hud "The action dock fills the band's command region at a fixed size" | C8b |
| contextual-hud "The dock's shortcut legend…" | C8c `webclient-retire-exploration-submenus` |
| contextual-hud "The feed presents the dialogue variant from the committed panel" | C6c |
| contextual-hud "The message window presents the current response one page at a time…" | C7 `webclient-typewriter-reading-prefs` |
| contextual-hud "The command line is a collapsible row docked on the message region's top edge" | C5 `webclient-collapsible-command-line` (ADDED there) |
| exploration-menu "The keyboard-first exploration dock roots at the scene overview and opens dialogue directly" | C9 `explore-talk-open-action` (ADDED there) |
| desktop-shell "Required desktop surfaces remain visible and usable", "Keyboard routing is menu-first and submission-safe" | C8b |
| component-showcase "Every required UI component…" | C8a `webclient-scene-overview-component` |

- "The dock keeps its regular exploration form in dialogue mode" is REMOVED. The design names it as replaced, and its "The dock stays usable during a conversation" scenario cannot survive. Its one annotation (`test_node_suite_evidence.py::test_dialogue_dock_vitest_evidence_passes`) re-anchors to the new collapse requirement.
- The two new IDs are covered by `test_node_suite_evidence.py` evidence tests (dialogue dock and stage actor) and by `test_browser_exploration_dialogue.py`.
- The desktop-shell required-surface block drops "bounded caption", as the C6 coordinator note asks. The browser-verification "bounded caption" text is restated in C10c.
- `openspec validate` reports that archive would refuse blocks whose base is an unarchived series change. That is expected.

**Archive order: C9 (`explore-talk-open-action`) → C10a (`dialogue-panel-host-portrait`) → C10b (this change) → C10c (`webclient-dialogue-choices-overlay`).** C10c modifies this change's legend, dialogue-variant (removed there), message-window, and collapse texts. If any base block changes before archive, re-sync this change's block, keeping only its own edits.

## Risks / Trade-offs

- [The browser blurs a focused element that becomes `display:none` before the rescue runs] → D5's pre-flush rescue moves focus to the always-visible page surface before the attribute flips. A browser test asserts `document.activeElement` is never `body` across the transition.
- [The 42em cap leaves the right part of the 1920px window empty] → Intended. The ≤ 42 measure is a design goal (§3). The NPC portrait stands above that empty area.
- [The plate reduces dialogue page capacity by one line at 1080] → Accepted (D7). Dialogue lines are short, and paging measures the real box.
- [Budget] → StageActor, story, and tests (1.5h); wiring and speaker (0.5h); collapse, focus home, and router gate (1.5h); plate (1h); Vitest (1.5h); browser (1.5h); specs and gates (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing new is persisted.
