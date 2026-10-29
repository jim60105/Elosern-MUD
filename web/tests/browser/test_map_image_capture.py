"""The capture command's browser boundary, in a real browser.

Two halves, both real:

- the built map-only page (§10) is opened from ``file://`` with every HTTP and
  HTTPS request aborted, and the exact payload the command builds — read by the
  real ``load_capture_snapshot`` — is rendered, screenshotted as the stage
  rectangle and checked for exact pixel size, readiness and map-only chrome;
- the command itself runs as a subprocess in the editor's locked capture
  environment against the same workspace, so publication, refusal and the
  untouched source bytes are observed from the outside.

No editor service, dev server or network is used by either half.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import struct
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
CAPTURE_DIST = REPO_ROOT / "tools" / "map-editor" / "frontend" / "capture-dist"
SCRIPT = REPO_ROOT / ".agents" / "skills" / "map-data-authoring" / "scripts" / "capture_map.py"
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
SETTLEMENT_ID = "synthetic_town"
INTERIOR_ID = "synthetic_hall"

RENDER = """async (payload) => {
  const value = await window.renderMapCapture(payload);
  return {
    value,
    fonts: document.fonts.status,
    status: window.__mapCaptureState.status,
    error: window.__mapCaptureState.error,
    stage: (() => {
      const rect = document.querySelector('[data-capture-stage]').getBoundingClientRect();
      return {width: rect.width, height: rect.height};
    })(),
    chrome: document.querySelectorAll(
      '.map-pill, .editor__header, .editor__inspector, .editor__nav, button, a'
    ).length,
    texts: document.querySelectorAll('[data-capture-stage] text').length,
  };
}"""


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


synthetic = _load("synthetic_workspace")


def command_helpers():
    """The capture command's own subprocess helpers from the top-level suite."""

    import tests.test_map_image_capture as helpers

    return helpers


