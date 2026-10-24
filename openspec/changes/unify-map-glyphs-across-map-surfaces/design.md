# Design

## Context

Before this change there were three separate glyph vocabularies:

- **Minimap island** (`MapLattice.vue` + `map-lattice.css`). It had the draft marker ladder from webclient-map-01-draft-chrome D2:
  - an r8 seal-stroked current circle;
  - an r4.5 ink visited dot and a hollow unvisited dot;
  - a remembered diamond;
  - an r5 gold landmark ring;
  - an r10 gold-glow actionable disc;
  - an open outline gate arch with feet (`GATE_ARCH_R` 12), framing the node marker.
- **Area map** (`AreaMapView.vue`). It drew its own here-seal (glow r14, ring r10, dot r6), a dot r5.5 (visited, or dashed seen), a dashed travel halo r15 and a filled gate arch `M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z`. All of this was inline, with scoped styles.
- **World map** (`WorldMapView.vue`). It drew its spire, place, quest pin and here-seal inline. Its land, wash, hatching, district, nation, trail and approximate-ring ink were in its own scoped style block.
- **Map drawer legend** (`MapDrawer.vue`). It drew `.lg--*` CSS boxes, borders, gradients and clip-paths that only approximated these glyphs.

The implementation described here is already in the primary working tree, uncommitted under `web/webclient-app/`. `os-apply` adopts it on `feat/unify-map-glyphs-across-map-surfaces`, verifies it, and adds the traceability and browser-test work listed in `tasks.md`.

## Goals / Non-Goals

**Goals:**

- Give each concept in the area/minimap node family, the world point family and the world ink family exactly one definition. Make every map surface and legend render from it.
- Make the minimap's nodes identical to the area map's (non-cell) nodes, and make legend samples identical to their map's glyphs.
- Keep island geometry honest: footprints, overlap spreading, label clearance and the compass aim ring all follow the larger shared glyphs.
- Keep the stable test ids and classes that browser and unit tests select on.

**Non-Goals:**

- The area map's wilderness-cell branch. Its inset here-seal (r13/9/5) and 7-unit gate inside a cell rectangle stay local to `AreaMapView.vue`, so on a wilderness layer the island and the area tab differ by one unit in those two marks.
- The area road casing and core, and the commission diamond. They get no shared definition. The legend copies their exact values into `MapDrawer.vue` (`.lg-road__*`, `.lg-quest`).
- Converting the shared glyph paint to design tokens. The area map's literal colours (for example `#15130f`, `#2b2924`, `#3a342a`) move unchanged into the shared components.
- The pre-existing overlap of a rim edge-direction diamond with its rim name (for example 西部丘◆陵與谷地). It exists on master too.
- Any server, payload or protocol change.

## Decisions

1. **One component per glyph family, not shared CSS classes alone.**
   - `components/MapNodeGlyph.vue` is an SVG-fragment component. Props: `state` (`current|visited|seen`), `gate`, `travel`, `selected`, `scale`, `markerClass`, `haloClass` and `testIds`.
   - Draw order: the travel halo r15 first (dashed gold, under everything). Then `current` draws glow r14, ring r10 and dot r6, and wins over `gate`. A gate draws `gatePath(scale)`, darker with the `is-seen` variant. Anything else draws dot r5.5, and the seen variant is dark with a dashed stroke.
   - The component owns its scoped styles, which moved from AreaMapView.
   - `components/WorldMapGlyph.vue` handles `kind` `here|landmark|place|quest`, plus `placeKind` and `tracked`. Its scoped styles moved from WorldMapView, including `path, circle { vector-effect: non-scaling-stroke }`.
   - Why components: a component carries geometry and paint together, so a host cannot reuse the shape with different paint. Hosts keep their own hit areas, selection rings and positioning.
   - Alternative rejected: a shared CSS file plus copied SVG markup. The markup would still drift.

2. **World ink as one shared stylesheet.** `components/world-map-ink.css` holds the land, wash, hatch line, district `is-lit`/`is-unlit`, nation casing/border, trail casing/line and approx fill/ring rules. Both `WorldMapView.vue` and `MapDrawer.vue` include it with `<style scoped src="./world-map-ink.css">`, so the legend's sample shapes take the map's own classes. Tone variants, terrain, coast and the selection styles stay in WorldMapView. They are not legend concepts.

3. **Geometry constants follow the full map** (`lib/map_marker_geometry.js`):
   - glyph radii: `HERE_GLOW_R` 14, `HERE_RING_R` 10, `HERE_DOT_R` 6, `NODE_DOT_R` 5.5, `HALO_R` 15;
   - gate: `GATE_HALF` 8, `GATE_STROKE` 2, and `GATE_FOOTPRINT` = hypot(9, 9), the mitred base corners;
   - `MARKER_LANDMARK_R` 5, now used only by rim edge markers;
   - `gatePath(scale)`.

   `paintedMarkerFootprint` returns the maximum of: `HALO_R + 1` when the node has an action; `HERE_GLOW_R` for current; `GATE_FOOTPRINT` for a gateway; otherwise `NODE_DOT_R + 1`.

   In `composables/use-map-lattice-geometry.js`, `MARKER_CURRENT_RING_R` (the compass aim ring) goes from 10.5 to 17, so the ring stays outside the travel halo. The rim comment becomes `R_MAX + HALO_R = 103`.

