## Context

See proposal.md (Why). The state below comes from the code and from the earlier series changes, assuming C1 to C10c, C11a (`webclient-motion-level`), and C11b (`webclient-scene-transitions`) are archived.

- **Motion (C11a, C11b):**
  - `<html data-motion>` carries the effective level.
  - The tokens `--motion-panel` (250ms), `--motion-actor` (350ms), `--motion-reveal` (250ms), `--motion-flash` (120ms), `--motion-stagger` (40ms), `--motion-flash-peak` (0.85), `--motion-travel`, `--motion-shift-sm` / `--motion-shift-lg`, `--ease-enter`, and `--ease-exit` exist.
  - Under `reduced`: panel, actor, and reveal are 150ms; flash, stagger, travel, and flash-peak are 0. Under `off` everything is 0.
  - `lib/transition_hooks.js` `inertWhileLeaving` sets `inert` on a leaving element (C11b D1).
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
- **Every mode:** `transition: transform var(--motion-panel) var(--ease-exit), opacity var(--motion-panel) var(--ease-exit), visibility 0s linear 0s`.
- **Dialogue mode:** the rule replaces C10b's `display:none` with:
  - `position: absolute; top: 0; right: 0; bottom: 0; width: 33.3333%`
  - `transform: translateX(calc(100% * var(--motion-travel)))`, `opacity: 0`, `visibility: hidden`
  - `transition-delay: 0s, 0s, var(--motion-panel)`, so visibility flips only after the slide
- **Returning to exploration:** the region is a grid item again at `transform: none; opacity: 1; visibility: visible` with zero delay, so it slides back from the offset it holds, using `--ease-enter`.
- `.stage-band` gets `overflow: hidden`, so the translated panel never paints outside the band.

`HudFrame` binds `:inert="mode === 'dialogue'"` on the anchor. It flips in the same patch as `data-elosern-mode`, so the region leaves the accessibility tree, the tab order, and hit-testing at commit. `visibility: hidden` at the end also removes it from the accessibility tree while the element stays mounted. `#action-dock` is never remounted, as C10b requires.

At `reduced`, travel is 0 and the duration is 150ms, so the panel only fades over the widened window. At `off`, the change is instant.

*Why `visibility` and not `display:none` after the slide:* `display` cannot be delayed by a transition, and a script `transitionend` toggle would add a timer path that `off` must bypass. A delayed `visibility` transition is pure CSS and resolves to instant at `off`.

### D2. The live mode-change hook
`HudFrame` keeps `modeChange = ref(null)` and sets it in `watch(() => props.mode, (to, from) => { modeChange.value = from && to !== from ? `${from}-${to}` : modeChange.value })`. The watcher has no `immediate`. It renders `:data-mode-change="modeChange"`.
- Mounting, and a reconnect that remounts the shell, never set the attribute. A resync that commits the same mode does not change it.
- The attribute persists until the next live change. Every animation keyed on it has one iteration, so it plays once.
- Selectors use suffix and prefix matches:
  - `[data-mode-change$="-combat"]` for entering combat
  - `[data-mode-change^="combat-"]` for leaving it

**Flash.** A new `<div class="stage-flash" data-testid="stage-flash" aria-hidden="true">` sits above the backdrop and portraits and below the islands (z 3). Its CSS is `position: absolute; inset: 0; pointer-events: none; background: #fff; opacity: 0`. `[data-mode-change$="-combat"] .stage-flash { animation: elosern-stage-flash var(--motion-flash) var(--ease-standard) 1 }`, with keyframes `50% { opacity: var(--motion-flash-peak) }`. At `reduced` the peak is 0, and at `off` the duration is 0, so the flash is invisible at both. Design §9.1 lists no flash for reduced, and a white flash is a photosensitivity trigger.

