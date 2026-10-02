# Proposal: Decouple map metrics from the font release

## Why

The `webclient-local-map` main spec pins drawn-label geometry to one absolute
metric of the bundled monospace face — the 0.602 em Latin cell — including the
release-specific pitches it produces (50 and 64 units). Updating the bundled
Jim Mono TC from v0.2.0 to v0.4.0 changed the Latin cell advance from
1233/2048 to 1200/2048 em (the Latin base moved from Hack to Cascadia Code NF
in v0.3.0), which invalidates the spec's literal numbers and every test that
echoes them. Without decoupling, every future font release requires a new
OpenSpec change; this change makes the spec metric-relative so a font bump
touches only the tool pin and regenerated artifacts.

## What Changes

- MODIFY the minimap requirement: every `0.602 em` literal in the requirement
  body (the label-pair clearance term, the cell definition, the worst-case
  truncated-label term, the marker-name fit budget) becomes `CELL_EM`, the
  shipped face's Latin cell advance that the font manifest publishes; the
  pitch scenario drops the release-specific 50/64-unit numbers in favour of
  the cell-measure derivation; the label cell-budget scenario's formula uses
  `CELL_EM`; the footprint-crop scenario's 264/232-unit literals (which
  depend on the radial geometry contract, itself cell-measure-derived) become
  contract-relative wording.
- ADD a requirement making the shipped font manifest the single source of the
  cell measure: the importer records the face's Latin `cell_advance`
  (advance/upem), the cell-table generator exports `CELL_EM` from it, and map
  label-fit logic consumes the generated value rather than a hand-written
  constant; release-dependent geometry constants stay pinned to tests that
  re-derive them from `CELL_EM`.
- No player-command surface change, no server or game-state change, no
  wire/payload change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-local-map`: the two font-metric literals in the minimap
  requirement become derived-measure wording, and a new requirement fixes the
  manifest-to-`CELL_EM` chain as the single source of the map cell measure.

## Impact

- `tools/import_mono_font.py`: release pin (v0.4.0), `CELL_ADVANCE`, manifest
  `cell_advance` field (already repinned/regenerated in the working tree).
- `tools/gen_mono_cells.py` and `web/webclient-app/lib/mono_cells.js`:
  generated `CELL_EM = 1200 / 2048` block.
- `web/static/webclient/js/elosern/local_map.js`: radial geometry contract
  comments cite the derived cell measure; re-derived constants.
- Tests that echoed the old metric: `tests/test_mono_font_contract.py`,
  `tests/test_mono_cells_table.py`, the node gate
  `web/static/webclient/js/tests/local_map.test.js`, the Vitest suites under
  `web/webclient-app/tests/`, and `tests/browser/test_vue_typography.py`
  (CI-owned) derive from `CELL_EM` / the manifest instead of literals.
- `docs/development/frontend-developer-guide.md` metrics section reworded to
  the derived measure.
