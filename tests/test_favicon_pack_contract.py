"""Repository contract tests for the favicon pack.

The pack under ``web/static/favicon/`` is generated from ``web/brand/`` by
``pnpm run favicon`` (realfavicon). These checks keep the generated files, the
shared Django include, and the three frontend surfaces (game webclient, GM
portal, Storybook) pointing at the same assets.
"""

from pathlib import Path
import json
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "web/static/favicon"
INCLUDE = REPO_ROOT / "web/templates/brand/favicon.html"
MARKUPS = REPO_ROOT / "web/brand/favicon-markups.json"
STATIC_PREFIX = "/static/"

STATIC_TAG_RE = re.compile(r"""\{%\s*static\s+"([^"]+)"\s*%\}""")
HREF_RE = re.compile(r'href="([^"]+)"')


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class FaviconPackContractTests(unittest.TestCase):
    def test_include_mirrors_generated_markups(self):
        """Every generated link resolves to a pack file the include serves."""
        markups = json.loads(_read(MARKUPS))["markups"]
        generated = []
        for markup in markups:
            match = HREF_RE.search(markup)
            if match is None:
                continue
            href = match.group(1)
            self.assertTrue(href.startswith(STATIC_PREFIX), href)
            generated.append(href[len(STATIC_PREFIX):])
        self.assertTrue(generated)
        included = STATIC_TAG_RE.findall(_read(INCLUDE))
        self.assertEqual(sorted(included), sorted(generated))
        for name in included:
            path = REPO_ROOT / "web/static" / name
            self.assertTrue(path.is_file(), f"missing pack file {path}")
            self.assertGreater(path.stat().st_size, 0, f"{path} is empty")

    def test_manifest_icons_exist_in_pack(self):
        manifest = json.loads(_read(PACK_DIR / "site.webmanifest"))
        self.assertTrue(manifest["icons"])
        for icon in manifest["icons"]:
            src = icon["src"]
            self.assertTrue(src.startswith(STATIC_PREFIX), src)
            self.assertTrue((REPO_ROOT / "web/static" / src[len(STATIC_PREFIX):]).is_file(), src)

    def test_svg_favicon_is_one_colour_and_adapts_to_browser_theme(self):
        svg = _read(PACK_DIR / "favicon.svg")
        colours = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6})"', svg))
        self.assertEqual(len(colours), 1, colours)
        self.assertIn("prefers-color-scheme: light", svg)
        self.assertIn("prefers-color-scheme: dark", svg)

    def test_game_and_gm_templates_include_the_pack(self):
        for name in (
            "web/templates/webclient/base.html",
            "web/templates/gm/index.html",
            "web/templates/gm/forbidden.html",
        ):
            with self.subTest(template=name):
                head = _read(REPO_ROOT / name).split("</head>", 1)[0]
                self.assertIn('{% include "brand/favicon.html" %}', head)

    def test_storybook_serves_the_pack_svg_as_its_favicon(self):
        main = _read(REPO_ROOT / ".storybook/main.js")
        self.assertRegex(
            main,
            r'from:\s*"\.\./web/static/favicon/favicon\.svg",\s*to:\s*"/favicon\.svg"',
        )


if __name__ == "__main__":
    unittest.main()
