# vitals-bar-redesign — Tasks

## 1. Move the anchor geometry to the stage bottom

- [x] 1.1 In `HudFrame.vue`, change `[data-anchor="vitals"]` CSS from the top-anchored column to a bottom-anchored dock: `bottom: var(--band-h); left: calc(16px * var(--ui-scale)); width: var(--vitals-dock-w);` (the new `--vitals-dock-w: 25vw` token in `tokens.css`) with `max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y))` so it never grows over the top band. Remove the old `top` offset chain. Move the command-line row's `left` to `calc(var(--vitals-dock-w) + 32px * var(--ui-scale))` so it starts 16px past the wider dock.
- [x] 1.2 Mirror the same geometry in `app-shell.css` where it repeats the anchor offsets (keep the two files in step, as their comments demand).
- [x] 1.3 Update the HudFrame header comment: the `vitals` anchor is the lower-left dock standing on the band's top edge, the condition icons over the gauges, allowed to cover the portrait's lowest strip.
- [x] 1.4 Confirm layering: the dock paints above `actor-left` (anchor z-index 4 vs portrait z-index 2 — already true) and stays below the band (z-index 5); the band's seam feather over the dock's lowest strip was checked visually and needs no change.
- [x] 1.5 Flip the reveal direction in `StatusPanel.vue`'s `<style>`: `.vitals-reveal-enter-from` moves from `translateY(-shift)` to `translateY(+shift)` and `.vitals-reveal-leave-to` to `translateY(+shift)` — the dock now rises from the band edge and sinks back into it (spec: "rising 12px into its bottom-anchored resting position"). Keep the durations, the `data-instant` rule, and the transition names byte-identical.

## 2. VitalsTrack: one numeral readout over three thin lines

- [x] 2.1 Restructure `VitalsTrack.vue`: delete the `.vh` header lines and the visible gauge labels; render one readout row (per gauge, in hp/mp/sp order: its icon in the gauge hue and its `current / maximum` numerals, the reading a `role="group"` named by the 生命/魔力/耐力 label) above three thin lines, keeping `data-testid="status-panel__gauge-value--{key}"` on the numerals and `data-testid="status-panel__gauge--{key}"` on each line.
- [x] 2.2 Move the 危險 `low-mark` into the hp reading after its numerals, keeping `data-testid="vitals-low-marker"`; the low recolour moves onto the hp current value.
- [x] 2.3 Keep `.ghost`/`.fill` spans, their transitions, `data-instant`, the 300ms trail delay, and the epoch reset logic byte-identical.
- [x] 2.4 Legibility: the current value in `--paper-50` at tabular mono figures with a dark text-shadow, the maximum receding to `--paper-500`; verified over the populated stage and at full, damaged, low, and empty states.
- [x] 2.5 Tighten the rhythm: the three lines are 4px tall, parted by a 1px seam, each tapering to a point at its far end and running a little shorter than the one above.
- [x] 2.6 Move the island chrome off `.vitals` onto the `StatusPanel` root; `VitalsTrack` becomes transparent.
- [x] 2.7 Keep the combat session line (`status-panel__combat`) above the readout inside the same block, restyled to sit on the transparent dock.

## 3. ConditionChips: chromeless icon row with tooltips

- [x] 3.1 Strip the `.hud` island chrome and the `狀態` header from `ConditionChips.vue`; root becomes a transparent icon row (keep `data-testid="status-panel__conditions"`).
- [x] 3.2 Reduce each chip to the severity glyph icon only (button, `aria-label = conditionLabel(condition)`), fixed icon size; drop the visible name/duration spans.
- [x] 3.3 Add the tooltip: one `role="tooltip"` element stating the condition's label, verbatim duration, and readable modifiers, opened by `mouseenter`/`focus`, closed by `mouseleave`/`blur`/Escape, a scroll or resize, the condition leaving the payload, or the dock hiding; link with `aria-describedby`; teleported to `body` and placed from the icon's box so the scrolling anchor never clips it.
- [x] 3.4 Keep the `+N` overflow icon and its disclosure, restyled chromeless: disclosing a bounded column of the same tooltip content for the hidden conditions, closing on Escape/re-activation.
- [x] 3.5 Empty conditions list renders nothing (rule unchanged).
- [x] 3.6 Escape ladder position: the keydown handler lives in `ConditionChips.vue` and calls `stopPropagation()` on Escape ONLY while a tooltip (or the disclosure) is open, so the shell's drawer/router Escape ladder is untouched otherwise — mirroring `DesktopNavigation.onToolKeydown`'s consumption guard, not a new global rung.

## 4. StatusPanel composition order

- [x] 4.1 In `StatusPanel.vue`, render `ConditionChips` first, then `VitalsTrack`; carry the dock chrome on the root div as the feathered instrument plate (panel ink + blur masked to thin out to the right and top, brass lozenge, crown, and spine from the band tokens). Keep the `<Transition name="vitals-reveal">` + `v-show` + `inertWhileLeaving` contract and `data-testid="status-panel"` byte-stable.
- [x] 4.2 Confirm `AppShell.vue`'s focus-rescue and `HIDDEN_BY_MODE` selectors still match (`[data-anchor='vitals']` unchanged name — no edit needed).

## 5. Tests and stories

- [x] 5.1 Update `status_panel.test.js`, `vitals_track.test.js`: numerals hook lives in the readout (assert `current / maximum` text still resolves via `status-panel__gauge-value--hp`); no visible gauge label; conditions render as glyph-only buttons with the full prose in `aria-label`; no chip name text visible.
- [x] 5.2 Add tooltip behavior tests: hover/focus opens, leave/blur closes, Escape closes and is not consumed when no tooltip is open, and the tooltip closes when its condition leaves or the dock hides; add the anchor-geometry and reveal-direction source assertions to `hud_frame.test.js`.
- [x] 5.3 Update `VitalsTrack.stories.js`, `ConditionChips.stories.js`, `StatusPanel.stories.js` wrapper frames to the 25vw dock width; keep full/damaged/low/empty coverage and the changing-numerals unequal-digit story; add a focused-icon tooltip story.
- [x] 5.4 Run the focused Vitest tests (`pnpm test`) and the Node gate (`node --test web/static/webclient/js/tests/*.test.js`). Update the managed browser tests that measure the vitals anchor (`test_browser_shell_surfaces.py`: a new dock-geometry and tooltip journey; `test_browser_contextual_hud_stage.py`: the command-line row starts past the dock); execution of managed browser tests is CI-owned.

## 6. Verify

- [x] 6.1 Visual smoke at 1920x1080 and 1280x720: dock on the band's edge, lowest-quarter overlap only, numerals legible at full/empty fill, 32-condition overflow reachable.
- [x] 6.2 `openspec validate vitals-bar-redesign --strict` passes.
- [x] 6.3 Run `uv run --locked python -m tools.contract_gate` (seconds; traceability + lints + shard manifests — not a test run; required before handoff).
- [x] 6.4 Run the Storybook gates: `pnpm run build-storybook` and `pnpm run showcase-coverage` (frozen required-set manifest unchanged — VitalsTrack/ConditionChips/StatusPanel stay covered in their restyled dock forms; inspect the updated stories visually: damaged/low numerals, empty lines, 32-condition overflow with +N disclosure, the focused-icon tooltip story).
