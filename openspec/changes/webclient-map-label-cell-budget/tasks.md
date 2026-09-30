## 1. Cell measure

- [ ] 1.1 Add `tools/gen_mono_cells.py` (stdlib only). It reads the regular-weight list of the bundled monospace manifest (`web/webclient-app/fonts/hack/codepoints.json`, a module constant the font change repoints), collapses it into sorted `[lo, hi]` runs, and rewrites the block between `// BEGIN GENERATED one-cell` and `// END GENERATED one-cell` in `web/webclient-app/lib/mono_cells.js` (D1). Verify: `uv run --locked python tools/gen_mono_cells.py` exits 0, and a second run leaves `git status` clean.
- [ ] 1.2 Add `web/webclient-app/lib/mono_cells.js` with `CELL_EM = 1233 / 2048`, `codePointCells(cp)` (binary search over `ONE_CELL_RUNS`: 1 inside, 2 outside), and `textCells(text)` (sum over `Array.from`). Verify: a new Vitest file checks ASCII = 1, `…` = 1, `─` = 1, `（` = 2, `中` = 2, `①` = 2 (absent from Hack), and `textCells("霧骨渡口…") === 9`.
- [ ] 1.3 Add `tests/test_mono_cells_table.py`. It imports the generator's pure render function, rebuilds the block from the manifest in memory, and byte-compares it. Verify: `uv run --locked python -m unittest tests.test_mono_cells_table` passes, and hand-editing one run makes it fail.

## 2. Lattice and marker geometry

- [ ] 2.1 In `use-map-lattice-geometry.js`:
  - compute `labelClearancePitch` from `textCells` per D2;
  - declare `outwardNameCells = (labelMax + 1) × 2` and derive the unit `outwardNameBox` from it per D3;
  - rewrite the neighbouring comments per D5.

  Verify with Vitest cases: labels `霧骨渡口…` / `霧骨渡口…` yield 72 at `labelFont` 12 and 83 at 14; five-ASCII-glyph labels yield 43 at 12.
- [ ] 2.2 In `use-map-lattice-render.js`, give `fitMarkerName` a measure argument and cell-aware greedy head/tail growth. Use `codePointCells` for horizontal names (top/bottom on every surface, left/right on the overlay) and a unit measure for the island's left/right vertical stack. Budget terms follow D3, with integer cells and the `1e-9` guard. Verify with Vitest cases:
  - a mixed name (`北門 Gate`), a `（qualifier）` name, and an all-CJK name each fit their exact cell budget;
  - the overlay's outward box holds five CJK glyphs, and six are truncated;
  - the island vertical-stack result is unchanged for existing fixtures.
- [ ] 2.3 Update the comments in `MapLattice.vue` (`markerNameFont`) and `use-map-lattice-render.js` (`MARKER_NAME_ASCENT`) to the cell model, with no font names (D5). Verify: `git grep -n "Hack\|Noto Sans TC" web/webclient-app/composables web/webclient-app/components/MapLattice.vue` finds nothing.

## 3. Radial contract

- [ ] 3.1 Confirm the radial label type size actually drawn (the 11-unit basis in the contract comment against the surfaces' `labelFont`). In `web/static/webclient/js/elosern/local_map.js`, update the radial contract comment and `RADIAL_GEOMETRY` to the D4 numbers for that basis: 63 × 23, `ARC = 72`, `R0 = G = 77` at 11, or 69 × 23, 77 and 82 at 12. Verify: `node --test web/static/webclient/js/tests/local_map.test.js` passes after 3.2.
- [ ] 3.2 Update `web/static/webclient/js/tests/local_map.test.js`: the `ARC` pin, the chord-sweep threshold, `arcMin`, and any `R0`/`G`-derived expectations. Extend the footprint sweep to use the new label box. Add a check that dynamically imports `web/webclient-app/lib/mono_cells.js` and asserts the declared box width equals `ceil(textCells("霧骨渡口…") × CELL_EM × basis) + 3`. Verify: `node --test web/static/webclient/js/tests/*.test.js` passes.

## 4. Test fixtures and geometry oracle

- [ ] 4.1 Update `web/webclient-app/tests/world/map_lattice_renderer.test.js`: the label box becomes `textCells × CELL_EM × font`, expected pitches and scales are recomputed from D2, and the comment is rewritten per D5. Record in the task notes which fixtures shrink (ASCII labels) and which grow (CJK labels). Update `map_lattice_edge_names.test.js` in the same way. Verify: `CI=true pnpm exec vitest run web/webclient-app/tests/world` passes, and no overlap or containment assertion was removed or widened.
- [ ] 4.2 Run the focused browser geometry oracle, one method per command, each under the 10-minute cap. Verify: all pass; any fixture that crosses the island's 0.75 floor is reported, not accepted.
  - `test_browser_local_map_lattice`: `test_densely_populated_lattice_scales_down_without_reintroducing_overlap`, `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`, `test_long_remembered_list_never_resizes_the_island`
  - `test_browser_local_map_geometry`: `test_minimap_content_stays_inside_its_island`, `test_island_type_ladder_stays_under_its_own_chrome_step`
  - `test_browser_map_legibility`: all three methods
  - `test_browser_local_map_layout_variants`: `test_walked_instance_layer_renders_radial_on_both_surfaces`
  - the browser method(s) behind the scenarios "A lone gateway on an edge carries its whole authored name" and "The disclosure chain ends at the largest surface's declared capacity" (find them with `git grep -n "covers_requirement" web/tests/browser | grep minimap` and the scenario wording)
- [ ] 4.3 Capture agent-browser screenshots (headless, throwaway Chromium) of the Storybook map stories before and after, at 1440×900 and 1280×720:
  - `world-localmap--full-lattice`, `world-localmap--edge-markers`, `world-localmap--instance`;
  - `overlays-mapoverlay--full-lattice`, `overlays-mapoverlay--radial-graph`.

  Verify: no clipped or overlapping label or name, and any pitch or scale change matches D2–D4. Run `agent-browser close` afterwards.

## 5. Gates

- [ ] 5.1 Run the gates. Verify: all green.
  - `CI=true pnpm test`
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `uv run --locked python -m unittest discover -s tests -t .`
  - `uv run --locked python -m tools.contract_gate`
  - `openspec validate webclient-map-label-cell-budget --strict`
- [ ] 5.2 Requirement traceability. The modified requirement keeps its name, so its ID `webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone` is unchanged. Add that ID, as a string literal, to `@covers_requirement` on `tests/test_mono_cells_table.py`. Verify: `uv run --locked python -m tools.spec_traceability check` passes.
