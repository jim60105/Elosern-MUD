# Design

## Context

- `web/webclient-app/components/PlaceCard.vue` (HEAD 20b9f0c4) has a global (unscoped) `<style>` block. `.place-card` carries the island box: `padding`, `background: linear-gradient(90deg, #bda47714, transparent 55%), var(--panel)`, `backdrop-filter`, `border: var(--line)`, `border-radius: var(--radius)`, `box-shadow`. `.place-card__action` is an outlined pill (`border: 1px solid #736b5c`, `border-radius: var(--radius-sm)`, `--f-sans`). `.place-card-enter-from` translates by `calc(-1 * var(--motion-shift-lg) * var(--motion-travel))` (from the left).
- `web/webclient-app/styles/app-shell.css` repeats `.place-card { padding: …; row-gap: … }` and `.place-card__time { line-height: 1.2; }` under `@media (max-height: 820px)` (lines ~208-212). A global rule there would override the panel padding that clears the spine.
- `map-column-instrument-geometry` (depends-on) has already set the column to `--map-column-w` with a 10px gap and removed that block's `map` gap line.
- The approved prototype is `docs/design/map-column-instrument-panels/PlaceCardInstrument.vue` with `instrument-panel.css`; its code comments record why each choice reads better.
- Tests that must keep passing unchanged in intent: `web/webclient-app/tests/place_card.test.js` (testid order `place-card__location`, `place-card__rule`, `place-card__time`; `[data-testid="anchor-map"] > [data-testid="place-card"]:first-child`; button testids, `aria-label`, `休息` text, `place-card__action--wait` class; `hover` payloads), `tests/app_client_room_actions.test.js`, `tests/preserved_contract.test.js`, and the browser journeys that click `place-card-look` / `place-card-wait`.

## Goals / Non-Goals

**Goals:**

- One shared, reusable instrument-panel stylesheet for the `map` column.
- The place card wears it, right-aligns its two lines, carries chromeless room actions and slides a new location in from the right.

**Non-Goals:**

- Any change to PlaceCard's props, emits, `data-testid`s, `aria-label`s, the `inertWhileLeaving` binding, the Tab chaining (`onTab`), the readout content (`PLACE_LOOK_READOUT`, `PLACE_WAIT_READOUT`) or AppShell's mounting.
- Refactoring the vitals dock (`StatusPanel.vue`) onto the shared stylesheet; it keeps its own left-anchored chrome.
- Restyling `RiteEntry.vue` or `TitleBallotMenu.vue`.
- Touching `LocalMap.vue` or `ObjectiveTracker.vue` (the next two changes).

## Decisions

### D1. Shared chrome: `web/webclient-app/components/instrument-panel.css`

A plain stylesheet beside the components (the precedent is `components/gallery.css`, imported by its components), so it is loaded wherever a consumer is mounted, in the client and in Storybook alike. Create it verbatim:

