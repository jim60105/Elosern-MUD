# Design

## Context

Before this change, each surface had its own glyph vocabulary:
- **Minimap island** (`MapLattice.vue` + `map-lattice.css`): the draft marker ladder from webclient-map-01-draft-chrome D2. It drew an r8 seal-stroked current circle, an r4.5 ink visited dot, a hollow unvisited dot, a remembered diamond, an r5 gold landmark ring, an r10 gold-glow actionable disc, and an open outline gate arch with feet (`GATE_ARCH_R` 12).
- **Area map, point nodes** (`AreaMapView.vue`): a here-seal (glow r14, ring r10, dot r6), a dot r5.5 (visited, or seen with a dashed outline), a dashed travel halo r15, and a filled gate arch `M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z`, all drawn inline.
- **Area map, wilderness cells**: a private here-seal (r13/9/5), a 7-unit arch and a pin-shaped commission path (`M0 -9 L5.5 -2 L0 4 L-5.5 -2 Z`). The road casing and core and the point-node commission diamond were AreaMapView-scoped CSS.
- **World map** (`WorldMapView.vue`): spire, place, quest pin and here-seal drawn inline. Its ink was scoped, and it had its own 8×8, 45° hatch `<pattern>`.
- **Map drawer legend** (`MapDrawer.vue`): `.lg--*` CSS approximations.

**Working-tree state (primary checkout, uncommitted):**
- `MapNodeGlyph.vue`, `WorldMapGlyph.vue` and `world-map-ink.css` exist.
- The island, the area point nodes, the world map and both legends already use them.
- The `island_labels.js` fix is in.
- Still missing:
  - proportional scaling (`MapNodeGlyph` multiplies radii by a `scale` prop, so strokes stay fixed, and `WorldMapGlyph` uses `vector-effect: non-scaling-stroke`);
  - the island glyph scale (the island draws at 1);
  - the scaled footprints;
  - the wilderness-cell cutover;
  - a shared area road/commission source (the legend copies values into `.lg-road__*` and `.lg-quest`);
  - a single hatch pattern (MapDrawer declares a second copy).

## Goals / Non-Goals

**Goals:**
- Give every concept in the shared families (spec: area/minimap node, area ink, world point, world ink) exactly one definition. Every surface renders from it, with no exceptions.
- Let surfaces differ only by a uniform scale that applies to the whole glyph, strokes and dashes included.
- Draw the minimap at one island glyph scale, 0.75. Geometry follows it: footprints, spreading, label clearance, the stub start and the aim ring.
- Keep the stable test ids and classes that browser and unit tests select on.

**Non-Goals:**
- Turning the shared glyph paint into design tokens. The components keep the area map's mix of tokens and hex literals unchanged.
- Rim edge-direction diamonds and their rim landmark ring. These are island-only rim markers, not shared map concepts. They also have a pre-existing overlap with their rim names (for example 西部丘◆陵與谷地), which exists on master too.
- Island hit areas and the radial-layout `markerScale` semantics.
- Any server, payload or protocol change.

## Decisions

1. **One component or stylesheet per glyph family.** Geometry and paint travel together, so a host cannot reuse a shape with different paint. Hosts own hit areas, selection rings and positioning. The rejected alternative was shared CSS plus copied markup, because the markup still drifts.
   - **Node glyphs, `components/MapNodeGlyph.vue`** (exists). Props: `state` (`current|visited|seen`), `gate`, `travel`, `selected`, `markerClass`, `haloClass`, `testIds`. Draw order:
     1. the travel halo, r15, dashed gold, under everything;
     2. current: glow r14, ring r10, dot r6 (current takes precedence over gate);
     3. otherwise a gate: the arch, with an `is-seen` variant;
     4. otherwise the dot, r5.5, with a dashed seen variant.
   - **World points, `components/WorldMapGlyph.vue`** (exists). `kind` is `here|landmark|place|quest`, plus `placeKind` and `tracked`.
   - **World ink, `components/world-map-ink.css`** (exists). Included with `<style scoped src>` by `WorldMapView.vue` and `MapDrawer.vue`.
   - **Area ink (new).**
     - `components/area-map-ink.css` takes the `.area-map__road*` rules (casing and core; walked, frontier and travel) out of AreaMapView. AreaMapView and MapDrawer both include it scoped.
     - `components/MapCommissionGlyph.vue` owns the commission diamond `M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z` and its paint. The area point nodes, the wilderness cells and the legend draw it.
     - The legend's road sample becomes `<g class="area-map__road is-walked|is-frontier">` with the casing and core lines. `.lg-road__*` and `.lg-quest` are deleted.
   - **Hatch pattern (new), `components/WorldHatchPattern.vue`.** It renders `<pattern :id patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">` with its hatch line, and owns the hatch-line rule, which moves out of `world-map-ink.css`. WorldMapView and the world legend each place it in their `<defs>` with their own uid-scoped id.

