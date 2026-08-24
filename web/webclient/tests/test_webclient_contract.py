"""Repository contracts for the local desktop WebClient shell (section 4.1).

These are pure repository checks: the project WebClient template and project
client modules must never reference a remote runtime URL, and the locally
served, committed browser assets must exist with license records.

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

# Committed runtime assets the page loads from the project origin (the Vue
# bundle under ``app/dist`` is gitignored and built in CI / the container
# image, so it is not a committed asset).
EXPECTED_RUNTIME_ASSETS = (
    "css/webclient.css",
    "css/ansi_palette.css",
    "js/jquery_ready_shim.js",
    "js/text_console.js",
    "js/elosern/protocol.js",
    "js/elosern/keyboard_router.js",
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

    def test_runtime_assets_exist(self):
        """Every committed runtime asset exists and is non-empty."""
        for relative in EXPECTED_RUNTIME_ASSETS:
            path = STATIC_ROOT / relative
            self.assertTrue(path.exists(), f"missing runtime asset {path}")
            self.assertGreater(
                path.stat().st_size, 100, f"runtime asset {path} looks empty"
            )

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


if __name__ == "__main__":
    unittest.main()
