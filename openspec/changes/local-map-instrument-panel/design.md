# Design

## Context

- `web/webclient-app/components/LocalMap.vue` (HEAD 20b9f0c4): root `<aside class="local-map" data-testid="local-map" @click="onIslandClick">`; its first child is the full-bleed `<button class="local-map__affordance" data-testid="local-map__expand">` (`position: absolute; inset: 0`). The header `.local-map__meta` holds the title, `<span v-if="showsOrientation" class="local-map__orientation" data-testid="local-map__orientation">北↑ 東→</span>` and the `.local-map__expand-icon` SVG. `showsOrientation` is `computed(() => props.localMap.layoutVariant === "lattice")`. `MapLattice` gets `:show-axis="true"` and draws `data-testid="local-map__axis"` only when `!isGraph && currentPos` (`MapLattice.vue` line ~557).
- Scoped styles: `.local-map` has `padding: var(--sp-1)`, `background: var(--panel)`, `backdrop-filter`, `border: var(--line)`, `border-radius: var(--radius)`, `box-shadow: var(--shadow)`, `align-self: flex-end`; `.local-map:hover { border-color: var(--ink-600); }`; `.local-map__affordance` `border-radius: var(--radius)`; `.local-map__orientation` rule; `.local-map__footer` `padding-inline: calc(4px * var(--ui-scale))`.
- `web/webclient-app/styles/app-shell.css` lines ~409-410: `.elosern-root .local-map { border-color: #bca57966; }` and `.elosern-root .local-map:hover { border-color: var(--gold-500); }`.
- `place-card-instrument-panel` (depends-on) created `web/webclient-app/components/instrument-panel.css` with the `.instrument-panel` class and its `--instrument-pad-right`, `--instrument-solid`, `--instrument-clear` properties; `map-column-instrument-geometry` made the column at least 282px × S wide.
- The approved prototype `docs/design/map-column-instrument-panels/LocalMapInstrument.vue` wraps the live component in a panel and hides the legend with CSS; this change does the same in the component itself and removes the legend from the DOM.

## Goals / Non-Goals

**Goals:**

- The minimap island sits in its own instrument panel, card-free, with the canvas clear of the spine and the legend gone.
- Every test, story and spec that pinned the legend is updated; the lattice axis cross keeps its behaviour.

**Non-Goals:**

- Any change to `MapLattice.vue`, the projection (`lib/minimap_projection.js`), the island's 240-unit canvas, node/marker/label drawing, the assistive-technology mirrors, the affordance's single-emit click contract, the `move` / `open-map` events, `aimedNode`, or the full-map drawer.
- Removing the axis cross (`:show-axis="true"` stays). Alternative considered: dropping the axis together with the legend, as the old "worded marks license the axis" rule would imply. Rejected: the approved prototype keeps the axis (it hides only the legend), the axis is the lattice's coordinate geometry, and the current-node coordinate readout already states the coordinate claim in words.
- Changing the combat hide rule `.elosern-stage[data-elosern-mode="combat"] .local-map` in `HudFrame.vue` (the whole `map` anchor is `display: none` in combat anyway).
- Editing the prototype under `docs/design/map-column-instrument-panels/`; after this change its "instrument" layout wraps the already-panelled live minimap in a second panel. It stays a historical reference.

## Decisions

### D1. Template: an instrument-panel wrapper around the unchanged island

```html
<template>
  <div class="instrument-panel local-map-panel" data-testid="local-map-panel">
    <aside class="local-map" data-testid="local-map" @click="onIslandClick">
      <!-- unchanged content, minus the orientation span -->
    </aside>
  </div>
</template>
```

- Delete the `<span v-if="showsOrientation" …>北↑ 東→</span>` element, the `showsOrientation` computed and its comment block, and reword the header-row comment (the header holds the title and the decorative open-map glyph; no orientation marks: the minimap never rotates).
- Add `import "./instrument-panel.css";` to the script and a header-comment paragraph (local-map-instrument-panel: the island stands card-free inside its own instrument panel; the canvas clears the spine).
- Keep `isGraph` (the mirrors use it).