**Veil.** `.stage-combat-veil` is always rendered, `aria-hidden="true"`, with `opacity: 0; transition: opacity var(--motion-reveal) var(--ease-standard)`. Under combat mode it has `opacity: 1`. The pulse moves to a `::before` layer that carries the veil gradient, active only in combat, so the pulse's opacity keyframes and the fade's opacity transition never fight over one property.

**Panel flip.**
- `[data-mode-change$="-combat"] [data-anchor="band-command"] > *` plays `elosern-panel-flip-in`.
- `[data-mode-change^="combat-"] [data-anchor="band-command"] > *` plays `elosern-panel-flip-out`.
- Both run over `--motion-panel` with `--ease-enter`: from `transform: perspective(900px) rotateY(calc(±90deg * var(--motion-travel))); opacity: 0` to rest.
- The two names alternate, because a combat entry is always followed by a combat exit, so each change restarts the animation without a script.
- The dock's content has already switched at commit (the combat root), so the flip reveals the committed menu, and the dock keeps focus throughout.

The keyframes live in `styles/tokens.css` next to the shared ones.

### D3. The host enters and leaves
`AppClient` wraps the host actor:

```
<Transition name="actor-enter" v-bind="inertWhileLeaving">
  <StageActor v-if="…" :key="dialogueVm.host.identity" side="right" … />
</Transition>
```

- Enter from and leave to: `opacity: 0; transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)))`.
- Active: `transition: opacity var(--motion-actor), transform var(--motion-actor)`, with `--ease-enter` on enter and `--ease-exit` on leave.
- Keying by host identity makes a host change during a session (a new host, not a new portrait) slide one actor out and the next in, while C11b's crossfade handles a new portrait for the same host.
- The actor has no focusable element, and `inert` covers pointer hits while it leaves.

### D4. The name plate
`MessageWindow` wraps the plate in `<Transition name="plate" v-bind="inertWhileLeaving">`.
- Enter: opacity 0 → 1 over `--motion-reveal`.
- Leave: `position: absolute` (so the text area is not held open), opacity → 0 over `--motion-reveal`.
- The plate takes its 30px row at commit, and the window re-pages once.

### D5. The choices stagger
- `DialogueChoices`' root becomes `<TransitionGroup tag="div" name="choice-row" appear class="dialogue-choices" role="menu" …>`. The attributes and the keydown listener fall through to the rendered `div`, so the single-tab-stop menu contract of C10c is unchanged.
- Each row carries `:style="{ '--row-index': index }"`.
- CSS:
  - `.choice-row-enter-from { opacity: 0; transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel))) }`
  - `.choice-row-enter-active { transition: opacity var(--motion-reveal) var(--ease-enter), transform var(--motion-reveal) var(--ease-enter); transition-delay: calc(var(--motion-stagger) * var(--row-index)) }`
- No leave or move classes, so rows swapped out by `↦ 移動…` or its return are removed at once, and the new view's rows stagger in.
- `AppClient` wraps `#choices`' `DialogueChoices` in `<Transition name="choices-card">`, with an enter fade over `--motion-reveal` and no leave animation. The list vanishes at activation, after C10c D7 has moved focus to the page surface.
- Rows are in the DOM from the first frame. C10c D7's focus-on-show and every key and pointer path work immediately, and a digit activates a row still fading in.

### D6. Focus and reach
- **Entering dialogue.** C10b's pre-flush rescue moves focus from `band-command` to `message-page` before the patch that sets `inert`, so focus never drops to the body.
- **Leaving dialogue.** The post-flush rescue focuses `#action-dock`, whose region cleared `inert` in the same patch and is sliding in. An entering element is in reach from its first frame.
- **Combat.** The dock never leaves, so focus stays on it through the flip.
- **Choices.** The list is focusable from its first frame (D5).
- **Leaving copies.** The leaving host actor and the leaving plate are inert (D3, D4).

### D7. Drawers and overlays are unchanged
Design §9.3 keeps drawers "as today", and C11a already makes them obey the level: every drawer and recession duration is `--motion-base`, which is 0 at `reduced` and `off`. Making the drawer's mount slide actually play would change drawer presentation, which the design's non-goals exclude, so nothing is edited. `OverlayHost` has no transition.

