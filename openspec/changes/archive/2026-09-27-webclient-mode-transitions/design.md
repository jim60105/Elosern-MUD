## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C10c, C11a (`webclient-motion-level`), and C11b (`webclient-scene-transitions`) are archived.

- **Motion (C11a, C11b):**
  - `<html data-motion>` carries the effective level.
  - The tokens `--motion-panel` (250ms), `--motion-actor` (350ms), `--motion-reveal` (250ms), `--motion-flash` (120ms), `--motion-stagger` (40ms), `--motion-flash-peak` (0.85), `--motion-travel`, `--motion-shift-sm` / `--motion-shift-lg`, `--ease-enter`, and `--ease-exit` exist.
  - Under `reduced`: panel, actor, and reveal are 150ms; flash, stagger, travel, and flash-peak are 0. Under `off` everything is 0.
  - `lib/transition_hooks.js` `inertWhileLeaving` sets `inert` on a leaving element (C11b D1). Every stage `<Transition>` binds `:css="motionLevel !== 'off'"` from a threaded `motionLevel` prop (C11b).
  - The requirements "Presentation timing never gates committed state or input" and "A leaving element is out of reach while it animates out" are the contracts.
- **`HudFrame.vue`**:
  - The stage root `.elosern-stage[data-elosern-mode]` holds `.stage-vignette`, `.stage-combat-veil` (`display:none` outside combat, with `animation: elosern-combat-pulse var(--motion-pulse) … infinite` on its own opacity), the backdrop slot, `actor-left` / `actor-right` (anchors with the class `stage-actor`), the islands, `.stage-band` with `band-message` / `band-command`, the `choices` anchor (C10c), and the `command-line` anchor.
  - In dialogue mode (C10b D4), `.stage-band` has one column and `[data-anchor="band-command"]` is `display:none`.
- **`AppShell.vue`** (C10b D5, C10c D7):
  - `HIDDEN_BY_MODE.dialogue = "[data-anchor='band-command']"`.
  - The mode watcher's pre-flush phase moves focus out of `band-command` to `message-page` before the attribute flips.
  - Its post-flush phase calls `restoreFocusHome()` on leaving dialogue when focus is on the body, in `band-message`, or in `choices`.
- **`AppClient.vue`** (C10b D2, C10c D4):
  - `#actor-right` renders `<StageActor v-if="mode === 'dialogue' && dialogueVm" side="right" …>`.
  - `#choices` renders `<DialogueChoices v-if="choicesShown" …>`.
- **`MessageWindow.vue`** (C10b D7): the name plate `message-name-plate` is the window's first flex child while the dialogue panel is available.
- **`DialogueChoices.vue`** (C10c D5): the root is `div.dialogue-choices[role=menu][tabindex=0][aria-activedescendant]`, with row `div[role=menuitem]` children, and a `view` of `choices` or `exits`.
- **`ActionDock`** in `#action-dock` is never remounted. It changes its content from the scene overview to the combat root when the mode changes.
- **Drawers:**
  - `AppClient` mounts `HudDrawer` with `v-if` and `:open="true"`, so its transform transition (`--motion-base`) does not animate the first mount. The stage recession uses `--motion-base`.
  - `OverlayHost` has no transition.
  - C11a resolves `--motion-base` to 0 under `reduced` and `off`.

## Goals / Non-Goals

**Goals:**
- The dialogue and combat rows and the choices stagger of design §9.3, at all three levels, from tokens only.
- The message window's width changes once, at commit.
- Only live mode changes animate.
- Focus never lands on a leaving element, and input is never delayed.

**Non-Goals:**
- Foes in `actor-right` during combat and every beat animation (C13).
- Changing drawer or overlay presentation (D7).
- Any script-timed animation.

## Decisions

### D1. The command region slides over a band that widens at once
The band keeps C10b's one-column grid in dialogue, so the message region is the band's full width in the commit's frame. The window's measurer re-pages once. Animating `grid-template-columns` instead would make its ResizeObserver re-page on every frame of the slide (coordinator-approved "the window widens instantly").

`[data-anchor="band-command"]`:
- **Dialogue mode:** the rule replaces C10b's `display:none` with:
  - `position: absolute; top: 0; right: 0; bottom: 0; width: 33.3333%`
  - `transform: translateX(calc(100% * var(--motion-travel)))`, `opacity: 0`, `visibility: hidden`
