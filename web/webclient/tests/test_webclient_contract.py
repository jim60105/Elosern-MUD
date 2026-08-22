"""Repository contracts for the local desktop WebClient shell (section 4.1).

These are pure repository checks: the project WebClient template and project
client modules must never reference a remote runtime URL, and the locally
served, pinned browser assets must exist with license records.

The matching main-spec requirements are not indexed under ``openspec/specs/``
until the delta specs are synced (section 8.2); the traceability annotation is
added there together with the other foundation tests.
"""

from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement

WEB_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = WEB_ROOT / "static" / "webclient"
TEMPLATE_ROOT = WEB_ROOT / "templates" / "webclient"
VENDOR_ROOT = STATIC_ROOT / "vendor"

EXPECTED_VENDOR_ASSETS = (
    "js/jquery-3.2.1.min.js",
    "js/goldenlayout.min.js",
    "css/goldenlayout-base.css",
    "css/goldenlayout-dark-theme.css",
    "LICENSES.md",
)


class WebclientShellContractTest(unittest.TestCase):
    """Assert the shell loads every runtime UI dependency from the project origin."""

    @covers_requirement(
        "webclient-desktop-shell::the-webclient-loads-a-local-vue-spa-desktop-shell"
    )
    def test_templates_reference_no_remote_url(self):
        """No http:// or https:// URL appears in a project WebClient template."""
        for name in ("base.html", "webclient.html"):
            path = TEMPLATE_ROOT / name
            self.assertTrue(path.exists(), f"missing template {path}")
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("http://", content, f"{path} references a remote http URL")
            self.assertNotIn("https://", content, f"{path} references a remote https URL")

    def test_vendored_assets_exist(self):
        """Every pinned runtime asset exists and is non-empty."""
        for relative in EXPECTED_VENDOR_ASSETS:
            path = VENDOR_ROOT / relative
            self.assertTrue(path.exists(), f"missing vendored asset {path}")
            self.assertGreater(
                path.stat().st_size, 100, f"vendored asset {path} looks empty"
            )

    def test_license_record_covers_every_asset(self):
        """LICENSES.md records every vendored file and an MIT license."""
        license_path = VENDOR_ROOT / "LICENSES.md"
        self.assertTrue(license_path.exists())
        text = license_path.read_text(encoding="utf-8")
        for relative in EXPECTED_VENDOR_ASSETS:
            if relative == "LICENSES.md":
                continue
            self.assertIn(
                relative, text, f"LICENSES.md does not record {relative}"
            )
        self.assertIn("MIT", text, "LICENSES.md does not record the MIT license")
        self.assertIn("jQuery 3.2.1", text, "LICENSES.md does not pin the jQuery version")

    def test_client_modules_reference_no_remote_url(self):
        """No project-authored client JS/CSS (outside vendor and tests) uses a remote URL."""
        offenders = []
        for path in sorted(STATIC_ROOT.rglob("*")):
            if not path.is_file() or path.suffix not in (".js", ".css"):
                continue
            relative = path.relative_to(STATIC_ROOT).as_posix()
            if (
                relative.startswith("vendor/")
                # Vite build output (gitignored; regenerated from the authored
                # sources plus locked npm dependencies, never hand-authored).
                or relative.startswith("app/dist/")
                or "/tests/" in "/" + relative
            ):
                continue
            content = path.read_text(encoding="utf-8")
            if "http://" in content or "https://" in content:
                offenders.append(relative)
        self.assertEqual(
            offenders, [], "project client modules reference remote URLs"
        )

    def test_vendored_goldenlayout_is_pinned_not_latest(self):
        """The vendored GoldenLayout is a committed file, not a live URL."""
        golden = VENDOR_ROOT / "js" / "goldenlayout.min.js"
        self.assertTrue(golden.exists())
        content = golden.read_text(encoding="utf-8")
        self.assertIn("LayoutManager", content)
        self.assertNotIn("golden-layout.com/files/latest", content)


if __name__ == "__main__":
    unittest.main()
