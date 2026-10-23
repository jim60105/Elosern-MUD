"""Executed evidence for the pure map-client geometry contracts.

``covers_requirement`` attaches only to Python ``test_*`` methods, so each
contract class runs its focused Vitest file once through the JSON reporter and
every method asserts that the describe block for its requirement executed at
least one test and that all of them passed. An exit code alone is not
evidence: a renamed describe block or an empty run fails here.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
VIEWPORT_SUITE = REPO_ROOT / "web/webclient-app/tests/world/map_viewport.test.js"


def ensure_locked_frontend_install() -> None:
    """Install the locked pnpm dependencies once when Vitest is not present.

    The top-level CI job has Node and pnpm but no prior install step, so this
    module must not depend on another module having installed first.
    """
    if (REPO_ROOT / "node_modules/.bin/vitest").exists():
        return
    result = subprocess.run(
        ["pnpm", "install", "--frozen-lockfile"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=540,
    )
    if result.returncode != 0:
        raise AssertionError(
            "pnpm install --frozen-lockfile failed:\n" + result.stdout + result.stderr
        )


def run_vitest_json(suite: Path) -> tuple[subprocess.CompletedProcess, dict]:
    """Run exactly one Vitest file and return the process and its JSON report."""
    ensure_locked_frontend_install()
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "vitest.json"
        result = subprocess.run(
            [
                "npx",
                "--no-install",
                "vitest",
                "run",
                str(suite),
                "--reporter=json",
                f"--outputFile={report_path}",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    return result, report


class ViewportContracts(unittest.TestCase):
    """Runs ``map_viewport.test.js`` once; one method per requirement."""

    result: subprocess.CompletedProcess
    report: dict

    @classmethod
    def setUpClass(cls):
        if not VIEWPORT_SUITE.is_file():
            raise AssertionError(f"missing Vitest file {VIEWPORT_SUITE}")
        cls.result, cls.report = run_vitest_json(VIEWPORT_SUITE)

    def assert_run_green(self):
        failing = [
            " > ".join([*case.get("ancestorTitles", []), case.get("title", "")])
            + "\n"
            + "\n".join(case.get("failureMessages", []))
            for entry in self.report.get("testResults", [])
            for case in entry.get("assertionResults", [])
            if case.get("status") == "failed"
        ]
        output = "\n\n".join(failing) or (self.result.stdout + self.result.stderr)
        self.assertEqual(self.result.returncode, 0, "map viewport Vitest failed:\n" + output)
        self.assertTrue(self.report, "Vitest wrote no JSON report:\n" + output)
        files = self.report.get("testResults", [])
        self.assertEqual(
            [Path(entry["name"]).resolve() for entry in files],
            [VIEWPORT_SUITE.resolve()],
            "exactly the viewport file must run",
        )
        self.assertEqual(self.report.get("numFailedTests"), 0)
        self.assertGreater(self.report.get("numPassedTests", 0), 0)

    def assert_block_passed(self, describe: str):
        self.assert_run_green()
        cases = [
            case
            for entry in self.report["testResults"]
            for case in entry.get("assertionResults", [])
            if case.get("ancestorTitles", [None])[0] == describe
        ]
        self.assertTrue(cases, f"no tests ran under describe {describe!r}")
        statuses = {case["title"]: case["status"] for case in cases}
        self.assertTrue(
            all(status == "passed" for status in statuses.values()),
            f"describe {describe!r} has non-passing tests: {statuses}",
        )

    @covers_requirement(
        "webclient-map-viewport::map-navigation-preserves-uniform-geometry-and-the-zoom-anchor"
    )
    def test_uniform_projection_pan_and_anchored_zoom(self):
        # Uniform k on both axes with only the north axis inverted, the 3.5
        # gap ratio surviving pan and zoom, the zoom anchor pinned (also when
        # limits clamp), and project/unproject round trips.
        self.assert_block_passed("map navigation preserves uniform geometry and the zoom anchor")

    @covers_requirement(
        "webclient-map-viewport::map-zoom-stops-and-fit-follow-scope-and-aspect-ratio"
    )
    def test_zoom_stops_and_aspect_fit(self):
        # Continent fit on both axes in wide and tall frames without
        # distortion, the 800/200/40 km world stops, geometry-derived
        # settlement stops, the wilderness window, plus/minus stepping, fit
        # and recentre in scope units, and no fabricated coordinates.
        self.assert_block_passed("map zoom stops and fit follow scope and aspect ratio")

    @covers_requirement(
        "webclient-map-viewport::offscreen-geometry-avoids-the-selected-detail-drawer"
    )
    def test_edge_clamp_avoids_detail_drawer(self):
        # Pointers clamp left of the open 360 px drawer and recompute when it
        # closes; the same usable rectangle governs every edge.
        self.assert_block_passed("offscreen geometry avoids the selected detail drawer")


if __name__ == "__main__":
    unittest.main()
