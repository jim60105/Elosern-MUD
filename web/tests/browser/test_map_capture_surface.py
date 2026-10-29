"""The offline map capture surface in a real browser, from the filesystem.

The page under test is `tools/map-editor/frontend/capture-dist/index.html`,
opened as a `file://` document: no editor service, no dev server, no Node
runtime and no network. Every payload is a synthetic workspace's projection
built by the real editor service in this process, then handed to the page as
an in-memory object through `window.renderMapCapture`.

The assertions are about painted geometry, visibility and the readiness
signal — synthetic values and measured positions, never shipped names, literal
SVG or counts from repository map content.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = REPO_ROOT / "tools" / "map-editor" / "frontend"
CAPTURE_DIST = FRONTEND / "capture-dist"
SETTLEMENT_LAYERS = ["nodes", "roads", "labels"]
INTERIOR_LAYERS = ["rooms", "connections", "exterior", "labels"]
CONTINENT_LAYERS = ["terrain", "water", "ridge", "locations", "footprint", "partition", "labels"]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools/map-editor/tests" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load("process_harness")
synthetic = _load("synthetic_workspace")

# Everything a caller judges an image by: painted extents, visibility and
# readiness, measured in the stage's own pixel frame.
PROBE = """() => {
  const stage = document.querySelector('[data-capture-stage]');
  const svg = stage && stage.querySelector('svg');
  const origin = stage ? stage.getBoundingClientRect() : { left: 0, top: 0 };
  const box = (element) => {
    const rect = element.getBoundingClientRect();
    return {
      left: rect.left - origin.left,
      top: rect.top - origin.top,
      right: rect.right - origin.left,
      bottom: rect.bottom - origin.top,
    };
  };
  const all = (selector) => (svg ? [...svg.querySelectorAll(selector)] : []);
  return {
    marks: all('.map-mark').length,
    shapes: all('.map-shape').length,
    links: all('.map-link').length,
    chevrons: all('[data-direction-chevron]').length,
    raster: all('[data-terrain-preview]').length,
    background: all('[data-background]').length,
    texts: all('text').map((node) => ({ text: node.textContent, ...box(node) })),
    cards: all('.map-mark__card').map(box),
    markKinds: all('.map-mark').map((node) => node.dataset.kind),
    drawables: [
      ...all('.map-shape').map((node) => `shape:${node.dataset.shape}`),
      ...all('.map-mark').map((node) => `mark:${node.dataset.qualifiedRef}`),
      ...(svg && svg.querySelector('[data-terrain-preview]') ? ['raster'] : []),
    ],
    locationTransforms: all('.map-mark[data-kind="location"]').map((node) => node.getAttribute('transform')),
    stage: stage ? box(stage) : null,
    chrome: document.querySelectorAll(
      '.map-pill, .editor__header, .editor__inspector, .editor__nav, [data-diagnostics-list], button, a'
    ).length,
    fonts: document.fonts ? document.fonts.status : 'missing',
  };
}"""

RENDER = """async (payload) => {
  const fontsBefore = document.fonts.status;
  const value = await window.renderMapCapture(payload);
  return {
    value,
    fontsBefore,
    fontsAfter: document.fonts.status,
    status: window.__mapCaptureState.status,
    error: window.__mapCaptureState.error,
  };
}"""


class MapCaptureSurfaceBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (CAPTURE_DIST / "index.html").is_file():
            raise RuntimeError(
                "the capture page is not built: pnpm --dir tools/map-editor/frontend run build:capture"
            )
        cls.root = Path(tempfile.mkdtemp(prefix="map-capture-browser-"))
        cls.workspace = synthetic.write_workspace(cls.root / "workspace")
        # The projection is read once by this process; the page itself never
        # talks to the service.
        cls.editor = harness.EditorProcess(cls.workspace, frontend_dist=cls.root / "no-frontend-build")
        cls.editor.__enter__()
        cls.world = cls.editor.workspace_state()["world"]

    @classmethod
    def tearDownClass(cls) -> None:
        cls.editor.__exit__(None, None, None)
        shutil.rmtree(cls.root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self.addCleanup(self._close)
        self.requests: list[str] = []
        self.blocked: list[str] = []

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def open(self, page_dir: Path | None = None, viewport: tuple[int, int] = (1280, 960), ready: bool = True):
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()

        def block(route):
            self.blocked.append(route.request.url)
            route.abort()

        context.route("http://**", block)
        context.route("https://**", block)
        page.on("request", lambda request: self.requests.append(request.url))
        page.goto((page_dir or CAPTURE_DIST).as_uri() + "/index.html")
        if ready:
            page.wait_for_function("() => window.__mapCaptureState !== undefined", timeout=15000)
        return page

    def reload(self, page) -> None:
        page.reload()
        page.wait_for_function("() => window.__mapCaptureState !== undefined", timeout=15000)

    def payload(self, view: str, map_id=None, **overrides):
        request = {
            "world": self.world,
            "partition": None,
            "view": view,
            "map_id": map_id,
            "width": 1280,
            "height": 960,
            "bounds": None,
            "hidden_layers": [],
        }
        request.update(overrides)
        return request

    def render(self, page, request):
        return page.evaluate(RENDER, request)

    def probe(self, page):
        return page.evaluate(PROBE)

    def assert_only_file_requests(self):
        self.assertEqual(self.blocked, [])
        self.assertTrue(self.requests)
        foreign = [url for url in self.requests if not url.startswith("file:")]
        self.assertEqual(foreign, [], "a local-file page must load nothing over the network")
        self.assertTrue([url for url in self.requests if url.endswith(".woff2")], "local font faces load")
        self.assertTrue([url for url in self.requests if url.endswith(".css")], "the local stylesheet loads")

    def assert_contained(self, probe, size=(1280, 960), tolerance=0.5):
        painted = list(probe["texts"]) + list(probe["cards"])
        self.assertTrue(painted, "the render painted no labels or cards")
        for item in painted:
            self.assertGreaterEqual(item["left"], -tolerance, item)
            self.assertGreaterEqual(item["top"], -tolerance, item)
            self.assertLessEqual(item["right"], size[0] + tolerance, item)
            self.assertLessEqual(item["bottom"], size[1] + tolerance, item)

    def continent_mark_count(self) -> int:
        continent = self.world["continent"]
        preview = continent.get("terrain_preview") or {}
        current = preview.get("status") == "current"
        return (
            len(self.world["locations"])
            + len(continent.get("harbor_sites") or [])
            + sum(len(waterway.get("fords_m") or []) for waterway in continent["waterways"])
            + (len(preview.get("passes") or []) if current else 0)
        )

    # -- one page, one selected view, no service ------------------------------

    def test_each_view_renders_from_a_file_page_with_network_denied(self):
        expected_marks = {
            "continent": self.continent_mark_count(),
            "settlement": len(self.world["settlements"][0]["nodes"]),
            "interior": len(self.world["interiors"][0]["rooms"]) + 1,
        }
        for view, map_id in (
            ("continent", None),
            ("settlement", synthetic.SETTLEMENT_ID),
            ("interior", synthetic.INTERIOR_ID),
        ):
            page = self.open()
            outcome = self.render(page, self.payload(view, map_id))
            self.assertEqual(outcome["status"], "ready", outcome)
            self.assertIsNone(outcome["error"])
            self.assertEqual(set(outcome["value"]), {"bounds", "units", "axes"})
            self.assertEqual(outcome["fontsAfter"], "loaded")
            probe = self.probe(page)
            self.assertEqual(probe["marks"], expected_marks[view], view)
            self.assertEqual(probe["stage"], {"left": 0, "top": 0, "right": 1280, "bottom": 960})
            # Map only: no header, navigation, inspector, controls or status.
            self.assertEqual(probe["chrome"], 0)
            self.assertTrue(probe["texts"], "labels are painted")
            self.assert_contained(probe)
            self.assert_only_file_requests()
            page.context.close()

    def test_the_continent_camera_converts_kilometres_and_keeps_one_scale(self):
        page = self.open()
        outcome = self.render(page, self.payload("continent", width=200, height=100, bounds=[0, 0, 10, 20]))
        self.assertEqual(outcome["status"], "ready", outcome)
        self.assertEqual(outcome["value"]["bounds"], [-15, 0, 25, 20])
        self.assertEqual(outcome["value"]["units"], "km")
        self.assertEqual(outcome["value"]["axes"], {"x": "east", "y": "north"})
        probe = self.probe(page)
        self.assertEqual(probe["stage"]["right"], 200)
        # Each location is one point in the requested frame: kilometre east and
        # north from the payload, projected into [-15,25] x [0,20] at 200x100.
        fake = [(0.0, 0.0)] * len(self.world["locations"])
        for index, location in enumerate(self.world["locations"]):
            east_km = location["centre_m"][0] / 1000
            north_km = location["centre_m"][1] / 1000
            fake[index] = ((east_km + 15) / 40 * 200, (20 - north_km) / 20 * 100)
        rendered = [
            tuple(float(value) for value in re.findall(r"-?[\d.]+", transform))
            for transform in probe["locationTransforms"]
        ]
        self.assertEqual(len(rendered), len(fake))
        for index, (east_px, north_px) in enumerate(fake):
            self.assertAlmostEqual(rendered[index][0], east_px, delta=0.15, msg=f"location {index} east")
            self.assertAlmostEqual(rendered[index][1], north_px, delta=0.15, msg=f"location {index} north")
        page.context.close()

    def test_the_interior_camera_reports_down_positive_layout_units(self):
        page = self.open()
        outcome = self.render(
            page, self.payload("interior", synthetic.INTERIOR_ID, width=100, height=100, bounds=[1, 2, 5, 8])
        )
        self.assertEqual(outcome["status"], "ready", outcome)
        self.assertEqual(outcome["value"]["bounds"], [0, 2, 6, 8])
        self.assertEqual(outcome["value"]["units"], "layout")
        self.assertEqual(outcome["value"]["axes"], {"x": "right", "y": "down"})
        # A requested region clips at the image edge; nothing is recentred to
        # make the map content fit.
        probe = self.probe(page)
        self.assertEqual(probe["stage"]["right"], 100)
        self.assertTrue(probe["texts"], "the selected extent still paints its content")
        page.context.close()

    def test_a_full_fit_keeps_cards_and_measured_labels_inside_the_image(self):
        for view, map_id in (
            ("continent", None),
            ("settlement", synthetic.SETTLEMENT_ID),
            ("interior", synthetic.INTERIOR_ID),
        ):
            page = self.open()
            outcome = self.render(page, self.payload(view, map_id))
            self.assertEqual(outcome["status"], "ready", outcome)
            self.assert_contained(self.probe(page))
            page.context.close()

    def test_a_small_output_still_draws_the_requested_map(self):
        page = self.open(viewport=(320, 320))
        outcome = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID, width=200, height=200))
        self.assertEqual(outcome["status"], "ready", outcome)
        probe = self.probe(page)
        self.assertEqual(probe["marks"], len(self.world["settlements"][0]["nodes"]))
        self.assertEqual(probe["links"], len(self.world["settlements"][0]["roads"]))
        page.context.close()

    def test_faces_introduced_by_a_later_capture_still_settle_before_readiness(self):
        page = self.open()
        first = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID))
        self.assertEqual(first["status"], "ready", first)
        before = len([url for url in self.requests if url.endswith(".woff2")])
        second = self.render(page, self.payload("interior", synthetic.INTERIOR_ID))
        self.assertEqual(second["status"], "ready", second)
        after = len([url for url in self.requests if url.endswith(".woff2")])
        self.assertGreater(after, before, "the second capture needed a face the first did not")
        self.assertEqual(second["fontsAfter"], "loaded")
        texts = self.probe(page)["texts"]
        self.assertTrue(texts, "the second capture paints labels")
        self.assertTrue(all(item["right"] - item["left"] > 0 for item in texts), "measured ink, not fallback tofu")
        page.context.close()

    def test_an_automatic_fit_that_cannot_hold_the_surface_is_refused(self):
        # The interior cards are 200 px wide; an automatic fit into 80x80
        # pixels cannot contain them, so the request must not resolve.
        page = self.open(viewport=(320, 320))
        with self.assertRaises(Exception) as raised:
            self.render(page, self.payload("interior", synthetic.INTERIOR_ID, width=80, height=80))
        self.assertIn("does not fit", str(raised.exception))
        self.assertEqual(page.evaluate("() => window.__mapCaptureState.status"), "error")
        page.context.close()

    # -- layer ownership ------------------------------------------------------

    def test_hidden_geometry_takes_only_its_own_labels(self):
        page = self.open()
        everything = self.render(page, self.payload("continent"))
        self.assertEqual(everything["status"], "ready")
        full = self.probe(page)
        self.reload(page)
        reduced_render = self.render(page, self.payload("continent", hidden_layers=["locations"]))
        self.assertEqual(reduced_render["status"], "ready")
        reduced = self.probe(page)
        self.assertNotIn("location", reduced["markKinds"])
        self.assertNotIn("site", reduced["markKinds"])
        self.assertEqual(reduced["shapes"], full["shapes"], "other geometry stays painted")
        self.assertGreater(reduced["shapes"], 0)
        names = {location["display_name_zh"] for location in self.world["locations"]}
        self.assertFalse({label["text"] for label in reduced["texts"]} & names)
        self.assertLess(len(reduced["texts"]), len(full["texts"]))
        page.context.close()

    def test_every_continent_layer_hides_exactly_its_own_geometry(self):
        # A footprint cell and a district outline make the two layers that the
        # synthetic workspace's own sources do not carry; both arrive as
        # payload data, exactly as the capture request defines them.
        world = json.loads(json.dumps(self.world))
        world["settlements"][0]["footprint"] = {"cells": [[3, 3]]}
        partition = {"outlines": {"synthetic_district": [[0, 0, 10000, 0, 10000, 10000, 0, 10000]]}}
        page = self.open()
        baseline_render = self.render(page, {**self.payload("continent"), "world": world, "partition": partition})
        self.assertEqual(baseline_render["status"], "ready")
        baseline = self.probe(page)
        everything = set(baseline["drawables"])
        self.assertTrue(everything, "the baseline paints drawables")
        removed: dict[str, set[str]] = {}
        for layer in CONTINENT_LAYERS[:-1]:
            self.reload(page)
            outcome = self.render(
                page, {**self.payload("continent", hidden_layers=[layer]), "world": world, "partition": partition}
            )
            self.assertEqual(outcome["status"], "ready", layer)
            self.assertEqual(outcome["value"], baseline_render["value"], f"{layer}: the camera must not move")
            probe = self.probe(page)
            removed[layer] = everything - set(probe["drawables"])
            self.assertTrue(removed[layer], f"{layer} owns no drawable")
            self.assertEqual(probe["raster"], 0 if layer == "terrain" else 1, layer)
        # Every drawable belongs to exactly one layer, and every layer draws.
        seen: set[str] = set()
        for layer, items in removed.items():
            self.assertFalse(seen & items, f"{layer} overlaps another layer: {sorted(seen & items)}")
            seen |= items
        self.assertEqual(seen, everything, "the layer classification covers every drawable")
        page.context.close()

    def test_hiding_labels_keeps_cards_glyphs_and_direction_indicators(self):
        page = self.open()
        full_render = self.render(page, self.payload("interior", synthetic.INTERIOR_ID))
        self.assertEqual(full_render["status"], "ready")
        full = self.probe(page)
        self.assertGreater(full["chevrons"], 0, "curved connections carry a direction chevron")
        self.assertGreater(len(full["cards"]), 0, "rooms paint cards")
        self.reload(page)
        hidden_render = self.render(page, self.payload("interior", synthetic.INTERIOR_ID, hidden_layers=["labels"]))
        self.assertEqual(hidden_render["status"], "ready")
        probe = self.probe(page)
        self.assertEqual(probe["texts"], [])
        self.assertEqual(probe["marks"], full["marks"])
        self.assertEqual(len(probe["cards"]), len(full["cards"]))
        self.assertEqual(probe["chevrons"], full["chevrons"])
        page.context.close()

    def test_settlement_nodes_and_roads_are_independent(self):
        page = self.open()
        roads_hidden = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID, hidden_layers=["roads"]))
        self.assertEqual(roads_hidden["status"], "ready")
        probe = self.probe(page)
        self.assertEqual(probe["marks"], len(self.world["settlements"][0]["nodes"]))
        self.assertEqual(probe["links"], 0)
        self.reload(page)
        nodes_hidden = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID, hidden_layers=["nodes"]))
        self.assertEqual(nodes_hidden["status"], "ready")
        probe = self.probe(page)
        self.assertEqual(probe["marks"], 0)
        self.assertEqual(probe["links"], len(self.world["settlements"][0]["roads"]))
        page.context.close()

    def test_everything_hidden_leaves_the_background_at_the_same_camera(self):
        for view, map_id, layers, background in (
            ("continent", None, CONTINENT_LAYERS, 1),
            ("settlement", synthetic.SETTLEMENT_ID, SETTLEMENT_LAYERS, 1),
            ("interior", synthetic.INTERIOR_ID, INTERIOR_LAYERS, 0),
        ):
            page = self.open()
            visible = self.render(page, self.payload(view, map_id))
            self.assertEqual(visible["status"], "ready")
            self.reload(page)
            hidden = self.render(page, self.payload(view, map_id, hidden_layers=layers))
            self.assertEqual(hidden["status"], "ready")
            self.assertEqual(hidden["value"], visible["value"], f"{view}: the camera must not move")
            probe = self.probe(page)
            self.assertEqual(
                (probe["marks"], probe["shapes"], probe["links"], probe["texts"], probe["raster"]),
                (0, 0, 0, [], 0),
                view,
            )
            self.assertEqual(probe["background"], background, f"{view}: the normal background remains")
            page.context.close()

    # -- inert content, readiness and rejection -------------------------------

    def test_authored_text_and_url_like_names_stay_inert(self):
        world = json.loads(json.dumps(self.world))
        world["locations"][0]["display_name_zh"] = synthetic.HOSTILE_DESC
        world["locations"][1]["display_name_zh"] = synthetic.URL_LIKE_SCENE
        page = self.open()
        outcome = self.render(page, {**self.payload("continent"), "world": world})
        self.assertEqual(outcome["status"], "ready", outcome)
        labels = {label["text"] for label in self.probe(page)["texts"]}
        self.assertIn(synthetic.HOSTILE_DESC, labels)
        self.assertIn(synthetic.URL_LIKE_SCENE, labels)
        self.assertIsNone(page.evaluate("window.__mapCapturePwned"))
        self.assertEqual(page.locator("img").count(), 0)
        self.assertFalse([url for url in self.blocked + self.requests if "example.invalid" in url])
        self.assert_only_file_requests()
        page.context.close()

    def test_readiness_waits_for_fonts_and_layout(self):
        page = self.open()
        self.assertFalse(
            [url for url in self.requests if url.endswith(".woff2")],
            "with no text on the page, no local face has been fetched yet",
        )
        outcome = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID))
        self.assertTrue(
            [url for url in self.requests if url.endswith(".woff2")],
            "the render fetches the faces its labels need",
        )
        self.assertEqual(outcome["fontsAfter"], "loaded")
        self.assertEqual(outcome["status"], "ready")
        texts = self.probe(page)["texts"]
        self.assertGreater(len(texts), 0, "labels are laid out when the promise resolves")
        self.assertTrue(all(item["right"] - item["left"] > 0 for item in texts), "every label has measured ink")
        page.context.close()

    def test_malformed_requests_reject_without_a_partial_render(self):
        page = self.open()
        cases = [
            {"view": "village"},
            {"view": "settlement", "map_id": None},
            {"view": "settlement", "map_id": "no_such_map"},
            {"width": 0},
            {"height": -4},
            {"bounds": [0, 0, -1, 2]},
            {"hidden_layers": "labels"},
        ]
        for override in cases:
            request = self.payload("settlement", synthetic.SETTLEMENT_ID)
            request.update(override)
            with self.assertRaises(Exception, msg=str(override)):
                page.evaluate("async (payload) => window.renderMapCapture(payload)", request)
            state = page.evaluate("() => window.__mapCaptureState")
            self.assertEqual(state["status"], "error", override)
            self.assertTrue(state["error"], override)
        self.assertEqual(self.probe(page)["marks"], 0, "a rejected request paints no map")
        page.context.close()

    def test_a_delayed_local_font_holds_readiness_until_it_arrives(self):
        delay = 0.5
        served: list[str] = []

        def slow(route):
            time.sleep(delay)
            body = Path(urlparse(route.request.url).path).read_bytes()
            served.append(route.request.url)
            route.fulfill(status=200, body=body, content_type="font/woff2")

        page = self.open()
        page.context.route("**/*.woff2", slow)
        started = time.monotonic()
        outcome = self.render(page, self.payload("settlement", synthetic.SETTLEMENT_ID))
        elapsed = time.monotonic() - started
        self.assertTrue(served, "the render fetched its local faces through the delayed route")
        self.assertEqual(outcome["status"], "ready")
        self.assertGreaterEqual(elapsed, delay, "readiness waited for the delayed face instead of resolving early")
        self.assertTrue(self.probe(page)["texts"], "the labels are laid out once the face arrives")
        page.context.close()

    def test_a_page_whose_script_is_missing_never_reports_readiness(self):
        broken = self.root / "broken-capture"
        shutil.copytree(CAPTURE_DIST, broken, dirs_exist_ok=True)
        page_html = broken / "index.html"
        page_html.write_text(re.sub(r"<script[^>]*></script>", "", page_html.read_text(encoding="utf-8")), "utf-8")
        page = self.open(page_dir=broken, ready=False)
        self.assertTrue(page.evaluate("() => window.renderMapCapture === undefined"))
        self.assertTrue(page.evaluate("() => window.__mapCaptureState === undefined"))
        page.context.close()


class MapSurfaceEditorSmokeBrowserTest(unittest.TestCase):
    """The interactive host still behaves after the shared-surface extraction.

    Selection, pan, zoom and one editable-mark move are driven with real
    pointer input against the built editor page and its service; the moved
    position is read back from the service's workspace state, never from the
    page.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="map-surface-smoke-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")
        self.digest = synthetic.tree_digest(self.workspace)
        self.editor = harness.EditorProcess(self.workspace, frontend_dist=harness.FRONTEND_DIST)
        self.editor.__enter__()
        self.addCleanup(self.editor.__exit__, None, None, None)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self.addCleanup(self._close)
        self.posts: list[str] = []

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def open(self):
        context = self._browser.new_context(viewport={"width": 1451, "height": 790})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        page.click('[data-domain-tab="settlement"]')
        page.wait_for_selector('[data-kind="node"]')
        return page

    def changed(self) -> set[str]:
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(self.digest) | set(now) if self.digest.get(path) != now.get(path)}

    def wait_for(self, page, predicate, message: str) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            page.wait_for_timeout(50)
        self.fail(message)

    def node(self, name: str) -> str:
        return f"settlement_node:{synthetic.SETTLEMENT_ID}:{name}"

    def translate(self, page, ref: str) -> tuple[float, float]:
        transform = page.locator(f'[data-qualified-ref="{ref}"]').get_attribute("transform")
        values = [float(value) for value in re.findall(r"-?[\d.]+", transform)]
        return values[0], values[1]

    def blank_point(self, page) -> dict:
        point = page.evaluate(
            """() => {
              const host = document.querySelector('.map-canvas');
              const rect = host.getBoundingClientRect();
              for (let gy = 0.12; gy < 0.95; gy += 0.08) {
                for (let gx = 0.05; gx < 0.95; gx += 0.05) {
                  const x = rect.left + rect.width * gx;
                  const y = rect.top + rect.height * gy;
                  const hit = document.elementFromPoint(x, y);
                  if (hit && !hit.closest('.map-mark, .map-pill')) return { x, y };
                }
              }
              return null;
            }"""
        )
        self.assertIsNotNone(point, "the canvas has no pointer-free area")
        return point

    def test_selection_pan_zoom_and_one_mark_move_still_work(self):
        page = self.open()
        gate = self.node("gate")
        page.click(f'[data-qualified-ref="{gate}"]')
        self.assertEqual(page.locator('.map-mark[aria-pressed="true"]').count(), 1)
        self.assertEqual(page.locator(f'[data-qualified-ref="{gate}"]').get_attribute("aria-pressed"), "true")

        # Pan: a pointer drag on the surface moves the camera, never the world.
        before = self.translate(page, gate)
        point = self.blank_point(page)
        page.mouse.move(point["x"], point["y"])
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(point["x"] + 16 * step, point["y"] + 8 * step)
        page.mouse.up()
        after = self.translate(page, gate)
        self.assertAlmostEqual(after[0] - before[0], 80, delta=1.5, msg="the pan follows the pointer")
        self.assertAlmostEqual(after[1] - before[1], 40, delta=1.5)
        self.assertEqual(self.posts, [])
        self.assertEqual(self.changed(), set())

        # Zoom: a wheel step scales the whole surface by the shared span
        # factor about one anchor, so the distance between two marks scales
        # by exactly that factor and both agree on the same fixed point.
        yard_before = self.translate(page, self.node("yard"))
        page.mouse.move(point["x"], point["y"] + 200)
        page.mouse.wheel(0, -300)
        factor = 1.0018**-300  # WHEEL_ZOOM_BASE ** deltaY applied to the span
        zoomed_gate = self.translate(page, gate)
        zoomed_yard = self.translate(page, self.node("yard"))
        before_gap = math.hypot(yard_before[0] - after[0], yard_before[1] - after[1])
        zoomed_gap = math.hypot(zoomed_yard[0] - zoomed_gate[0], zoomed_yard[1] - zoomed_gate[1])
        self.assertAlmostEqual(zoomed_gap / before_gap, 1 / factor, delta=0.01, msg="one uniform zoom")
        anchors = [
            (zoomed_gate[axis] - after[axis] / factor) / (1 - 1 / factor) for axis in (0, 1)
        ]
        yard_anchors = [
            (zoomed_yard[axis] - yard_before[axis] / factor) / (1 - 1 / factor) for axis in (0, 1)
        ]
        for axis in (0, 1):
            self.assertAlmostEqual(anchors[axis], yard_anchors[axis], delta=2, msg="one zoom anchor")
        # The opposite wheel restores the same camera.
        page.mouse.wheel(0, 300)
        restored = self.translate(page, gate)
        self.assertAlmostEqual(restored[0], after[0], delta=1.5)
        self.assertAlmostEqual(restored[1], after[1], delta=1.5)

        # One editable-mark move: a node drag becomes exactly one command.
        yard = self.node("yard")
        page.click(f'[data-qualified-ref="{yard}"]')
        origin = page.locator(f'[data-qualified-ref="{yard}"]').bounding_box()
        x, y = origin["x"] + origin["width"] / 2, origin["y"] + origin["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x + 16 * step, y + 8 * step)
        page.mouse.up()
        self.wait_for(
            page,
            lambda: self.changed() == {f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"},
            "the drag release did not save the node",
        )
        self.assertEqual([url.rsplit("/", 1)[1] for url in self.posts], ["move_nodes"])
        state = self.editor.workspace_state()
        moved = next(node for node in state["world"]["settlements"][0]["nodes"] if node["id"] == "yard")
        self.assertNotEqual(moved["local_m"], [300, 400], "the saved position is the dragged one")
        page.context.close()

if __name__ == "__main__":
    unittest.main()