Alternative considered: putting the `instrument-panel` class on the `<aside>` itself. Rejected: the full-bleed affordance spans the aside's box, so it would also cover the panel's feathered padding (clicks on the thinned ink would open the map and the focus ring would outline the whole panel); the prototype wraps for the same reason. Consequence: the `map` anchor's direct child is now `local-map-panel`, and the `.local-map` identifier moves one level down (spec scenario "The island keeps the identifier its mode gating selects on").

### D2. Scoped styles

Add:

```css
/* The minimap's instrument panel (local-map-instrument-panel): the canvas
   stands clear of the spine (22px of right padding, the spine at 14px), so
   the brass line runs unbroken past the footer; the ink holds solid under
   the canvas and its clearance (240px + 22px from the right) and feathers
   out over a short 24px band to its left, so the opaque canvas never sits
   on thinned ink. The column is at least 282px wide for this. */
.local-map-panel {
  --instrument-pad-right: 22px;
  --instrument-solid: calc(262px * var(--ui-scale));
  --instrument-clear: calc(286px * var(--ui-scale));
  align-self: stretch;
  width: 100%;
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
```

Change `.local-map`: delete `padding`, `background`, `backdrop-filter`, `-webkit-backdrop-filter`, `border`, `border-radius` and `box-shadow`; keep every other declaration (`position: relative`, flex column, `gap`, sizing, `align-self: flex-end`, fonts, `cursor: pointer`); rewrite its comment (no card; the panel carries the ground). Delete the `.local-map:hover` rule and the `.local-map__orientation` rule with its comment. In `.local-map__affordance` set `border-radius: 0;`. Update `.local-map__affordance:focus-visible`'s comment (the ring traces the island's box, now square) and keep its declarations.

Add to `.local-map__meta` and `.local-map__footer`: `text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);`. Change `.local-map__footer` `padding-inline` to `0`. Change `.local-map__expand-icon` and add the hover rule:

```css
.local-map__expand-icon {
  flex: none;
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  color: var(--gold-400);
  /* The open-map glyph answers the hover the card's border used to answer. */
  opacity: 0.86;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.local-map:hover .local-map__expand-icon,
.local-map:focus-within .local-map__expand-icon {
  opacity: 1;
}
```

Update the `.local-map__detail` comment that lists "title, orientation marks and readout" to "title and readout".

### D3. `app-shell.css`

Delete the two lines `.elosern-root .local-map { border-color: #bca57966; }` and `.elosern-root .local-map:hover { border-color: var(--gold-500); }`.

### D4. Unit tests