### D8. Tests
- **Vitest** `tests/mode_transitions.test.js`, with `stubs: { transition: false, 'transition-group': false }` where hooks matter:
  - `HudFrame` mounted in combat has no `data-mode-change`. A prop change from exploration to combat gives `exploration-combat`, and a change back gives `combat-exploration`.
  - The `band-command` anchor is `inert` exactly in dialogue.
  - `.stage-flash` and `.stage-combat-veil` are `aria-hidden` and rendered in every mode.
  - In `AppClient`, the host `StageActor` gets `inert` while leaving on the return to exploration.
  - `DialogueChoices` rows carry `--row-index` 0…N−1, the root keeps `role="menu"` and `tabindex="0"`, and a keydown on the root before any `transitionend` activates a pick.
  - `tests/hud_frame.test.js`: the dialogue case asserts `inert` plus the one-column band, instead of `display:none`.
  - `tests/dialogue_choices.test.js` stays green with the group.
- **Browser** `web/tests/browser/test_browser_mode_transitions.py` at 1920x1080. It polls DOM state and reads computed styles, never elapsed time.
  - `test_dialogue_enter_and_leave_full` (`motion_level=None`, which is `full`):
    - after 交談: `band-message` width is the band's width at once, `band-command` has `inert` and a computed `transition-duration` containing `0.25s`, it ends `visibility: hidden`, the host actor's enter transition is `0.35s`, and the plate is present
    - after 結束對話: the leaving actor is inert, the dock is focused, and `band-command` is not inert in the commit's frame
  - `test_combat_enter_and_leave_full`: inject combat. The stage has `data-mode-change="exploration-combat"`, `.stage-flash`'s `getAnimations()` shows `elosern-stage-flash` at 120ms, the veil's opacity transition is `0.25s`, and the band-command child runs `elosern-panel-flip-in`. Inject exploration: `combat-exploration`, and no flash animation.
  - `test_choices_stagger_full`: once the choices show, rows have `transition-delay` `0s`, `0.04s`, `0.08s`, …, the list is focused, and a digit press activates at once.
  - `test_reload_in_combat_plays_nothing`: after a reload in combat, `data-mode-change` is absent and `.stage-flash` has no animations.
  - `test_mode_transitions_reduced` (`motion_level="reduced"`): band-command, actor, and plate durations are ≤ `0.15s`, the computed transforms stay identity, the flash's peak resolves to 0, and every row's delay is `0s`.
  - `test_mode_transitions_off` (default `off`): in the frame after each commit, every surface is in its final state: `visibility: hidden` on the collapsed region, no leaving copy, and the veil at its final opacity.
  - Annotate all of them with `webclient-contextual-hud::mode-changes-transition-at-the-motion-level`. Also annotate the dialogue journey with the collapse ID and the combat journey with the visibility ID.
  - Update any `display:none` assertion on the dialogue command region in `test_browser_exploration_dialogue.py`, `test_browser_contextual_hud_stage.py`, and `test_browser_layout.py` to "hidden and inert". Playwright's `is_hidden` already treats `visibility: hidden` as hidden, and the suite's default `off` level makes the state immediate.
- **Evidence:** `test_node_suite_evidence.py` gains `test_mode_transitions_vitest_evidence_passes`, annotated with the new ID.

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
- [An element that is `inert` but still painted could confuse sighted keyboard users] → Focus has already moved (D6), and the element is gone within 250ms.
- [The CSS animation restart depends on alternating names] → Mode sequences always alternate entering and leaving combat. A browser journey asserts a second combat entry flashes again.
- [Budget] → collapse slide (1.5h), hook, flash, veil, and flip (2h), actor and plate (0.75h), stagger (0.75h), Vitest (1h), browser (1.5h), specs and gates (0.5h). About 8h.

## Migration Plan

None. The client is unreleased, and nothing is persisted.
