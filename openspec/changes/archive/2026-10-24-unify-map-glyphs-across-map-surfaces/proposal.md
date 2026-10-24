## Why

Each map surface drew its own version of the same icon (圖示).
- The minimap island had a private marker ladder: a seal-stroked r8 current circle, an ink r4.5 visited dot, a hollow unvisited dot, a gold landmark ring, a gold-glow actionable halo, and an open outline arch with feet around gateways.
- The map drawer's area map drew a different here-seal, dot and filled gate arch. Its wilderness cells drew yet another, smaller seal and gate.
- Both `?` legends approximated the maps with CSS boxes or copied paint values, and the gate sample matched neither map.

A player who learns a symbol on one surface cannot trust it on another, and every new surface drifts again. The goal is one shared icon set. Every map surface that shows a concept draws it from that concept's single source, with no exceptions. Surfaces may differ only by a uniform size scale.

## What Changes

- **Shared sources, one per glyph family:**
  - `MapNodeGlyph.vue` paints the area and minimap nodes: travel halo, current here-seal, visited dot, dashed seen dot and filled gate arch.
  - A shared area ink source holds the road casing and core and the commission diamond. Its pattern follows `world-map-ink.css`: a scoped stylesheet plus a commission glyph.
  - `WorldMapGlyph.vue` paints the world point glyphs: here, landmark spire, place by kind, and the commission pin with an optional tracked halo.
  - `world-map-ink.css` holds the shared world ink.
  - One hatch pattern definition is used by both the world map and the world legend.
- **Proportional per-surface scale.** A surface may set one uniform scale for a glyph. That scale applies to the whole glyph group, including stroke widths and dash patterns. This replaces the radius-only `scale` prop, which left strokes fixed.
- **Minimap.** It draws `MapNodeGlyph` at one island glyph scale constant, `ISLAND_GLYPH_SCALE`, 0.75 by default, so its icons are smaller than the area map's. The same factor also scales:
  - the painted footprints used by projection spreading, label clearance, label-layout obstacles and the stub start;
  - the compass aim ring radius, which stays just outside the scaled travel halo.

  The island's private ladder is gone:
  - in-canvas landmark nodes no longer get a gold ring;
  - a current gateway shows the here-seal and keeps its `通往 <leads_to>` line;
  - nodes with a move action show the area map's dashed travel halo;
  - non-current gateways show the area map's filled arch.

  Test ids are kept.
- **Area map.** Point nodes render through `MapNodeGlyph` at scale 1. The wilderness-cell branch also draws `MapNodeGlyph` and the shared commission diamond, at a single cell-layout scale. Its private r13/9/5 seal, 7-unit gate and cell diamond path are removed.
- **World map.** It renders through `WorldMapGlyph` and the shared ink and hatch pattern. Its glyphs scale as a whole with the UI scale.
- **Legends.** Both map-drawer legend tabs draw SVG samples from the shared sources, at base map size times the UI scale. All `.lg--*` approximations and the copied `.lg-road__*` and `.lg-quest` values are removed.
- **Island label fix.** The raster-fallback placement could put a label over its own node marker. It no longer does.
- **Storybook.** `LegendAreaGlyphs` and `LegendWorldGlyphs` are added. `MetricAltoriaSouthGate` now asserts the current gate's here-seal. The stories are extended for the removed exceptions and the island scale.
- **BREAKING** (visual contract only, pre-release):
  - The minimap's draft marker ladder (webclient-map-01-draft-chrome D2) and its gold landmark ring are gone.
  - Minimap node paint is now the area map's paint, drawn at 0.75.
  - World glyph strokes now scale with the UI scale.

Part of the implementation is already in the primary working tree, uncommitted under `web/webclient-app/`: the shared node and world glyphs, the world ink, the island and legend cutover, and the label fix. The exception removals, proportional scaling, the island scale and footprint scaling are new work. `tasks.md` separates the two.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-map-drawer`:
  - Adds the cross-surface single-source rule, with no exceptions and with a per-surface uniform proportional scale.
  - Adds the rule that legend samples are drawn by the map they explain.
  - The current-marker requirement has the island share the drawer's here-seal at its own scale.
- `webclient-local-map`:
  - The island draws the area map's node glyphs at one island glyph scale.
  - Painted footprints, the gateway glyph and the current gateway's seal, the marker-ladder and colour-source scenarios, and the landmark treatment are restated for the shared, scaled glyph.
  - Adds the rule that a fallback label never covers its own marker.

## Impact

- **Code already present:**
  - new: `components/MapNodeGlyph.vue`, `components/WorldMapGlyph.vue`, `components/world-map-ink.css`;
  - modified: `MapLattice.vue`, `AreaMapView.vue` (point nodes), `WorldMapView.vue`, `MapDrawer.vue`, `map-lattice.css`, `composables/use-island-dissolve.js`, `composables/use-map-lattice-geometry.js`, `lib/map_marker_geometry.js`, `lib/island_labels.js`.
- **Code still to change:**
  - `MapNodeGlyph.vue` and `WorldMapGlyph.vue`: proportional group scale;
  - `lib/map_marker_geometry.js`: the island scale and scaled footprints;
  - `lib/minimap_projection.js`;
  - `composables/use-map-lattice-geometry.js`: aim ring, label obstacles, stub;
  - `MapLattice.vue`;
  - `AreaMapView.vue`: the wilderness-cell branch and the shared area ink;
  - new shared area ink and commission glyph;
  - a new shared hatch pattern;
  - `MapDrawer.vue` and `WorldMapView.vue`.
- **Stories:** `stories/Overlays/MapDrawer.stories.js` and `stories/World/LocalMap.stories.js`. The frozen showcase manifest is unchanged.
- **Tests:**
  - Vitest updates for the new sizes, footprints and the removed exceptions;
  - new Vitest describe blocks with Python traceability wrappers;
  - browser test updates, including `test_browser_local_map_rendering.py` and the geometry audit inset.
- No server, protocol or payload change.
