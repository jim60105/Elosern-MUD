# Tasks: Decouple map metrics from the font release

## 1. Pin and regenerate the font artifacts

- [x] 1.1 Repin `tools/import_mono_font.py` to Jim Mono TC v0.4.0 (release,
      asset, digest) and add the `CELL_ADVANCE = (1200, 2048)` pin plus the
      documented bump procedure.
- [x] 1.2 Re-run the importer: 196 slices, `codepoints.json` with the new
      `cell_advance` field, `styles/fonts-mono.css`, and the licence set
      (OFL licence, notice, Cascadia Code NF licence replacing Hack).
- [x] 1.3 Generalize `tools/gen_mono_cells.py` to emit the generated
      `CELL_EM` block from the manifest and regenerate
      `web/webclient-app/lib/mono_cells.js`.

## 2. Consume the derived measure in map logic and docs

- [x] 2.1 Update the radial geometry derivation comments in
      `web/static/webclient/js/elosern/local_map.js` to cite the generated
      cell measure (label width `ceil(9 * CELL_EM * 12) + 3`, diagonal from
      it); re-derive `ARC`/`R0`/`G` from the recurrence (75/80/80, proven by
      the exhaustive node-gate footprint sweep).
- [x] 2.2 Reword the metrics section of
      `docs/development/frontend-developer-guide.md` to the derived measure
      (no 0.602/Hack literals).

## 3. De-literal the tests

- [x] 3.1 Generalize `tests/test_mono_font_contract.py`: licence-set
      assertion, weight-superset invariant, manifest-derived CJK coverage
      check.
- [x] 3.2 Update the node gate `web/static/webclient/js/tests/local_map.test.js`:
      read `cell_advance` from the manifest, derive `LABEL_W` and the radial
      recurrence assertions from it.
- [x] 3.3 Update the Vitest pins under `web/webclient-app/tests/`
      (`core/mono_cells.test.js`, `world/map_label_cells.test.js`,
      `world/map_lattice_fidelity.test.js`, `world/map_lattice_name_fit.test.js`,
      `world/map_lattice_edge_names.test.js`, `world/map_lattice_renderer.test.js`,
      `world/local_map.test.js`) to derive from `CELL_EM`.
- [x] 3.4 Update `web/tests/browser/test_vue_typography.py` (CI-owned) advance
      literal to the manifest value.

## 4. Prove the contract

- [x] 4.1 Add tests for the new manifest-source requirement (manifest
      `cell_advance` equals the exported `CELL_EM`); the
      `covers_requirement` annotation lands when the delta syncs into the
      main spec.
- [x] 4.2 Run focused Python unittests, the node gate, and the Vitest suite.
- [x] 4.3 Run `uv run --locked python -m tools.contract_gate` and
      `openspec validate decouple-map-metrics-from-font-release --strict`.
