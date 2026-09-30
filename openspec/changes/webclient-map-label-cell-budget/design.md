## Context

See proposal.md (Why) for the motivation. The code paths that turn label text into reserved room are
listed below. Each one counts code points and multiplies by a type size. The measurements come from the
Jim Mono TC v0.1.0 OTFs (upem 2048, Latin advance 1233, CJK advance 2466) and the Hack v3.003 TTFs
(Latin advance 1233).

| Site | Current budget | Orientation |
| --- | --- | --- |
| `use-map-lattice-geometry.js` `labelClearancePitch` | `(glyphs(a) + glyphs(b)) / 2 × labelFont + labelFont / 2` | horizontal |
| `use-map-lattice-geometry.js` `outwardNameBox` (overlay only) | `(labelMax + 1) × markerNameFont` | horizontal |
| `use-map-lattice-render.js` `fittedEdgeMarkers` span term | `floor(span / markerNameFont)` glyphs | horizontal on top/bottom edges and overlay left/right; vertical stack on island left/right |
| `use-map-lattice-render.js` `fitMarkerName` | glyph counts: head, `…`, tail, `（qualifier）` | as above |
| `elosern/local_map.js` `RADIAL_GEOMETRY` | label box 58 × 23 = `5 × 11 + 3`, so `ARC = 67` and `R0 = G = 72` | horizontal |
| `elosern/local_map.js` `edgeMarkersFor` | consumes `nameWidth` and `nameHeight` from the surface | — |

- **Label type sizes.** The island uses `labelFont` 12 (`LocalMap.vue:194`) and the overlay uses 14
  (`MapOverlay.vue:170`). `markerNameFont` defaults to 10.
- **Surface orientation.** Island names on left/right edges stack vertically, one glyph per `tspan` with
  `dy = markerNameFont`. Every other marker name and every node label is one horizontal line.
- **Truncation.** `truncatedLabel` keeps at most `labelMax` (4) code points plus `…` (U+2026). Both Hack
  and Jim Mono TC draw `…` one cell wide.
- **Vertical budgets.** The row pitch, `LABEL_BAND`, `MARKER_NAME_ASCENT`, the label baseline, and the
  vertical-stack step budget the line height, not the advance. Jim Mono TC keeps Hack's vertical
  metrics (hhea 1901/−483). None of these change.
- **Fallback.** A code point the monospace face lacks falls through the `--f-mono` stack to a
  proportional face: Noto Sans TC at about 1 em, a system emoji font, or the generic `monospace`. That
  happens for the narrow symbols Hack lacks, such as ①, ★ and ℃, and for CJK today.

## Goals / Non-Goals

**Goals:**

- Every horizontal text budget on the map surfaces is measured in monospace cells. The budget is
  exact for code points the monospace face draws, and conservative for everything that falls back.
- One helper defines the cell measure. The lattice and the marker fitter call it. The radial model
  declares its worst case from it, and a test ties the two together.

**Non-Goals:**

- Changing the monospace font. That is `webclient-jim-mono-tc-font`.
- Measuring rendered text in the DOM. The map geometry stays DOM-independent, as the spec requires.
- Changing `labelMax`, the type sizes, or the island's vertical-stack budget.
- Budgeting non-map monospace surfaces (command line, keycaps, message art). They flow in CSS boxes.
- Emoji. A system emoji font may be wider than 2 cells, 1.204 em. Place names carry no emoji, and the
  limit is documented here.

## Decisions

### D1. The cell measure comes from the bundled face, not from Unicode properties

`web/webclient-app/lib/mono_cells.js` exports:

- `CELL_EM = 1233 / 2048`, about 0.602;
- `codePointCells(cp)`: 1 when `cp` is in the bundled monospace face's one-cell set, and 2 otherwise;
- `textCells(text)`: the sum over `Array.from(text)`;
- `ONE_CELL_RUNS`: a generated, sorted array of `[lo, hi]` runs that `codePointCells` searches.

The one-cell set is the regular-weight code-point manifest that the monospace slice generator already
commits. For this change that is `web/webclient-app/fonts/hack/codepoints.json`. Every entry there is
a Hack glyph of advance 1233 (verified by the Hack change: every Hack advance is 1233).

- `tools/gen_mono_cells.py` (stdlib only) reads the manifest and rewrites the block between
  `// BEGIN GENERATED one-cell` and `// END GENERATED one-cell` in `mono_cells.js`.
- `tests/test_mono_cells_table.py` rebuilds the block in memory and byte-compares it, following the
  `tools/gen_ansi_palette.py` precedent.
- When `webclient-jim-mono-tc-font` swaps the face, it points the generator at the new manifest's
  narrow set and regenerates.

This counts every code point outside the face as 2 cells: CJK, fullwidth forms, and narrow symbols
the face lacks. That is exact for a 2-cell CJK face and at least 1.204 em for anything that falls back
to a roughly 1 em face. The table also needs no Unicode-version agreement with the font's build. It is
the font's own cmap.

*Alternative:* Unicode East Asian Width (`W`/`F` = 2, else 1) through Python's `unicodedata`.
Rejected after critique. It budgets a narrow symbol the face lacks, such as ① or ★ drawn by Noto Sans
TC at about 1 em, at 0.602 em, which under-reserves by about 66%. It also ties the table to a Python
Unicode version.

*Alternative:* a hand-written "CJK blocks are wide" heuristic. Rejected, because it silently disagrees
with the font.

### D2. The lattice label term in cells

`labelClearancePitch` computes `((textCells(a) + textCells(b)) / 2 × CELL_EM + 0.5) × labelFont`, rounded
up. The worst case is two truncated labels of four CJK glyphs plus `…`, which is 9 cells each:

