"""Contract for the committed, self-hosted Jim Mono TC monospace slices.

The WebClient's ``--f-mono`` role draws Latin, box drawing, and CJK with Jim
Mono TC served from the project origin as small unicode-range woff2 slices
(openspec change ``webclient-jim-mono-tc-font``, design D1/D6). This test
reads the committed import outputs -- ``styles/fonts-mono.css``,
``fonts/jimmonotc/`` and its ``codepoints.json`` manifest -- plus the token
sheet and the bundled Noto Sans TC sheet. Pure file reads; no browser, no
network.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "web" / "webclient-app"
FONT_DIR = APP_ROOT / "fonts" / "jimmonotc"
CSS_PATH = APP_ROOT / "styles" / "fonts-mono.css"
NOTO_CSS_PATH = APP_ROOT / "styles" / "fonts.css"
TOKENS_PATH = APP_ROOT / "styles" / "tokens.css"

WEIGHTS = {400: "regular", 700: "bold"}
ONE_CELL_GROUPS = ("latin", "latin-ext", "greek-cyrillic", "box", "symbols")
MAX_BYTES = 65536
# The imported release's CJK coverage per weight; a new release updates it.
CJK_COUNT = 13283
ARROWS = set(range(0x2190, 0x2194))
ASCII = set(range(0x20, 0x7F))
PRIVATE_USE = ((0xE000, 0xF8FF), (0xF0000, 0x10FFFF))


def _ranges(value: str) -> set[int]:
    cps: set[int] = set()
    for part in value.split(","):
        lo, _, hi = part.strip().upper().removeprefix("U+").partition("-")
        cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return cps


def _faces() -> list[dict]:
    """Parse every @font-face rule of the imported stylesheet."""
    faces = []
    for block in re.findall(r"@font-face \{(.*?)\}", CSS_PATH.read_text(encoding="utf-8"), re.S):
        src = re.search(r"src: url\(([^)]+)\) format\('woff2'\);", block).group(1)
        match = re.fullmatch(r"\.\./fonts/jimmonotc/JimMonoTC-(Regular|Bold)\.([a-z0-9-]+)\.woff2", src)
        faces.append({
            "family": re.search(r"font-family: ([^;]+);", block).group(1),
            "weight": int(re.search(r"font-weight: (\d+);", block).group(1)),
            "style": re.search(r"font-style: ([^;]+);", block).group(1),
            "display": re.search(r"font-display: ([^;]+);", block).group(1),
            "src": src,
            "file_style": match and match.group(1),
            "group": match and match.group(2),
            "codepoints": _ranges(re.search(r"unicode-range: ([^;]+);", block).group(1)),
        })
    return faces


def _noto_wide() -> set[int]:
    """East Asian Wide/Fullwidth code points of the bundled Noto Sans TC 400 faces."""
    cps: set[int] = set()
    for block in re.findall(r"@font-face \{(.*?)\}", NOTO_CSS_PATH.read_text(encoding="utf-8"), re.S):
        if "font-family: 'Noto Sans TC'" in block and "font-weight: 400;" in block:
            cps |= _ranges(re.search(r"unicode-range: ([^;]+);", block).group(1))
    return {cp for cp in cps if unicodedata.east_asian_width(chr(cp)) in ("W", "F")}


def _is_cjk_group(group: str) -> bool:
    return re.fullmatch(r"cjk-\d+", group) is not None


class MonoFontContractTest(unittest.TestCase):
    """The committed Jim Mono TC slices are small, disjoint, two-cell CJK, and licensed."""

    @classmethod
    def setUpClass(cls):
        cls.faces = _faces()
        cls.manifest = json.loads((FONT_DIR / "codepoints.json").read_text(encoding="utf-8"))

    def test_every_url_resolves_and_every_slice_is_referenced(self):
        referenced = [(CSS_PATH.parent / face["src"]).resolve() for face in self.faces]
        self.assertEqual(len(referenced), len(set(referenced)), "a slice is declared twice")
        for path in referenced:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(set(referenced), {path.resolve() for path in FONT_DIR.glob("*.woff2")})

    def test_every_face_is_the_jim_mono_tc_family_at_its_weight(self):
        for face in self.faces:
            with self.subTest(src=face["src"]):
                self.assertEqual(face["family"], '"Jim Mono TC"')
                self.assertEqual(face["style"], "normal")
                self.assertEqual(face["display"], "swap")
                self.assertEqual(WEIGHTS[face["weight"]], face["file_style"].lower())
                self.assertTrue(face["group"] in ONE_CELL_GROUPS or _is_cjk_group(face["group"]), face["group"])

    def test_both_weights_ship_every_one_cell_group(self):
        for weight in WEIGHTS:
            groups = sorted(face["group"] for face in self.faces if face["weight"] == weight and not _is_cjk_group(face["group"]))
            self.assertEqual(groups, sorted(ONE_CELL_GROUPS))

    def test_every_slice_is_woff2_within_the_small_file_bound(self):
        slices = sorted(FONT_DIR.glob("*.woff2"))
        self.assertTrue(slices)
        for path in slices:
            with self.subTest(slice=path.name):
                data = path.read_bytes()
                self.assertEqual(data[:4], b"wOF2")
                self.assertLessEqual(len(data), MAX_BYTES)

    def test_declared_ranges_are_disjoint_and_match_the_manifest(self):
        for weight, key in WEIGHTS.items():
            with self.subTest(weight=weight):
                faces = [face for face in self.faces if face["weight"] == weight]
                union = set().union(*(face["codepoints"] for face in faces))
                self.assertEqual(sum(len(face["codepoints"]) for face in faces), len(union), "declared ranges overlap")
                one = set().union(*(f["codepoints"] for f in faces if not _is_cjk_group(f["group"])))
                cjk = set().union(*(f["codepoints"] for f in faces if _is_cjk_group(f["group"])))
                self.assertEqual(one, set(self.manifest[key]))
                self.assertEqual(cjk, set(self.manifest["cjk"][key]))

    def test_both_weights_declare_the_same_cjk(self):
        cjk = self.manifest["cjk"]
        self.assertEqual(cjk["regular"], cjk["bold"])
        self.assertEqual(len(cjk["regular"]), CJK_COUNT)

    def test_cjk_is_the_bundled_noto_wide_coverage_minus_the_recorded_gaps(self):
        cjk = set(self.manifest["cjk"]["regular"])
        missing = set(self.manifest["noto_wide_missing"])
        self.assertFalse(cjk & missing)
        self.assertEqual(cjk, _noto_wide() - missing)

    def test_key_code_points_land_in_the_right_cell_class(self):
        one = set(self.manifest["regular"])
        cjk = set(self.manifest["cjk"]["regular"])
        for cp in (0x20, 0x41, 0x7E, 0x2026, 0x2500, 0x2502, 0x250C, 0x253C, 0x2588, *ARROWS):
            self.assertIn(cp, one, hex(cp))
        for cp in (0x770B, 0x5317, 0x9580, 0x3002, 0xFF0C, 0xFF0F, 0xFF01, 0x3000):
            self.assertIn(cp, cjk, hex(cp))
            self.assertNotIn(cp, one, hex(cp))

    def test_ascii_and_arrows_ship_only_in_the_latin_slice(self):
        for face in self.faces:
            with self.subTest(weight=face["weight"], group=face["group"]):
                if face["group"] == "latin":
                    self.assertLessEqual(ASCII | ARROWS, face["codepoints"])
                else:
                    self.assertFalse((ASCII | ARROWS) & face["codepoints"])

    def test_no_private_use_code_point_is_declared(self):
        for face in self.faces:
            for lo, hi in PRIVATE_USE:
                self.assertFalse(any(lo <= cp <= hi for cp in face["codepoints"]), face["src"])

    def test_licences_ship_beside_the_font_files(self):
        licence = (FONT_DIR / "licenses" / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("SIL OPEN FONT LICENSE", licence.upper())
        self.assertIn("Version 1.1", licence)
        self.assertTrue((FONT_DIR / "licenses" / "NOTICE.md").is_file())
        self.assertIn("Bitstream Vera", (FONT_DIR / "licenses" / "Hack-LICENSE.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
