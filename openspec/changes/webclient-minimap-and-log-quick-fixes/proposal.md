## Why

The requester's review of the live client (design `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §1, §11) found three defects that need no layout rewrite. On interior layers the minimap's graph-variant remembered list (`ul.local-map__remembered`, testid `local-map-remembered`) gains one chip per visited room. In the guild hall it lists a dozen places, and the hud-right height-budget measurement shrinks the canvas to make room, so the map can disappear behind its own list. The island draws its lattice at scale 1 with coordinate margin inside a box as wide as the column, so a normal 3×3 neighbourhood fills only the centre of the card, behind two frames (the island border and 9px padding, then the canvas's own border). The full log opens scrolled to the first line, but the player wants the last one or two replies. The project is unreleased, so the list and the measurement machinery are deleted, not kept as an option.

## What Changes

- **BREAKING (internal)**: delete the island's graph-variant remembered list from `web/webclient-app/components/LocalMap.vue`: the `<ul class="local-map__remembered">` element (testid `local-map-remembered`), `showsRememberedList`, the `rememberedEl` ref, and its `.local-map__remembered*` / `.local-map__node-label` CSS. On the graph variant the island instead mounts a visually-hidden, non-focusable mirror (`data-testid="local-map-remembered-mirror"`, labelled `記得的地點`), following the pattern of the existing edge-marker mirror. It has one entry per remembered node, giving the untruncated payload label.
- **BREAKING (internal)**: delete the hud-right height-budget machinery from `LocalMap.vue`: `measureCanvasBudget`, `anchorHeightBudget`, `ANCHOR_BOTTOM_CLEARANCE`, `sectionHeight`, `canvasMaxHeight`, the `metaEl` / `detailEl` refs, the `onMounted` ResizeObserver, and the `onUpdated` re-measure.
- The island becomes a fixed-size card: a 1px hairline border, `--sp-1` (4px) padding, the header row, a **208 × 208 CSS px square canvas**, and the readout row. The row always reserves its one line, so the card never changes size with the payload. The card is right-aligned in the hud-right anchor instead of stretching to the column width. On the island, the canvas drops its own second border.
- `MapLattice.vue` / `composables/use-map-lattice-geometry.js`: the island-only `fieldFill` prop is replaced by a `canvasSize` prop. A surface that sets it gets a fixed square canvas whose viewBox is always square and at least that size, so the uniform scale never exceeds 1:
  - **Lattice (pitch-fit).** The drawn square pitch grows from its derived minimum to fill the canvas less an 8px inset (the marker gutter replaces the inset when it exists). The pitch is capped at 1.5 × the declared pitch. Any remaining slack becomes coordinate margin painted by the dot field. When even the minimum pitch does not fit, the square viewBox grows and the whole drawing scales down uniformly, as today.
  - **Graph.** The radial canvas is cropped to its drawn footprint plus 8px, centred on the current node, and never magnified.
  - Marker radii and label type sizes stay exactly as declared.
- `MapOverlay.vue`: on the graph variant, the full-map overlay renders the remembered nodes as a visible, non-focusable list (`data-testid="map-overlay-remembered"`). Each entry has the diamond indicator and the full name, so a sighted reader who does not use assistive technology can read every remembered room one activation away from the island. On the lattice variant the overlay still presents remembered nodes only as named edge markers.
- `FullLogOverlay.vue`: `focusSelf()` scrolls the overlay to its last line after the focus trap takes focus, so the full log opens at the latest reply. Lines that arrive while the log is open do not move the reader's scroll position.
- Restate the `webclient-local-map` minimap requirement and the `webclient-contextual-hud` minimap-convention requirement for the fixed square island, pitch-fit, the graph-variant mirror, and the overlay list. Remove every height-budget, fixed-point, and "remembered list on the island" clause. Add a full-log requirement to `webclient-input-narrative`.
- No OOB schema, presenter, server, model (`web/static/webclient/js/elosern/local_map.js`), or persistence change.

Out of scope:
- Fitting the full-map overlay to the viewport, zoom / pan / 置中, and moving the overlay legend into a `?` popover belong to `webclient-full-map-fit-view` (C2). C2 keeps this change's overlay remembered list.
- Moving the minimap to the new `map` anchor and adding the objective line belong to `webclient-avg-stage-shell` (C4).
- Paging the log belongs to `webclient-message-paging` (C6).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-local-map`: the minimap rendering requirement ("The browser minimap renders states without relying on color alone") is restated with these changes:
  - The island is a fixed square canvas with a 1px frame, filled by pitch-fit (lattice) or by footprint crop (graph), and the uniform scale never exceeds 1.
  - The island no longer shows the graph-variant remembered list. On that variant it carries a visually-hidden mirror, and the overlay renders the visible list.
  - Every hud-right height-budget, fixed-point, and section-count clause is removed, along with its scenarios.
- `webclient-contextual-hud`: "The minimap island states only its own drawing convention" no longer names a radial-graph list entry as the visible presentation of a remembered node.
- `webclient-input-narrative`: adds "The full-log surface opens at its latest line".

## Impact

- Edited:
  - `web/webclient-app/components/LocalMap.vue`, `MapLattice.vue`, `map-lattice.css`, `MapOverlay.vue`, `FullLogOverlay.vue`
  - `web/webclient-app/composables/use-map-lattice-geometry.js`
  - `web/webclient-app/styles/app-shell.css` (the `.local-map` overrides)
  - Stories `stories/World/LocalMap.stories.js`, `stories/World/MapLattice.stories.js`, `stories/Overlays/MapOverlay.stories.js`
- Vitest:
  - `tests/world/local_map.test.js`
  - `tests/world/map_lattice_fidelity.test.js`
  - `tests/world/map_lattice_name_fit.test.js`
  - `tests/world/map_layout_variants.test.js`
  - `tests/world/map_lattice_legend_labels.test.js` (comment only)
  - `tests/overlays/map_overlay.test.js`
  - `tests/full_log_overlay.test.js`
- Browser tests:
  - `web/tests/browser/test_browser_local_map_geometry.py`
  - `test_browser_local_map_lattice.py`
  - `test_browser_local_map_rendering.py`
  - `test_browser_local_map_layout_variants.py`
  - `test_browser_contextual_hud_stage.py`
- Spec traceability: requirement titles are unchanged except for the added `webclient-input-narrative::the-full-log-surface-opens-at-its-latest-line`, which a browser test in `test_browser_contextual_hud_stage.py` covers.
- Dependencies: none. Later changes in the series build on this one: C2 (`webclient-full-map-fit-view`) and C4 (`webclient-avg-stage-shell`) modify the same two map requirements on top of this change's text.
