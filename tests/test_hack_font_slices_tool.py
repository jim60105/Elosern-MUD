"""Unit tests for the pure helpers of tools/gen_hack_font_slices.py.

The generator's slice assignment, run collapsing, and stylesheet rendering
decide which code points each Hack woff2 slice declares (openspec change
``webclient-hack-mono-font``, design D2/D4/D6). They import nothing outside
the standard library, so these tests run in the project environment with no
fontTools and no network access, on synthetic cmaps.
"""

from __future__ import annotations

import re
import unittest

from tools import gen_hack_font_slices as gen


def _declared(css: str) -> list[tuple[int, str, set[int]]]:
    """Return (weight, src, code points) per @font-face in a rendered sheet."""
    faces = []
    for block in re.findall(r"@font-face \{(.*?)\}", css, re.S):
        weight = int(re.search(r"font-weight: (\d+);", block).group(1))
        src = re.search(r"url\(([^)]+)\)", block).group(1)
        cps: set[int] = set()
        for part in re.search(r"unicode-range: ([^;]+);", block).group(1).split(", "):
            lo, _, hi = part.removeprefix("U+").partition("-")
            cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
        faces.append((weight, src, cps))
    return faces


class RunsTest(unittest.TestCase):
    def test_adjacent_code_points_collapse_into_one_run(self):
        self.assertEqual(gen.runs([0x41, 0x42, 0x43]), [(0x41, 0x43)])

    def test_single_and_gapped_code_points_stay_separate(self):
        self.assertEqual(gen.runs([0x2026, 0x20, 0x22, 0x21]), [(0x20, 0x22), (0x2026, 0x2026)])

    def test_unicode_range_uses_the_lowercase_fonts_css_style(self):
        self.assertEqual(gen.unicode_range([0x20, 0x21, 0x2122]), "U+20-21, U+2122")


class AssignTest(unittest.TestCase):
    def test_arrows_are_claimed_by_latin_only(self):
        claimed = gen.assign([0x41, 0x2190, 0x2191, 0x2192, 0x2193, 0x2194])
        self.assertEqual(claimed["latin"], [0x41, 0x2190, 0x2191, 0x2192, 0x2193])
        self.assertEqual(claimed["symbols"], [0x2194])

    def test_latin_takes_punctuation_out_of_the_latin_ext_window(self):
        claimed = gen.assign([0x2013, 0x2015])
        self.assertEqual(claimed["latin"], [0x2013])
        self.assertEqual(claimed["latin-ext"], [0x2015])

    def test_code_points_outside_every_window_are_dropped(self):
        claimed = gen.assign([0x41, 0x4E00, 0x2328 + 0x10000])
        self.assertEqual(sum(map(len, claimed.values())), 1)

    def test_the_excluded_set_is_the_documented_one(self):
        self.assertEqual(gen.EXCLUDED, {0x0000, 0x000D, 0xFEFF})


class RenderCssTest(unittest.TestCase):
    CMAP = [0x20, 0x41, 0x100, 0x3B1, 0x2190, 0x2500, 0x25B2, 0x2328, 0x2715]

    def render(self) -> str:
        claimed = gen.assign(self.CMAP)
        return gen.render_css({weight: claimed for weight, _w, _m in gen.WEIGHTS})

    def test_every_weight_declares_every_slice_with_a_relative_url(self):
        faces = _declared(self.render())
        self.assertEqual(len(faces), len(gen.WEIGHTS) * len(gen.SLICES))
        self.assertEqual({weight for weight, _src, _cps in faces}, {400, 700})
        for _weight, src, _cps in faces:
            self.assertRegex(src, r"^\.\./fonts/hack/hack-(regular|bold)\.[a-z-]+\.woff2$")

    def test_declared_ranges_come_only_from_claimed_code_points_and_stay_disjoint(self):
        faces = _declared(self.render())
        for weight in (400, 700):
            sets = [cps for w, _src, cps in faces if w == weight]
            union = set().union(*sets)
            self.assertEqual(sum(map(len, sets)), len(union))
            self.assertEqual(union, set(self.CMAP))

    def test_code_points_absent_from_the_cmap_are_never_declared(self):
        # Hack lacks U+2328 and U+2715; they must fall through to the next
        # family, so no slice may declare them even though windows hold them.
        cmap = [cp for cp in self.CMAP if cp not in (0x2328, 0x2715)]
        claimed = gen.assign(cmap)
        css = gen.render_css({weight: claimed for weight, _w, _m in gen.WEIGHTS})
        for _weight, _src, cps in _declared(css):
            self.assertNotIn(0x2328, cps)
            self.assertNotIn(0x2715, cps)

    def test_overlapping_claims_are_rejected(self):
        claimed = {name: [] for name, _windows in gen.SLICES}
        claimed["latin"] = [0x41]
        claimed["box"] = [0x41]
        with self.assertRaises(ValueError):
            gen.render_css({weight: claimed for weight, _w, _m in gen.WEIGHTS})


if __name__ == "__main__":
    unittest.main()
