## Why

After `webclient-dialogue-stage-actors` (C10b), a conversation has both portraits on the stage, the collapsed command region, and the name plate. But the message window still renders the dialogue as an unpaged, untyped variant: the reply, the pick rows, the free row, and the exit row share one scroll region. The choices therefore sit beside text the player has not read yet. The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §8.2) asks for three things. The session line is paged and typed like any response (§6). The choice list appears centred over the stage only after the last page is fully shown. The list ends with `⌨ 自由對話`, `↦ 移動…` (which swaps in the exits), and `✕ 結束對話`. This change (C10c) delivers that. It also restates the free-form borrow, which C9 left as the only borrower of the command line, and closes the C5 gap: `CommandLine` accepts a borrowed send that `dispatchAction` then refuses, because the store also requires `phase === "active"`, and `sendText` drops the borrow on that refusal.

**Implementation profile:** visual. The centred choice card over the stage, its reveal after reading, and its keyboard and pointer feel at the reference viewport need layout and interaction judgement.

## What Changes

- **BREAKING (internal)**: `web/webclient-app/components/MessageWindow.vue` deletes the dialogue variant (the C6b D6 port as C10b left it):
  - the `data-variant="dialogue"` branch, the `.dlg` box and `.say` line, the `.choices` / `.pick` / `.pick-exit` rows and their emits (`dialogue-pick`, `dialogue-freeform`, `dialogue-leave`)
  - the anchored echo suppression and the box pin, and their CSS

  In dialogue mode the window pages and types the current response exactly like any other mode, with C10b's name plate above the text area. It emits `reading-change` with `true` exactly while the current response's last page is on screen, fully shown, with no pending action mark, and `false` otherwise. `focusHome()` focuses the page surface.
- **New governed component `web/webclient-app/components/DialogueChoices.vue`** (story `stories/Core/DialogueChoices.stories.js`, manifest title `Core/DialogueChoices`).
  - It is a single-tab-stop menu composite (`role="menu"`, `aria-label="對話選項"`, `tabindex="0"`, `aria-activedescendant`), and its rows are `role="menuitem"`.
  - Rows, in order:
    - one per `dialogue.choices` entry, with digit badge 1–N
    - `⌨ 自由對話`
    - `↦ 移動…`
    - `✕ 結束對話`
  - `↦ 移動…` swaps the list for the exit rows of the committed exploration overview, each with its direction glyph and destination (`components/dock-exits.js`). A disabled exit stays focusable with its reason. Escape returns to the choices.
  - Keys:
    - ArrowUp and ArrowDown move with wrap; Home and End jump to the ends.
    - Enter and Space activate the focused row. A held repeat is ignored.
    - Digit `1`–`N` activates pick N.
    - Every handled key is consumed (`preventDefault` + `stopPropagation`), so the document bridge never sees it. `/` is left unhandled, so it still opens the command line.
  - A pointer activation focuses the row and activates it through the same path.
  - Emits: `pick` (a view-model pick row), `freeform`, `move` (an overview exit item), and `leave`.
- `web/webclient-app/components/HudFrame.vue`: a new stage anchor `choices` (`data-anchor="choices"`, `data-testid="anchor-choices"`, slot `choices`).
  - It is centred on the stage box, `width: min(560px, 40%)`, bounded by the stage box, and scrolls internally.
  - It sits at z 4, with the islands and above the portraits.
  - It is `display:none` outside dialogue mode.
