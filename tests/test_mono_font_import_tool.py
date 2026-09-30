"""Unit tests for tools/import_mono_font.py (openspec change webclient-jim-mono-tc-font, D1).

The import tool filters the pinned Jim Mono TC web release down to the kept
Regular / Bold slices, rewrites their stylesheet, and derives the code point
manifest. These tests run on a synthetic release zip built in memory, so they
need no network access and no real font files.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from tools import import_mono_font as tool

ROOT = "JimMonoTC-9.9.9-web"
WOFF2 = b"wOF2" + b"\0" * 60

# (style, group, weight, unicode-range) in release order.
RULES = [
    ("Regular", "latin", 400, "U+0020-007E, U+2190-2193"),
    ("Regular", "latin-ext", 400, "U+0100-017F"),
    ("Regular", "greek-cyrillic", 400, "U+0391-03A9"),
    ("Regular", "box", 400, "U+2500-259F"),
    ("Regular", "symbols", 400, "U+25A0-25FF"),
    ("Regular", "icons-0", 400, "U+E000-E0FF"),
    ("Regular", "cjk-0", 400, "U+770B, U+3002"),
    ("Regular", "cjk-1", 400, "U+4E2D"),
    ("Regular", "cjk-x0", 400, "U+2A6D6"),
    ("Bold", "latin", 700, "U+0020-007E, U+2190-2193"),
    ("Bold", "latin-ext", 700, "U+0100-017F"),
    ("Bold", "greek-cyrillic", 700, "U+0391-03A9"),
    ("Bold", "box", 700, "U+2500-259F"),
    ("Bold", "symbols", 700, "U+25A0-25FF, U+2665"),
    ("Bold", "cjk-0", 700, "U+770B, U+3002"),
    ("Bold", "cjk-1", 700, "U+4E2D"),
    ("Italic", "latin", 400, "U+0020-007E"),
]

NOTO_CSS = """
@font-face {
  font-family: 'Noto Sans TC';
  font-style: normal;
  font-weight: 400;
  src: url(../fonts/notosans/a.0.woff2) format('woff2');
  unicode-range: U+770b, U+3002, U+4e2d, U+5317, U+41;
}
@font-face {
  font-family: 'Noto Sans TC';
  font-style: normal;
  font-weight: 700;
  src: url(../fonts/notosans/b.0.woff2) format('woff2');
  unicode-range: U+9580;
}
"""


def release_css(rules=RULES) -> str:
    blocks = []
    for style, group, weight, ranges in rules:
        font_style = "italic" if "Italic" in style else "normal"
        blocks.append(
            "@font-face {\n"
            '  font-family: "Jim Mono TC";\n'
            f'  src: url("/fonts/JimMonoTC-{style}.{group}.woff2") format("woff2");\n'
            f"  font-weight: {weight};\n"
            f"  font-style: {font_style};\n"
            "  font-display: swap;\n"
            f"  unicode-range: {ranges};\n"
            "}\n"
        )
    return "\n".join(blocks)


def make_zip(rules=RULES, css=None, files=None, licenses=None, extra=None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{ROOT}/JimMonoTC.css", css if css is not None else release_css(rules))
        names = files if files is not None else {f"JimMonoTC-{s}.{g}.woff2": WOFF2 for s, g, _w, _r in rules}
        for name, data in names.items():
            zf.writestr(f"{ROOT}/{name}", data)
        for name, data in (licenses if licenses is not None else {"LICENSE": b"SIL OPEN FONT LICENSE Version 1.1"}).items():
            zf.writestr(f"{ROOT}/licenses/{name}", data)
        for info, data in extra or ():
            zf.writestr(info, data)
    return buf.getvalue()


class ParseTest(unittest.TestCase):
    def test_parse_ranges_expands_singles_and_spans(self):
        self.assertEqual(tool.parse_ranges("U+0041-0043, U+2026,U+4e2d"), {0x41, 0x42, 0x43, 0x2026, 0x4E2D})

    def test_parse_css_reads_quoted_and_unquoted_urls(self):
        css = release_css(RULES[:1]) + release_css(RULES[1:2]).replace('url("/fonts/', "url(/fonts/").replace('.woff2")', ".woff2)")
        rules = tool.parse_css(css)
        self.assertEqual([(r["style"], r["group"]) for r in rules], [("Regular", "latin"), ("Regular", "latin-ext")])
        self.assertEqual(rules[0]["file"], "JimMonoTC-Regular.latin.woff2")
        self.assertIn(0x2190, rules[0]["codepoints"])

    def test_group_selection_keeps_one_cell_and_frequency_cjk_only(self):
        self.assertTrue(tool.is_kept("Regular", "latin"))
        self.assertTrue(tool.is_kept("Bold", "cjk-87"))
        for style, group in (("Regular", "icons-0"), ("Regular", "cjk-x0"), ("Italic", "latin"), ("BoldItalic", "cjk-0")):
            self.assertFalse(tool.is_kept(style, group), (style, group))


class BuildTest(unittest.TestCase):
    def build(self, archive):
        return tool.build(archive, NOTO_CSS)

    def test_outputs_hold_only_kept_slices_licences_manifest_and_sheet(self):
        out = self.build(make_zip())
        slices = sorted(k for k in out if k.endswith(".woff2"))
        self.assertEqual(len(slices), 14)
        self.assertFalse([k for k in slices if "icons" in k or "cjk-x" in k or "Italic" in k])
        self.assertIn("fonts/jimmonotc/licenses/LICENSE", out)
        self.assertIn("styles/fonts-mono.css", out)

    def test_sheet_rewrites_urls_and_keeps_other_properties_in_release_order(self):
        css = self.build(make_zip())["styles/fonts-mono.css"].decode()
        self.assertTrue(css.startswith("/*\n * GENERATED by tools/import_mono_font.py"))
        self.assertIn("SIL Open Font", css)
        first = css.split("@font-face {", 2)[1]
        self.assertEqual(
            [line.strip().split(":")[0] for line in first.strip().splitlines()[:-1]],
            ["font-family", "src", "font-weight", "font-style", "font-display", "unicode-range"],
        )
        self.assertIn("src: url(../fonts/jimmonotc/JimMonoTC-Regular.latin.woff2) format('woff2');", css)
        self.assertNotIn("/fonts/JimMonoTC", css.replace("../fonts/jimmonotc/JimMonoTC", ""))
        self.assertEqual(css.count("@font-face"), 14)
        self.assertLess(css.index("Regular.cjk-1"), css.index("Bold.latin."))

    def test_manifest_splits_one_cell_and_cjk_and_records_missing_wide_noto(self):
        manifest = json.loads(self.build(make_zip())["fonts/jimmonotc/codepoints.json"])
        self.assertEqual(manifest["release"], tool.RELEASE)
        self.assertIn(0x2665, manifest["bold"])
        self.assertNotIn(0x2665, manifest["regular"])
        self.assertNotIn(0x770B, manifest["regular"])
        self.assertEqual(manifest["cjk"], {"regular": [0x3002, 0x4E2D, 0x770B], "bold": [0x3002, 0x4E2D, 0x770B]})
        # 北 is wide and in Noto 400 but undeclared; A is narrow; 門 is only in Noto 700.
        self.assertEqual(manifest["noto_wide_missing"], [0x5317])

    def test_a_second_build_is_byte_identical(self):
        self.assertEqual(self.build(make_zip()), self.build(make_zip()))


class RejectTest(unittest.TestCase):
    def assertRejected(self, archive, fragment):
        with self.assertRaises(tool.ReleaseContractError) as ctx:
            tool.build(archive, NOTO_CSS)
        self.assertIn(fragment, str(ctx.exception))

    def files(self, **changes):
        names = {f"JimMonoTC-{s}.{g}.woff2": WOFF2 for s, g, _w, _r in RULES}
        for name, data in changes.items():
            if data is None:
                names.pop(name)
            else:
                names[name] = data
        return names

    def test_oversized_slice(self):
        big = {"JimMonoTC-Regular.box.woff2": b"wOF2" + b"\0" * tool.MAX_SLICE_BYTES}
        self.assertRejected(make_zip(files=self.files(**big)), "65536")

    def test_non_woff2_slice(self):
        self.assertRejected(make_zip(files=self.files(**{"JimMonoTC-Bold.box.woff2": b"OTTO"})), "not woff2")

    def test_kept_rule_without_its_file(self):
        self.assertRejected(make_zip(files=self.files(**{"JimMonoTC-Bold.cjk-1.woff2": None})), "has no file")

    def test_kept_file_without_a_rule(self):
        self.assertRejected(make_zip(files=self.files(**{"JimMonoTC-Bold.cjk-2.woff2": WOFF2})), "has no CSS rule")

    def test_overlapping_ranges_within_a_weight(self):
        rules = [r if (r[0], r[1]) != ("Regular", "box") else ("Regular", "box", 400, "U+2500-25A0") for r in RULES]
        self.assertRejected(make_zip(rules), "overlaps")

    def test_weights_with_different_cjk(self):
        rules = [r if (r[0], r[1]) != ("Bold", "cjk-1") else ("Bold", "cjk-1", 700, "U+4E2E") for r in RULES]
        self.assertRejected(make_zip(rules), "different CJK")

    def test_ascii_or_arrow_outside_latin(self):
        rules = [r if (r[0], r[1]) != ("Regular", "symbols") else ("Regular", "symbols", 400, "U+2194-21FF, U+0041") for r in RULES]
        rules = [r if (r[0], r[1]) != ("Regular", "latin") else ("Regular", "latin", 400, "U+0020-0040, U+0042-007E, U+2190-2193") for r in rules]
        self.assertRejected(make_zip(rules), "outside latin")
        rules = [r if (r[0], r[1]) != ("Bold", "latin") else ("Bold", "latin", 700, "U+0020-007E") for r in RULES]
        rules = [r if (r[0], r[1]) != ("Bold", "symbols") else ("Bold", "symbols", 700, "U+2190-2193, U+25A0-25FF") for r in rules]
        self.assertRejected(make_zip(rules), "outside latin")

    def test_missing_licence(self):
        self.assertRejected(make_zip(licenses={"NOTICE.md": b"x"}), "licenses/LICENSE")

    def test_licence_member_escaping_the_tree(self):
        self.assertRejected(make_zip(extra=[(f"{ROOT}/licenses/../../evil.txt", b"x")]), "unsafe")

    def test_duplicate_member(self):
        self.assertRejected(make_zip(extra=[(f"{ROOT}/JimMonoTC-Bold.box.woff2", WOFF2)]), "duplicate")

    def test_symbolic_link_member(self):
        info = zipfile.ZipInfo(f"{ROOT}/licenses/link")
        info.external_attr = (0o120777 << 16)
        self.assertRejected(make_zip(extra=[(info, b"/etc/passwd")]), "symbolic link")


class MainTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "release.zip"
        self.archive.write_bytes(make_zip())
        font_dir = self.root / "app/fonts/jimmonotc"
        font_dir.mkdir(parents=True)
        (font_dir / "old.woff2").write_bytes(b"old")
        noto = self.root / "app/styles/fonts.css"
        noto.parent.mkdir(parents=True)
        noto.write_text(NOTO_CSS)
        for name, value in {
            "APP_ROOT": self.root / "app",
            "FONT_DIR": font_dir,
            "CSS_PATH": self.root / "app/styles/fonts-mono.css",
            "NOTO_CSS_PATH": noto,
            "ASSET_SHA256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
        }.items():
            patcher = mock.patch.object(tool, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tree(self):
        return sorted(p.relative_to(self.root).as_posix() for p in self.root.joinpath("app").rglob("*") if p.is_file())

    def test_a_checksum_mismatch_exits_before_touching_the_tree(self):
        before = self.tree()
        with mock.patch.object(tool, "ASSET_SHA256", "0" * 64), self.assertRaises(SystemExit):
            tool.main([str(self.archive)])
        self.assertEqual(self.tree(), before)

    def test_a_contract_breach_returns_non_zero_and_writes_nothing(self):
        self.archive.write_bytes(make_zip(licenses={}))
        before = self.tree()
        with mock.patch.object(tool, "ASSET_SHA256", hashlib.sha256(self.archive.read_bytes()).hexdigest()), \
                mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(tool.main([str(self.archive)]), 1)
        self.assertEqual(self.tree(), before)

    def test_a_run_replaces_the_tree_and_a_second_run_is_identical(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(tool.main([str(self.archive)]), 0)
        first = {p: (self.root / p).read_bytes() for p in self.tree()}
        self.assertNotIn("app/fonts/jimmonotc/old.woff2", first)
        self.assertIn("app/fonts/jimmonotc/codepoints.json", first)
        self.assertIn("app/styles/fonts-mono.css", first)
        for leftover in ("fonts/jimmonotc.tmp", "fonts/jimmonotc.old", "styles/fonts-mono.css.tmp"):
            self.assertFalse((self.root / "app" / leftover).exists(), leftover)
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(tool.main([str(self.archive)]), 0)
        self.assertEqual({p: (self.root / p).read_bytes() for p in self.tree()}, first)

    def test_a_failed_staging_leaves_the_old_tree_and_no_leftovers(self):
        before = self.tree()
        real = Path.write_bytes

        def flaky(path, data):
            if path.name == "codepoints.json":
                raise OSError("disk full")
            return real(path, data)

        with mock.patch.object(Path, "write_bytes", flaky), self.assertRaises(OSError):
            tool.main([str(self.archive)])
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.root / "app/fonts/jimmonotc.tmp").exists())


if __name__ == "__main__":
    unittest.main()