```css
/* The instrument panel chrome (place-card-instrument-panel), after
   docs/development/hud-instrument-panels.md and the approved prototype
   docs/design/map-column-instrument-panels/instrument-panel.css, for a panel
   in the top-right `map` column: anchored on the top and right edges, so the
   lozenge sits at the top-right corner, the crown runs left along the top,
   the spine runs down the right side, and the ink ground feathers out to the
   left and towards the bottom.

   Each panel of the column carries its own copy: they share a column, not a
   subject. A panel tunes the chrome through custom properties, each with a
   fallback here:
   --instrument-pad-right  content padding that clears the spine (a px length,
                           multiplied by the chrome factor);
   --instrument-solid      where the ink starts to thin, measured from the
                           right (a percentage or a length);
   --instrument-clear      where the ink is fully gone (default: the left
                           edge).
   The ground never extends past the box: the `map` anchor scrolls vertically
   and clips horizontally, so an overhang would end in a hard edge. */
.instrument-panel {
  position: relative;
  isolation: isolate;
  box-sizing: border-box;
  min-width: 0;
  /* 12px on top clears the lozenge and the crown; 6px at the bottom keeps the
     column's three panels no taller than the three cards they replace (the
     last 12px of ink feather out under it). */
  padding:
    calc(12px * var(--ui-scale))
    calc(var(--instrument-pad-right, 26px) * var(--ui-scale))
    calc(6px * var(--ui-scale))
    calc(10px * var(--ui-scale));
}
.instrument-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--panel);
  backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-mask-image:
    linear-gradient(270deg, #000 0%, #000 var(--instrument-solid, 52%), rgba(0, 0, 0, 0.55) calc((var(--instrument-solid, 52%) + var(--instrument-clear, 100%)) / 2), transparent var(--instrument-clear, 100%)),
    linear-gradient(180deg, #000 0%, #000 calc(100% - 12px * var(--ui-scale)), transparent 100%);
  -webkit-mask-composite: source-in;
  mask-image:
    linear-gradient(270deg, #000 0%, #000 var(--instrument-solid, 52%), rgba(0, 0, 0, 0.55) calc((var(--instrument-solid, 52%) + var(--instrument-clear, 100%)) / 2), transparent var(--instrument-clear, 100%)),
    linear-gradient(180deg, #000 0%, #000 calc(100% - 12px * var(--ui-scale)), transparent 100%);
  mask-composite: intersect;
  pointer-events: none;
}
/* The brass fitting. The spine stands 14px in from the right edge, under the
   lozenge's centre (the lozenge is 30px wide). */
.instrument-panel::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    var(--band-ornament) right 0 top 0 / calc(30px * var(--ui-scale)) calc(11px * var(--ui-scale)) no-repeat,
    linear-gradient(270deg, var(--band-edge), var(--band-edge-dim) 45%, transparent)
      right calc(30px * var(--ui-scale)) top calc(5px * var(--ui-scale)) / calc(72% - 30px * var(--ui-scale)) 1px no-repeat,
    linear-gradient(180deg, var(--band-edge), var(--band-edge-dim) 60%, transparent)
      right calc(14px * var(--ui-scale)) top calc(11px * var(--ui-scale)) / 1px calc(100% - 11px * var(--ui-scale)) no-repeat;
  pointer-events: none;
}
```

Every custom property it reads without a fallback (`--panel`, `--ui-scale`, `--band-ornament`, `--band-edge`, `--band-edge-dim`) is defined in `styles/tokens.css`. Alternative considered: a `<InstrumentPanel>` wrapper component. Rejected: the place card must stay the anchor's direct first child (`place_card.test.js`), and a class composes onto any existing root without changing the DOM.

### D2. `PlaceCard.vue` template and script

- Script: add `import "./instrument-panel.css";` after the existing imports; update the header comment (the card is an instrument panel, place-card-instrument-panel; the location slides in from the right).
- Template: the root `<section>` gains the class: `class="place-card instrument-panel"` (keep `:class="{ 'place-card--actions': actionsEnabled }"`, `data-testid`, `aria-label`). Nothing else in the template changes.

### D3. `PlaceCard.vue` style block

Replace the whole `<style>` block with (global, unscoped as today; the header comment rewritten for the instrument panel):

```css
.place-card {
  width: 100%;
  /* An island in the `map` column's flex stack: never squeezed below its
     content when the column is short (the column scrolls instead). */
  flex: none;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto auto;
  align-content: start;
  row-gap: calc(5px * var(--ui-scale));
  /* The heading's slide stays inside the panel. */
  overflow: hidden;
}
.place-card__location,
.place-card__time {
  margin: 0;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Crisp edges on any art, where the ground has thinned out. */
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8), 0 0 calc(8px * var(--ui-scale)) rgba(11, 13, 16, 0.7);
}
.place-card__location {
  grid-area: 1 / 1;
  align-self: center;
  font: 400 var(--text-lg)/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  /* The tracking adds air after the last glyph; pull it back so the glyph
     edge, not the tracking, meets the right-aligned edge. */
  margin-right: -0.12em;
  color: var(--paper-50);
}
.place-card__rule {
  grid-area: 2 / 1 / 3 / -1;
  justify-self: end;
  display: block;
  width: calc(56px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(270deg, var(--gold-400), rgba(228, 200, 142, 0));
  opacity: 0.75;
}
.place-card__time {
  grid-area: 3 / 1;
  align-self: center;
  font: var(--text-sm)/1.35 var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  letter-spacing: 0.04em;
  color: var(--paper-500);
}
.place-card--actions {
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: calc(6px * var(--ui-scale));
}
/* Chromeless actions: no pill, no fill, no border. The 30px hit box, the
   glyph at rest opacity .86, and a brass tick under the active one. */
.place-card__action {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(3px * var(--ui-scale));
  box-sizing: border-box;
  min-width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-serif);
  letter-spacing: 0.06em;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);
  /* Optical alignment: the hit box has 4px of air around the glyph, so pull
     it towards the spine to line the glyph's edge up with the text edge. */
  margin-right: calc(-4px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  border: 0;
  background: none;
  color: var(--gold-400);
  opacity: 0.86;
  cursor: pointer;
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.place-card__action--look { grid-area: 1 / 2; align-self: center; }
.place-card__action--wait { grid-area: 3 / 2; align-self: center; }
.place-card__action svg {
  flex: none;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.8));
}
.place-card__action::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: calc(2px * var(--ui-scale));
  width: calc(10px * var(--ui-scale));
  height: 1px;
  margin-left: calc(-5px * var(--ui-scale));
  background: var(--gold-500);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.place-card__action:hover,
.place-card__action:focus-visible {
  opacity: 1;
  color: var(--paper-50);
}
.place-card__action:hover::after,
.place-card__action:focus-visible::after {
  opacity: 1;
}
.place-card__action:focus-visible {
  outline: none;
  box-shadow: var(--focus);
  border-radius: var(--radius-sm);
}
/* The location change: a new place slides in from the anchored (right)
   edge while the old name fades where it stands. Without travel (reduced)
   both are plain fades; at `off` the transition has no CSS phase. */
.place-card-enter-active {
  transition:
    opacity calc(var(--motion-reveal) * 0.7) var(--ease-standard) calc(var(--motion-reveal) * 0.3),
    transform var(--motion-reveal) var(--ease-enter);
}
.place-card-leave-active {
  transition: opacity calc(var(--motion-reveal) * 0.5) var(--ease-standard);
}
.place-card-enter-from {
  opacity: 0;
  transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)));
}
.place-card-leave-to {
  opacity: 0;
}
```

