"""Continent geography tools of the map editor in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``) against a fresh synthetic workspace and
drives the built page with real pointer and keyboard input. Assertions read
the source files on disk and the service's workspace state: which document
changed, how many commands were posted, and what the core derived. Shipped
copy is never asserted.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[3]
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
REFERENCE = (1451, 790)
LARGE = (2560, 1440)


def _load(name: str):
    import importlib.util
    import sys

    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harness = _load("process_harness")
synthetic = _load("synthetic_workspace")

CONTINENT = "content/maps/continent.yaml"
LOCATIONS = "content/maps/locations.yaml"
DISTRICTS = "content/maps/districts.yaml"
SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
PARTITION = "world/maps/data/district_partition.json"
RIVER = "continent:waterway:synthetic_river"


class MapEditorGeographyBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-geography-browser-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.workspace = synthetic.write_workspace(root / "workspace")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self.addCleanup(self._close)
        self.posts: list[str] = []

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def start(self, prepare=None) -> None:
        if prepare:
            prepare(self.workspace)
        self.editor = harness.EditorProcess(self.workspace, frontend_dist=harness.FRONTEND_DIST)
        self.editor.__enter__()
        self.addCleanup(self.editor.__exit__, None, None, None)
        self.baseline = synthetic.tree_digest(self.workspace)

    def sign_partition(self, workspace: Path) -> None:
        """A metadata-only partition artifact signed for the synthetic inputs."""

        code = (
            "import sys, json\n"
            "from pathlib import Path\n"
            "from elosern_map_core import load_authoring_world, make_source_document\n"
            "root = Path(sys.argv[1])\n"
            "paths = json.loads(sys.argv[2])\n"
            "world = load_authoring_world(make_source_document(p, (root / p).read_text(encoding='utf-8')) for p in paths)\n"
            "print(world.partition_signature)\n"
        )
        import subprocess

        result = subprocess.run(
            [str(harness.editor_python()), "-I", "-c", code, str(workspace), json.dumps(list(synthetic.DOCUMENTS))],
            capture_output=True, text=True, check=True, env=harness.scrubbed_env(), cwd=harness.PROJECT,
        )
        target = workspace / PARTITION
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"version": 2, "algorithm_version": 1, "source_signature": result.stdout.strip(),
                        "fingerprint": "synthetic"}),
            encoding="utf-8",
        )

    def open(self, viewport=REFERENCE):
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        self.page = page
        return page

    def wait_for(self, predicate, message: str) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            self.page.wait_for_timeout(50)
        self.fail(message)

    def settle(self, page) -> None:
        page.wait_for_function("() => !document.querySelector('[data-chip=\"save\"].chip--busy')", timeout=15000)

    def names(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.posts]

    def changed(self) -> set[str]:
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(now) | set(self.baseline) if now.get(path) != self.baseline.get(path)}

    def data(self, document: str):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    def route(self):
        return self.data(CONTINENT)["terrain"]["waterways"]["synthetic_river"]["route"]

    # -- tests -----------------------------------------------------------
    def test_a_river_point_drag_is_one_continent_command_that_stales_the_partition(self):
        self.start(self.sign_partition)
        page = self.open()
        self.assertEqual(self.editor.workspace_state()["partition_status"]["status"], "current")
        self.assertEqual(page.locator('[data-chip="partition"]').get_attribute("data-chip-state"), "current")
        preview = self.editor.workspace_state()["world"]["continent"]["terrain_preview"]["samples"]
        # Selecting the feature reveals its control-point diamonds.
        page.click(f'[data-object="{RIVER}"]')
        handle = page.locator(f'[data-qualified-ref="{RIVER}#0"][data-kind="handle"]')
        handle.wait_for()
        box = handle.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x, y - 60 * step / 5)
        page.mouse.up()
        self.wait_for(lambda: self.route()[0] != {"cell_x": 20, "cell_y": 20}, "the release did not save the point")
        self.settle(page)
        self.assertEqual(self.names(), ["move_control_point"])
        self.assertEqual(self.changed(), {CONTINENT})
        moved = self.route()[0]
        self.assertGreater(moved["cell_y"], 20)
        state = self.editor.workspace_state()
        self.assertEqual(state["partition_status"]["status"], "stale")
        self.assertNotEqual(state["world"]["continent"]["terrain_preview"]["samples"], preview)
        self.wait_for(
            lambda: page.locator('[data-chip="partition"]').get_attribute("data-chip-state") == "stale",
            "the partition chip did not turn stale",
        )
        # The point inspector labels its frame; a typed value is a second command.
        self.assertEqual(self.page.locator("[data-inspector-ref]").inner_text(), f"{RIVER}#0")
        field = page.locator('[data-field-input="point-0"]')
        field.fill("18")
        field.press("Enter")
        self.wait_for(lambda: self.route()[0]["cell_x"] == 18, "the numeric entry was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_control_point", "move_control_point"])
        self.assertEqual(self.changed(), {CONTINENT})
        self.assertEqual(sorted(json.loads((self.workspace / PARTITION).read_text())), sorted(
            ["version", "algorithm_version", "source_signature", "fingerprint"]))

    def test_an_incomplete_number_writes_nothing_and_escape_restores_it(self):
        self.start()
        page = self.open()
        page.click(f'[data-object="{RIVER}"]')
        page.click(f'[data-object="{RIVER}#1"]')
        field = page.locator('[data-field-input="point-1"]')
        saved = field.input_value()
        field.fill("2o")
        field.press("Enter")
        self.assertEqual(field.get_attribute("aria-invalid"), "true")
        self.assertEqual(page.locator('[data-field-error="point-1"]').count(), 1)
        field.press("Escape")
        self.assertEqual(field.input_value(), saved)
        self.assertEqual(self.posts, [])
        self.assertEqual(self.changed(), set())

    def test_a_new_location_without_a_local_map_is_searchable_and_fabricates_nothing(self):
        self.start()
        page = self.open()
        page.click('[data-tool="location"]')
        canvas = page.locator('[data-region="canvas"]').bounding_box()
        page.mouse.click(canvas["x"] + canvas["width"] * 0.7, canvas["y"] + canvas["height"] * 0.5)
        page.locator('[data-creation="location"]').wait_for()
        page.fill('[data-creation-field="id"]', "synthetic_ruin")
        page.fill('[data-creation-field="display_name_zh"]', "新廢墟")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: "synthetic_ruin" in self.data(LOCATIONS)["locations"], "the location was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_location"])
        self.assertEqual(self.changed(), {LOCATIONS})
        state = self.editor.workspace_state()
        location = next(row for row in state["world"]["locations"] if row["id"] == "synthetic_ruin")
        self.assertEqual(location["local_maps"], [])
        self.assertEqual({row["id"] for row in state["world"]["settlements"]}, {synthetic.SETTLEMENT_ID})
        # Selected after creation: the inspector states the absent local map.
        self.wait_for(lambda: page.locator('[data-local-map="absent"]').count() == 1, "absence was not stated")
        self.assertEqual(page.locator("[data-open-local-map]").count(), 0)
        page.keyboard.press("Escape")
        page.keyboard.press("Escape")
        page.fill("[data-search]", "新廢墟")
        self.assertEqual(page.locator('[data-search-result="location:synthetic_ruin"]').count(), 1)
        # Editing a field is one more locations-only command.
        page.click('[data-search-result="location:synthetic_ruin"]')
        page.fill('[data-field-input="location-name"]', "古廢墟")
        page.press('[data-field-input="location-name"]', "Enter")
        self.wait_for(
            lambda: self.data(LOCATIONS)["locations"]["synthetic_ruin"]["display_name_zh"] == "古廢墟",
            "the name was not saved",
        )
        self.assertEqual(self.changed(), {LOCATIONS})

    def test_a_location_with_a_local_map_opens_it_and_refuses_deletion(self):
        self.start()
        page = self.open()
        page.click(f'[data-object="location:{synthetic.LOCATION_ID}"]')
        page.click('[data-action="delete"]')
        self.assertEqual(page.locator('[data-delete-refusal]').count(), 1)
        self.assertEqual(self.posts, [])
        page.click(f'[data-open-local-map="{synthetic.SETTLEMENT_ID}"]')
        self.wait_for(
            lambda: page.locator('[data-domain-tab="settlement"]').get_attribute("aria-pressed") == "true",
            "the local map did not open",
        )
        self.assertEqual(self.changed(), set())

    def test_footprint_cells_and_a_district_landmark_by_keyboard_write_only_their_owner(self):
        self.start()
        page = self.open()
        # The footprint layer starts hidden; showing it is a view preference.
        page.click('[data-layer="footprint"]')
        page.click(f'[data-object="footprint:{synthetic.SETTLEMENT_ID}"]')
        origin = page.locator('[data-footprint-cell="5,5"]')
        origin.wait_for()
        origin.focus()
        page.keyboard.press("ArrowRight")
        page.keyboard.press("Space")
        self.wait_for(
            lambda: self.data(SETTLEMENT)["wilderness_entry"]["shape"] == ["##"], "the footprint toggle was not saved"
        )
        self.settle(page)
        self.assertEqual(self.names(), ["set_footprint_cell"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        footprint = self.editor.workspace_state()["world"]["settlements"][0]["footprint"]
        self.assertEqual(footprint["cells"], [[5, 5], [6, 5]])

        self.baseline = synthetic.tree_digest(self.workspace)
        page.click('[data-object="district:synthetic_district"]')
        page.select_option('[data-landmark-field="domain"]', "wilderness_cell")
        page.fill('[data-landmark-field="x"]', "20")
        page.fill('[data-landmark-field="y"]', "20")
        page.press('[data-landmark-field="y"]', "Enter")
        self.wait_for(
            lambda: self.data(DISTRICTS)["districts"]["synthetic_district"]["landmark"]["domain"] == "wilderness_cell",
            "the landmark was not saved",
        )
        self.settle(page)
        self.assertEqual(self.changed(), {DISTRICTS})
        self.assertEqual(self.names()[-1], "set_district_field")
        # Saved as work in progress: the water cell is diagnosed, still visible.
        codes = {item["code"] for item in self.editor.workspace_state()["diagnostics"]}
        self.assertIn("unreachable_landmark", codes)
        page.click("[data-diagnostics-toggle]")
        self.assertGreaterEqual(page.locator('[data-diagnostic="unreachable_landmark"]').count(), 1)

    def test_clicking_a_feature_shape_selects_it_and_shows_its_handles(self):
        self.start()
        page = self.open()
        river = page.locator(f'[data-shape-ref="{RIVER}"]')
        box = river.bounding_box()
        # A quarter along the straight synthetic river, away from its ford.
        page.mouse.click(box["x"] + box["width"] * 0.25, box["y"] + box["height"] / 2)
        self.wait_for(
            lambda: page.locator("[data-inspector-ref]").count() == 1
            and page.locator("[data-inspector-ref]").inner_text() == RIVER,
            "a click on the river shape did not select it",
        )
        self.assertEqual(page.locator('[data-kind="handle"]').count(), 2)
        self.assertEqual(self.posts, [])

    def test_derived_borders_have_no_handles_at_the_large_viewport(self):
        self.start()
        page = self.open(LARGE)
        self.assertGreaterEqual(page.locator('[data-derived="true"]').count(), 1)
        self.assertEqual(page.locator('[data-derived="true"][data-shape-ref]').count(), 0)
        self.assertEqual(page.locator("[data-terrain-preview]").count(), 1)
        page.click('[data-object="continent:ridge"]')
        page.fill('[data-field-input="ridge-base_x"]', "14")
        page.press('[data-field-input="ridge-base_x"]', "Enter")
        self.wait_for(lambda: self.data(CONTINENT)["terrain"]["ridge"]["base_x"] == 14, "the ridge parameter was not saved")
        self.assertEqual(self.changed(), {CONTINENT})
        self.assertEqual(self.names(), ["set_terrain_parameter"])
