## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C9b, C10a, and C10b (`webclient-dialogue-stage-actors`) are archived.

- **`MessageWindow.vue`** (C6b, C6c, C7, C10b):
  - Paged variant:
    - reader state `responseKey` / `pageIndex` / anchor
    - the typing clock `use-typewriter.js` (`typing`, `typed`)
    - the marker (`▼` / `■`, only once the page is complete)
    - the pending-mark flush
    - the focusable page surface `message-page`
    - the live region `message-live`
  - Dialogue variant (C6b D6, trimmed by C10b), rendered while `mode === "dialogue"` and the view model exists:
    - the residual response blocks with the anchored echo suppression
    - the `.dlg` box with `.say`
    - the `.choices` rows emitting `dialogue-pick`, `dialogue-freeform`, and `dialogue-leave`
    - the box pin
  - C10b added the name plate `message-name-plate` and `focusHome()`.
- **`AppShell.vue`** (C5, C6c, C10b) forwards the window's `dialogue-*` emits to `AppClient`:
  - `onDialoguePick` dispatches `explore.talk_scripted` with the pick's payload and `commandDisplay`.
  - The free row calls `store.borrowDialogueCommand` (`stores/elosern/interaction.js`, which sets `ctx.freeformTarget` and bumps `drawerRequest`).
  - The exit dispatches `explore.dialogue_leave`.
  - `restoreFocusHome()` focuses `#action-dock`, or in dialogue `messageWindow.focusHome()`.
  - The mode watcher rescues focus on entering and leaving dialogue.
- **Keyboard** (C10b D6): in dialogue, `focusPress` claims digits through `handleCaptionDialoguePick` / `captionDialoguePresented()`, claims `/` through the router, and leaves every other key unclaimed.
- **Scene overview** (C8a, C8b, C9a, C9b): in dialogue the router's only frame is the overview (C9b D1). `store.view.rootMenu` holds it, with `sections` naming `exits` items. Each exit item carries `actionId: "explore.move"`, a `payload` (with `current_node`), `commandDisplay`, `enabled`, and `disabledReason`. `components/dock-exits.js` (C8a) resolves the direction glyph and the destination display name that `SceneOverview` renders.
- **Command line** (C5):
  - `CommandLine.vue` `submit()` emits `submit`, then clears the field and emits `sent` only when `connected && !mutationsLocked && !inFlight`.
  - `sendText` (`stores/elosern/transport.js`) routes a bound `freeformTarget` to `dispatchAction("explore.talk_freeform", …)`. It bumps `drawerCloseRequest` only when the dispatch returns a request, and then sets `ctx.freeformTarget = null` in every case (line 293).
  - `dispatchAction` refuses when `!connected || mutationsLocked || phase !== "active" || inFlight`.
  - A borrowed send in a non-active phase is therefore cleared from the field, the line collapses, nothing is dispatched, and the borrow is dropped.
- **Stage anchors** (C4a–C4c, C10b): `HudFrame.vue` renders `place`, `vitals`, `map`, `actor-left`, `actor-right`, `.stage-band` (`band-message`, `band-command`), and `command-line`. The islands are at z 4, the portraits at z 2, and the band at z 5.

## Goals / Non-Goals

**Goals:**
- The dialogue line is read page by page with typing, under the name plate, and the choices appear only after it is fully read.
- One choice list over the stage: picks, free speech, move, and leave, keyboard-first and pointer-equivalent.
- The borrowed send is accepted exactly when it is delivered, and a rejected borrowed send is never lost or re-routed as a command.

**Non-Goals:**
- The choices' stagger, the list's fade, and the portraits' motion (C11).
- Any server, protocol, or dialogue-panel change.
- Stripping the `<host>說：` prefix from the narrative line (see D2).

## Decisions

### D1. Delete the dialogue variant; the window pages in every mode
`MessageWindow` loses:
- the `data-variant="dialogue"` branch
- the variant's render function
- the residual-block echo suppression and the box pin
- the three `dialogue-*` emits
- the `.dlg` / `.say` / `.choices` / `.pick*` CSS

`data-variant` always reads `paged`. The window's `dialogue` and `artPanel` props shrink to what the plate needs (`dialogue` for the view model). The plate (C10b D7) stays as the header row. The typing, marker, flush, re-page, and announcement rules (C6b, C7) now apply to the session line with no special case, which is what C7 D9 anticipated.