- **Transitions, only under `.elosern-stage[data-mode-change]`** (D2), so a mount or a reconnect renders the final state at once:
  - leaving (the dialogue rule): `transform var(--motion-panel) var(--ease-exit)`, `opacity calc(var(--motion-panel) * 0.6) var(--ease-standard)`, and `visibility var(--motion-panel) linear`. The panel accelerates away but thins early, so it never sits opaque over the widened window. `visibility` is discrete: with a full-length transition and no delay it stays `visible` until the slide ends. This avoids a literal `0s` delay, which the duration guard rejects.
  - returning (the base rule): `transform var(--motion-panel) var(--ease-enter)` and `opacity calc(var(--motion-panel) * 0.8) var(--ease-standard)`, with no `visibility` transition. The region is visible, and the dock focusable, in the commit's own frame. A discrete `visibility` transition would hold `hidden` for the first frame and the post-flush focus rescue would miss the dock. The region re-enters the grid at the offset it holds and decelerates home.
- **No `.stage-band { overflow: hidden }`.** The region sits at the stage's right edge, and the stage root's own `overflow: hidden` already clips the slide. Clipping the band would also clip the dock's verb popover.

`HudFrame` binds `:inert="mode === 'dialogue' || null"` on the anchor. `null` removes the attribute where the DOM has no `inert` property (jsdom), so it is never rendered as `inert="false"`. It flips in the same patch as `data-elosern-mode`, so the region leaves the accessibility tree, the tab order, and hit-testing at commit. `visibility: hidden` at the end also removes it from the accessibility tree while the element stays mounted. `#action-dock` is never remounted, as C10b requires.

At `reduced`, travel is 0 and the duration is 150ms, so the panel only fades over the widened window. At `off`, the change is instant.

### D2. The live mode-change hook
The shell's `mode` prop is coerced (`store.view.mode || 'exploration'`). A transport reset nulls the raw mode, and the resync snapshot sets it again. So a watcher on `HudFrame`'s prop would see `exploration → combat` on a reconnect into combat and flash. The signal is therefore computed from the **raw** committed mode by `composables/use-mode-change.js`, registered first in `use-app-client.js`:
- `nextModeChange(previous, from, to)` is pure. It returns null when either endpoint is null, `previous` when `from === to`, and otherwise `` `${from}-${to}` ``.
- A default (pre-flush) watcher on `store.view.mode` sets `modeChange`, so the ref changes in the same patch as the mode.
- `modeHydrating` is true from **any** null edge (the reset that clears the mode, or a mount before the first snapshot). A post-flush watcher clears it once a `null → mode` arrival has rendered. Both edges of a reconnect mid-dialogue are separate flushes: `dialogue → null`, then `null → dialogue`. The flag covers both, so the host and the plate neither leave nor enter with a fade (plan-review finding).
- `AppClient` passes `modeChange` and `modeHydrating` to `AppShell`. `AppShell` renders `modeChange` through `HudFrame`'s new `modeChange` prop as `:data-mode-change`, and forwards `modeHydrating` to `MessageWindow`.

Consequences:
- Mounting and a reconnect never set the attribute. A same-mode resync keeps it.
- The attribute persists until the next live change. Every animation keyed on it has one iteration, so it plays once.
- Selectors: `[data-mode-change$="-combat"]` for the flash (its layer is never remounted), and `[data-mode-change]` for the transitions. The flip uses its own one-shot key (below), because a CSS animation plays whenever a matching element is inserted, and the persistent attribute would replay the flip on a later remount of the dock.

