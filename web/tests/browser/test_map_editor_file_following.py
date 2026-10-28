"""Map editor continuous file following and recovery in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``, real directory watcher) against a fresh
synthetic workspace and drives the built page while an external writer
changes the files on disk. Assertions read the files, the service state and
state hooks on the page (never shipped copy).
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
REFERENCE = (1451, 790)


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

LAYOUT = f"content/map-editor-layouts/{synthetic.INTERIOR_ID}.yaml"
INTERIOR = f"content/maps/interiors/{synthetic.INTERIOR_ID}.yaml"
SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
BACK = f"interior_room:{synthetic.INTERIOR_ID}:back"
FRONT = f"interior_room:{synthetic.INTERIOR_ID}:front"


def _layout(x: int, y: int) -> str:
    return f"version: 1\nkind: layout\nid: {synthetic.INTERIOR_ID}\npositions:\n  back: {{x: {x}, y: {y}}}\n"


def _replace(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.external")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


class MapEditorFileFollowingBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-follow-browser-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.workspace = synthetic.write_workspace(root / "workspace")
        self.layout = self.workspace / LAYOUT
        self.port = harness.free_port()
        self.editor = self.start()
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self.addCleanup(self._close)
        self.posts: list[str] = []

    def start(self):
        editor = harness.EditorProcess(self.workspace, port=self.port, frontend_dist=harness.FRONTEND_DIST)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        return editor

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    # -- helpers ---------------------------------------------------------
    def open(self, *, browser=None):
        context = (browser or self._browser).new_context(viewport={"width": REFERENCE[0], "height": REFERENCE[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        page.click('[data-domain-tab="interior"]')
        page.wait_for_selector(f'[data-qualified-ref="{BACK}"]')
        self.page = page
        return page

    def wait_for(self, predicate, message: str, timeout: float = 20) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            # Playwright delivers page events only while one of its calls runs.
            self.page.wait_for_timeout(50)
        self.fail(message)

    def names(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.posts]

    def back(self):
        if not self.layout.exists():
            return None
        state = self.editor.workspace_state()
        rooms = {room["id"]: room["layout_position"] for room in state["world"]["interiors"][0]["rooms"]}
        return rooms["back"]

    def external_sequence(self) -> int:
        return self.editor.workspace_state()["external_change"]["sequence"]

    def settle(self, page) -> None:
        page.wait_for_function(
            "() => !document.querySelector('[data-chip=\"save\"].chip--busy')", timeout=15000
        )

    # -- tests -----------------------------------------------------------
    def test_a_loadable_external_change_is_adopted_with_the_view_and_selection_kept(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        before = page.locator(f'[data-qualified-ref="{BACK}"]').bounding_box()
        _replace(self.layout, _layout(4, 0))
        page.wait_for_function(
            f"() => document.querySelector('[data-layout-field=\"x\"]')?.value === '4'", timeout=20000
        )
        self.assertEqual(page.locator('[data-domain-tab="interior"][aria-pressed="true"]').count(), 1)
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), BACK)
        self.assertEqual(page.locator(f'[data-qualified-ref="{BACK}"][aria-pressed="true"]').count(), 1)
        after = page.locator(f'[data-qualified-ref="{BACK}"]').bounding_box()
        self.assertNotEqual(after["x"], before["x"])
        self.assertEqual(page.locator("[data-banner]").count(), 0)
        self.assertEqual(self.names(), [])
        self.assertEqual(self.layout.read_text(encoding="utf-8"), _layout(4, 0))

    def test_an_open_draft_holds_the_external_change_until_load_new_version(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        field = page.locator('[data-layout-field="x"]')
        field.fill("4")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        _replace(self.layout, _layout(7, 8))
        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
        self.assertIn(LAYOUT, page.locator('[data-banner="external-draft"]').text_content())
        # The draft and the displayed snapshot are kept until the explicit action.
        self.assertEqual(field.input_value(), "4")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        page.click('[data-banner-action="adopt"]')
        page.wait_for_function("() => !document.querySelector('[data-banner]')", timeout=15000)
        field = page.locator('[data-layout-field="x"]')
        self.assertEqual(field.input_value(), "7")
        self.assertIsNone(field.get_attribute("data-draft"))
        self.assertEqual(self.names(), [])
        self.assertEqual(self.layout.read_text(encoding="utf-8"), _layout(7, 8))

    def test_tab_reaches_load_new_version_without_confirming_a_held_draft(self):
        firefox = self._playwright.firefox.launch(headless=True)
        self.addCleanup(firefox.close)
        case = 0
        for browser_name, browser in (("chromium", self._browser), ("firefox", firefox)):
            for viewport in (REFERENCE, (725, 395)):
                for kind, key in (("layout", "Tab"), ("name", "Shift+Tab")):
                    with self.subTest(browser=browser_name, viewport=viewport, field=kind):
                        case += 1
                        page = self.open(browser=browser)
                        page.click(f'[data-object="{BACK}"]')
                        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
                        compact = viewport != REFERENCE
                        if compact:
                            page.click('[data-drawer-toggle="inspector"]')
                            page.wait_for_selector('[data-region="inspector"][aria-modal="true"]')
                        if kind == "layout":
                            selector = '[data-layout-field="x"]'
                            path = self.layout
                            external = _layout(10 + case, 20 + case)
                            expected = str(10 + case)
                            draft = "4"
                        else:
                            selector = '[data-field-input="room-name_zh"]'
                            path = self.workspace / INTERIOR
                            data = synthetic.interior_data()
                            expected = f"External room {case}"
                            data["rooms"]["back"]["name_zh"] = expected
                            external = synthetic.yaml_text(data)
                            draft = "Unconfirmed room"
                        field = page.locator(selector)
                        field.fill(draft)
                        _replace(path, external)
                        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
                        field.press(key)
                        action = page.locator('[data-banner-action="adopt"]')
                        self.assertTrue(action.evaluate("(element) => element === document.activeElement"))
                        self.assertEqual(field.input_value(), draft)
                        self.assertEqual(field.get_attribute("data-draft"), "true")
                        self.assertEqual(page.locator('[data-banner="external-draft"]').count(), 1)
                        self.assertEqual(page.locator('[data-banner="save-rejected"]').count(), 0)
                        self.assertEqual(page.locator('[data-region="inspector"][aria-modal="true"]').count(), 0)
                        self.assertEqual(self.names(), [])
                        action.press("Enter")
                        page.wait_for_function(
                            "([selector, value]) => document.querySelector(selector)?.value === value"
                            " && !document.querySelector('[data-banner]')",
                            arg=[selector, expected], timeout=15000,
                        )
                        self.assertIsNone(field.get_attribute("data-draft"))
                        self.assertEqual(self.names(), [])
                        self.assertEqual(path.read_text(encoding="utf-8"), external)
                        page.context.close()

    def test_an_invalid_draft_cannot_be_removed_by_selection_or_navigation(self):
        annex = synthetic.interior_data()
        annex["id"] = "synthetic_z_annex"
        annex["rooms"] = {"annex_room": annex["rooms"]["back"]}
        annex["connections"] = []
        annex["exterior"]["room"] = "annex_room"
        _replace(
            self.workspace / "content/maps/interiors/synthetic_z_annex.yaml",
            synthetic.yaml_text(annex),
        )
        page = self.open()
        page.wait_for_function(
            "() => [...document.querySelector('.nav__map-select').options]"
            ".some(option => option.value === 'synthetic_z_annex')", timeout=20000,
        )
        page.click(f'[data-object="{BACK}"]')
        field = page.locator('[data-layout-field="x"]')
        field.fill("1o")
        _replace(self.layout, _layout(7, 8))
        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
        page.click(f'[data-object="{FRONT}"]')
        self.wait_for(
            lambda: field.evaluate("(element) => element === document.activeElement"),
            "the unresolved layout draft was not refocused",
        )
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), BACK)
        self.assertEqual(field.input_value(), "1o")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        self.assertEqual(field.get_attribute("aria-invalid"), "true")
        self.assertEqual(page.locator('[data-banner="external-draft"]').count(), 1)
        page.select_option(".nav__map-select", "synthetic_z_annex")
        self.wait_for(
            lambda: field.evaluate("(element) => element === document.activeElement"),
            "the map dropdown did not preserve the unresolved draft",
        )
        self.assertEqual(page.locator(".nav__map-select").input_value(), synthetic.INTERIOR_ID)
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), BACK)
        self.assertEqual(field.input_value(), "1o")
        self.assertEqual(page.locator('[data-banner="external-draft"]').count(), 1)
        page.click('[data-domain-tab="settlement"]')
        self.assertEqual(page.locator('[data-domain-tab="interior"][aria-pressed="true"]').count(), 1)
        self.assertEqual(field.input_value(), "1o")
        self.assertEqual(self.names(), [])
        box = page.locator(f'[data-qualified-ref="{FRONT}"]').bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + 60, y + 30, steps=4)
        page.mouse.up()
        self.wait_for(
            lambda: field.evaluate("(element) => element === document.activeElement"),
            "dragging another room removed the unresolved draft",
        )
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), BACK)
        self.assertEqual(field.input_value(), "1o")
        self.assertEqual(self.names(), [])
        field.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-layout-field=\"x\"]')?.value === '7'"
            " && !document.querySelector('[data-banner]')", timeout=15000,
        )
        self.assertEqual(self.names(), [])
        self.assertEqual(self.layout.read_text(encoding="utf-8"), _layout(7, 8))
        page.click(f'[data-object="{FRONT}"]')
        self.wait_for(
            lambda: page.locator("[data-inspector-ref]").text_content() == FRONT,
            "selection stayed blocked after explicit draft cancellation",
        )
        # A valid blur still confirms once before navigation removes its field.
        page.click(f'[data-object="{BACK}"]')
        field.fill("9")
        page.click(f'[data-object="{FRONT}"]')
        self.wait_for(lambda: self.back() == [9, 8], "valid blur confirmation was blocked")
        self.settle(page)
        self.assertEqual(self.names(), ["move_interior_layout"])

    def test_hiding_a_layer_cannot_remove_an_invalid_field_draft(self):
        page = self.open()
        page.click('[data-domain-tab="continent"]')
        river = "continent:waterway:synthetic_river"
        page.click(f'[data-object="{river}"]')
        page.click(f'[data-object="{river}#0"]')
        field = page.locator('[data-field-input="point-0"]')
        saved = field.input_value()
        field.fill("1o")
        page.click('[data-layer="water"]')
        self.wait_for(
            lambda: field.evaluate("(element) => element === document.activeElement"),
            "the unresolved control-point draft was not refocused",
        )
        self.assertEqual(field.input_value(), "1o")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        self.assertEqual(field.get_attribute("aria-invalid"), "true")
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), f"{river}#0")
        self.assertTrue(page.locator('[data-layer="water"]').is_checked())
        self.assertEqual(self.names(), [])
        field.press("Escape")
        self.assertEqual(field.input_value(), saved)
        page.click('[data-layer="water"]')
        self.wait_for(
            lambda: page.locator(f'[data-object="{river}#0"]').count() == 0,
            "the layer stayed blocked after explicit draft cancellation",
        )
        self.assertFalse(page.locator('[data-layer="water"]').is_checked())
        self.assertEqual(self.names(), [])

    def test_a_draft_confirmed_against_the_old_snapshot_is_rejected_without_changing_disk(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        field = page.locator('[data-layout-field="x"]')
        field.fill("4")
        _replace(self.layout, _layout(7, 8))
        external = self.layout.read_bytes()
        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
        field.press("Enter")
        page.wait_for_selector('[data-banner="save-rejected"]', timeout=15000)
        self.settle(page)
        self.assertEqual(self.names(), ["move_interior_layout"])
        self.assertEqual(self.layout.read_bytes(), external)
        self.assertEqual(self.back(), [7, 8])
        # With the draft gone, the new version is shown; nothing was retried.
        self.wait_for(lambda: page.locator('[data-layout-field="x"]').input_value() == "7",
                      "the held external change was not adopted")
        self.assertEqual(self.names(), ["move_interior_layout"])

    def test_malformed_yaml_is_shown_stale_and_recovers_automatically(self):
        page = self.open()
        path = self.workspace / SETTLEMENT
        path.write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
        page.wait_for_selector('[data-preview-state="stale"]', timeout=20000)
        self.assertEqual(page.locator(".map-canvas__badge").count(), 1)
        self.assertIn(SETTLEMENT, page.locator('[data-banner="stale"]').text_content())
        # The frontend does not pre-disable controls: the service rejects.
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_selector('[data-banner="save-rejected"]', timeout=15000)
        self.settle(page)
        self.assertFalse(self.layout.exists())
        self.assertEqual(path.read_text(encoding="utf-8"), "version: 1\nkind: [unclosed\n")
        _replace(path, synthetic.yaml_text(synthetic.settlement_data()))
        page.wait_for_selector('[data-preview-state="current"]', timeout=20000)
        page.wait_for_function("() => !document.querySelector('[data-banner]')", timeout=15000)
        self.assertEqual(page.locator(".map-canvas__badge").count(), 0)
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(self.layout.exists, "the write did not resume after recovery")

    def test_an_externally_removed_selection_is_cleared_with_a_notice(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        data = synthetic.interior_data()
        del data["rooms"]["back"]
        data["connections"] = []
        _replace(self.workspace / INTERIOR, synthetic.yaml_text(data))
        page.wait_for_selector("[data-selection-removed]", timeout=20000)
        self.assertIn(BACK, page.locator("[data-selection-removed]").text_content())
        self.assertEqual(page.locator("[data-inspector-ref]").count(), 0)
        self.assertEqual(page.locator(f'[data-qualified-ref="{BACK}"]').count(), 0)
        page.click(f'[data-object="{FRONT}"]')
        self.assertEqual(page.locator("[data-selection-removed]").count(), 0)
        self.assertEqual(self.names(), [])

    def test_a_restart_keeps_a_stale_inspectable_snapshot_and_needs_an_explicit_read(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        self.editor.__exit__(None, None, None)
        page.wait_for_selector('[data-connection="disconnected"]', timeout=20000)
        self.assertEqual(page.locator(".map-canvas__badge").count(), 1)
        # The disconnected snapshot stays inspectable.
        page.click(f'[data-object="{FRONT}"]')
        self.assertEqual(page.locator("[data-inspector-ref]").text_content(), FRONT)
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_selector('[data-banner="disconnected"]', timeout=15000)
        self.settle(page)
        attempted = list(self.posts)
        self.editor = self.start()
        page.wait_for_selector('[data-connection="restarted"]', timeout=20000)
        self.assertEqual(page.locator('[data-banner="restarted"]').count(), 1)
        self.assertEqual(page.locator(".map-canvas__badge").count(), 1)
        # Nothing was replayed into the new session. The exact POST count after
        # the later fresh-read write proves no replay happened in between.
        self.assertFalse(self.layout.exists())
        page.click('[data-banner-action="reconnect"]')
        page.wait_for_selector('[data-connection="connected"]', timeout=15000)
        page.wait_for_function("() => !document.querySelector('[data-banner]')", timeout=15000)
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(self.layout.exists, "the write after the fresh read did not land")
        self.settle(page)
        self.assertEqual(len(self.posts), len(attempted) + 1)


if __name__ == "__main__":
    unittest.main()