- `web/webclient-app/AppClient.vue` (and `AppShell.vue` forwarding the slot and the window's `reading-change`) renders `DialogueChoices` in `#choices` exactly while all of these hold:
  - the mode is `dialogue`
  - the dialogue view model is available
  - the window reports reading complete
  - no dispatch is in flight (`store.view.dispatch.inFlight` is null)

  Wiring:
  - `pick` goes to the existing `onDialoguePick`, which dispatches `explore.talk_scripted`.
  - `freeform` goes to `store.borrowDialogueCommand`, which expands the line through C5's borrow path.
  - `move` goes to `store.dispatchAction("explore.move", item.payload, item.commandDisplay)`, the same payload the overview's exit chip dispatches.
  - `leave` goes to `explore.dialogue_leave`.
  - Exit items come from `store.view.rootMenu`, which is the overview in dialogue (C9 D6); the `exits` section is used.
- Focus: in dialogue mode the focus home becomes the choice list while it is rendered, and the page surface otherwise. `AppShell.restoreFocusHome()` follows.
  - When the list appears while focus is on the page surface, inside the message window, or on the body, it takes focus.
  - Before an activation dispatches, focus moves to the page surface, so the list's removal never drops focus.
  - C10b's leave-dialogue rescue also covers focus inside the `choices` anchor.
- `web/webclient-app/stores/elosern/interaction.js` deletes the caption digit retarget: `handleCaptionDialoguePick`, `captionDialoguePresented`, and the retarget branch in `focusPress`. In dialogue mode `focusPress` now claims only `/`. The digits belong to the focused list.
- **Command line accept rule and the phase gap:**
  - `stores/elosern/view.js` publishes `commandAccepts`:
    - while a free-form borrow is bound: `connected && !mutationsLocked && phase === "active" && !inFlight`
    - otherwise: `connected && !mutationsLocked && !inFlight`, unchanged for ordinary text, which does not use `dispatchAction`
  - `components/CommandLine.vue` takes one `accepting` prop in place of its predicate, and clears and emits `sent` only when it is true.
  - `stores/elosern/transport.js` `sendText` keeps `ctx.freeformTarget` when `dispatchAction` returns `null`, so a retry after the lock lifts is still speech.
- `lib/controls-reference.js`: the digits and Enter rows describe the choice list.
- Spec deltas:
  - The dialogue-variant requirement is replaced by a choices requirement.
  - Restated:
    - the stage anchors, the visibility matrix, the message window (paged in dialogue, name plate), the legend, and C10b's collapse requirement (focus home and keys)
    - the command line row (the borrow row and the accept rule)
    - the typing requirement (the dialogue line types)
    - desktop-shell keyboard routing
    - the browser-verification acceptance text (no "bounded caption")
  - The desktop-shell command-line requirement is replaced, so that its borrowed-send scenarios name the dialogue free row and the dialogue focus home.
- No OOB schema, presenter, server, or persistence change.

Out of scope:
- The choices' 40ms stagger, the portrait slide-in, and every other transition: `webclient-motion-layer` (C11).
- Combat foes in `actor-right`: `webclient-combat-beat-playback` (C13).
- The typed `talk` command and the dialogue panel's content (unchanged).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - REMOVED "The feed presents the dialogue variant from the committed panel" (C10b text).
  - ADDED "Dialogue choices appear centred over the stage after the line is fully read".
  - MODIFIED, each on C10b's text:
    - "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces"
    - "Surface visibility is gated by the committed game mode"
    - "The message window presents the current response one page at a time in the band's message region"
    - "The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance"
    - "The command region collapses in dialogue mode and the message window spans the band"
    - "The command line is a collapsible row docked on the message region's top edge"
- `webclient-input-narrative`: MODIFIED "A page types in at the reader's text speed and auto-advance is opt-in" (C7): the dialogue line types like any page.
- `webclient-desktop-shell`:
  - REMOVED "The collapsible command line preserves ordinary text control" (C5).
  - ADDED "The collapsible command line preserves ordinary text control and the dialogue's free-form borrow".
  - MODIFIED "Keyboard routing is menu-first and submission-safe" (C10b).
- `webclient-browser-verification`: MODIFIED "Browser acceptance covers foundation recovery and layout behavior" (C5).
- `webclient-component-showcase`: MODIFIED "Every required UI component is a Vue SFC with a documented Storybook story" (C10b): adds the dialogue choices, and the message window's dialogue state becomes the name-plate page.

## Impact

- New: `web/webclient-app/components/DialogueChoices.vue`, `stories/Core/DialogueChoices.stories.js`, `tests/dialogue_choices.test.js`.
- Edited source:
  - `web/webclient-app/components/MessageWindow.vue`, `HudFrame.vue`, `AppShell.vue`, `CommandLine.vue`, `web/webclient-app/AppClient.vue`
  - `stores/elosern/{interaction,transport,view}.js`, `stores/elosern.js` (drops the retarget exports)
  - `styles/app-shell.css`, `lib/controls-reference.js`, `component-manifest.json`
  - Stories `stories/Core/MessageWindow.stories.js`, `HudFrame.stories.js`, `AppShell.stories.js`, `CommandLine.stories.js`
- Vitest:
  - `tests/message_window_dialogue.test.js` (rewritten for the paged dialogue with the plate and `reading-change`)
  - `tests/message_window_typing.test.js` (the dialogue case types)
  - `tests/app.test.js`, `tests/hud_frame.test.js`, `tests/command_line.test.js`, `tests/dialogue_store.test.js`, `tests/dialogue_dock.test.js`, `tests/store/digit_row_picks.test.js`
- Python evidence: `web/webclient/tests/test_node_suite_evidence.py` (dialogue evidence file list; the re-anchors below); the showcase snapshots gain `Core/DialogueChoices`.
- Browser: `web/tests/browser/test_browser_exploration_dialogue.py` (the keyboard-only journey move → overview → 交談 → read → choice → free speech → 移動… → leave), `test_browser_input_narrative.py`, `test_browser_shell_command_line.py`, `test_browser_contextual_hud_anchors.py`, `browser_helpers.py`.
- Spec traceability:
  - `webclient-contextual-hud::the-feed-presents-the-dialogue-variant-from-the-committed-panel` re-anchors to `…::dialogue-choices-appear-centred-over-the-stage-after-the-line-is-fully-read`.
  - `webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control` (11 annotations: `test_browser_input_narrative.py` ×3, `test_browser_shell_command_line.py` ×5, `test_browser_exploration_dialogue.py` ×1, `test_node_suite_evidence.py` ×2) re-anchors to `…-and-the-dialogue-s-free-form-borrow`.
- Dependencies:
  - Archive order: C9 → C10a → C10b (`webclient-dialogue-stage-actors`) → C10c (this change) → C11 (`webclient-motion-layer`).
  - Hot-spot files shared with C10b and C11: `AppClient.vue`, `AppShell.vue`, `HudFrame.vue`, `MessageWindow.vue`, `app-shell.css`.
