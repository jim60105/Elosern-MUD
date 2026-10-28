"""Map editor layout drafts, autosave and segment undo in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``) against a fresh synthetic workspace and
drives the built page with real pointer and keyboard input. Assertions read
the layout file on disk and the service's workspace state, never shipped copy.
"""

from __future__ import annotations

import hashlib
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
BACK = f"interior_room:{synthetic.INTERIOR_ID}:back"


class MapEditorPersistenceBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-persist-browser-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.workspace = synthetic.write_workspace(root / "workspace")
        self.layout = self.workspace / LAYOUT
        self.world = synthetic.tree_digest(self.workspace)
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

    # -- helpers ---------------------------------------------------------
    def open(self):
        context = self._browser.new_context(viewport={"width": REFERENCE[0], "height": REFERENCE[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        page.click('[data-domain-tab="interior"]')
        page.wait_for_selector(f'[data-qualified-ref="{BACK}"]')
        self.page = page
        return page

    def settle(self, page) -> None:
        # The client stays busy until the answer and its refetch are in.
        page.wait_for_function(
            "() => !document.querySelector('[data-chip=\"save\"].chip--busy')", timeout=15000
        )

    def wait_for(self, predicate, message: str) -> None:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if predicate():
                return
            # Playwright delivers page events only while one of its calls runs.
            self.page.wait_for_timeout(50)
        self.fail(message)

    def stored(self) -> dict | None:
        if not self.layout.exists():
            return None
        state = self.editor.workspace_state()
        rooms = state["world"]["interiors"][0]["rooms"]
        return {room["id"]: room["layout_position"] for room in rooms}

    def names(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.posts]

    def back(self):
        """The saved layout position of the dragged room, or None (yet)."""

        return (self.stored() or {}).get("back")

    def drag(self, page, ref: str, dx: float, dy: float, *, cancel: bool = False) -> None:
        box = page.locator(f'[data-qualified-ref="{ref}"]').bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x + dx * step / 5, y + dy * step / 5)
        if cancel:
            page.keyboard.press("Escape")
        page.mouse.up()

    def world_unchanged(self) -> None:
        now = synthetic.tree_digest(self.workspace)
        now.pop(LAYOUT, None)
        self.assertEqual(now, self.world)

    # -- tests -----------------------------------------------------------
    def test_a_drag_is_one_saved_operation_that_undoes_to_absence_and_redoes(self):
        page = self.open()
        before = page.locator(f'[data-qualified-ref="{BACK}"]').bounding_box()
        self.drag(page, BACK, 260, 0)
        self.wait_for(lambda: self.back() is not None, "the drag release did not save the layout")
        self.settle(page)
        self.assertEqual([url.rsplit("/", 1)[1] for url in self.posts], ["move_interior_layout"])
        after = page.locator(f'[data-qualified-ref="{BACK}"]').bounding_box()
        self.assertGreater(after["x"], before["x"] + 100)
        saved = self.stored()["back"]
        self.assertEqual(self.stored()["front"], None)
        self.assertGreater(saved[0], 1)
        self.assertEqual(page.locator('[data-chip="save"].chip--ok').count(), 1)

        page.keyboard.press("Control+z")
        self.wait_for(lambda: not self.layout.exists(), "undo did not remove the first layout")
        self.settle(page)
        page.keyboard.press("Control+Shift+z")
        self.wait_for(self.layout.exists, "redo did not recreate the layout")
        self.settle(page)
        self.assertEqual(self.stored()["back"], saved)
        self.world_unchanged()

    def test_escape_cancels_a_drag_and_shift_arrow_nudges_one_step_per_press(self):
        page = self.open()
        self.drag(page, BACK, 260, 0, cancel=True)
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        page.keyboard.press("Shift+ArrowRight")
        page.keyboard.press("Shift+ArrowDown")
        self.wait_for(lambda: self.back() == [3, 1], "three nudges were not saved")
        self.settle(page)
        # Commands are strictly ordered: exactly the three nudges were sent,
        # so the cancelled drag sent nothing before them.
        self.assertEqual(self.names(), ["move_interior_layout"] * 3)
        history = self.editor.workspace_state()["history"]
        self.assertIsNotNone(history["undo"])
        page.keyboard.press("Control+z")
        self.wait_for(lambda: self.back() == [3, 0], "undo did not revert one nudge")
        self.world_unchanged()

    def test_an_incomplete_field_draft_is_never_written_and_escape_restores_it(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        field = page.locator('[data-layout-field="x"]')
        saved_value = field.input_value()
        field.fill("1o")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        self.assertEqual(page.locator('[data-chip="save"].chip--draft').count(), 1)
        field.press("Enter")
        self.assertEqual(page.locator('[data-field-error="x"]').count(), 1)
        self.assertEqual(field.get_attribute("aria-invalid"), "true")
        # Save flushes accepted work only; it never forces the draft.
        field.press("Control+s")
        field.press("Escape")
        self.assertEqual(field.input_value(), saved_value)
        self.assertIsNone(field.get_attribute("data-draft"))
        # The selection survives the draft's Escape.
        self.assertEqual(page.locator('[data-layout-fields]').count(), 1)
        field.fill("4")
        field.press("Tab")
        self.wait_for(lambda: self.back() == [4, 0], "a blurred complete draft was not saved")
        self.settle(page)
        # Only the confirmed value was ever sent: neither Enter on the
        # incomplete draft nor Save submitted it.
        self.assertEqual(self.names(), ["move_interior_layout"])

    def test_a_refreshed_page_does_not_inherit_undo_history(self):
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(self.layout.exists, "the nudge was not saved")
        self.settle(page)
        saved = hashlib.sha256(self.layout.read_bytes()).hexdigest()
        page.reload()
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        self.posts.clear()
        page.keyboard.press("Control+z")
        # A later command proves the undo key sent nothing before it.
        page.click('[data-domain-tab="interior"]')
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(lambda: self.back() == [3, 0], "the post-refresh nudge was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_interior_layout"])
        self.assertNotEqual(hashlib.sha256(self.layout.read_bytes()).hexdigest(), saved)

    def test_a_failed_save_is_reported_with_the_baseline_intact_and_no_retry(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("directory permissions do not bind the superuser")
        page = self.open()
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(self.layout.exists, "the first nudge was not saved")
        self.settle(page)
        first = self.layout.read_bytes()
        self.layout.parent.chmod(0o555)
        self.addCleanup(self.layout.parent.chmod, 0o755)
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_selector('[data-banner="save-failed"]', timeout=15000)
        self.assertEqual(page.locator('[data-chip="save"].chip--seal').count(), 1)
        self.settle(page)
        self.assertEqual(self.layout.read_bytes(), first)
        self.layout.parent.chmod(0o755)
        page.click('[data-banner-action="reload"]')
        page.wait_for_function("() => !document.querySelector('[data-banner]')", timeout=15000)
        # No automatic retry happened between the failure and the reread.
        self.assertEqual(self.names(), ["move_interior_layout", "move_interior_layout", "reload"])
        self.assertEqual(self.stored()["back"], [2, 0])


if __name__ == "__main__":
    unittest.main()
