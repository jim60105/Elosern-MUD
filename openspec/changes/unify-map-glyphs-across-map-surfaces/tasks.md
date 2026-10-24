# Tasks

Each task is marked as follows:
- **[EXISTS]**: already implemented, uncommitted, under `web/webclient-app/` in the primary checkout. That includes the untracked `components/MapNodeGlyph.vue`, `components/WorldMapGlyph.vue` and `components/world-map-ink.css`. Apply adopts that diff into `.worktrees/unify-map-glyphs-across-map-surfaces` on `feat/unify-map-glyphs-across-map-surfaces` and verifies it.
- **[NEW]**: still to be built.
- **[EXISTS+NEW]**: adopt the existing diff, then extend it.

Tick a box only after its verification passes in the worktree.

## 1. Shared glyph sources and proportional scaling

- [ ] 1.1 [EXISTS+NEW] `components/MapNodeGlyph.vue`.
  - Adopt: the state, gate, travel, selected, `markerClass`, `haloClass` and `testIds` contract, and the styles moved from AreaMapView.
  - New: replace the radius-only `scale` prop with `size` (default 1). Make it a single root `<g transform="scale(size)">` around base-unit shapes, with no `vector-effect`. Make `gatePath()` return the base path.
  - Verify in Vitest: a mount with `size=0.5` keeps the base `r` and `d` attributes, the root group carries `scale(0.5)`, and the component source holds no `vector-effect`.
  - Verify in a Storybook play (task 6.2): the halved rendered box, stroke width and dash lengths. jsdom has no layout, so these checks cannot run in Vitest.
- [ ] 1.2 [EXISTS+NEW] `lib/map_marker_geometry.js`.
  - Adopt: the base constants, `GATE_FOOTPRINT = hypot(9, 9)` and `paintedMarkerFootprint`.
  - New: export `ISLAND_GLYPH_SCALE = 0.75`, the single definition, and `AREA_CELL_GLYPH_SCALE = 0.875`. Change the signature to `paintedMarkerFootprint(node, size = 1)`, returning the base value times `size`.
  - Verify: `tests/minimap_projection.test.js` is re-baselined. Base footprints are 16/14/hypot(9,9)/6.5. The scaled island footprints are those values times 0.75. The default spread clearance is `2 × 16 × 0.75`.
- [ ] 1.3 [EXISTS+NEW] `components/WorldMapGlyph.vue` and `components/world-map-ink.css`, included scoped in `WorldMapView.vue`.
  - New: give `WorldMapGlyph` a single `<g>` root and drop its `vector-effect: non-scaling-stroke`, so strokes scale with `scale(uiScale)`.
  - Verify in Vitest: `tests/world/world_map_view.test.js` passes, the glyph group carries `scale(uiScale)`, and `WorldMapGlyph.vue`'s source holds no `vector-effect`.
  - Verify in the browser (task 7.3, or a Storybook play): the computed `vector-effect` of the glyph shapes is `none`.
- [ ] 1.4 [NEW] Shared area ink.
  - Create `components/area-map-ink.css` for the road casing and core rules (walked, frontier, travel), and include it scoped in `AreaMapView.vue` and `MapDrawer.vue`.
  - Create `components/MapCommissionGlyph.vue`, holding the diamond `M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z` and its paint, and use it for AreaMapView's point-node commission.
  - Verify: `tests/world/area_map_view.test.js` passes, and no `.area-map__road*` or `.area-map__quest` paint rule remains in AreaMapView's own style block.
- [ ] 1.5 [NEW] Create `components/WorldHatchPattern.vue` (8×8 `userSpaceOnUse`, `rotate(45)`, owning the hatch line and its rule). Use it in WorldMapView's `<defs>` with the uid-scoped id, and move the hatch-line rule out of `world-map-ink.css`.
  - Verify: the world-map hatch tests pass, and WorldMapView declares no hatch `<pattern>` geometry inline (its swell pattern is not hatching).

## 2. Minimap island uses the area map's glyphs at the island scale

