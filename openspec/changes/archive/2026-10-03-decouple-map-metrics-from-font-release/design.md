# Design: Decouple map metrics from the font release

## D1 — One authored source for the cell measure

The Latin cell advance of the bundled Jim Mono TC face becomes data, not
prose or hand-written constants:

1. `tools/import_mono_font.py` pins `CELL_ADVANCE = (1200, 2048)` alongside
   the release pin and writes it into `codepoints.json` as
   `"cell_advance": {"advance": ..., "upem": ...}`. The pin is verified
   against the release's own `hmtx` at import time (throwaway fontTools run;
   fontTools stays out of the project dependencies).
2. `tools/gen_mono_cells.py` emits a `BEGIN/END GENERATED CELL_EM` block in
   `web/webclient-app/lib/mono_cells.js` exporting `CELL_EM = advance / upem`.
   The block is byte-regenerated exactly like the one-cell table, and
   `tests/test_mono_cells_table.py` byte-compares it.
3. Map surfaces and tests import `CELL_EM` from `mono_cells.js` (node gate)
   or read `cell_advance` from the manifest (Python side).

Bump procedure (documented in the importer docstring): change the release
pin, asset name, digest, and advance pin; rerun the importer and the cell
generator; every derived assertion recomputes.

## D2 — Spec wording becomes relative

`openspec/specs/webclient-local-map/spec.md` keeps its derivational
requirements ("derived minimum pitch", "budgeted in monospace cells") but
drops the release-absolute literals: the pitch scenario names the cell
measure abstractly instead of `0.602 em`, `50`, `64`; the cell-budget
scenario uses `CELL_EM` in the clearance formula. Release-specific numbers
live only in tests that recompute them from the exported measure, so a bump
that changes them changes generated artifacts, never the contract.

## D3 — Re-derived constants for the v0.4.0 face

With `CELL_EM = 1200 / 2048` (was `1233 / 2048`):

- Worst truncated label width: `ceil(9 × CELL_EM × 12) + 3` = 67 (was 69).
- Worst single-node footprint diagonal: `sqrt(67^2 + 23^2)` = 70.84, so the
  radial contract keeps `ARC = 77`, `R0 = G = 82` — the previous values
  remain conservative; they are NOT normative in the main spec, and only
  their derivation comments change wording to cite the derived measure.
- Lattice pitches at the 12-unit step: two+four-glyph 49 (was 50),
  four+four 63 (was 64); the 9-cell label pitch 70 (was 72).
- Edge-marker fitting: `floor(58 / (CELL_EM * 10))` = 9,
  `floor(174 / (CELL_EM * 10))` = 29; derived name width
  `22 * CELL_EM * 11` = 141.796875 (was 145.696).
- Vitest pins: 21-glyph band `21 * 2 * CELL_EM * 14` = 179.8 -> 180 (was
  185), 5-glyph at 12 = 42 (was 43).

## D4 — Contract tests stop echoing release data

`tests/test_mono_font_contract.py` asserts invariants instead of v0.2.0
snapshots:

- Licences: the shipped licence set contains the Jim Mono TC OFL 1.1
  licence + notice and at least one upstream licence text, without naming
  which upstream families are bundled (the base swapped Hack -> Cascadia
  Code NF in v0.3.0).
- Weights: bold's one-cell set includes regular's (regular - bold is empty).
  The v0.2.0 three-codepoint extra is release data and disappears; the
  invariant that regular never has cells bold lacks survives.
- CJK count: derived as bundled-Noto wide coverage minus the manifest's
  recorded `noto_wide_missing`, not a literal.

## D5 — Traceability

New tests for the ADDED requirement (traceability-annotated) live in
`tests/test_mono_cells_table.py` (manifest and generated `CELL_EM` agree)
and the node/Vitest gates (map-fit derives from the exported value). No
player-facing command changes, so no command-doc updates are needed.
