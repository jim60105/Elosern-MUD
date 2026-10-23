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
AREA_VIEW_SUITE = REPO_ROOT / "web/webclient-app/tests/world/area_map_view.test.js"
WORLD_VIEW_SUITE = REPO_ROOT / "web/webclient-app/tests/world/world_map_view.test.js"
VITEST_BIN = REPO_ROOT / "node_modules/.bin/vitest"


def ensure_locked_frontend_install() -> None:
    """Install the locked pnpm dependencies once when Vitest is not present.

    The top-level CI job has Node and pnpm but no prior install step, so this
    module must not depend on another module having installed first.
    """
    if VITEST_BIN.exists():
        return
    try:
        result = subprocess.run(
            ["pnpm", "install", "--frozen-lockfile"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=540,
        )
    except FileNotFoundError as exc:
        raise AssertionError(
            "Vitest is not installed and pnpm is not on PATH; install the locked "
            "frontend toolchain (pnpm install --frozen-lockfile) first"
        ) from exc
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
                str(VITEST_BIN),
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


class VitestContractMixin:
    """Runs ``SUITE`` once per class; each method checks one describe block."""

    SUITE: Path
    SUITE_NAME: str
    result: subprocess.CompletedProcess
    report: dict

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.SUITE.is_file():
            raise AssertionError(f"missing Vitest file {cls.SUITE}")
        cls.result, cls.report = run_vitest_json(cls.SUITE)

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
        self.assertEqual(
            self.result.returncode, 0, f"{self.SUITE_NAME} Vitest failed:\n" + output
        )
        self.assertTrue(self.report, "Vitest wrote no JSON report:\n" + output)
        files = self.report.get("testResults", [])
        self.assertEqual(
            [Path(entry["name"]).resolve() for entry in files],
            [self.SUITE.resolve()],
            f"exactly the {self.SUITE_NAME} file must run",
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


class ViewportContracts(VitestContractMixin, unittest.TestCase):
    """Runs ``map_viewport.test.js`` once; one method per requirement."""

    SUITE = VIEWPORT_SUITE
    SUITE_NAME = "map viewport"

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


class AreaViewContracts(VitestContractMixin, unittest.TestCase):
    """Runs ``area_map_view.test.js`` once; one method per requirement."""

    SUITE = AREA_VIEW_SUITE
    SUITE_NAME = "area map view"

    @covers_requirement(
        "webclient-area-map-view::area-rendering-uses-truthful-geometry-and-server-fog"
    )
    def test_truthful_geometry_and_server_fog(self):
        # Schema-valid fixtures; unequal metre gaps proportional under pan and
        # zoom; dot step, dot caption and scale bar stating one distance; the
        # 15 x 15 wilderness window in cells with its district and cell_km
        # scale; radial rooms with no distance claims; an absent dungeon
        # branch (and a commission into it) leaving no node, road or text;
        # whole names with lower-priority labels hidden; new-map resets.
        self.assert_block_passed("area rendering uses truthful geometry and server fog")

    @covers_requirement(
        "webclient-area-map-view::area-selection-offers-travel-only-for-an-authoritative-adjacent-exit"
    )
    def test_adjacent_only_travel(self):
        # Pointer and keyboard selection reach 前往 only on a current-adjacent
        # node whose descriptor leads to it, emitting exactly
        # {exit_ref, destination, current_node} once; remote, current and
        # mismatched-descriptor nodes submit nothing; a drag never selects.
        self.assert_block_passed(
            "area selection offers travel only for an authoritative adjacent exit"
        )


class WorldViewContracts(VitestContractMixin, unittest.TestCase):
    """Runs ``world_map_view.test.js`` once; one method per requirement."""

    SUITE = WORLD_VIEW_SUITE
    SUITE_NAME = "world map view"

    @covers_requirement(
        "webclient-world-map-view::world-layers-render-in-the-approved-exploration-order"
    )
    def test_ordered_layers_and_unlit_privacy(self):
        # Schema-valid fixtures; the fourteen layers in the approved order;
        # unlit districts as hatching, a dotted border and 未探明 with no
        # landmark, terrain, place or undisclosed name; approximate
        # commissions as a dashed 36 km circle on the supplied 50 km point
        # labelled 大致方位 with no exact pin; only supplied borders.
        self.assert_block_passed("world layers render in the approved exploration order")

    @covers_requirement(
        "webclient-world-map-view::world-map-detail-follows-zoom-thresholds-without-shrinking-text"
    )
    def test_inclusive_lod_and_trail_resolution(self):
        # Inclusive 1000 km and 450 km boundaries, nations at 大陸/國, labels
        # never below 16px with collisions hidden by priority, and the trail
        # as a line until 近郊, then cells at the supplied 1 or 5 km
        # resolution; the dense worst case stays bounded.
        self.assert_block_passed("world map detail follows zoom thresholds without shrinking text")

    @covers_requirement(
        "webclient-world-map-view::newly-lit-districts-animate-accessibly-from-their-landmark"
    )
    def test_reveal_motion_and_announcement(self):
        # One 600 ms ink spread centred on the new district's landmark and
        # one 已探明 announcement per unlit-to-lit transition; none on the
        # first payload, a repeat, a remount, a new epoch or regressed
        # knowledge; reduced/off motion lights instantly and still announces.
        self.assert_block_passed("newly lit districts animate accessibly from their landmark")

    @covers_requirement(
        "webclient-world-map-view::world-selection-exposes-readable-permitted-detail"
    )
    def test_semantic_selection_detail(self):
        # The lit deep forest lists both nations by id; a single-nation
        # district lists one; unlit selections stay nameless; commissions and
        # places mirror supplied text; HTML buttons select and a drag never
        # does.
        self.assert_block_passed("world selection exposes readable permitted detail")


if __name__ == "__main__":
    unittest.main()
