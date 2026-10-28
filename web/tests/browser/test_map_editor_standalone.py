"""The standalone map editor in a real browser, with no game running.

The editor service runs as a separate process from its own locked
environment (``tools/map-editor``) with an empty ``PATH`` (so no Node is
resolvable) against a temporary synthetic workspace; there is no game server,
database or game bundle. Every non-loopback request from the page is aborted
and recorded, so a CDN, network font or URL-like scene identifier would show
up as a failure instead of silently loading.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
FRONTEND = REPO_ROOT / "tools" / "map-editor" / "frontend"
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


class _StandaloneEditorBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

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

    def open(self, editor=None, viewport=REFERENCE, ready="current"):
        editor = editor or getattr(self, "editor")
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        own = urlparse(editor.origin).netloc

        def route(request_route):
            url = request_route.request.url
            if urlparse(url).netloc == own:
                self.requests.append(url)
                request_route.continue_()
            else:
                self.blocked.append(url)
                request_route.abort()

        page.route("**/*", route)
        page.goto(editor.origin + "/")
        page.wait_for_selector(f'[data-preview-state="{ready}"]', timeout=15000)
        return page

    def assert_only_local_requests(self):
        self.assertEqual(self.blocked, [])
        paths = [urlparse(url).path for url in self.requests]
        self.assertTrue(any(path.startswith("/assets/") for path in paths))
        self.assertFalse([path for path in paths if path.startswith("/static/")])


class MapEditorStandaloneBrowserTest(_StandaloneEditorBrowser):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.root = Path(tempfile.mkdtemp(prefix="map-editor-browser-"))
        cls.workspace = synthetic.write_workspace(cls.root / "workspace")
        cls.editor = harness.EditorProcess(cls.workspace, frontend_dist=harness.FRONTEND_DIST)
        cls.editor.__enter__()
        cls.state = cls.editor.workspace_state()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.editor.__exit__(None, None, None)
        shutil.rmtree(cls.root, ignore_errors=True)
        super().tearDownClass()

    def test_continent_settlement_and_interior_snapshots_render(self):
        page = self.open()
        world = self.state["world"]
        page.wait_for_selector('[data-kind="location"]')
        self.assertEqual(page.locator('[data-kind="location"]').count(), len(world["locations"]))
        self.assertEqual(page.locator('[data-shape="mainland"]').count(), 1)
        self.assertGreaterEqual(page.locator('[data-tree="location:%s"] .tag' % synthetic.BARE_LOCATION_ID).count(), 1)

        page.click('[data-domain-tab="settlement"]')
        settlement = world["settlements"][0]
        page.wait_for_selector('[data-kind="node"]')
        self.assertEqual(page.locator('[data-kind="node"]').count(), len(settlement["nodes"]))
        self.assertEqual(page.locator(".map-link--road").count(), len(settlement["roads"]))
        # Core-derived geometry: the longer road is the bent one on screen too.
        lengths = page.eval_on_selector_all(
            ".map-link--road .map-link__core", "els => els.map(el => el.getTotalLength())"
        )
        self.assertEqual(len(lengths), 2)
        self.assertGreater(max(lengths), min(lengths))

        page.click('[data-domain-tab="interior"]')
        page.wait_for_selector('[data-kind="room"]')
        self.assertEqual(page.locator('[data-kind="room"]').count(), len(world["interiors"][0]["rooms"]))
        self.assert_only_local_requests()

    def test_local_build_assets_load_with_node_unavailable_and_network_denied(self):
        self.assertIsNone(shutil.which("node", path=self.editor._empty_path))
        page = self.open()
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=15000)
        fonts = page.evaluate(
            "[...performance.getEntriesByType('resource')].filter(e => e.name.endsWith('.woff2')).map(e => e.name)"
        )
        own = self.editor.origin + "/assets/"
        self.assertTrue(fonts)
        self.assertTrue(all(name.startswith(own) for name in fonts))
        self.assertEqual(page.locator(".map-mark").count() > 0, True)
        self.assert_only_local_requests()

    def test_game_theme_scales_without_the_game_shell(self):
        scan = subprocess.run(
            ["node", str(FRONTEND / "scripts/import-boundary.mjs"), "--json"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        report = json.loads(scan.stdout)
        self.assertEqual(report["violations"], [])
        self.assertGreater(report["scanned"], 0)
        shell = (REPO_ROOT / "web/webclient-app/styles/app-shell.css").read_text(encoding="utf-8")
        shell_selector = next(
            line.split("{")[0].strip()
            for line in shell.splitlines()
            if "{" in line and line.strip().startswith(".") and not line.strip().startswith("@")
        )
        for viewport, scale in ((REFERENCE, 1.0), (LARGE, 1.4)):
            page = self.open(viewport=viewport)
            self.assertAlmostEqual(
                float(page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--ui-scale')")),
                scale,
            )
            selectors = page.evaluate(
                "[...document.styleSheets].flatMap(s => [...s.cssRules]).map(r => r.selectorText).filter(Boolean)"
            )
            self.assertNotIn(shell_selector, selectors)
            smallest = page.evaluate(
                """() => {
                  const sizes = [];
                  for (const el of document.querySelectorAll('body *')) {
                    const text = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
                    if (!text || !el.getClientRects().length) continue;
                    sizes.push(parseFloat(getComputedStyle(el).fontSize));
                  }
                  return Math.min(...sizes);
                }"""
            )
            self.assertGreaterEqual(smallest, 16 * scale - 0.01)
            title = page.locator(".editor__title")
            self.assertGreater(float(title.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")), 16 * scale)
            page.context.close()
        self.assert_only_local_requests()

    def test_authored_prose_and_scene_ids_stay_inert_text(self):
        page = self.open()
        page.click('[data-domain-tab="settlement"]')
        page.click(f'[data-object="settlement_node:{synthetic.SETTLEMENT_ID}:yard"]')
        description = page.locator('[data-field="描述"]')
        self.assertEqual(description.text_content(), synthetic.HOSTILE_DESC)
        page.click(f'[data-object="settlement_node:{synthetic.SETTLEMENT_ID}:gate"]')
        self.assertEqual(page.locator('[data-field="場景"]').text_content(), synthetic.URL_LIKE_SCENE)
        self.assertIsNone(page.evaluate("window.__mapEditorPwned"))
        self.assertEqual(page.locator("img, script:not([src])").count(), 0)
        self.assertFalse([url for url in self.blocked + self.requests if "example.invalid" in url])
        self.assert_only_local_requests()


class MapEditorStalePreviewBrowserTest(_StandaloneEditorBrowser):
    def test_a_failed_reread_keeps_the_last_preview_marked_stale(self):
        root = Path(tempfile.mkdtemp(prefix="map-editor-stale-"))
        self.addCleanup(shutil.rmtree, root, True)
        workspace = synthetic.write_workspace(root / "workspace")
        relative = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
        with harness.EditorProcess(workspace, frontend_dist=harness.FRONTEND_DIST) as editor:
            page = self.open(editor)
            page.click('[data-domain-tab="settlement"]')
            nodes = page.locator('[data-kind="node"]').count()
            (workspace / relative).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
            session = editor.session()
            status, _ = editor.reload(session["token"], session["session_generation"])
            self.assertEqual(status, 200)
            # The SSE invalidation makes the page refetch the complete state.
            page.wait_for_selector('[data-preview-state="stale"]', timeout=15000)
            banner = page.locator('[data-banner="stale"]')
            self.assertIn(relative, banner.text_content())
            self.assertEqual(page.locator('[data-kind="node"]').count(), nodes)
            self.assertEqual(page.locator(".map-canvas__badge").count(), 1)
            synthetic.write_workspace(workspace)
            editor.reload(session["token"], session["session_generation"])
            page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
            self.assertEqual(page.locator('[data-banner]').count(), 0)
        self.assert_only_local_requests()

    def test_an_unloadable_workspace_shows_no_preview_with_diagnostics(self):
        root = Path(tempfile.mkdtemp(prefix="map-editor-none-"))
        self.addCleanup(shutil.rmtree, root, True)
        workspace = synthetic.write_workspace(root / "workspace")
        (workspace / "content/maps/locations.yaml").write_text("version: 1\nkind: locations\nid: locations\nlocations: {}\nextra: 1\n", encoding="utf-8")
        with harness.EditorProcess(workspace, frontend_dist=harness.FRONTEND_DIST) as editor:
            page = self.open(editor, ready="unavailable")
            self.assertEqual(page.locator("[data-no-preview]").count(), 1)
            self.assertEqual(page.locator(".map-mark").count(), 0)
            self.assertGreater(page.locator("[data-diagnostic]").count(), 0)
            self.assertIn("content/maps/locations.yaml", page.locator(".diagnostics__list").text_content())
            self.assertEqual(page.locator('[data-banner="unavailable"]').count(), 1)
        self.assert_only_local_requests()


if __name__ == "__main__":
    unittest.main()