| Surface (`labelFont`) | Old worst term | New worst term | Five-ASCII-glyph pair, new |
| --- | --- | --- | --- |
| island (12) | 66 | 72 (+9%) | 43 (was 66) |
| overlay (14) | 77 | 83 | 50 |

The spec's floor, never less than `(labelMax + 1) × labelFont + 3`, still holds. ASCII and short names
now ask for less room. Fixtures whose adjacent labels are ASCII therefore get a smaller derived pitch,
while all-CJK fixtures get a larger one. The overlay term stays far below its declared pitches, so the
overlay scenario's "never binds" still holds.

### D3. Marker-name fitting in cells

- **Measure per orientation.** `fitMarkerName(label, budget, measure)` takes a measure function:
  `codePointCells` for a horizontal line, and `() => 1` for the island's vertical stack. The vertical
  stack advances one type step per glyph.
- **Algorithm.** The function keeps its shape: the whole name if it fits; otherwise the name with its
  `（qualifier）` kept and the head truncated; otherwise head, `…` and tail. Every length comparison
  uses the measure. Head and tail grow greedily one code point at a time while they fit. `…` costs 1
  under either measure.
- **Integer budgets.** Budgets are integers computed without floating-point rounding traps:
  - The outward box is declared in cells: `outwardNameCells = (labelMax + 1) × 2`, which is 10 cells,
    room for five wide glyphs, the same capacity as today. The unit width passed as `nameWidth` to
    `edgeMarkersFor` is `outwardNameCells × CELL_EM × markerNameFont`. The overlay's gutter and
    `slotMinH` widen through the existing closed-form packing.
  - The span term for horizontal names is `floor(span / (CELL_EM × markerNameFont) + 1e-9)` cells.
  - The island's vertical stack keeps `floor(span / markerNameFont)` glyphs.
- **Island band.** The island passes `nameWidth: 0` and `nameHeight: 16`. The widest vertical-stack
  glyph is `2 × CELL_EM × 10 = 12.04` units, inside the 16-unit band.

*Alternative:* budget every code point at 2 cells. Rejected. It truncates ASCII names needlessly, and
the requirement says shorter names ask only for the room they occupy.

### D4. The radial contract numbers

`elosern/local_map.js` declares a worst-case label box instead of reading label text. Its documented
basis is `5 × 11 + 3 = 58`, the 11-unit label step. Recomputed from the cell measure on the same basis:

- width `ceil(9 × CELL_EM × 11) + 3 = 63`; height 23 is unchanged;
- diagonal `sqrt(63² + 23²) = 67.07`, so `ARC = ceil + 4 = 72`;
- `R0 = G = ARC + 5 = 77`.

Task 3.1 first confirms the basis against the radial label size actually drawn. If the radial variant
draws labels at 12 units, the same derivation gives 69 × 23, `ARC = 77`, and `R0 = G = 82`, and the
larger set is used.

`local_map.test.js` pins the result. It also imports `mono_cells.js` through dynamic `import()`, since
the helper is an ES module, and asserts that the declared width equals
`ceil(textCells("霧骨渡口…") × CELL_EM × basis) + 3`. The UMD constant can then never drift from the
helper.

`elosern/*` is the model's own source. This is a change to the model's declared geometry contract,
not a Vue workaround.

### D5. Map comments become font-agnostic

The comments that name "Hack ASCII / Noto Sans TC CJK" are rewritten to describe the cell model, in
`use-map-lattice-geometry.js`, `MapLattice.vue`, `use-map-lattice-render.js`,
`tests/world/map_lattice_renderer.test.js`, and `tests/world/map_lattice_edge_names.test.js`. The font
change then touches no map file.

### D6. Tests

- **Helper** (Vitest): ASCII is 1, `…` is 1, `─` is 1, `中` is 2, `（` is 2, `①` (absent from Hack) is 2,
  and `textCells("霧骨渡口…")` is 9.
- **Table byte-compare** (`tests/test_mono_cells_table.py`, see D1).
- **Renderer tests.** `map_lattice_renderer.test.js` models label boxes with `GLYPH_W = 11`. The box
  becomes `textCells × CELL_EM × font`, and expected pitches and scales are recomputed from D2.
  Fixtures that shrink (ASCII labels) and fixtures that grow (CJK labels) are both named in the task
  notes.
- **Marker-fit tests.** They are extended with a mixed name (`北門 Gate`), a `（qualifier）` name, and a
  check that the overlay's outward box fits exactly 10 cells: five CJK glyphs fit, and six are
  truncated.
- **Browser geometry oracle.** It is re-run as focused single methods (tasks group 4). No assertion is
  loosened.

## Risks / Trade-offs

- **[Dense CJK lattices scale down sooner]**
  - The island's worst term grows from 66 to 72 units.
  - Mitigation: the 0.75 island floor and the legibility tests are re-run. A fixture that crosses the
    floor is reported, not accepted.
- **[ASCII-labelled fixtures get tighter pitches]**
  - Mitigation: the bare term, the marker footprints and the connector clearance are unchanged, so
    only the label term shrinks. The overlap assertions prove it.
- **[Radial rings grow about 7–14%]**
  - Mitigation: the radial Node sweep and `test_walked_instance_layer_renders_radial_on_both_surfaces`.
- **[A long edge-marker name no longer fits]**
  - The scenario "A lone gateway on an edge carries its whole authored name" (`西部丘陵與谷地（南門）`,
    22 cells = 132 units at 10) needs a horizontal span of at least 132 units.
  - Mitigation: its test is re-run. If the island's top/bottom span is shorter, that is reported
    instead of changing the scenario.
- **[Emoji width is unknown]** Documented in Non-Goals.

## Migration Plan

This lands before `webclient-jim-mono-tc-font`. There is no data migration. Rollback is a revert.
