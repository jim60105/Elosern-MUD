## Why

Each map surface drew its own version of the same icon (圖示). The minimap island had a private marker ladder: a seal-stroked r8 current circle, an ink r4.5 visited dot, a hollow unvisited dot, a gold landmark ring, a gold-glow actionable halo, and an open outline arch with feet around gateways. The map drawer's area map drew a different here-seal, dot and filled gate arch. Both `?` legends approximated the maps with CSS boxes, and the gate sample matched neither map. A player who learns a symbol on one surface cannot trust it on another, and each new surface would have drifted again. The goal is one shared icon set: every map surface that shows a concept draws it from that concept's single source.

## What Changes

- Add one shared source for each family of map glyphs:
  - `MapNodeGlyph.vue` paints every area-map and minimap node: the travel halo, the current here-seal, the visited dot, the dashed seen dot and the filled gate arch. Geometry comes from `lib/map_marker_geometry.js`.
  - `WorldMapGlyph.vue` paints the world-map point glyphs: here, landmark spire, place by kind, and the commission pin with an optional tracked halo.
  - `world-map-ink.css` holds the shared world ink: land, lit wash, hatching, district strokes, nation border, trail and approximate ring.
- The minimap island now draws its nodes with `MapNodeGlyph`, the area map's own glyph. This replaces its private ladder:
  - the gold landmark ring on in-canvas nodes is removed (the area map marks no landmark node);
  - a current gateway shows the here-seal, as the area map does, and keeps its `通往 <leads_to>` line;
  - the actionable halo becomes the area map's dashed travel halo (r15);
  - the gateway outline arch with feet becomes the area map's filled arch.
  Footprints, overlap spreading, the compass aim ring radius (10.5 to 17) and the current-glide/dissolve target follow the new glyph sizes. Test ids are kept.
- The area map (non-cell nodes) and the world map render through the shared components. Their appearance does not change.
- Both map-drawer legend tabs draw SVG samples at 1:1 map size × ui-scale:
  - the area tab uses `MapNodeGlyph`;
  - the world tab uses `WorldMapGlyph` and the `world-map-ink.css` classes.
  All `.lg--*` CSS approximations are removed.
- Fix an island label bug that the larger footprints exposed: the raster-fallback placement could put a label over its own node marker.
- Storybook: add `LegendAreaGlyphs` and `LegendWorldGlyphs` to the MapDrawer stories. `MetricAltoriaSouthGate` now asserts that the current gate room shows the here-seal.
- **BREAKING** (visual contract only, pre-release): the minimap's draft marker ladder (webclient-map-01-draft-chrome D2) and its gold landmark ring are gone. Minimap node paint is now the area map's paint, so it follows the area map's literal colours where the old ladder used island tokens.

- **Known goal gap**: some marks are still not single-source, and the spec lists them as named exceptions that must reproduce the map's exact values:
  - the area map's wilderness-cell here-seal (r13/9/5) and 7-unit gate, so on a wilderness layer the island's r14 seal and 8-unit arch differ from the area tab's by about one unit;
  - the area road strokes;
  - the commission diamond;
  - the world hatch pattern element.

  Closing these is a follow-up decision.

The implementation is already in the primary working tree, uncommitted under `web/webclient-app/`. This change describes it for `os-apply` to adopt, verify, and finish the remaining traceability and browser-test work.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-map-drawer`: adds the cross-surface single-source glyph rule and the legend-samples-are-the-map's-glyphs rule. The current-marker requirement now has the island sharing the drawer's glyph instead of keeping its own.
- `webclient-local-map`: the island draws the area map's node glyphs. Painted footprints, the gateway glyph and the current gateway's seal, the marker-ladder/no-colour and colour-source scenarios, and landmark treatment are restated for the shared glyph. Adds the rule that a fallback label never covers its own marker.

## Impact

- Code (already present, uncommitted): `web/webclient-app/components/{MapNodeGlyph.vue,WorldMapGlyph.vue,world-map-ink.css}` (new), plus `MapLattice.vue`, `AreaMapView.vue`, `WorldMapView.vue`, `MapDrawer.vue`, `map-lattice.css`, `composables/use-island-dissolve.js`, `composables/use-map-lattice-geometry.js`, `lib/map_marker_geometry.js` and `lib/island_labels.js`.
- Stories: `stories/Overlays/MapDrawer.stories.js` and `stories/World/LocalMap.stories.js`. The frozen showcase manifest is unchanged (no new titles).
- Tests: five updated Vitest files. Still needed: new Vitest describe blocks with Python traceability wrappers in `tests/test_map_client_contracts.py`, and an update to `web/tests/browser/test_browser_local_map_rendering.py`, which still expects the arch on the current gate room.
- No server, protocol or payload change.
