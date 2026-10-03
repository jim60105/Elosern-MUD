# vitals-bar-redesign — Tasks

## 1. Move the anchor geometry to the stage bottom

- [ ] 1.1 In `HudFrame.vue`, change `[data-anchor="vitals"]` CSS from the top-anchored column to a bottom-anchored dock: `bottom: var(--band-h); left: calc(16px * var(--ui-scale)); width: calc(262px * var(--ui-scale));` with `max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y))` so it never grows over the top band. Remove the old `top` offset chain.
- [ ] 1.2 Mirror the same geometry in `app-shell.css` where it repeats the anchor offsets (keep the two files in step, as their comments demand).
- [ ] 1.3 Update the HudFrame header comment: the `vitals` anchor is the lower-left dock standing on the band's top edge, the condition icons over the bars, allowed to cover the portrait's lowest strip.
- [ ] 1.4 Confirm layering: the dock paints above `actor-left` (anchor z-index 4 vs portrait z-index 2 — already true); no change needed unless the visual check disagrees.
- [ ] 1.5 Flip the reveal direction in `StatusPanel.vue`'s `<style>`: `.vitals-reveal-enter-from` moves from `translateY(-shift)` to `translateY(+shift)` and `.vitals-reveal-leave-to` to `translateY(+shift)` — the dock now rises from the band edge and sinks back into it (spec: "rising 12px into its bottom-anchored resting position"). Keep the durations, the `data-instant` rule, and the transition names byte-identical.

## 2. VitalsTrack: one compact bar per gauge with on-track numerals

- [ ] 2.1 Restructure the `.vital` block in `VitalsTrack.vue`: delete the `.vh` header line; render one row of icon + label, then the `.track` filling the remainder; move the `.num` numerals inside `.track` as an overlay span (right-aligned, `pointer-events: none` off for AT — it carries the numerals), keeping `data-testid="status-panel__gauge-value--{key}"`.
- [ ] 2.2 Move the 危險 `low-mark` onto the row after the label, keeping `data-testid="vitals-low-marker"` and the low recolour rule.
- [ ] 2.3 Keep `.ghost`/`.fill` spans, their transitions, `data-instant`, the 300ms trail delay, and the epoch reset logic byte-identical.
- [ ] 2.4 Add the legibility treatment for the numerals: dark text-shadow and a right-edge ink plate inside the track; verify over a full hp fill and over the empty ground.
- [ ] 2.5 Tighten the rhythm: shrink the intra-block gap to the compact token (bars gap ≤ 4px * ui-scale) and drop all per-row header margins.
- [ ] 2.6 Move the `.hud` island chrome (fill/blur/border/shadow) off `.vitals` onto the `StatusPanel` root; `VitalsTrack` becomes transparent.
- [ ] 2.7 Keep the combat session line (`status-panel__combat`) above the bars inside the same block, restyled to sit on the transparent dock.

## 3. ConditionChips: chromeless icon row with tooltips

- [ ] 3.1 Strip the `.hud` island chrome and the `狀態` header from `ConditionChips.vue`; root becomes a transparent wrapping icon row (keep `data-testid="status-panel__conditions"`).
- [ ] 3.2 Reduce each chip to the severity glyph icon only (button, `aria-label = conditionLabel(condition)`), fixed glyph size; drop the visible name/duration spans.
- [ ] 3.3 Add the tooltip: one `role="tooltip"` element rendering `conditionLabel(condition)` prose, opened by `mouseenter`/`focus`, closed by `mouseleave`/`blur`/Escape; link with `aria-describedby`; Escape consumed only while a tooltip is open (guard like `DesktopNavigation.onToolKeydown`).
- [ ] 3.4 Keep the `+N` overflow icon and its disclosure, restyled chromeless: disclosing a bounded column of the same tooltip content for the hidden conditions, closing on Escape/re-activation.
- [ ] 3.5 Empty conditions list renders nothing (rule unchanged).
- [ ] 3.6 Escape ladder position: the tooltip keydown handler lives in `ConditionChips.vue` and calls `stopPropagation()` on Escape ONLY while a tooltip is open (guard flag), so the shell's drawer/router Escape ladder is untouched when no tooltip is open — mirroring `DesktopNavigation.onToolKeydown`'s consumption guard, not a new global rung.

## 4. StatusPanel composition order

- [ ] 4.1 In `StatusPanel.vue`, render `ConditionChips` first, then `VitalsTrack`; carry the dock's `.hud` chrome on the root div. Keep the `<Transition name="vitals-reveal">` + `v-show` + `inertWhileLeaving` contract and `data-testid="status-panel"` byte-stable.
- [ ] 4.2 Confirm `AppShell.vue`'s focus-rescue and `HIDDEN_BY_MODE` selectors still match (`[data-anchor='vitals']` unchanged name — no edit needed).

## 5. Tests and stories

- [ ] 5.1 Update `status_panel.test.js`: numerals hook lives on the track overlay (assert `current / maximum` text still resolves via `status-panel__gauge-value--hp`); conditions render as glyph-only buttons with the full prose in `aria-label`; no chip name text visible.
- [ ] 5.2 Add tooltip behavior tests: focus opens, blur closes, Escape closes and is not consumed when no tooltip is open.
- [ ] 5.3 Update `VitalsTrack.stories.js`, `ConditionChips.stories.js`, `StatusPanel.stories.js` wrapper frames to the compact dock width; keep full/damaged/low/empty coverage and the changing-numerals unequal-digit story.
- [ ] 5.4 Run focused Vitest (`pnpm test` on the touched files) and the Node gate; then the browser vitals journey class locally.

## 6. Verify

- [ ] 6.1 Visual smoke at 1920x1080 and 1280x720: dock on the band's edge, feet strip overlap only, numerals legible at full/empty fill, 32-condition overflow reachable.
- [ ] 6.2 `openspec validate vitals-bar-redesign --strict` passes.