def png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("the screenshot is not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


class MapImageCaptureBrowserTest(unittest.TestCase):
    """One map-only page, exact pixels, no chrome and no network."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (CAPTURE_DIST / "index.html").is_file():
            raise RuntimeError(
                "the capture page is not built: pnpm --dir tools/map-editor/frontend run build:capture"
            )
        cls.root = Path(tempfile.mkdtemp(prefix="map-image-capture-browser-"))
        cls.workspace = synthetic.write_workspace(cls.root / "workspace")
        cls.payload = cls._payload("settlement", SETTLEMENT_ID)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.root, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def _payload(cls, view: str, map_id: str | None) -> dict:
        helpers = command_helpers()
        code = (
            "import json\n"
            "from elosern_map_editor.capture_snapshot import load_capture_snapshot\n"
            f"snapshot = load_capture_snapshot({str(cls.workspace)!r}, view={view!r}, map_id={map_id!r})\n"
            "print(json.dumps(snapshot))\n"
        )
        result = subprocess.run(
            [str(helpers.capture_python()), "-I", "-c", code],
            cwd=cls.workspace,
            env=helpers.harness.scrubbed_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            raise RuntimeError(f"the snapshot probe failed:\n{result.stderr[-2000:]}")
        snapshot = json.loads(result.stdout)
        return {
            "world": snapshot["world"],
            "partition": snapshot["partition"],
            "view": view,
            "map_id": map_id,
            "width": 1280,
            "height": 960,
            "bounds": None,
            "hidden_layers": [],
        }

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

    def open(self, page_dir: Path | None = None, viewport=(1280, 960), ready=True):
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

    def assert_local_only(self) -> None:
        self.assertEqual(self.blocked, [], "the capture page must not reach for the network")
        self.assertTrue(self.requests)
        self.assertEqual([url for url in self.requests if not url.startswith("file:")], [])
        self.assertTrue([url for url in self.requests if url.endswith(".woff2")], "local faces load")
        self.assertTrue([url for url in self.requests if url.endswith(".css")], "the local stylesheet loads")

    # -- page contract -------------------------------------------------------

    def test_the_loader_payload_renders_map_only_at_the_exact_pixel_rectangle(self):
        page = self.open()
        payload = {**self.payload, "width": 320, "height": 240}

        outcome = page.evaluate(RENDER, payload)

        self.assertEqual(outcome["status"], "ready", outcome)
        self.assertEqual(outcome["fonts"], "loaded")
        self.assertEqual(set(outcome["value"]), {"bounds", "units", "axes"})
        self.assertEqual(outcome["value"]["units"], "m")
        self.assertEqual(outcome["value"]["axes"], {"x": "east", "y": "north"})
        self.assertEqual(outcome["stage"], {"width": 320, "height": 240})
        self.assertEqual(outcome["chrome"], 0, "no editor chrome belongs in the image")
        self.assertGreater(outcome["texts"], 0, "the map's labels are painted")
        shot = page.query_selector("[data-capture-stage]").screenshot(
            type="png", animations="disabled"
        )
        self.assertEqual(png_size(shot), (320, 240))
        self.assert_local_only()
        page.context.close()

    def test_a_viewport_other_than_the_document_default_still_captures_exactly(self):
        page = self.open(viewport=(900, 700))
        payload = {**self.payload, "width": 900, "height": 700}

        outcome = page.evaluate(RENDER, payload)
        shot = page.query_selector("[data-capture-stage]").screenshot(
            type="png", animations="disabled"
        )

        self.assertEqual(outcome["status"], "ready", outcome)
        self.assertEqual(png_size(shot), (900, 700))
        page.context.close()

    def test_readiness_waits_for_a_delayed_local_face(self):
        delay = 0.4
        served: list[str] = []

        def slow(route):
            time.sleep(delay)
            body = Path(urlparse(route.request.url).path).read_bytes()
            served.append(route.request.url)
            route.fulfill(status=200, body=body, content_type="font/woff2")

        page = self.open()
        page.context.route("**/*.woff2", slow)
        started = time.monotonic()
        outcome = page.evaluate(RENDER, self.payload)
        elapsed = time.monotonic() - started

        self.assertTrue(served, "the render fetched a local face through the delayed route")
        self.assertEqual(outcome["status"], "ready")
        # Recorded by the page immediately after the render promise settled, so
        # a dispatcher-side delay cannot disguise an early resolution.
        self.assertEqual(outcome["fonts"], "loaded")
        self.assertGreaterEqual(elapsed, delay, "readiness waited instead of resolving early")
        self.assertGreater(outcome["texts"], 0)
        page.context.close()

    def test_a_page_without_the_entry_script_never_reports_readiness(self):
        broken = self.root / "broken-capture"
        shutil.copytree(CAPTURE_DIST, broken, dirs_exist_ok=True)
        page_html = broken / "index.html"
        page_html.write_text(
            re.sub(r"<script[^>]*></script>", "", page_html.read_text(encoding="utf-8")),
            encoding="utf-8",
        )

        page = self.open(page_dir=broken, ready=False)

        self.assertTrue(page.evaluate("() => window.renderMapCapture === undefined"))
        self.assertTrue(page.evaluate("() => window.__mapCaptureState === undefined"))
        page.context.close()

    # -- the command itself --------------------------------------------------

    def captures(self) -> Path:
        path = self.root / "captures" / self.id().rsplit(".", 1)[-1]
        path.mkdir(parents=True, exist_ok=True)
        return path

    def run_command(self, *arguments: str):
        helpers = command_helpers()
        environment = helpers.harness.scrubbed_env()
        return subprocess.run(
            [str(helpers.capture_python()), "-I", str(SCRIPT), *arguments],
            cwd=self.workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_the_command_publishes_one_exact_image_and_leaves_the_sources_untouched(self):
        before = synthetic.tree_digest(self.workspace)
        destination = self.captures() / "synthetic-town.png"

        result = self.run_command(
            "--view", "settlement", "--map", SETTLEMENT_ID,
            "--width", "320", "--height", "240",
            "--format", "png", "--output", str(destination),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["image_path"], str(destination))
        self.assertEqual(png_size(destination.read_bytes()), (320, 240))
        self.assertEqual(synthetic.tree_digest(self.workspace), before)
        self.assertEqual([path.name for path in destination.parent.iterdir()], ["synthetic-town.png"])

    def test_a_refused_command_publishes_nothing_and_preserves_an_existing_image(self):
        before = synthetic.tree_digest(self.workspace)
        destination = self.captures() / "existing.png"
        previous = b"an image written by an earlier capture"
        destination.write_bytes(previous)

        result = self.run_command(
            "--view", "interior", "--map", INTERIOR_ID,
            "--width", "80", "--height", "80",
            "--format", "png", "--output", str(destination),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertIn("does not fit", result.stderr)
        self.assertEqual(destination.read_bytes(), previous)
        self.assertEqual([path.name for path in self.captures().iterdir()], ["existing.png"])
        self.assertEqual(synthetic.tree_digest(self.workspace), before)


if __name__ == "__main__":
    unittest.main()
