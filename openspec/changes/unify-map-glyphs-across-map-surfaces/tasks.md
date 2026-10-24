# Tasks

The implementation for groups 1–5 already exists, uncommitted, under `web/webclient-app/` in the primary checkout (see `design.md`). Apply adopts that working-tree diff and the three untracked files (`components/MapNodeGlyph.vue`, `components/WorldMapGlyph.vue`, `components/world-map-ink.css`) into `.worktrees/unify-map-glyphs-across-map-surfaces` on `feat/unify-map-glyphs-across-map-surfaces`, checks them against this list, and ticks each box only after its verification passes there. Group 6 is new work.

## 1. Shared glyph sources

- [ ] 1.1 Adopt `components/MapNodeGlyph.vue`:
  - travel halo r15 under the glyph;
  - current = glow r14, ring r10, dot r6, winning over gate;
  - gate = `gatePath(scale)` with an `is-seen` variant;
  - otherwise dot r5.5, seen variant dashed;
  - props `markerClass`/`haloClass`/`testIds`, and scoped styles moved from AreaMapView.

  Verify the area-map node branch renders through it and that `tests/world/map_drawer.test.js` passes.
- [ ] 1.2 Adopt `lib/map_marker_geometry.js`: the full-map constants, `gatePath(scale)`, `GATE_FOOTPRINT = hypot(9, 9)`, and `paintedMarkerFootprint` as max(halo 16 if action; 14 current; GATE_FOOTPRINT gateway; 6.5 otherwise). Verify with `tests/minimap_projection.test.js` (footprint constants, explicit-footprint and grouped-overlap cases).
- [ ] 1.3 Adopt `components/WorldMapGlyph.vue` (here, landmark, place by `placeKind`, quest with `tracked` halo, `vector-effect: non-scaling-stroke`) and `components/world-map-ink.css`, and include the stylesheet in `WorldMapView.vue` with `<style scoped src>`. Verify the world map's glyphs and ink render unchanged: `tests/world/world_map_view.test.js` passes, and the MapDrawer world stories render as before.

## 2. Minimap island uses the area map's glyphs

