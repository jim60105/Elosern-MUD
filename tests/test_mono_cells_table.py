"""Monospace cell table contract (webclient-map-label-cell-budget).

The map geometry budgets label text in monospace cells from the one-cell
table in ``web/webclient-app/lib/mono_cells.js``. That table is generated from
the bundled monospace face's code point manifest by ``tools/gen_mono_cells.py``;
regenerating it in memory must reproduce the committed block byte for byte, so
the budget can never drift from the face.
"""

from __future__ import annotations

import unittest

from tools import gen_mono_cells
from tools.spec_traceability import covers_requirement


class MonoCellsTableTest(unittest.TestCase):
    """The committed one-cell table matches its pure generator."""

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_regeneration_reproduces_the_committed_block(self):
        committed = gen_mono_cells.OUTPUT_PATH.read_text(encoding="utf-8")
        block = gen_mono_cells.render_block(gen_mono_cells.load_codepoints())
        self.assertIn(block, committed)
        self.assertEqual(gen_mono_cells.splice(committed, block), committed)

    def test_runs_collapse_sorted_code_points(self):
        self.assertEqual(gen_mono_cells.runs([5, 1, 2, 3, 9, 10, 2]), [(1, 3), (5, 5), (9, 10)])
        self.assertEqual(gen_mono_cells.runs([]), [])

    def test_manifest_holds_the_cells_the_map_relies_on(self):
        one_cell = set(gen_mono_cells.load_codepoints())
        for cp in (0x20, 0x41, 0x7E, 0x2026, 0x2500):
            self.assertIn(cp, one_cell, hex(cp))
        for cp in (0x4E2D, 0xFF08, 0x2460, 0x3000):
            self.assertNotIn(cp, one_cell, hex(cp))

    def test_the_committed_cell_em_is_the_manifest_advance_ratio(self):
        # The map's cell measure has exactly one authored source: the manifest's
        # cell_advance. The committed generated block must equal what the
        # manifest regenerates, and the generated expression must evaluate to
        # the manifest ratio itself, not a hand-written copy.
        # Annotate with
        # covers_requirement("webclient-local-map::the-shipped-font-manifest-is-the-single-source-of-the-map-cell-measure")
        # when the decouple-map-metrics-from-font-release delta syncs into the
        # main spec (active-change IDs are not yet in the traceability index).
        committed = gen_mono_cells.OUTPUT_PATH.read_text(encoding="utf-8")
        cell = gen_mono_cells.load_cell_advance()
        block = gen_mono_cells.render_cell_em(cell)
        self.assertIn(block, committed)
        expression = block.split("CELL_EM = ", 1)[1].split(";", 1)[0]
        self.assertEqual(float(eval(expression)), cell["advance"] / cell["upem"])


if __name__ == "__main__":
    unittest.main()
