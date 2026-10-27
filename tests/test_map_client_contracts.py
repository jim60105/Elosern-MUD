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
# The neutral viewport primitives moved into the local @elosern/map-view
# package (map-view-shared-foundations); this suite now proves the game's own
# stop/chrome policy wired through them.
VIEWPORT_SUITE = REPO_ROOT / "web/webclient-app/tests/world/map_view_policy.test.js"
AREA_VIEW_SUITE = REPO_ROOT / "web/webclient-app/tests/world/area_map_view.test.js"
WORLD_VIEW_SUITE = REPO_ROOT / "web/webclient-app/tests/world/world_map_view.test.js"
DRAWER_SUITE = REPO_ROOT / "web/webclient-app/tests/world/map_drawer.test.js"
POINTER_SUITE = REPO_ROOT / "web/webclient-app/tests/world/map_edge_pointers.test.js"
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
    """Runs ``map_view_policy.test.js`` once; one method per requirement."""

    SUITE = VIEWPORT_SUITE
    SUITE_NAME = "map view policy"

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


class MapDrawerContracts(VitestContractMixin, unittest.TestCase):
    """Runs ``map_drawer.test.js`` once; one method per requirement."""

    SUITE = DRAWER_SUITE
    SUITE_NAME = "map drawer"

    @covers_requirement(
        "webclient-map-drawer::the-map-drawer-opens-the-appropriate-scope-and-preserves-session-views"
    )
    def test_scope_by_layer_and_session_views(self):
        # Area in settlements, dungeons and interiors and world in the
        # wilderness on every opening; each tab keeps its pan, zoom and
        # selection; the world tab opens at 國 with the tracked commission;
        # a new epoch retires all memory; one header with ARIA tabs and one
        # close control inside OverlayHost.
        self.assert_block_passed("the map drawer opens the appropriate scope and preserves session views")

    @covers_requirement(
        "webclient-map-drawer::map-requests-follow-explicit-scope-and-committed-moves-only-while-open"
    )
    def test_requests_on_open_tab_and_committed_moves(self):
        # Exactly one map.view {scope} on open and on each tab switch; one
        # refresh after a committed move once its presentation commits;
        # nothing for input, a rejected or earlier move or a closed drawer;
        # the pending slot waits for the lock and drops on close/disconnect.
        self.assert_block_passed("map requests follow explicit scope and committed moves only while open")

    @covers_requirement(
        "webclient-map-drawer::floating-map-chrome-avoids-selected-details"
    )
    def test_floating_chrome_and_text_mirrors(self):
        # Pill, commission list and scale bar float over the full map; the
        # 360 px card opens only on selection with the pill left of it;
        # every commission is mirrored as text and a pointer shows its
        # commission when activated.
        self.assert_block_passed("floating map chrome avoids selected details")

    @covers_requirement(
        "webclient-map-drawer::map-keyboard-and-pointer-interaction-remains-modal-and-accessible"
    )
    def test_modal_keys_escape_order_and_exact_move(self):
        # Escape closes the legend, then the selection, then the map; the
        # map keys drive the view and never reach the document behind the
        # modal; 前往 forwards the exact descriptor with the drawn current
        # node, and waits while a request is unsettled.
        self.assert_block_passed("map keyboard and pointer interaction remains modal and accessible")

    @covers_requirement(
        "webclient-map-drawer::the-old-full-map-lattice-has-no-remaining-consumer"
    )
    def test_overlay_lattice_removed(self):
        # MapOverlay, map_view.js and use-map-view.js are gone, MapLattice
        # keeps only its island parameters, and the map surface renders the
        # real area/world views.
        self.assert_block_passed("the old full-map lattice has no remaining consumer")

    @covers_requirement(
        "webclient-map-drawer::area-view-memory-resets-on-coordinate-frame-changes"
    )
    def test_area_memory_resets_on_frame_change(self):
        # Memory keyed by map_id and frame key/unit; city to wilderness to
        # interior and settlement to settlement clear view and selection
        # synchronously; a republish of the same map keeps them; each new
        # frame opens on its current node in its own unit.
        self.assert_block_passed("area view memory resets on coordinate-frame changes")

    @covers_requirement(
        "webclient-map-drawer::the-drawer-current-marker-makes-one-truthful-position-claim"
    )
    def test_one_current_marker(self):
        # One concentric, inert current ring on the area map and one current
        # marker with no identity on the world map.
        self.assert_block_passed("the drawer current marker makes one truthful position claim")

    @covers_requirement(
        "webclient-map-drawer::every-map-surface-draws-a-shared-map-concept-from-its-one-glyph-source"
    )
    def test_shared_glyph_sources(self):
        # The island and the area map draw identical node glyphs up to each
        # surface's uniform group scale; wilderness cells draw the shared
        # seal, arch and commission diamond at the cell scale; the legend's
        # road and commission samples and both hatch instances come from the
        # one source; world glyphs scale with the UI; a static guard keeps
        # every shared concept's geometry in its single file.
        self.assert_block_passed("every map surface draws a shared map concept from its one glyph source")

    @covers_requirement(
        "webclient-map-drawer::map-legend-samples-are-drawn-by-the-map-they-explain"
    )
    def test_legend_samples_drawn_by_their_map(self):
        # SVG-only samples from the maps' own definitions (no CSS-drawn
        # approximation), the area gate arch and the world spire and pin
        # identical to the maps', the r 14 approximate ring, and sample
        # boxes of 32 units times the UI scale.
        self.assert_block_passed("map legend samples are drawn by the map they explain")


class MapEdgePointerContracts(VitestContractMixin, unittest.TestCase):
    """Runs ``map_edge_pointers.test.js`` once."""

    SUITE = POINTER_SUITE
    SUITE_NAME = "map edge pointers"

    @covers_requirement(
        "webclient-map-drawer::floating-map-chrome-avoids-selected-details"
    )
    def test_pointer_layout(self):
        # On-screen commissions draw nothing; pointers sit where the ray
        # leaves the drawer-aware rectangle, nearest first, at most three
        # plus ＋n, a pitch apart and whole inside their side, as named
        # buttons.
        self.assert_block_passed("floating map chrome avoids selected details")