- [ ] 2.1 Adopt the `MapLattice.vue` node rendering:
  - each node is wrapped as `local-map__glyph` / `local-map__here` and uses `MapNodeGlyph`;
  - `glyphState` maps `visible_unvisited` to `seen` and visited/remembered to `visited`;
  - the primary shape keeps `local-map__marker local-map__marker--<visibility>`, and a non-current gate keeps `local-map__gate-glyph`;
  - the halo keeps `local-map__actionable`, and the `data-testid`s stay as before;
  - the in-canvas landmark ring is removed.

  Verify `tests/world/map_lattice_legend_labels.test.js` (r5.5 visited dot, no `.local-map__landmark`) and `tests/world/map_lattice_renderer.test.js` (arch path equals the area map's).
- [ ] 2.2 Adopt the glide and dissolve retarget to `.local-map__here` (`MapLattice.vue`, `composables/use-island-dissolve.js`, `map-lattice.css`) and the removal of the old ladder, landmark, actionable and gate-glyph CSS. Verify `tests/world/map_lattice_scale_motion.test.js` and the island dissolve tests pass.
- [ ] 2.3 Adopt `MARKER_CURRENT_RING_R` 17 and the `R_MAX + HALO_R = 103` comment in `composables/use-map-lattice-geometry.js`. Verify the exit-compass aim-ring tests pass and that the ring lies outside the r15 halo.
- [ ] 2.4 Adopt the current-gate change: a current gateway shows the here-seal, keeps the `通往 <leads_to>` line, and shows no arch. Verify `tests/world/local_map.test.js` ("draws the current gate room's here seal, room name and 通往 line on the city side", and the gateway-feet spacing at 2 × 16).

## 3. Island label fix

- [ ] 3.1 Adopt the `lib/island_labels.js` raster-fallback guard, which skips boxes with `reach < request.footprint + LABEL_GAP`. Add a focused case to `tests/island_labels.test.js` in which, without the guard, the nearest raster box lies inside the label's own footprint. Verify the label lands outside its own marker's reach, and that `tests/world/local_map.test.js` keeps the current label at `y = 14 + 3 + 0.8 × 16`.

## 4. Map drawer legend

- [ ] 4.1 Adopt the area legend tab in `MapDrawer.vue`:
  - `lg-svg` samples with a 32-unit viewBox at `32px × --ui-scale`;
  - `MapNodeGlyph` for current, visited, seen, visited+travel and visited+gate;
  - road casing/core (walked and frontier) and the commission diamond, with values identical to AreaMapView's.
- [ ] 4.2 Adopt the world legend tab:
  - `WorldMapGlyph` for here, landmark, settlement place and quest pin (translated by 5);
  - `world-map-ink.css` included scoped, with wash+lit border, land+uid-scoped hatch pattern+unlit border, nation, trail and approx ring r14;
  - removal of every `.lg--*` rule.
- [ ] 4.3 Add a Vitest describe block named exactly "every map surface draws a shared map concept from its one glyph source" to `tests/world/map_drawer.test.js`. It asserts:
  - island and area-map node shapes match (radii and gate path after the marker scale is removed);
  - the island has no landmark ring or outline arch, including for a node with `landmark: true` and a move action;
  - `map-lattice.css` keeps no `.local-map__marker*`, `.local-map__actionable` or `.local-map__gate-glyph` paint rule;
  - world point glyphs come from the shared component.

  Verify it passes.
- [ ] 4.4 Add a describe block named exactly "map legend samples are drawn by the map they explain" to `tests/world/map_drawer.test.js`. It asserts:
  - both tabs render only SVG samples, with no `.lg` element;
  - the area gate sample `d` equals the map's;
  - the seen sample is `.map-glyph__dot.is-seen`;
  - the world samples carry the `world-map__*` ink and glyph classes;
  - the approx ring is r14;
  - the named-exception samples (road casing/core, commission diamond, hatch pattern) equal the map's values.

  Verify it passes.
- [ ] 4.5 In the existing "the drawer current marker makes one truthful position claim" block, add a case asserting that the island current node draws exactly one `map-glyph__here-glow/ring/dot` set at radii 14/10/6 × marker scale. Verify the block passes.

## 5. Storybook

- [ ] 5.1 Adopt `LegendAreaGlyphs` and `LegendWorldGlyphs` in `stories/Overlays/MapDrawer.stories.js`, and the here-seal assertion in `MetricAltoriaSouthGate` (`stories/World/LocalMap.stories.js`). Verify `pnpm run build-storybook` succeeds, the stories' play functions pass, and `pnpm run showcase-coverage` passes with the frozen manifest unchanged.

## 6. Traceability, browser tests and docs

- [ ] 6.1 In `tests/test_map_client_contracts.py` `MapDrawerContracts`, add `covers_requirement` methods for `webclient-map-drawer::every-map-surface-draws-a-shared-map-concept-from-its-one-glyph-source` and `webclient-map-drawer::map-legend-samples-are-drawn-by-the-map-they-explain`, each asserting the matching describe block from 4.3/4.4 passed. Take the IDs from `uv run --locked python -m tools.spec_traceability list` after sync. Verify both methods pass.
- [ ] 6.2 In `web/webclient/tests/test_node_suite_evidence.py`, add Vitest evidence annotated `webclient-local-map::the-minimap-island-draws-the-area-map-s-node-glyphs` and `webclient-local-map::an-island-fallback-label-never-covers-its-own-node-glyph`, copying the canonical IDs verbatim from `uv run --locked python -m tools.spec_traceability list` after sync (the slug turns an apostrophe into a hyphen). It runs the lattice, local-map and island-label suites and asserts the specific test names from 2.1–2.4 and 3.1. Verify `uv run --locked python -m tools.spec_traceability check` reports no uncovered requirement after archive sync.
- [ ] 6.3 Update `web/tests/browser/test_browser_local_map_rendering.py` (around line 353), which still expects `local-map__gate-glyph` on the current gate room. Assert the here-seal (`.map-glyph__here-ring`, no gate glyph on the current node) instead. Revisit the `INSET = 12` ("r8 seal") assumption in `test_browser_local_map_geometry.py` for the r14 here-glow and the r16 halo footprint. Then run the managed Playwright browser suites that touch the island and drawer: `test_browser_local_map_rendering.py`, `test_browser_local_map_geometry.py`, `test_browser_map_legibility.py`, `test_browser_scene_transitions.py` (FLIP glide now moves `.local-map__here`), `test_browser_exit_compass.py` (aim ring r17), `test_browser_local_map_lattice.py`, `test_browser_local_map_layout_variants.py`, `test_browser_local_map_interaction.py`, `test_browser_contextual_hud_stage.py` and `test_map_drawer.py`. Verify they pass.
- [ ] 6.4 Update `web/webclient-app/AGENTS.md`. The minimap/map-drawer bullets must say that every map glyph has one shared source (`MapNodeGlyph` for area and minimap nodes; `WorldMapGlyph` plus `world-map-ink.css` for the world), that legends draw the maps' own glyphs, and that a non-current gateway wears the filled gold arch while a current gateway wears the here-seal. Verify the text matches the delta specs.
- [ ] 6.5 Run `pnpm test` from the repo root. Verify every test passes except the known pre-existing full-suite timeout in `map_drawer.test.js` ("opens with focus on the selected tab even when it is not the first", about 4.7 s on master), and verify that test passes alone. Then run `openspec validate unify-map-glyphs-across-map-surfaces --strict`.

## Workflow follow-up

- Archive with `os-archive` after verification; it syncs the delta specs and runs the post-sync traceability gate.
- Follow-up candidate (out of scope): shared definitions for the area road strokes, the commission diamond and the wilderness-cell here/gate marks, and tokenised paint for the shared node glyph.
