"""Repository-wide contract for the committed Vue-migration design draft (設計稿).

The validated static single-screen showcase is committed verbatim under
``docs/design/elosern-redesign/`` with its self-hosted woff2 set under
``docs/design/fonts-dl/`` (roadmap A1, change
``webclient-vue-00-audit-and-design-docs``). It is the design reference the
B-wave component changes build against, so it must stay a self-contained,
offline file set: linked from ``docs/_sidebar.md``, referencing no remote or
CDN asset, and with every local asset reference resolving to a committed file.
This is a plain repository regression check (no new main-capability
requirement, so no ``covers_requirement`` annotation).
"""

from pathlib import Path
import re
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
DESIGN_ROOT = REPO_ROOT / "docs" / "design"
DESIGN_DIR = DESIGN_ROOT / "elosern-redesign"
SIDEBAR = REPO_ROOT / "docs" / "_sidebar.md"

SIDEBAR_LINK_TARGET = "/design/elosern-redesign/index"
REMOTE_SCHEMES = ("http://", "https://")
REMOTE_REFERENCE = re.compile(r"""(?:src|href)\s*=\s*["']\s*//|url\(\s*["']?//""")
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+?)['\"]?\s*\)")
HTML_LOCAL = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""")


class DesignDraftDocumentsContract(unittest.TestCase):
    def test_design_draft_exists_under_docs(self):
        for name in ("index.html", "fonts.css", "REDESIGN.md"):
            with self.subTest(file=name):
                self.assertTrue((DESIGN_DIR / name).is_file())
        fonts = sorted(DESIGN_ROOT.glob("fonts-dl/*/*.woff2"))
        self.assertGreater(len(fonts), 0)
        source = (DESIGN_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="fonts.css"', source)

    def test_design_draft_is_linked_from_the_sidebar(self):
        sidebar = SIDEBAR.read_text(encoding="utf-8")
        self.assertIn(f"]({SIDEBAR_LINK_TARGET})", sidebar)

    def test_design_draft_references_no_remote_or_cdn_asset(self):
        candidates = sorted(DESIGN_DIR.glob("*.html")) + sorted(DESIGN_DIR.glob("*.css"))
        for path in candidates:
            source = path.read_text(encoding="utf-8")
            with self.subTest(file=path.relative_to(REPO_ROOT).as_posix()):
                for scheme in REMOTE_SCHEMES:
                    self.assertNotIn(scheme, source)
                self.assertIsNone(
                    REMOTE_REFERENCE.search(source), "protocol-relative asset reference"
                )
                self.assertNotIn("cdn.", source.lower())

    def test_design_draft_local_asset_references_resolve(self):
        fonts_css = DESIGN_DIR / "fonts.css"
        css = fonts_css.read_text(encoding="utf-8")
        targets = sorted(set(CSS_URL.findall(css)))
        self.assertGreater(len(targets), 0)
        for target in targets:
            with self.subTest(url=target):
                self.assertTrue(
                    (DESIGN_DIR / target).is_file(), f"missing font asset: {target}"
                )

        index = DESIGN_DIR / "index.html"
        html = index.read_text(encoding="utf-8")
        local_targets = sorted(
            {
                target
                for target in HTML_LOCAL.findall(html)
                if not target.startswith(("#", "http://", "https://", "mailto:"))
            }
        )
        self.assertTrue(local_targets)
        for target in local_targets:
            with self.subTest(ref=target):
                self.assertTrue((DESIGN_DIR / target).is_file())