- [ ] 2.1 [EXISTS] `MapLattice.vue` node rendering:
  - the `local-map__glyph` and `local-map__here` wrapper;
  - `glyphState` (`visible_unvisited` to seen; visited and remembered to visited);
  - the primary-shape classes, the `local-map__gate-glyph` and `local-map__actionable` hooks and the `data-testid`s;
  - the in-canvas landmark ring removed.

  Verify: `tests/world/map_lattice_legend_labels.test.js` (visited dot, no `.local-map__landmark`, including a landmark node with a move action) and `tests/world/map_lattice_renderer.test.js` (base arch path equals the area map's).
- [ ] 2.2 [NEW] `MapLattice.vue` computes `glyphSize`: `ISLAND_GLYPH_SCALE` for the lattice variant, and `ISLAND_GLYPH_SCALE * markerScale` for the graph variant. It passes that value to `MapNodeGlyph`, and the stub start becomes `(HALO_R + 1) × glyphSize`. In `use-map-lattice-render.js`, the graph `labelY()` uses `LABEL_BASELINE_HALF = HALO_R + 1` times `glyphSize`.
  - Verify with Vitest cases:
    - the lattice glyph group is `scale(0.75)` at `markerScale` 1 and also at 2;
    - the graph glyph group is `scale(0.75 × markerScale)`;
    - the stub line starts at radius 12.
  - Re-baseline `tests/world/map_layout_variants.test.js` and `tests/world/map_lattice_name_fit.test.js` for the graph label offset and glyph sizes.
  - Update `stories/World/MapLattice.stories.js` plays that depend on `markerScale`.
- [ ] 2.3 [NEW] Island footprints.
  - Pass the scale through: `minimap_projection.js` `spreadExits` uses `paintedMarkerFootprint(node, ISLAND_GLYPH_SCALE)`, and `use-map-lattice-geometry.js` `nodeFootprint` uses the variant's `glyphSize` (task 2.2).
  - Label-layout obstacles become `Math.max(HALO_R × s, footprint)`.
  - Verify by re-baselining:
    - `tests/minimap_projection.test.js` (explicit footprint and grouped overlap);
    - `tests/world/local_map.test.js` (gateway-feet spacing `2 × 16 × 0.75 = 24`, and the current label `y = 14 × 0.75 + 3 + 0.8 × 16 = 26.3`);
    - `tests/world/map_lattice_renderer.test.js` (actionable gate spacing).
  - Add a case that changes the constant (mocked) and asserts that glyph size, footprint, stub start and aim ring all follow it.
- [ ] 2.4 [EXISTS+NEW] `composables/use-map-lattice-geometry.js`.
  - New: `MARKER_CURRENT_RING_R = HALO_R * ISLAND_GLYPH_SCALE + 2`, and the comment becomes `R_MAX + HALO_R × s`.
  - Verify: a Vitest case asserts that the aim ring's inner stroke edge, at its 1.6 px stroke, exceeds the halo's outer edge `(15 + 0.6) × 0.75`. The exit-compass aim tests pass.
- [ ] 2.5 [EXISTS] Glide and dissolve retarget to `.local-map__here` (`MapLattice.vue`, `composables/use-island-dissolve.js`, `map-lattice.css`), and the old ladder, landmark, actionable and gate-glyph CSS removed.
  - Verify: `tests/world/map_lattice_scale_motion.test.js` and the dissolve tests pass. A case asserts that `map-lattice.css` holds no `.local-map__marker*`, `.local-map__actionable` or `.local-map__gate-glyph` paint rule.
- [ ] 2.6 [EXISTS] A current gateway shows the here-seal and keeps its `通往 <leads_to>` line, with no arch.
  - Verify: `tests/world/local_map.test.js` ("draws the current gate room's here seal, room name and 通往 line on the city side").

## 3. Area map wilderness cells

- [ ] 3.1 [NEW] The AreaMapView `node.cell` branch draws `MapNodeGlyph` (current, gate) and `MapCommissionGlyph` at `AREA_CELL_GLYPH_SCALE`, keeping the corner offset. Delete the private r13/9/5 seal, the 7-unit arch, the cell pin path and their `area-map__here-*` and `area-map__gate` rules.
  - Verify: a Vitest case on a wilderness area map asserts that the cell current, gate and commission marks use the shared classes and base paths inside a `scale(0.875)` group. It also asserts that no `area-map__here-*` or `area-map__gate` element remains, and that the scaled glyph's extent (`HERE_GLOW_R × 0.875 = 12.25`) is no more than half of the smallest cell side in the `tests/world/area_map_view.test.js` wilderness fixture at its minimum zoom stop. If it is larger, lower `AREA_CELL_GLYPH_SCALE` and record the new value in `design.md`.

## 4. Island label fix

- [ ] 4.1 [EXISTS] The `lib/island_labels.js` raster-fallback guard: skip a box when `reach < request.footprint + LABEL_GAP`.
  - New test in `tests/world/island_labels.test.js`: without the guard, the nearest raster box lies inside the label's own footprint. Verify the label lands outside it.

## 5. Map drawer legend

- [ ] 5.1 [EXISTS+NEW] Area legend tab.
  - Adopt: the `lg-svg` samples and the `MapNodeGlyph` samples (current, visited, seen, visited+travel, visited+gate).
  - New: the road samples use `<g class="area-map__road is-walked|is-frontier">` from `area-map-ink.css`, and the commission sample uses `MapCommissionGlyph`. Delete `.lg-road__*` and `.lg-quest`.
- [ ] 5.2 [EXISTS+NEW] World legend tab.
  - Adopt: the `WorldMapGlyph` samples, the `world-map-ink.css` include, the approx ring r14, and the removal of every `.lg--*` rule.
  - New: the hatch sample uses `WorldHatchPattern` instead of its own `<pattern>`.
- [ ] 5.3 [NEW] In `tests/world/map_drawer.test.js`, add the describe block "every map surface draws a shared map concept from its one glyph source". It asserts:
  - island and area-map node shapes are identical after dividing out each group's scale (path `d`, `r`, classes);
  - island strokes scale with the group;
  - the island has no landmark ring or outline arch;
  - the wilderness cell marks are the shared glyphs;
  - the legend road and commission samples carry the shared classes;
  - MapDrawer and WorldMapView both render the shared hatch pattern.

  Verify it passes.
- [ ] 5.4 [NEW] Add the describe block "map legend samples are drawn by the map they explain". It asserts:
  - SVG-only samples, with no `.lg`, `.lg-road__*` or `.lg-quest` element;
  - the area gate `d` equals the map's;
  - the seen sample is `.map-glyph__dot.is-seen`;
  - the world samples carry the `world-map__*` classes and the shared hatch pattern;
  - the approx ring is r14.

  Verify it passes.
- [ ] 5.5 [NEW] Add a static single-source guard test, in Vitest reading the component sources. It asserts that:
  - the hatch pattern geometry (`patternTransform="rotate(45)"` and the `world-map__hatch-line` rule) appears only in `WorldHatchPattern.vue` (the area dot field and the world swell `<pattern>`s are not hatching);
  - the gate arch path is produced only by `gatePath()` in `lib/map_marker_geometry.js`, and no `.vue` file holds an arch path literal (`A8 8 0 0 1` or `A7 7 0 0 1`);
  - the diamond literal `M0 -7.5 L5.5 0` appears only in `MapCommissionGlyph.vue`;
  - no `.lg-road`, `.lg-quest`, `.lg--`, `area-map__here-` or `area-map__gate` rule or element remains in any component.

  Verify it passes.
- [ ] 5.6 [NEW] In "the drawer current marker makes one truthful position claim", add a case: the island current node draws one `map-glyph__here-glow/ring/dot` set at base radii 14/10/6 inside a `scale(ISLAND_GLYPH_SCALE)` group. Verify the block passes.

## 6. Storybook

- [ ] 6.1 [EXISTS+NEW] In `stories/Overlays/MapDrawer.stories.js`, adopt `LegendAreaGlyphs` and `LegendWorldGlyphs`.
  - New: their plays also assert the shared road and commission classes and the shared hatch pattern.
  - New: add an area play on a wilderness layer, or extend an existing wilderness area story, asserting that the cell marks are `MapNodeGlyph` or `MapCommissionGlyph`. Do not add a new story title (frozen manifest).
- [ ] 6.2 [EXISTS+NEW] In `stories/World/LocalMap.stories.js`, adopt the `MetricAltoriaSouthGate` here-seal assertion.
  - New: assert that the island glyph group carries `scale(0.75)`.
  - Verify: `pnpm run build-storybook` succeeds, the plays pass, and `pnpm run showcase-coverage` passes. Visually check the 0.75 island and the 1920×1080 world map with agent-browser, and record the outcome for the open questions in `design.md`.

## 7. Traceability, browser tests, docs and integration

- [ ] 7.1 [NEW] In `tests/test_map_client_contracts.py` `MapDrawerContracts`, add `covers_requirement` methods asserting that the 5.3 and 5.4 describe blocks passed. Copy the canonical IDs verbatim from `uv run --locked python -m tools.spec_traceability list` after sync; the slug turns an apostrophe into a hyphen. The expected IDs are `webclient-map-drawer::every-map-surface-draws-a-shared-map-concept-from-its-one-glyph-source` and `webclient-map-drawer::map-legend-samples-are-drawn-by-the-map-they-explain`.
- [ ] 7.2 [NEW] In `web/webclient/tests/test_node_suite_evidence.py`, add Vitest evidence annotated with the canonical IDs from the list command. The expected IDs are `webclient-local-map::the-minimap-island-draws-the-area-map-s-node-glyphs` and `webclient-local-map::an-island-fallback-label-never-covers-its-own-node-glyph`. The evidence runs the lattice, local-map, projection and island-label suites, and asserts the test names from groups 2 and 4.
  - Verify: `uv run --locked python -m tools.spec_traceability check` passes after the archive sync.
- [ ] 7.3 [NEW] Browser tests.
  - Update `web/tests/browser/test_browser_local_map_rendering.py` near line 353 to assert the here-seal (`.map-glyph__here-ring`, no gate glyph) on the current gate room.
  - Revisit `INSET = 12` ("r8 seal") in `test_browser_local_map_geometry.py` for the scaled footprints.
  - Run these managed Playwright suites and verify they pass:
    - `test_browser_local_map_rendering.py`
    - `test_browser_local_map_geometry.py`
    - `test_browser_map_legibility.py`
    - `test_browser_scene_transitions.py` (the FLIP glide moves `.local-map__here`)
    - `test_browser_exit_compass.py` (aim ring)
    - `test_browser_local_map_lattice.py`
    - `test_browser_local_map_layout_variants.py`
    - `test_browser_local_map_interaction.py`
    - `test_browser_contextual_hud_stage.py`
    - `test_map_drawer.py`
- [ ] 7.4 [NEW] Update `web/webclient-app/AGENTS.md` (the minimap and map-drawer bullets). Every map glyph has one shared source:
  - `MapNodeGlyph` and `MapCommissionGlyph` plus `area-map-ink.css` for the area map and the minimap;
  - `WorldMapGlyph`, `WorldHatchPattern` and `world-map-ink.css` for the world map.

  Surfaces differ only by a uniform proportional scale, set by `ISLAND_GLYPH_SCALE` for the minimap. Legends draw the maps' own glyphs. A non-current gateway wears the filled gold arch, and a current one the here-seal. Verify that the text matches the delta specs.
- [ ] 7.5 [NEW] Run `pnpm test` from the repo root. Verify everything passes except the known pre-existing full-suite timeout ("opens with focus on the selected tab even when it is not the first", about 4.7 s on master), and that this test passes alone. Then run `openspec validate unify-map-glyphs-across-map-surfaces --strict`.

## Workflow follow-up

- Archive with `os-archive` after verification. It syncs the delta specs and runs the post-sync traceability gate.
