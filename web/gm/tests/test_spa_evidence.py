"""Evidence bridge: execute the GM SPA gates as Python test evidence.

The GM SPA (``web/admin-app``) is verified by Node/Vitest gates;
``covers_requirement`` can only attach to a Python ``test_*`` function, so this
module runs the GM Vite build, the dependency-free import-boundary test, the
GM Vitest files, and the extended showcase-coverage gate, asserting each
passes. Following the precedent of earlier Vue evidence bridges, the
``@covers_requirement`` annotations for the ``gm-portal-spa`` requirements
were applied at the change's archive, once the delta spec synced into the
main spec put the requirement IDs into the traceability index.

Every build runs under the shared showcase build lock: ``storybook build``
copies ``web/static`` (which holds ``gm/dist``) and the GM build empties that
directory, so the two must never overlap across parallel test workers.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement
from web.webclient.tests._showcase_build import showcase_build_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
GM_DIST = REPO_ROOT / "web/static/gm/dist"
GAME_DIST = REPO_ROOT / "web/static/webclient/app/dist"
GM_TESTS = REPO_ROOT / "web/admin-app/tests"


def _run(command: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=timeout
    )


def _run_vitest(*names: str) -> subprocess.CompletedProcess[str]:
    """Run the named GM Vitest files; every named file must exist."""
    files = [GM_TESTS / name for name in names]
    missing = [str(path) for path in files if not path.is_file()]
    assert not missing, f"GM Vitest evidence files missing: {missing}"
    return _run(["npx", "--no-install", "vitest", "run", *map(str, files)])


def _game_dist_snapshot() -> dict[str, int] | None:
    if not GAME_DIST.is_dir():
        return None
    return {
        str(path.relative_to(GAME_DIST)): path.stat().st_mtime_ns
        for path in GAME_DIST.rglob("*")
        if path.is_file()
    }


class GmBuildEvidenceTest(unittest.TestCase):
    @covers_requirement("gm-portal-spa::independent-same-origin-gm-build")
    def test_gm_build_emits_stable_entries_without_touching_the_game_bundle(self):
        with showcase_build_lock():
            before = _game_dist_snapshot()
            # A stale output must never satisfy the assertions below.
            shutil.rmtree(GM_DIST, ignore_errors=True)
            result = _run(["pnpm", "run", "build:gm"], timeout=600)
            after = _game_dist_snapshot()
            entry_js = GM_DIST / "index.js"
            entry_css = GM_DIST / "index.css"
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(entry_js.is_file() and entry_js.stat().st_size > 0)
            self.assertTrue(entry_css.is_file() and entry_css.stat().st_size > 0)
            bundle = entry_js.read_text(encoding="utf-8")
            stylesheet = entry_css.read_text(encoding="utf-8")
            extra = sorted(
                str(path.relative_to(GM_DIST))
                for path in GM_DIST.rglob("*")
                if path.is_file() and path.parent != GM_DIST / "assets"
            )
        # Additional chunks stay under the GM output's assets/ directory.
        self.assertEqual(extra, ["index.css", "index.js"])
        # Same-origin and token-based: the GM base and the shared palette.
        self.assertIn("/gm/api", bundle)
        self.assertIn("--ink-950", stylesheet)
        self.assertIn("/static/gm/dist/assets/", stylesheet)
        self.assertIsNone(re.search(r"""url\(\s*['"]?https?://""", stylesheet))
        # Isolation: the game bundle is neither rebuilt nor deleted.
        self.assertEqual(before, after)
        self.assertNotIn("PANEL_ALLOWLIST", bundle)


class GmFrontendGateEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "gm-portal-spa::enforced-token-only-game-dependency-boundary",
        "gm-portal-spa::frontend-acceptance-gates",
    )
    def test_import_boundary_node_gate_passes(self):
        result = _run(["pnpm", "run", "test:gm-boundary"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"(?m)^\S+ fail 0$")
        self.assertIn("the real GM tree imports only allowlisted tokens and fonts", result.stdout)
        self.assertIn("forbidden: alternate relative path", result.stdout)

    @covers_requirement("gm-portal-spa::frontend-acceptance-gates")
    def test_gm_vitest_suite_passes(self):
        suites = sorted(path.name for path in GM_TESTS.glob("*.test.js"))
        self.assertEqual(
            suites,
            ["api.test.js", "components.test.js", "overview.test.js", "router.test.js", "session.test.js", "shell.test.js"],
        )
        result = _run_vitest(*suites)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Test Files\s+6 passed")

    @covers_requirement("gm-portal-spa::single-gm-fetch-boundary")
    def test_fetch_boundary_vitest_cases_pass(self):
        result = _run_vitest("api.test.js", "session.test.js")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Test Files\s+2 passed")

    @covers_requirement("gm-portal-spa::s1-navigation-and-history-routing")
    def test_navigation_and_routing_vitest_cases_pass(self):
        result = _run_vitest("router.test.js", "shell.test.js", "overview.test.js")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Test Files\s+3 passed")

    @covers_requirement("gm-portal-spa::operator-component-layer")
    def test_component_layer_vitest_cases_pass(self):
        result = _run_vitest("components.test.js", "shell.test.js")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Test Files\s+2 passed")

    @covers_requirement(
        "gm-portal-spa::operator-component-layer",
        "gm-portal-spa::frontend-acceptance-gates",
    )
    def test_showcase_coverage_includes_every_gm_component(self):
        result = _run(["node", "scripts/component-coverage.mjs"], timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("GM component coverage: all 8 required GM component(s)", result.stdout)
        self.assertIn("component coverage: all", result.stdout)

    @covers_requirement("gm-portal-spa::operator-component-layer")
    def test_showcase_coverage_fails_for_an_unlisted_gm_component(self):
        import json
        import tempfile

        manifest = json.loads(
            (REPO_ROOT / "web/admin-app/component-manifest.json").read_text(encoding="utf-8")
        )
        manifest["required"] = [t for t in manifest["required"] if t != "GM/GmTable"]
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "gm-manifest.json"
            probe.write_text(json.dumps(manifest), encoding="utf-8")
            result = _run(
                ["node", "scripts/component-coverage.mjs", "--gm-manifest", str(probe)],
                timeout=120,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GM/GmTable", result.stderr)
        self.assertIn("components/GmTable.vue", result.stderr)


if __name__ == "__main__":
    unittest.main()
