## Why

The map geometry reserves room for label text by counting code points and budgeting each one at one
type step (1 em). That bound holds for today's monospace stack, where CJK draws in Noto Sans TC at
1 em and Latin in Hack at 0.602 em. The follow-up change `webclient-jim-mono-tc-font` switches the
monospace role to Jim Mono TC, whose CJK glyphs are exactly two Latin cells wide (2 × 0.602 em =
1.204 em). Under that font the current budget under-reserves every CJK label by about 20%, so node
labels, edge-marker names, and radial labels would overlap or leave their reserved boxes. The budget
has to measure text the way a monospace font draws it, in cells, before the font can change.

## What Changes

- Add a pure helper that measures a string in monospace cells. A code point that the bundled
  monospace face draws one cell wide counts as one cell. Every other code point counts as two: CJK,
  fullwidth forms, and narrow symbols the face lacks, such as ① or ★, which fall back to an
  approximately 1 em face. A cell is 0.602 em, the advance of Hack and of Jim Mono TC. The one-cell
  table is generated from the monospace slice manifest that is already committed
  (`fonts/hack/codepoints.json`) by a small tool, and a test byte-compares it, like the ANSI palette.
- Lattice label term: two adjacent labels need `(cells(a) + cells(b)) / 2 × cellEm × labelFont +
  labelFont / 2` instead of `(glyphs(a) + glyphs(b)) / 2 × labelFont + …`. The worst truncated label
  on the island (four wide glyphs plus the narrow `…`) is 9 cells, or 5.418 em instead of 5 em; on the
  overlay (`labelMax` 10) it is 21 cells, 12.643 em instead of 11 em. ASCII labels now
  ask for less room than before.
- Edge-marker names: the horizontal fit budget along an edge, and the overlay's outward name box,
  are measured in integer cells. The outward box is declared as `(labelMax + 1) × 2` cells (22 on
  the overlay), keeping its capacity of `labelMax + 1` wide glyphs, and the overlay gutter grows with
  it.
- Radial (graph) placement contract in `web/static/webclient/js/elosern/local_map.js`: the worst label
  box is recomputed in cells at the 12-unit label step the island actually draws (the old basis was
  11), so it widens from 58 to 69 units, which raises `ARC` from 67 to 77 and `R0`/`G` from 72 to 82
  under the contract's own derivation (`ceil(diagonal) + 4`, `ARC + 5`). The Node tests pin these
  numbers and tie them to the helper. The overlay's radial labels (`labelMax` 10 at an unscaled 14)
  already exceed the scaled contract box today; that pre-existing gap is left to a follow-up.
- The monospace-token comments in the map code describe the cell model instead of naming a font, so
  the font switch that follows touches no map file.
- The map geometry browser tests and Vitest renderer tests are re-run. Tests whose fixtures encode
  the one-em-per-glyph budget are updated to the cell budget. No overlap or containment assertion is
  loosened.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-local-map`: the requirement "The browser minimap renders states without relying on color
  alone" changes its label term and its edge-marker name fit from "one full-width glyph per code point"
  to a monospace cell measure: one cell for a code point the bundled monospace face draws one cell
  wide, two for every other code point, 0.602 em per cell.

## Impact

- **Code**: new `web/webclient-app/lib/mono_cells.js` (generated one-cell table plus the cell
  helper), new `tools/gen_mono_cells.py`;
  `web/webclient-app/composables/use-map-lattice-geometry.js` (`labelClearancePitch`,
  `outwardNameBox`), `web/webclient-app/composables/use-map-lattice-render.js` (`fitMarkerName` and
  its budget), `web/webclient-app/components/MapLattice.vue` (comments),
  `web/static/webclient/js/elosern/local_map.js` (`RADIAL_GEOMETRY`).
- **Tests**: new `tests/test_mono_cells_table.py` (generator byte-compare) and Vitest coverage for
  the helper; updated `web/static/webclient/js/tests/local_map.test.js` (ARC/R0/G pins),
  `web/webclient-app/tests/world/map_lattice_renderer.test.js`, and
  `web/webclient-app/tests/world/map_lattice_edge_names.test.js`; focused re-runs of the map browser
  tests.
- **Layout**, in both directions:
  - All-CJK labels need more room: the island's worst label term goes from 66 to 72 units (+9%), and
    the overlay's (`labelMax` 10) from 161 to 185.
  - All-ASCII labels need less: five ASCII glyphs on the island go from 66 to 43.
  - The overlay's name gutter grows by about 20% (outward box 121 → 146 units) and the radial rings
    by about 14%.
  - Dense CJK lattices scale down slightly sooner, and the island's 0.75 floor is unchanged.
  - With the current Hack stack the new budget is conservative for every fallback character, because
    CJK and the symbols Hack lacks draw at about 1 em, which is at most 2 cells.
- **Dependencies**: none. `webclient-jim-mono-tc-font` depends on this change. The upstream Jim Mono TC small-slice release does not touch this repository and can proceed in parallel.