2. **Proportional scaling (new).**
   - `MapNodeGlyph` replaces its radius-only `scale` prop with a `size` prop, default 1. Its template becomes a single root `<g :transform="size === 1 ? null : `scale(${size})`">` holding base-unit shapes.
   - Shapes inside the group have no `vector-effect`, so stroke widths and dash arrays scale with the group.
   - `gatePath()` returns the base path, and `scale` is dropped from it.
   - `WorldMapGlyph` gets a single root `<g>` and drops `vector-effect: non-scaling-stroke`. Its strokes then scale with the world map's `scale(uiScale)` and with the legend's viewBox.
   - The world map's `.world-map__layer path, circle { vector-effect }` rule must not reach glyph internals. Vue scoped styles reach only a child's root element, and the root is now a `<g>`. Verify that the computed `vector-effect` of the glyph shapes is `none`.
   - The here-glow's breathing `transform: scale()` (with `transform-box: fill-box`) composes inside the group.

3. **Island glyph scale (new).**
   - `lib/map_marker_geometry.js` exports `ISLAND_GLYPH_SCALE = 0.75`. This is the one place it is set.
   - `MapLattice.vue` passes `size = glyphSize`, the variant's glyph scale defined below (`markerScale` defaults to 1, and `LocalMap` passes none).
   - `paintedMarkerFootprint(node, size = 1)` returns the base footprint times `size`. The base footprint is the maximum of `HALO_R + 1` when the node has an action, `HERE_GLOW_R` for current, `GATE_FOOTPRINT` for a gateway, and `NODE_DOT_R + 1` otherwise.
   - Island callers pass the island scale:
     - `lib/minimap_projection.js` `spreadExits` uses `ISLAND_GLYPH_SCALE`. Projection runs only on coordinate layers, where `markerScale` is 1.
     - `nodeFootprint` in `use-map-lattice-geometry.js` uses the variant's `glyphSize` (below): `ISLAND_GLYPH_SCALE` on the lattice variant, `ISLAND_GLYPH_SCALE * markerScale` on the graph variant.
     - The label-layout obstacle radius becomes `Math.max(HALO_R * s, nodeFootprint)`.
     - The `MapLattice` gateway stub start becomes `(HALO_R + 1) * s`.
   - `MARKER_CURRENT_RING_R` (the compass aim ring, drawn with a 1.6 px non-scaling stroke) becomes `HALO_R * ISLAND_GLYPH_SCALE + 2`, which is 13.25. Its inner stroke edge (about 12.45) then stays outside the halo's outer edge (15.6 × 0.75 = 11.7).
   - The rim comment becomes `R_MAX + HALO_R × s`.
   - Why a new constant instead of `markerScale`: `markerScale` also scales the radial graph layout's positions (`placed.x * markerScale`). Changing it would move nodes as well as shrink glyphs.
   - The two variants differ:
     - The lattice (coordinate) variant uses `glyphSize = ISLAND_GLYPH_SCALE`. Its `nodePos` ignores `markerScale`, so glyph, footprint, label obstacles and `spreadExits` all agree even when a bare mount passes `markerScale`.
     - The graph (radial) variant uses `glyphSize = ISLAND_GLYPH_SCALE * markerScale`, because its positions scale by `markerScale`.
     - `labelY()` in `use-map-lattice-render.js` is used only by the graph variant. It becomes `LABEL_BASELINE_HALF * glyphSize + 2 + labelFont`, with `LABEL_BASELINE_HALF = HALO_R + 1` (16, the largest base footprint) instead of the old 11.
   - Leave alone: `STUB_FOOTPRINT` (the stub arrow) and the rim diamonds, which are island-only rim pointers.
   - The aim-ring margin of 13.25 − 0.8 against 11.7 holds while the canvas renders at more than about 0.52× its 240-unit size. The island is 240 px or larger at the reference scale, so it always holds.