4. **Island state mapping and hooks** (`MapLattice.vue`):
   - `glyphState` maps `visible_unvisited` to `seen` and `visible_visited`/`remembered` to `visited`. Remembered places are presented by rim diamonds; the projection skips remembered nodes.
   - Each node draws `<g class="local-map__glyph" :class="{ 'local-map__here': current }"><MapNodeGlyph …/></g>`.
   - The primary shape keeps `local-map__marker local-map__marker--<visibility>` for the geometry audit. A non-current gate keeps `local-map__gate-glyph`. The halo carries `local-map__actionable`.
   - `glyphTestIds` keeps the `data-testid`s `local-map__marker--current`, `local-map__gate-glyph` and `local-map__actionable`.
   - Current-marker glide and dissolve now target `.local-map__here`, in MapLattice, `composables/use-island-dissolve.js` and `map-lattice.css`, so the whole glyph moves as one.
   - The old ladder, landmark, actionable and gate-glyph CSS is removed from `map-lattice.css`.

5. **Current wins over gate on the island too.** The area map draws a current gateway as the here-seal. The island now does the same, keeping the `通往 <leads_to>` second line, so the two surfaces agree. This is a visible change: the `MetricAltoriaSouthGate` story and `local_map.test.js` now assert the seal. One browser test still asserts the old arch (see `tasks.md`).

6. **Landmark ring dropped from in-canvas nodes.** The area map marks no landmark node. The landmark-gold label tier still carries the landmark treatment, and rim edge markers keep their ring.

7. **Label fallback guards its own marker** (`lib/island_labels.js`). The larger footprints exposed a raster-fallback case where a label covered the node it names: a node is not an obstacle to its own label, so the nearest raster box could sit on top of it. The fallback now skips any box whose reach is less than `request.footprint + LABEL_GAP`.

8. **Legend samples are real map SVG.** Each sample is an `<svg class="lg-svg" viewBox="-16 -16 32 32">`, sized `32px × --ui-scale`, so glyphs render 1:1 at map size.
   - Area tab: `MapNodeGlyph` for current, visited, seen, visited+travel and visited+gate, plus copied road and commission values.
   - World tab: `WorldMapGlyph` for here, landmark, settlement and quest; the quest pin is translated by 5 to centre it. The rest use `world-map-ink.css` classes: wash plus lit border; land plus a uid-scoped hatch pattern plus the unlit border; nation; trail; and the approx ring at r14.
   - All `.lg--*` rules are removed.

## Risks / Trade-offs

- [The island token rule weakens for node paint] → The old ladder used tokens (`--seal-deep`, `--ink-700`, `--vit-sp`, `--gold-glow`). The shared glyph carries the area map's literal colours. The delta narrows the island token scenarios to edges, labels, rim markers and chrome, and states that node paint is the shared glyph's. Tokenising the shared glyph would be a later change that touches every surface at once.
- [Larger island marks crowd dense layouts] → Footprints grew, from r9 to r14 for current and from r11 to r16 for an exit with an action. Projection spreading and label clearance read `paintedMarkerFootprint`, and the projection, local-map and lattice unit tests were re-baselined to the new values. The Playwright geometry audits have not been run yet, so `tasks.md` requires them.
- [Remembered in-canvas nodes lose their diamond] → Coordinate layers never draw remembered nodes in-canvas; they go to the rim. A graph layer that did would show the visited dot. This is accepted: remembered places keep their distinct rim presentation.
- [Hidden duplicates remain] → The wilderness-cell marks, road strokes and commission diamond are still duplicated, as listed in the spec's named exception. A follow-up can give them shared definitions.
- [The full-suite timeout is pre-existing] → `map_drawer.test.js` "opens with focus on the selected tab even when it is not the first" takes about 4.7 s on unmodified master and can hit the 5 s timeout under full-suite load. It passes alone and is unrelated to this change.

## Migration Plan

Pre-release. No compatibility layer and no data migration. Removed CSS classes (`.lg--*`, `.local-map__landmark`, the old `.local-map__marker--*` paint, `.area-map__dot-node`, `.area-map__halo`) have no remaining consumers. `styles/app-shell.css` has no `.elosern-root` duplicates of them.

## Open Questions

- Should the area road strokes, the commission diamond and the wilderness-cell marks get shared definitions in a follow-up, so that the single-source rule holds without exceptions?
- Should the shared node glyph's literal colours become design tokens, restoring the island's all-token rule on every surface?