### D2. The narrative line is paged verbatim
The session line reaches the narrative through the adapters: `{npc}說：{line}` for a greeting or scripted reply, and the fallback line verbatim for `talk_open` (C9a D3). The page shows exactly that. The name plate also names the host, so the name can appear twice.

*Why not strip the prefix:* the stripping was the variant's anchored echo match, a prose-shape rule. The design forbids deriving state from prose, and the page must equal the log (the full log shows the same line). The duplication is accepted, and a later server change could send the reply without the prefix.

*Alternative:* page the panel's `line` instead of the narrative response. Rejected, because it would create a second text source beside the log, break "the log is the single store of text" (design §6.1), and announce the line twice.

### D3. The reading-complete signal
`MessageWindow` computes `readingComplete` as all of the following:
- `ready` (fonts)
- no pending mark
- `pageIndex === pages.length - 1`
- `!typing`

It emits `reading-change` on every flip. It is purely reader state, never prose.

`AppShell` forwards it, and `AppClient` keeps `readingComplete` as a ref. On mount (the reconnect rule, which shows the last page complete) it starts `true`, so a reconnect inside a conversation shows the choices immediately.

### D4. Visibility rule for the list
`AppClient`: `choicesShown = mode === "dialogue" && dialogueVm && readingComplete && store.view.dispatch.inFlight == null`.

