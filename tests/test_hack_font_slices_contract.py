"""Contract for the committed, self-hosted Hack monospace slices.

The WebClient's ``--f-mono`` role draws with Hack served from the project
origin as small unicode-range woff2 slices (openspec change
``webclient-hack-mono-font``, design D2/D4/D5/D7). This test reads the
committed generator outputs -- ``styles/fonts-hack.css``, ``fonts/hack/`` and
its per-weight ``codepoints.json`` manifest -- and the token sheet, and checks
that every slice exists, is small, is not silently inlined by Vite, declares a
disjoint range, and that together the slices of one weight cover every
drawable Hack code point. Pure file reads; no browser, no network.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "web" / "webclient-app"
FONT_DIR = APP_ROOT / "fonts" / "hack"
CSS_PATH = APP_ROOT / "styles" / "fonts-hack.css"
TOKENS_PATH = APP_ROOT / "styles" / "tokens.css"

SLICE_NAMES = ("latin", "latin-ext", "greek-cyrillic", "box", "symbols")
WEIGHTS = {400: "regular", 700: "bold"}
MONO_STACK = '"Hack", "Noto Sans TC", monospace'
ARROWS = set(range(0x2190, 0x2194))
CJK_BLOCKS = ((0x2E80, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x10FFFF))
# Vite's assetsInlineLimit and the spec's small-file ceiling.
MIN_BYTES = 4096
MAX_BYTES = 40960


def _faces() -> list[dict]:
    """Parse every @font-face rule of the generated Hack stylesheet."""
    faces = []
    for block in re.findall(r"@font-face \{(.*?)\}", CSS_PATH.read_text(encoding="utf-8"), re.S):
        cps: set[int] = set()
        for part in re.search(r"unicode-range: ([^;]+);", block).group(1).split(", "):
            lo, _, hi = part.removeprefix("U+").partition("-")
            cps.update(range(int(lo, 16), int(hi or lo, 16) + 1))
        src = re.search(r"url\(([^)]+)\) format\('woff2'\)", block).group(1)
        faces.append({
            "family": re.search(r"font-family: ([^;]+);", block).group(1),
            "weight": int(re.search(r"font-weight: (\d+);", block).group(1)),
            "style": re.search(r"font-style: ([^;]+);", block).group(1),
            "src": src,
            "slice": re.fullmatch(r"\.\./fonts/hack/hack-[a-z]+\.([a-z-]+)\.woff2", src).group(1),
            "codepoints": cps,
        })
    return faces


class HackFontSlicesContractTest(unittest.TestCase):
    """The committed Hack slices are small, disjoint, complete, and licensed."""

    @classmethod
    def setUpClass(cls):
        cls.faces = _faces()
        cls.manifest = json.loads((FONT_DIR / "codepoints.json").read_text(encoding="utf-8"))

    def test_every_url_resolves_and_every_slice_is_referenced(self):
        referenced = {(CSS_PATH.parent / face["src"]).resolve() for face in self.faces}
        for path in referenced:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(referenced, {path.resolve() for path in FONT_DIR.glob("*.woff2")})
        for face in self.faces:
            self.assertEqual(face["family"], "'Hack'")
            self.assertEqual(face["style"], "normal")

    def test_every_slice_is_woff2_between_the_inline_limit_and_the_ceiling(self):
        slices = sorted(FONT_DIR.glob("*.woff2"))
        self.assertEqual(len(slices), len(WEIGHTS) * len(SLICE_NAMES))
        for path in slices:
            with self.subTest(slice=path.name):
                data = path.read_bytes()
                self.assertEqual(data[:4], b"wOF2")
                self.assertGreaterEqual(len(data), MIN_BYTES)
                self.assertLessEqual(len(data), MAX_BYTES)

    def test_both_weights_declare_every_slice_once(self):
        for weight, name in WEIGHTS.items():
            faces = [face for face in self.faces if face["weight"] == weight]
            self.assertEqual(sorted(face["slice"] for face in faces), sorted(SLICE_NAMES))
            for face in faces:
                self.assertIn(f"/hack-{name}.", face["src"])

    def test_declared_ranges_are_disjoint_and_cover_the_hack_cmap(self):
        for weight, name in WEIGHTS.items():
            with self.subTest(weight=weight):
                sets = [face["codepoints"] for face in self.faces if face["weight"] == weight]
                union = set().union(*sets)
                self.assertEqual(sum(map(len, sets)), len(union), "declared ranges overlap")
                self.assertEqual(union, set(self.manifest[name]))
                self.assertFalse(union & {0x0000, 0x000D, 0xFEFF})

    def test_arrows_ship_in_the_latin_slice_and_no_range_enters_cjk(self):
        for face in self.faces:
            with self.subTest(weight=face["weight"], slice=face["slice"]):
                if face["slice"] == "latin":
                    self.assertLessEqual(ARROWS, face["codepoints"])
                else:
                    self.assertFalse(ARROWS & face["codepoints"])
                for lo, hi in CJK_BLOCKS:
                    self.assertFalse(any(lo <= cp <= hi for cp in face["codepoints"]))

    def test_license_ships_beside_the_font_files(self):
        text = (FONT_DIR / "LICENSE.md").read_text(encoding="utf-8")
        self.assertIn("MIT", text)
        self.assertIn("Bitstream Vera", text)

    def test_monospace_token_names_only_the_bundled_faces(self):
        match = re.search(r"--f-mono:\s*([^;]+);", TOKENS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(match.group(1).strip(), MONO_STACK)


if __name__ == "__main__":
    unittest.main()