**Flash.** A new `<div class="stage-flash" data-testid="stage-flash" aria-hidden="true">` sits above the backdrop and portraits and below the islands (z 3), with `pointer-events: none` and `opacity: 0`.
- Its fill is a warm white radial (`#fffdf8` at the scene's centre falling to `#f4dcc0` at the edges), so it reads as an impact rather than a blank frame.
- `[data-mode-change$="-combat"] .stage-flash` plays `elosern-stage-flash var(--motion-flash) linear 1`. The keyframes carry their own curves: a hard attack to `var(--motion-flash-peak)` at 20%, then a long, soft release.
- At `reduced` the peak is 0, and at `reduced` and `off` the duration is 0, so the flash is invisible at both. Design §9.1 lists no flash for reduced, and a white flash is a photosensitivity trigger.

**Veil.** `.stage-combat-veil` is always rendered, `aria-hidden="true"`, at `opacity: 0`, and at `opacity: 1` in combat.
- Under `[data-mode-change]` it transitions `opacity var(--motion-actor) var(--ease-standard)`: 350ms at `full`, so the scene closes in slightly slower than the 250ms flip, and 150ms at `reduced`.
- The gradient and the pulse move to a `::before` layer, and the pulse runs only in combat, so the pulse's opacity keyframes and the fade's opacity transition never fight over one property.
- The `--stage-combat-veil` token is deepened: a blood-dark ring towards the corners over a faint overall dusk. The H1 value was nearly invisible over a painted backdrop.

**Panel flip.**
- `HudFrame` sets a `flip` ref from a watcher on `modeChange`, in the patch of a live change into combat (`*-combat`) or out of it (`combat-exploration`), and renders it as `data-flip` on the `band-command` anchor. An `animationend` for `elosern-panel-flip-*` bubbling to the anchor clears it. So a dock that remounts later in the same mode (its `v-if` briefly false) never flips again. The implementation review found this.
- `[data-anchor="band-command"][data-flip$="-combat"] > *` plays `elosern-panel-flip-in`.
- `[data-anchor="band-command"][data-flip="combat-exploration"] > *` plays `elosern-panel-flip-out`.
- Both run over `--motion-panel` with `--ease-enter`, from `opacity: 0; transform: perspective(1400px) rotateY(calc(∓72deg * var(--motion-travel)))` to rest. The committed menu turns in from nearly edge-on. The combat root turns in from one side and the overview from the other.
- The dock renders one root (`section#action-dock`), so `> *` is exactly the dock.
- The dock's content has already switched at commit (the combat root), so the flip reveals the committed menu, and the dock keeps focus throughout.

The keyframes live in `styles/tokens.css` next to the shared ones.

### D3. The host enters and leaves
`AppClient` wraps the host actor:

```
<Transition name="actor-enter" :css="hostTransitionCss" v-bind="inertWhileLeaving">
  <StageActor v-if="…" :key="dialogueVM.host.identity" side="right" … />
</Transition>
```

- `hostTransitionCss` is `motionLevel !== 'off' && !modeHydrating`. At `off` there is no CSS phase (C11b D1), and across a reconnect the host appears and goes in the commit's frame.
- Enter from and leave to: `opacity: 0; transform: translateX(calc(var(--motion-shift-lg) * 1.5 * var(--motion-travel)))`, which is 48px at `full`.
- Enter: opacity over `calc(var(--motion-actor) * 0.8)` with `--ease-standard`, and transform over `--motion-actor` with `--ease-enter`. Both are delayed by `calc(var(--motion-panel) * 0.24 * var(--motion-travel))`, about 60ms at `full` and 0 at `reduced`, so the eye reads the band clearing first and the host arriving second. The opacity rises a little faster than the figure moves, so no half-transparent body hangs in the air.
- Leave: `position: absolute; inset: 0` on the anchor's box, with opacity over `--motion-actor` (`--ease-standard`) and transform (`--ease-exit`).
- Keying by host identity makes a host change during a session (a new host, not a new portrait) slide one actor out and the next in, while C11b's crossfade handles a new portrait for the same host.
- The actor has no focusable element, and `inert` covers pointer hits while it leaves.

### D4. The name plate
`MessageWindow` wraps the plate in `h(Transition, { name: "plate", css: motionLevel !== "off" && !modeHydrating, ...inertWhileLeaving })`. The Transition stays in the vnode tree, so the text area keeps its position.
- The plate takes its row at commit, and the window re-pages once.
- Enter: its content fades over `--motion-reveal` and drifts `--motion-shift-sm × travel` in from the column's side, delayed by `calc(var(--motion-panel) * 0.4 * var(--motion-travel))`, so it arrives just after the host starts to walk on.
- Leave: `position: absolute; top: 0; left: 0; right: 0` (so the text area is not held open), with opacity over `calc(var(--motion-reveal) * 0.4)` and `--ease-standard`. It drops away before the new page surfaces under it. The frame review showed a slower leave overlapping the new page's first line.
- `--dialogue-inset` moves from the dialogue-only rule to `.message-window`, so a plate leaving after the commit back to exploration keeps its geometry while it fades.

### D5. The choices stagger
Pure CSS keyframes replace the proposed `TransitionGroup`. The rows are ordinary keyed elements, in the DOM, focusable, and clickable from their first frame. A view swap renders new keyed rows, which animate on insertion. Removed rows vanish at once, with no leaving copy. A group's leave copies would carry duplicate row ids for a double frame, and `off` would need a script-side `css` switch.
- Each row carries `:style="{ '--row-index': index }"` and `animation: elosern-choice-row-in var(--motion-reveal) var(--ease-enter) calc(var(--motion-stagger) * var(--row-index)) backwards`. The keyframe rises from `translateY(calc(var(--motion-shift-sm) * var(--motion-travel)))` at `opacity: 0`. `backwards` holds a row at its start through its delay, and nothing is filled after it, so hover, focus, and active-row styles are untouched.
- The card (`.dialogue-choices`) and the exits caption fade in (`elosern-choice-card-in`) over `--motion-reveal`. No `choices-card` Transition wraps the list in `AppClient`, and the list vanishes at activation, after C10c D7 has moved focus to the page surface.
- The rows' scroller is keyed by the view and carries `--row-count`. It plays `elosern-choice-rows-clip` (`overflow-y: hidden`) for `stagger × count + reveal`. The rising rows sit a shift below their rest, which at 1280×720 flashed a scrollbar on and off. The frame review caught it, and the clip covers exactly the entrance. This relies on the discrete animation of `overflow-y`, which the target Chromium supports (verified live in the story). A browser without it would only show that brief scrollbar, and `scrollIntoView` on the active row is unaffected (a clipped scroller still scrolls programmatically).
- The new `entrance` prop (default true; `AppClient` passes `!modeHydrating`) is read once, at mount. A list mounted in the frame a reconnect renders carries `dialogue-choices--still` (the card) and `dialogue-choices--rows-still` (the rows), both `animation: none`. The rows' stillness ends at the first view swap, whose new rows stagger in. The card never refades, and a later prop change never replays the entrance.
- At `reduced` the stagger and the rise are 0, so the rows fade in together over 150ms. At `off` the `!important` rule zeroes every duration and delay, and the rows show at rest.

### D6. Focus and reach
- **Entering dialogue.** C10b's pre-flush rescue moves focus from `band-command` to `message-page` before the patch that sets `inert`, so focus never drops to the body.
- **Leaving dialogue.** The post-flush rescue focuses `#action-dock`, whose region cleared `inert` in the same patch and is sliding in. An entering element is in reach from its first frame.
- **Combat.** The dock never leaves, so focus stays on it through the flip.
- **Choices.** The list is focusable from its first frame (D5).
- **Leaving copies.** The leaving host actor and the leaving plate are inert (D3, D4).

### D7. Drawers and overlays are unchanged
Design §9.3 keeps drawers "as today", and C11a already makes them obey the level: every drawer and recession duration is `--motion-base`, which is 0 at `reduced` and `off`. Making the drawer's mount slide actually play would change drawer presentation, which the design's non-goals exclude, so nothing is edited. `OverlayHost` has no transition.

### D8. Tests
- **Vitest** `tests/mode_transitions.test.js`, mounting `AppClient` with `stubs: { transition: false, 'transition-group': false }`:
  - `nextModeChange` for live, null-endpoint, and same-mode cases.
  - `HudFrame` renders `.stage-flash` and `.stage-combat-veil` `aria-hidden` in every mode, makes the `band-command` anchor `inert` exactly in dialogue, and renders the `modeChange` it is given. `data-flip` is set by a live combat change, cleared by the flip's `animationend` while `data-mode-change` persists, and never set by a dialogue change.
  - `AppClient`: the first snapshot sets no `data-mode-change`, and live changes name themselves. A same-mode resync keeps the change.
  - Leaving dialogue leaves one host copy with `actor-enter-leave-active` and `inert`, and the region's `inert` clears in the same patch.
  - A reconnect mid-dialogue (`beginTransport` and then a resync snapshot on a new epoch) removes the host and the plate at the reset with no leaving copy. It then renders the host, the plate, and the list at rest: no enter classes, and `dialogue-choices--still`.
  - A live entry animates the host and the list. At `off` the host has no CSS phase.
  - `DialogueChoices` rows carry `--row-index` 0…N−1, the root keeps `role="menu"` and `tabindex="0"`, a digit activates in the first frame, and `entrance: false` holds until a view swap.
  - Stub-shaped assertions in `tests/app_client_stage_actor.test.js`, `tests/overlays/objective_tracker_integration.test.js`, and `tests/message_window_dialogue.test.js` read through the Transition wrapper. `tests/hud_frame.test.js` asserts `inert`, the absolute collapsed state, and the one-column band instead of `display:none`.
- **Browser** `web/tests/browser/test_browser_mode_transitions.py` at 1920x1080. Each journey commits a snapshot and reads the stage in the next animation frame inside the same evaluation (computed styles, `getAnimations()`, classes), never elapsed time. Journeys that need the choice list read the live line first (`open_dialogue_choices`).
  - `test_dialogue_enter_and_leave_full`: the window spans the band at once, and the region is inert, absolute, and transitions for `0.25s`, ending hidden. The host enters with `0.35s`, and the plate enters. On leaving, the host leaves inert, the region is visible and not inert in the commit's frame, the list is gone, and the dock takes focus.
  - `test_combat_enter_and_leave_full`: `elosern-stage-flash` at 120ms, the flash and the veil `aria-hidden` and `pointer-events: none` and never the hit target, the veil's `0.35s` transition from below 1, and `elosern-panel-flip-in`. Leaving plays no flash and plays `elosern-panel-flip-out`. A second entry flashes again.
  - `test_choices_stagger_full`: row delays `0s`, `0.04s`, … `0.24s`, the list focused, and a digit dispatching at once.
  - `test_reload_in_combat_plays_nothing`: a transport reset and a resync on a new epoch, in combat and then in dialogue. No `data-mode-change`, no flash, the veil at 1, no flip, the region hidden in the resync's frame, the host and the plate at rest, and the list's rows unanimated.
  - `test_mode_transitions_reduced`: every duration is at most `0.15s`, transforms are identity, the flash peak is `0` with no visible flash, and row delays are `0s`.
  - `test_mode_transitions_off`: final states in the commit's frame (the region hidden or shown, no leaving copy, the veil at its final opacity, the flash at 0, the rows fully opaque).
  - Annotations: every journey carries `webclient-contextual-hud::mode-changes-transition-at-the-motion-level`. The dialogue journeys add the collapse ID and the leaving-element ID, and the combat journey adds the visibility ID.
- **Existing browser suites.** These are structural, not wording swaps:
  - `test_browser_exploration_dialogue.py`: `commandDisplay`/`dockDisplayed` become visibility, `inert`, and a hidden dock. The `full`-level journey's per-frame counter checks `inert` only, because the region is visible for its 250ms slide, and its hidden end state is asserted once the line is read.
  - `test_browser_contextual_hud_stage.py`: the dialogue command rect's zero width becomes `[inert, 'hidden', 'absolute']`.
  - `test_browser_layout.py`: `display:none` becomes hidden and `inert`.
  - `test_browser_contextual_hud_anchors.py`: the overlap check skips a `visibility: hidden` anchor.
- **Evidence:** `test_node_suite_evidence.py` gains `ModeTransitionsEvidenceTest.test_mode_transitions_vitest_evidence_passes`, annotated with the new ID.

### D9. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| contextual-hud "The command region collapses in dialogue mode and the message window spans the band" | C10c `webclient-dialogue-choices-overlay` |
| contextual-hud "Surface visibility is gated by the committed game mode" | C10c |

- Every scenario title is kept, and the bodies change only where they named `display:none` for the collapsed region, so no annotation moves.
- The new ID is covered as D8 lists.
- The choices requirement (C10c) is not modified: its show rule, focus, and keys are unchanged, and the stagger is stated in the new requirement.
- The stage-actor requirement (C10b) already leaves transitions to the motion layer.
- No desktop-shell requirement names `display:none` for the command region.

**Archive order: C10c (`webclient-dialogue-choices-overlay`) → C11a (`webclient-motion-level`) → C11b (`webclient-scene-transitions`) → C11c (this change).** C13 (`webclient-combat-beat-playback`) archives after this change. It reuses `data-mode-change` and `inertWhileLeaving` for the foes, and modifies the visibility matrix on this change's text. If a base block changes before archive, re-sync this change's blocks and keep only its own edits: the slide-out collapse and the matrix's exception.

## Risks / Trade-offs

- [The sliding panel covers the right third of the widened message text for 250ms] → The page text is capped at `42em` and left-aligned (C10b D7), so the right third of the full-width window holds no text at 1920px. The panel slides over empty window space.
- [AppShell's focus-rescue watcher still reads the coerced mode, so a reconnect mid-dialogue (`dialogue → null`, seen as `exploration`, then `→ dialogue`) can move focus twice: to the dock, then to the dialogue's home] → This predates this change, and the stage itself plays nothing. Gating that watcher on `modeHydrating` changes where focus rests during an outage for every mode, so it is deferred to a follow-up rather than folded in here.
- [An element that is `inert` but still painted could confuse sighted keyboard users] → Focus has already moved (D6), and the element is gone within 250ms.
- [The CSS animation restart depends on alternating names] → Mode sequences always alternate entering and leaving combat. A browser journey asserts a second combat entry flashes again.
- [Budget] → collapse slide (1.5h), hook, flash, veil, and flip (2h), actor and plate (0.75h), stagger (0.75h), Vitest (1h), browser (1.5h), specs and gates (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
