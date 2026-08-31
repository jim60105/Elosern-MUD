# Tasks: webclient-map-01-draft-chrome

## 1. Tokens

- [x] 1.1 Add draft map tokens to `web/webclient-app/styles/tokens.css`: `--seal-deep: #a52c31`, `--seal-light: #e06b6b`, `--ink-edge: #3a3344`, `--map-canvas-hi: #1a1420`, `--map-canvas-lo: #0c0a10`, label tiers `--map-label-here: #f2ecdf`, `--map-label-gold: #e2c06a`, `--map-label-seen: #8d8370`, `--map-label-far: #615a4c`; document each with a one-line English comment naming the draft source.

## 2. Shared lattice renderer (`MapLattice.vue`)

- [x] 2.1 Replace marker templates with the draft shape ladder: `current` = seal-deep circle r8 + seal-light stroke sw2 (scaled via existing `markerScale`); `visible_visited` = ink-filled circle r4.5 + `--ink-edge` stroke; `visible_unvisited` = hollow circle r4.5 stroke-only; landmark nodes add the gold `--gold-500` r5 treatment; keep `data-node`/focus/activation wiring and accessible names byte-identical.
- [x] 2.2 Restyle connector edges to draft strokes (traversable solid ink sw2, blocked dashed, unknown faint) via tokens; keep the non-interactive element-constructor layer and accessible-name-only edge labels.
- [x] 2.3 Switch node label fills to the label-tier tokens (current / landmark-gold / seen / far) at island scale; keep single-line truncation + accessible full label.
- [x] 2.4 Re-style the shared state legend to draft dot-chips (11×11 radius-3 chip + 11px label, 14px gap): remembered chip dashed gold border vs visited chip solid gold border; keep text labels.

## 3. Minimap island (`LocalMap.vue`)

- [x] 3.1 Restyle island chrome + header to draft `.mini`: radius/border, letterspaced title, the draft's `北↑ 東→` orientation mark pair on coordinate layers only (shipped single `北↑` gains `東→`; keep coordinate-free omission branch).
- [x] 3.2 Add pointer-click convenience: island root click opens the map overlay unless `event.target.closest()` finds an interactive descendant; no role/tabindex added; `local-map__expand` sibling unchanged; `cursor: pointer` on non-interactive body.
- [x] 3.3 Keep the `local-map` root class, remembered list, detail line, meta line, and height-budget canvas cap behavior untouched (verify by diff).

## 4. Full-map overlay (`MapOverlay.vue`)

- [x] 4.1 Wrap the shared lattice in the draft `mapcanvas`: radial-gradient background + rounded ink border as component CSS; no terrain paths.
- [x] 4.2 Render the single teardrop pin inside `MapLattice.vue`'s SVG behind an `overlay-chrome` prop (off on the island), anchored to the placement's current-node coordinates; fixed path, non-interactive, `aria-hidden` (design D4 ownership).
- [x] 4.3 Confirm the overlay legend consumes the dot-chip legend from 2.4 at overlay scale; remembered list/detail line remain absent.

## 5. Tests and stories

- [x] 5.1 Update Vitest geometry/selector expectations in `web/webclient-app/tests/world/map_lattice.test.js`, `world/local_map.test.js`, `overlays/map_overlay.test.js` for circle markers, chip legend, gradient frame, and pin; update the orientation assertion at `world/local_map.test.js:182` to the `北↑ 東→` pair; assert exactly one pin sharing the current marker's x and vertically above its y (design D4 ownership); add the remembered-item-click-does-not-open-map case and the island-click-opens-map case; keep `@covers_requirement` IDs unchanged (headings preserved).
- [x] 5.2 Re-verify stories `stories/World/LocalMap.stories.js` and `stories/Overlays/MapOverlay.stories.js` render the new chrome (no fixture change in this change).
- [x] 5.3 Run focused gates: `npm test`, `node --test web/static/webclient/js/tests/*.test.js` (unchanged logic — must stay green), `uv run --locked python -m tools.spec_traceability check`.
- [x] 5.4 Run the focused browser contract locally: `web/tests/browser/test_browser_contextual_hud.py::ContextualHudBrowserTest::test_h5_overlay_triggers_exclusion_and_focus_restoration` (the minimap expand → Escape → focus-restore flow pinned at :662/:681); this wave must not break it — run it, do not defer to CI.

## 6. Traceability

- [x] 6.1 Confirm the delta requirements' canonical IDs (headings unchanged) each still resolve to at least one annotated test; `tools.spec_traceability check` green.
- [x] 6.2 `openspec validate webclient-map-01-draft-chrome --strict` passes.