The `.place-card` rule declares no padding, background, blur, border, radius or shadow, so the `.instrument-panel` rule (same specificity, different properties) is never overridden. The 休息 button's `padding-right` override from today is dropped (the prototype's symmetric 4px padding with the -4px margin aligns the word's edge with the time line).

### D4. `app-shell.css`

Delete the `.place-card { … }` and `.place-card__time { line-height: 1.2; }` rules inside `@media (max-height: 820px)` and the comment sentence about compacting the place card. The media block keeps its `:root { --stage-inset-y }` and vitals gap lines. At 1280x720 the column may then exceed its anchor; `map-column-instrument-geometry` fades the clipped edge.

### D5. Tests

- `web/webclient-app/tests/place_card.test.js`, add (helpers: a local `rule(source, selector)` that returns the text from `selector {` to the next `}`, built like `hud_frame.test.js`'s `extractRule`):
  - `it("wears the shared instrument panel chrome instead of the island box")`: the mounted root has classes `place-card` and `instrument-panel`; the `.place-card {` rule of `PlaceCard.vue` contains none of `padding`, `background`, `backdrop-filter`, `border`, `border-radius`, `box-shadow`; `PlaceCard.vue` contains `import "./instrument-panel.css";`; `components/instrument-panel.css`'s `.instrument-panel::before` rule contains `background: var(--panel);`, `backdrop-filter: blur(calc(9px * var(--ui-scale)));`, `mask-image:` and `pointer-events: none;`; its `.instrument-panel::after` rule contains `var(--band-ornament) right 0 top 0`, `right calc(14px * var(--ui-scale))` and `pointer-events: none;`; its `.instrument-panel {` rule contains `calc(var(--instrument-pad-right, 26px) * var(--ui-scale))`; and it contains no `border:`, `border-radius` or `box-shadow`. `app-shell.css` does not match `/\.place-card\b/`.
  - `it("sets the room actions without chrome and marks only the active one")`: the `.place-card__action {` rule contains `border: 0;`, `background: none;`, `height: calc(30px * var(--ui-scale));`, `min-width: calc(30px * var(--ui-scale));`, `opacity: 0.86;`; the `.place-card__action::after` rule contains `opacity: 0;` and `background: var(--gold-500);`; the source contains `.place-card__action:hover::after,\n.place-card__action:focus-visible::after {\n  opacity: 1;`; the mounted 休息 button's text is still `休息`.
  - `it("slides a new location in from the right")`: the `.place-card-enter-from` rule contains `transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)));` and no `-1 *`.
- `web/tests/browser/test_browser_scene_transitions.py`, `test_full_motion_place_card_and_clear`: extend `_HEADING_PAIR`'s per-heading object with `tx` parsed from the computed `matrix(a, b, c, d, tx, ty)` (0 for `none`) and assert `by_text["南大道"]["tx"] > 0` (the entering heading is offset to the right while it travels). The reduced-motion test's existing no-slide assertions stay.
- `web/tests/browser/test_browser_proportional_ui_scale.py`, `test_large_desktop_renders_the_reference_at_the_chrome_cap` (~119-127): the comment "The place card compacts under the short-viewport media query…" becomes false once D4 lands. Reword it to say the place card's ratio is measured between the two acceptance sizes above the reference (`UNCAPPED` and `LARGE`); leave the assertion unchanged.
- `web/tests/browser/test_browser_map_column_instruments.py` (created by `map-column-instrument-geometry`), new method `test_place_card_is_an_instrument_panel` decorated `@covers_requirement("webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box", "webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time")`. Live client at `(1280, 720)`, `(1451, 790)`, `(2560, 1440)`; inject `status`, `local_map`, `exploration` (`_exploration_panel([])` from `._journey_support`) and `context_actions` (`_exploration_context_actions_panel()`) in exploration so the room actions render; wait for `[data-testid="place-card-wait"]`; `document.fonts.ready`; park the pointer at the viewport's top-left corner. Assert:
  - `[data-testid="place-card"]` computed `border-top-width`/`border-left-width` `0px`, `border-top-left-radius` `0px`, `box-shadow` `none`, `background-color` `rgba(0, 0, 0, 0)`; `getComputedStyle(card, '::before')` `mask-image` (or `-webkit-mask-image`) not `none` and `background-color` not transparent; `getComputedStyle(card, '::after')` `background-image` contains `url(` or `gradient` (the ornament) and `pointer-events` `none`.
  - The card's width equals `[data-anchor="map"]`'s width (delta 1.0).
  - Heading and time computed `text-align` is `right`; the rule's right edge is within 1px of the card's content-box right (card right minus its computed `padding-right`).
  - Each of `place-card__location`, `place-card__time`, `place-card-look`, `place-card-wait` has `right <= card.right - 14 * ui_scale(viewport) + 0.5`.
  - Both buttons: computed `border-top-width` `0px`, `background-color` `rgba(0, 0, 0, 0)`, rect width and height `>= 30 * ui_scale(viewport) - 0.5`; `place-card-wait` inner text is `休息`; `getComputedStyle(btn, '::after').opacity` is `0` for both; after `page.hover(PLACE_LOOK_SELECTOR)`, `page.wait_for_function` until the look button's `::after` opacity is `1` (the tick fades over `--motion-fast`), then assert the wait button's is still `0`.
  - Fit with actions visible: the injection also carries `art` (`valid_art_panel()`) and `objectives` (`_objectives_panel(3)`, the module-level helper of this file). At `(1451, 790)` and `(2560, 1440)` only, assert the anchor's `scrollHeight <= clientHeight + 1` (the column with a two-row action card still fits once the 820px compaction is gone). If it fails, stop and report the measured heights; do not add scroll or change the approved paddings.
  - Register it with `uv run --locked python -m tools.shard_register fix`.

### D6. Stories

`web/webclient-app/stories/Core/PlaceCard.stories.js`: the frame becomes `width: calc(291px * var(--ui-scale))` (the column's width at the 1451x790 reference) with a dark scene-like background so the feathered ground reads (`background: linear-gradient(135deg, #2b3440, #151920); padding: 20px;` on an outer wrapper, the 291px column inside); update the header comment (the card is an instrument panel; 休息 not 等待). Keep every exported story and its args.

### D7. Visual review (human-reviewed)

Review document: the approved prototype `docs/design/map-column-instrument-panels/PlaceCardInstrument.vue` (Storybook `Design/MapColumnInstrument`) against live-client screenshots. The human checks: right alignment against the spine, the leftward-fading rule, heading/time contrast over bright and dark scene art, the actions' resting opacity and brass tick, and the right-to-left slide feel at full motion. The implementer captures live screenshots at 1280x720, 1451x790 and 2560x1440 (actions visible, and one with the look button keyboard-focused) with `agent-browser` into the session scratchpad and lists their paths in the apply report; no test asserts the look.

## Risks / Trade-offs

- [The global `.place-card` styles and the shared stylesheet share specificity] → D3 keeps the two property sets disjoint; the D5 source test fails if `.place-card` regains a padding, background, border, radius or shadow.
- [Dropping the short-viewport compaction makes the column taller at 1280x720] → the geometry change's edge fade covers it; the 1451x790 and 2560x1440 fit is still asserted by `test_populated_island_stack_fits_its_anchor_at_both_viewports`.
- [Text over thinned ink at the left] → the text is right-aligned onto the solid side, with a dark text shadow; human review checks bright art.

## Migration Plan

None (pre-release, client-only presentation).