4. **Wilderness-cell cutover (new).**
   - In the `node.cell` branch, AreaMapView draws `<MapNodeGlyph :state :gate :size="AREA_CELL_GLYPH_SCALE">` for current and gate cells, and `MapCommissionGlyph` at the same scale with the existing corner offset.
   - It deletes its private `area-map__here-*`, `area-map__gate` and cell commission path rules.
   - `AREA_CELL_GLYPH_SCALE = 0.875`, so the arch keeps its former 7-unit half-width and the glow becomes 12.25.
   - Measured during apply (resolved): the cell side is `k − 2 × inset`, with `k = frame.width / span` px per cell and `inset = min(3, 0.06 k)`. At the widest zoom stop (周邊, the 15-cell window) the 960 × 600 fallback frame gives `k ≈ 36.8` and a side of about 32.4 px, so half a side is about 16.2 ≥ 12.25. Even at the continuous zoom-out limit (1.25 × that span) half a side is about 12.95. 1451 × 790 and 1920 × 1080 frames give larger cells. The value 0.875 stays.
   - The cell commission mark changes from the pin path to the shared diamond. This is a deliberate visible change.

5. **Island state mapping and hooks** (exists):
   - `glyphState` maps `visible_unvisited` to `seen` and `visible_visited` or `remembered` to `visited`. The projection skips remembered nodes; they appear on the rim.
   - The wrapper is `<g class="local-map__glyph" :class="{ 'local-map__here': current }">`.
   - The primary shape keeps `local-map__marker local-map__marker--<visibility>`. A non-current gate keeps `local-map__gate-glyph`, and the halo keeps `local-map__actionable`. The `data-testid`s are kept.
   - Glide and dissolve target `.local-map__here`.
   - The old ladder CSS has been removed.

6. **Current wins over gate; no in-canvas landmark ring** (exists). This matches the area map. The landmark treatment is now the landmark-gold label tier.

7. **Label fallback guards its own marker** (exists). `lib/island_labels.js` skips any raster box whose reach is less than `request.footprint + LABEL_GAP`. Footprints are now scaled, so the guard uses the scaled value.

8. **Legend samples** (exist; refined).
   - Each sample is `<svg class="lg-svg" viewBox="-16 -16 32 32">` at `32px × --ui-scale`, using the shared definitions at size 1.
   - The approx ring uses r14. On the map its radius is data-driven with a 16 px minimum, so it is not a fixed glyph size.

## Risks / Trade-offs

- **[Smaller island marks lose fine detail]** At 0.75, the seen dash becomes about 1.65 / 1.5 units and the halo dash 2.25. Verify readability on the 240 px island in Storybook and in the live client. The scale is a single constant, so tuning it is a one-line change.
- **[World glyph strokes thicken above UI scale 1]** Proportional scaling is the rule, and it changes the world map's look at large viewports. Check it in the 1920×1080 stories. The world SVG's viewBox is its frame size, so confirm that it displays at 1:1; otherwise glyph strokes would also follow the fit scale.
- **[Island colour tokens]** The old ladder used tokens. The shared glyph carries the area map's paint, which mixes tokens and hex literals. The delta narrows the island token scenarios to edges, labels, rim markers and chrome.
- **[Re-baselined geometry]** Footprints, spreading tests, label offsets (for example the current label `y`) and the browser geometry `INSET` all move with the scale. Every affected test is listed in `tasks.md`.
- **[Remembered in-canvas nodes]** `glyphState` maps `remembered` to the visited dot, but the coordinate projection never draws a remembered node in-canvas. Remembered places appear as rim diamonds, so this branch exists only for safety.
- **[Pre-existing timeout]** In `map_drawer.test.js`, "opens with focus on the selected tab even when it is not the first" takes about 4.7 s on master and can time out under full-suite load. It passes alone.

## Migration Plan

Pre-release, so there is no compatibility layer and no data migration. All removed classes and private paths are deleted together with their consumers. `styles/app-shell.css` holds no `.elosern-root` duplicates of them.

## Resolved Questions

- **Minimap glyph scale (user decision).** `ISLAND_GLYPH_SCALE` is 0.75 for now. Storybook screenshots of the island (World/LocalMap `MetricAltoriaPlaza` and `MetricAltoriaSouthGate`) are captured during apply so the size can be judged visually; tuning stays a one-line change.
- **World glyph strokes (user decision).** World glyph strokes scale with the UI scale under the proportional rule, with no fixed-screen-width exception. `WorldMapGlyph` drops `vector-effect: non-scaling-stroke`.
- **Wilderness cell scale (measured).** `AREA_CELL_GLYPH_SCALE = 0.875` fits the smallest wilderness cell; see Decision 4 for the measurement.

## Open Questions

(none)