- **The in-flight clause.** A pick marks a pending response, and C7 then shows the previous response's last page fully shown until the reply's first line arrives. Without the clause, the list would reappear during that wait and invite a second pick that would be suppressed anyway.
- **Freeform speech.** The deferred holds `inFlight` until the LLM reply, so the list stays away exactly while the player "is speaking" (C10b's speaker rule).

### D5. `DialogueChoices` component
- **Props:**
  - `picks` (the view model's pick rows)
  - `host` (`{identity, displayName}`)
  - `exits` (overview exit items)
  - `localMap` (for destination names through `dock-exits.js`)
  - `locked` (in flight or awaiting a revision)
- **Local state:** `view` (`"choices"` | `"exits"`) and `activeIndex`.
- **Markup:**
  - `<div class="dialogue-choices" role="menu" aria-label="對話選項" tabindex="0" :aria-activedescendant="rowId(activeIndex)" data-testid="dialogue-choices" @keydown="onKey">`
  - Each row is `<div role="menuitem" :id :data-testid="dialogue-pick|dialogue-freeform|dialogue-move|dialogue-exit|dialogue-exit-row|dialogue-exits-back" :aria-disabled>`, with a badge span (`1`–`N`, `⌨`, `↦`, `✕`, or the exit glyph) and a label.
  - The pick rows keep `data-keyword-id`.
- **Keys (`onKey`):**
  - ArrowUp / ArrowDown wrap. Home / End jump to the ends.
  - Enter / Space activate unless `event.repeat`.
  - Digits `1`–`N` act only in the `choices` view and only when pick N exists.
  - Escape acts only in the `exits` view: it returns to `choices` with the `↦ 移動…` row active.
  - Each handled key calls `preventDefault()` and `stopPropagation()`. Component listeners run before the document bridge (the same bubble-order argument as C6b D4), so the router never sees them.
  - Unhandled keys (`/`, Tab, and letters) pass through.
- **Pointer:** `@click` on a row sets `activeIndex` and activates it.
- **Disabled rows:** a disabled exit sets `aria-disabled="true"`, shows its reason under the label (`aria-describedby`), and activation does nothing.
- **Locked:** `locked` blocks every activation, although it cannot be observed, because the list is not rendered while in flight. It is kept as a guard for the one frame between dispatch and publish.
- **Emits:** `pick(row)`, `freeform()`, `move(item)`, and `leave()`. Before emitting, the component calls the `beforeActivate` prop callback (D7). `move` and the `↦ 移動…` swap never leave the component except as `move(item)`.

*Why `role="menu"` with an active descendant:* the rows are commands, not selectable options. One tab stop with `aria-activedescendant` is the same pattern as the dock (`#action-dock` owns focus and names the focused row), so screen readers and the pointer-activation contract see a familiar shape.

*Why the list owns the digits, not the store:* the store cannot know whether the list is shown, because the reading state is local to the window. A store retarget would claim digits while pages are still unread. The list is also the focus home whenever it is shown, so the digits reach it.

### D6. The `choices` anchor
`HudFrame.vue` adds `<div class="stage-anchor" data-anchor="choices" data-testid="anchor-choices"><slot name="choices" /></div>` with:

```
[data-anchor="choices"] { left: 50%; top: calc(var(--header-h) + (100% - var(--header-h) - var(--band-h)) / 2);
  transform: translate(-50%, -50%); width: min(560px, 40%);
  max-height: calc(100% - var(--header-h) - var(--band-h) - 32px); overflow-y: auto; z-index: 4; }
.elosern-stage:not([data-elosern-mode="dialogue"]) [data-anchor="choices"] { display: none; }
```

The card uses the reference's caption-panel treatment (charcoal fill, hairline border, radius). Rows are 44px with 20px text. The active row has the muted-gold fill and the leading `▸` glyph that dock rows use, so focus is shown by shape and fill.

Geometry check:
- 1920x1080: the stage box is 732px and the card is 560px wide, between the portraits (each about 446px wide at 6% inset) and clear of the 208px minimap.
- 1280x720: the stage box is 412px and the card is 512px wide. Seven rows at 44px plus padding is about 330px, which fits.

`AppShell` forwards a `choices` slot to HudFrame.

### D7. Focus
- **Showing:** a `watch(choicesShown)` in `AppClient` (flush `post`). When it becomes true and `document.activeElement` is the body, the page surface, or inside `[data-anchor="band-message"]`, it focuses the list.
- **Other focus:** if focus is elsewhere (a drawer, an overlay, the command field), the list does not steal it. It stays the focus home that `restoreFocusHome()` returns to.
- **Activating:** `beforeActivate` calls `shellRef.focusMessagePage()`, a new exposed AppShell method that focuses `message-page`. The list can then disappear on the next publish without dropping focus.
- **`restoreFocusHome()` in dialogue:** the list when it is rendered, else `messageWindow.focusHome()` (the page surface).
- **Leaving dialogue:** C10b's post-flush rescue selector adds `[data-anchor='choices']`.

### D8. The `↦ 移動…` exits come from the committed overview
`AppClient` computes `dialogueExits = store.view.rootMenu?.items.filter(i => i.section === "exits") ?? []`. That is the overview C9b D1 keeps as the router root in dialogue, built from the committed `exploration` panel by `overviewMenu`.
- `move(item)` calls `store.dispatchAction(item.actionId, item.payload, item.commandDisplay)`. This is the same payload and echo descriptor the overview chip's confirm path submits, but without pushing through the router, which is hidden.
- The movement settlement clears the session through the existing seam, and C8b's room-change reset keeps the dock at the new overview.

*Alternative:* reuse `SceneOverview` inside the list. Rejected: it is a router-bound chip grid with the dock's geometry and focus model, and the list needs a vertical menu with one focus model.

### D9. The borrow and the phase gap
- `view.js` publishes `freeformBound: ctx.freeformTarget != null` and `commandAccepts`, which is `connected && !mutationsLocked && !inFlight`, plus `phase === "active"` when `freeformBound`.
- `CommandLine.vue` replaces its use of `connected` / `mutationsLocked` / `inFlight` in `submit()` with one `accepting` prop. It keeps any other use of those props (disabled styling) unchanged.
- `AppShell` passes `:accepting="commandAccepts"`.
- `sendText` keeps `ctx.freeformTarget` when `dispatchAction` returns `null`, and clears it only after a dispatched request. The existing blur release (C5) still drops it when focus leaves the field.

The field and the dispatch path now share one predicate, so the field clears exactly when the request is sent. This closes the C5 Risks entry.

### D10. Tests
- **Vitest:**
  - `tests/dialogue_choices.test.js`:
    - the row order and badges
    - the digits, arrows with wrap, Home/End, and Enter/Space
    - repeat ignored
    - consumed keys not propagating (a document listener sees none)
    - `/` propagating
    - the exits view with a disabled exit, back, and Escape
    - pointer parity
    - `beforeActivate` called before each emit
  - `tests/message_window_dialogue.test.js`:
    - the paged dialogue with the plate
    - `reading-change` flips (typing, a further page, the pending mark, the last page complete)
    - no rows in the window
  - `tests/message_window_typing.test.js`: the former "variant does not type" case now types.
  - `tests/app.test.js`:
    - the list is shown only when all four conditions hold
    - the wiring of the four emits
    - focus moves to the list on show, and to the page surface on activate
  - `tests/command_line.test.js`: `accepting=false` keeps the text and does not emit `sent`.
  - `tests/dialogue_store.test.js`:
    - `commandAccepts` with and without a borrow, across phases
    - `sendText` keeps the target on a refused dispatch
  - `tests/store/digit_row_picks.test.js`: the caption retarget cases are deleted, and a dialogue-mode digit is unclaimed.
  - `tests/dialogue_dock.test.js`: digits are unclaimed in dialogue.
- **Browser:**
  - `test_browser_exploration_dialogue.py` gains the keyboard-only journey of the browser-verification scenario at 1920x1080. It waits for `data-typing="false"` (C7 helper) before reading the list, and asserts the list is absent while typing.
  - `test_browser_contextual_hud_anchors.py` gains the `choices` anchor geometry at both viewports.
  - `test_browser_shell_command_line.py` re-points its borrow cases to the list's free row, and adds the phase case by injecting a non-active phase through the bridge, as its lock cases do.
  - `test_browser_input_narrative.py` re-anchors.

### D11. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud: stage, visibility, message window, legend, command-line row, and the collapse requirement | C10b `webclient-dialogue-stage-actors` |
| contextual-hud "The feed presents the dialogue variant…" (REMOVED) | C10b |
| input-narrative "A page types in at the reader's text speed and auto-advance is opt-in" | C7 `webclient-typewriter-reading-prefs` |
| desktop-shell "Keyboard routing is menu-first and submission-safe" | C10b |
| desktop-shell "Required desktop surfaces remain visible and usable" (dialogue paragraph and "The dialogue caption stays bounded at the minimum viewport": choices live in the choice list, not the window) | C10b |
| desktop-shell "The collapsible command line preserves ordinary text control" (REMOVED) | C5 `webclient-collapsible-command-line` (ADDED there) |
| browser-verification "Browser acceptance covers foundation recovery and layout behavior" | C5 |
| component-showcase "Every required UI component…" | C10b |

- **The desktop-shell command-line requirement is replaced, not modified.** Its scenario "A dock-borrowed send returns focus to the dock" names a borrower (the dock) and a focus target that do not exist in dialogue, and a MODIFIED block cannot rename a scenario. Coordinator note (b) asks for exactly this restatement. The 11 annotations re-anchor.
- **The typing requirement keeps its title** "The dialogue variant does not type". Its body now states that no variant exists and the line types, which keeps the title literally true without a REMOVED + ADDED of a requirement whose subject is unchanged.
- **The browser-verification block drops "bounded caption"**, as the C6 note asks. It also drops the minimap legend clause that C1 made false (coordinator note 1). If C5's block is amended for the legend first, re-sync this block and keep only this change's edits.
- The new choices ID is covered by the `test_node_suite_evidence.py` dialogue evidence (the file list gains `dialogue_choices.test.js`) and by the browser journey. The replaced variant ID's annotations (the dialogue evidence test and `test_browser_exploration_dialogue.py`) re-anchor to it.

**Archive order: C9a (`explore-talk-open-action`) → C9b (`webclient-talk-open-dock`) → C10a (`dialogue-panel-host-portrait`) → C10b (`webclient-dialogue-stage-actors`) → C10c (this change) → C11 (`webclient-motion-layer`).** C11's choice stagger and dialogue transitions build on this change's list and anchor.

## Risks / Trade-offs

- [The host's name shows twice: in the plate and in the `X說：` prefix] → Accepted (D2). It is truthful and prose-free. A server-side change can drop the prefix later.
- [A long greeting delays the choices] → Intended by the design ("after the last page"). The player can press Enter to complete typing and advance quickly. Reduced motion and the `instant` speed show pages at once.
- [Focus stolen from a drawer when the list appears] → D7 moves focus only from the window, the body, or the message region.
- [The browser suite's dialogue journeys now wait for typing] → They use C7's `wait_for_page_shown` helper, or Enter to complete, before interacting with the list.
- [Budget] → Variant deletion and the reading signal (1.5h); `DialogueChoices`, story, and tests (2.5h); anchor, wiring, and focus (1.5h); accept rule and phase fix (0.5h); browser journeys (1.5h); specs and re-anchors (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing new is persisted.