- `web/webclient-app/tests/world/local_map.test.js`, add:
  - `it("stands the island card-free inside its own instrument panel")`: `mount(LocalMap, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } })`; `wrapper.element` has classes `instrument-panel` and `local-map-panel` and `data-testid="local-map-panel"`; its only element child is the `aside` with class `local-map` and `data-testid="local-map"`. Source checks on `LocalMap.vue` (`readFileSync`, a local `rule(source, selector)` helper like `hud_frame.test.js`'s `extractRule`): the `.local-map {` rule contains none of `padding`, `background`, `backdrop-filter`, `border:`, `border-radius`, `box-shadow`; the source has no `.local-map:hover {` rule, no `local-map__orientation`, no `showsOrientation`, no `北↑`; the `.local-map-panel {` rule contains the three custom-property lines of D2; the `.local-map__expand-icon {` rule contains `opacity: 0.86;`; the source contains `.local-map:hover .local-map__expand-icon,\n.local-map:focus-within .local-map__expand-icon {\n  opacity: 1;`; `LocalMap.vue` contains `import "./instrument-panel.css";`; `styles/app-shell.css` does not match `/\.local-map\b/`.
  - `it("states no orientation legend on any layer and draws the axis only on the lattice")`: for `LOCAL_MAP_SAMPLE` (grid), `LOCAL_MAP_WILDERNESS_SAMPLE`, `LOCAL_MAP_INTERIOR_SAMPLE`, `LOCAL_MAP_INSTANCE_SAMPLE`: no `[data-testid="local-map__orientation"]`, and the island text contains neither `北↑` nor `東→`; `[data-testid="local-map__axis"]` exists for the two lattice samples and not for the two graph samples.
- `web/webclient-app/tests/world/local_map.test.js`, existing tests that the change breaks and how each is handled (line numbers as of the proposal commit):
  - ~235-239 `it("keeps the .local-map root class the mode-gate CSS selects on")`: delete it; the first new test above replaces it (the root is now `local-map-panel`, the `aside` keeps `.local-map`).
  - ~241-252 `it("shows the orientation legend on grid and wilderness layers only")` and ~254-263 `it("omits the orientation legend on the coordinate-free instance and interior layers")`: delete both; the second new test above replaces them.
  - ~435 `expect(w.find('[data-testid="local-map__orientation"]').exists()).toBe(true);` and its comment `// The axis marks stay in the header…`: change to `.toBe(false)` with the comment `// The header states no orientation legend.`
  - ~591 the `for (const selector of [...])` loop: drop `".local-map__orientation"` from the array (keep `.local-map__meta` and `.local-map__detail`), and remove "orientation marks" from the comment at ~587.
  - Comments at ~51 and ~229-233 that mention the orientation legend: reword to say the meta line carries the title only and the island stands inside its instrument panel.
- `web/webclient-app/tests/world/map_layout_variants.test.js`: in "live-swaps an interior payload replacement to the radial layout" replace the two orientation assertions with `local-map__axis` existence (true before the swap, false after) and an assertion that no orientation element exists either time; rewrite "drives the orientation legend from layoutVariant, not the payload layer" as `it("draws the axis cross from the resolved layout variant and states no legend", …)`: a model with `layoutVariant: undefined` (which `LocalMap` and `MapLattice` resolve to the lattice) and the lattice model both draw `local-map__axis`, an interior model draws none, and no orientation element ever exists.
- `web/webclient-app/tests/overlays/objective_tracker_integration.test.js`: the expected `mapChildren` becomes `["place-card", "local-map-panel", "objective-tracker", "title-ballot-menu"]`.
- `web/webclient-app/tests/hud_frame.test.js`: run it; if any assertion reads the map anchor's direct children by `local-map`, update it to `local-map-panel` (descendant queries such as `[data-anchor="map"] [data-node]` need no change).

### D5. Browser tests

- `web/tests/browser/test_browser_contextual_hud_stage.py`, `test_minimap_island_single_affordance_keyboard_and_movement` (lines ~700-727): replace the orientation block with `self.assertEqual(page.locator('[data-testid="local-map__orientation"]').count(), 0)` plus the existing axis-count assertion (now commented as the lattice's own geometry); replace the drawer's orientation-count assertion with a page-wide count of 0; at line ~811 keep the axis-absent assertion and the page-wide orientation count of 0, rewording the comment.
- `web/tests/browser/test_browser_local_map_layout_variants.py`: in `_surface`, replace the `orientation` key with `axis: !!svg.querySelector('[data-testid="local-map__axis"]')` and add `legend: !!root.querySelector('[data-testid="local-map__orientation"]')`; update the docstring. At line ~202 assert `island["axis"]` is true and `island["legend"]` false; at ~291 assert `island["axis"]` false and `island["legend"]` false; at ~361 assert `surface["axis"]` false and `surface["legend"]` false.
- `web/tests/browser/test_browser_map_legibility.py` (~158, ~169): delete the `orientation` probe key and its assertion.
- `web/tests/browser/test_browser_local_map_geometry.py` (~498, ~549): reword the comments that list orientation marks (no assertion change).
- `web/tests/browser/test_browser_map_column_instruments.py`, new method `test_minimap_is_a_card_free_instrument_panel`, decorated `@covers_requirement("webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention", "webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box", "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure")`. Live client at `(1280, 720)`, `(1451, 790)`, `(2560, 1440)` with `status`, `valid_local_map_panel()` and `art` in exploration; `document.fonts.ready`; park the pointer at `(5, 5)`. With `S = ui_scale(viewport)`:
  - `[data-testid="local-map-panel"]`: border widths `0px`, `border-top-left-radius` `0px`, `box-shadow` `none`, `background-color` `rgba(0, 0, 0, 0)`; `::before` mask not `none`; `::after` `pointer-events` `none`; its width equals `[data-anchor="map"]`'s width (delta 1.0); its left and right equal `[data-testid="place-card"]`'s (delta 1.0); its top minus the place card's bottom equals `10 * S` (delta 1.0).
  - `[data-testid="local-map"]`: border widths `0px`, `box-shadow` `none`, `background-color` `rgba(0, 0, 0, 0)`, padding `0px` on all four sides.
  - `[data-testid="local-map__lattice"]` rect: width and height `240 * S` (delta 1.0); `panel.right - lattice.right` equals `22 * S` (delta 1.0); its computed `background-image` still contains `linear-gradient` (the corner brackets).
  - No `[data-testid="local-map__orientation"]` on the page; `.local-map [data-testid="local-map__axis"]` count is 1 (the seeded grid payload is a lattice).
  - `.local-map__expand-icon` computed opacity `0.86`; after `page.hover('[data-testid="local-map-detail"]')` wait until it is `1`; after moving the pointer back to `(5, 5)` and `page.focus('[data-testid="local-map__expand"]')`, wait until it is `1`.
  - Register it with `uv run --locked python -m tools.shard_register fix`.

### D6. Stories

- `web/webclient-app/stories/World/LocalMap.stories.js`: `renderMap` frames the component in `h("div", { style: "padding: 20px; background: linear-gradient(135deg, #2b3440, #151920);" }, [h("div", { style: "width: calc(291px * var(--ui-scale)); display: flex; flex-direction: column;" }, [h(LocalMap, args)])])` (the column's width at the 1451x790 reference); rewrite the header comment (no orientation legend; the island stands card-free inside its instrument panel) and the frame comment. Keep every export and its args. Other renderers in the file that frame `LocalMap` directly get the same 291px column.
- `web/webclient-app/stories/fixtures/local_map.js`: reword the comments at ~328, ~356, ~425, ~478 that mention the orientation legend (no data change).

### D7. Visual review (human-reviewed)

Review document: the approved prototype `docs/design/map-column-instrument-panels/LocalMapInstrument.vue` (Storybook `Design/MapColumnInstrument`) against live-client screenshots. The human checks: the unbroken spine beside the canvas, the solid ink under the canvas with the short left feather, the corner brackets reading as the canvas's only frame, the header without the legend, and the glyph's hover lift. The implementer captures live screenshots at 1280x720, 1451x790 and 2560x1440 (one with the island hovered) with `agent-browser` into the session scratchpad and lists their paths in the apply report; no test asserts the look.

## Risks / Trade-offs

- [The anchor's direct child changes from `local-map` to `local-map-panel`] → only one known test reads the direct children (D4); every other selector is a descendant query on `data-testid="local-map"`, which still exists.
- [Specs no longer pair the axis cross with worded marks] → the requirement rewrite states the axis as lattice geometry drawn only on the island's lattice; the full-map surface still draws none, and the vitest/browser assertions keep that.
- [Legacy scenario titles in the MODIFIED requirements still say the convention is "stated" or "worded"] → the validator keeps scenario names inside a MODIFIED requirement, so these titles stay while their bodies now describe the axis-only, legend-free behaviour: "The axis is drawn only where the convention is stated in words", "The stated convention and the drawn axis travel together", "A single-node room states orientation without any collision risk", "The orientation mark follows the resolved layout", "A coordinate-free layer omits the legend" (webclient-local-map) and "The island states the axis convention on a coordinate-bearing layer" (webclient-contextual-hud). The scenario body governs; implementers must not restore a legend to match a title.
- [Size: this is the batch's largest change (spec rewrite, about six unit-test edits, four browser files, stories and fixtures)] → accepted as about 1.3 engineer-days rather than split; the spec text is already written in this change, so the implementer's work is code, tests and comments only.
- [Hover on the panel's feathered padding no longer reacts] → intended: only the island (title, canvas, footer) is the map affordance, as before.

## Migration Plan

None (pre-release, client-only presentation).
