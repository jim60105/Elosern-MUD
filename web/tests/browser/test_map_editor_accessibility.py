"""Map editor workspace navigation, diagnostics, context copy and keyboard access.

Each test starts the standalone editor service as a separate process against
a fresh synthetic workspace and drives the built page with real keyboard and
pointer input. Assertions read the service state, the files on disk, the
clipboard and the page's ``data-*`` state hooks, never shipped wording.

200 % browser zoom is emulated in CSS pixels: the 1451x790 reference at
``device_scale_factor=2`` is a 725x395 CSS viewport. That reproduces the
layout width the page sees, not every media feature of a real browser zoom.
"""

from __future__ import annotations

import copy
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[3]
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"
REFERENCE = (1451, 790, 1)
LARGE = (2560, 1440, 1)
ZOOM_200 = (725, 395, 2)


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

SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
INTERIOR = f"content/maps/interiors/{synthetic.INTERIOR_ID}.yaml"
ANNEX_ID = "synthetic_annex"
ANNEX = f"content/maps/interiors/{ANNEX_ID}.yaml"
LAYOUT = f"content/map-editor-layouts/{synthetic.INTERIOR_ID}.yaml"
YARD = f"settlement_node:{synthetic.SETTLEMENT_ID}:yard"
FRONT = f"interior_room:{synthetic.INTERIOR_ID}:front"
BACK = f"interior_room:{synthetic.INTERIOR_ID}:back"
ANNEX_FRONT = f"interior_room:{ANNEX_ID}:front"
PARTITION = "world/maps/data/district_partition.json"


def write(workspace: Path, relative: str, data: dict) -> None:
    path = workspace / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(synthetic.yaml_text(data), encoding="utf-8")


def add_annex(workspace: Path) -> None:
    """A second interior whose only room has the same name as ``front``."""

    data = synthetic.interior_data()
    data["id"] = ANNEX_ID
    data["rooms"] = {"front": copy.deepcopy(data["rooms"]["front"])}
    data["connections"] = []
    data["exterior"] = None
    write(workspace, ANNEX, data)


def cut_gate_road(workspace: Path) -> None:
    """Make the district landmark unreachable (a saveable semantic diagnostic)."""

    data = synthetic.settlement_data()
    data["roads"] = [road for road in data["roads"] if road["source"] != "gate"]
    write(workspace, SETTLEMENT, data)


def stale_partition(workspace: Path) -> None:
    path = workspace / PARTITION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 2, "algorithm_version": 1, "source_signature": "0" * 64, "fingerprint": "synthetic"}),
        encoding="utf-8",
    )


def dense_diagnostics(workspace: Path, count: int = 60) -> None:
    cut_gate_road(workspace)
    data = synthetic.districts_data()
    base = data["districts"]["synthetic_district"]
    for index in range(count):
        entry = copy.deepcopy(base)
        entry["district_name_zh"] = f"合成區{index}"
        entry["landmark_name_zh"] = f"合成地標{index}"
        data["districts"][f"synthetic_district_{index:02d}"] = entry
    write(workspace, "content/maps/districts.yaml", data)
    locations = synthetic.locations_data()
    locations["locations"][synthetic.BARE_LOCATION_ID]["display_name_zh"] = "很長的地點名稱" * 12
    write(workspace, "content/maps/locations.yaml", locations)


class _AccessibilityBrowser(unittest.TestCase):
    BROWSER = "chromium"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def start(self, *prepare) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-a11y-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.workspace = synthetic.write_workspace(root / "workspace")
        for step in prepare:
            step(self.workspace)
        self.baseline = synthetic.tree_digest(self.workspace)
        self.editor = harness.EditorProcess(self.workspace, frontend_dist=harness.FRONTEND_DIST)
        self.editor.__enter__()
        self.addCleanup(self.editor.__exit__, None, None, None)
        self._playwright = sync_playwright().start()
        self._browser = getattr(self._playwright, self.BROWSER).launch(headless=True)
        self.addCleanup(self._close)
        self.posts: list[str] = []

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def open(self, viewport=REFERENCE, *, permissions=None):
        width, height, scale = viewport
        context = self._browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
            permissions=permissions or [],
        )
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

    def active(self, page, attribute: str):
        return page.evaluate(f"() => document.activeElement?.getAttribute({attribute!r}) ?? null")

    def active_region(self, page):
        return page.evaluate("() => document.activeElement?.closest('[data-region]')?.dataset.region ?? null")

    def inspected(self, page):
        locator = page.locator("[data-inspector-ref]")
        return locator.text_content() if locator.count() else None

    def domain(self, page):
        tabs = page.locator("[data-domain-tab]")
        for index in range(tabs.count()):
            if tabs.nth(index).get_attribute("aria-pressed") == "true":
                return tabs.nth(index).get_attribute("data-domain-tab")
        return None

    def tab_to(self, page, selector: str, limit: int = 60) -> None:
        for _ in range(limit):
            if page.evaluate("(s) => Boolean(document.activeElement?.matches(s))", selector):
                return
            page.keyboard.press("Tab")
        self.fail(f"Tab never reached {selector}")

    def disk_unchanged(self) -> None:
        self.assertEqual(synthetic.tree_digest(self.workspace), self.baseline)

    # -- the keyboard-only workflow, shared by Chromium and Firefox ----------
    def keyboard_workflow(self):
        self.start(cut_gate_road)
        page = self.open()
        # F6 cycles the five regions in order; Shift+F6 goes back.
        regions = []
        for _ in range(5):
            page.keyboard.press("F6")
            regions.append(self.active_region(page))
        self.assertEqual(regions, ["header", "nav", "canvas", "inspector", "diagnostics"])
        page.keyboard.press("Shift+F6")
        self.assertEqual(self.active_region(page), "inspector")
        page.keyboard.press("F6")
        # Diagnostics: open the strip and follow a row, by keyboard only.
        self.tab_to(page, "[data-diagnostics-toggle]")
        page.keyboard.press("Enter")
        self.tab_to(page, '[data-diagnostic="unreachable_landmark"] [data-diagnostic-action]')
        page.keyboard.press("Enter")
        self.wait_for(lambda: self.inspected(page) == YARD, "the diagnostic did not locate its object")
        self.assertEqual(self.domain(page), "settlement")
        self.assertIsNotNone(self.active(page, "data-inspector-title"))
        self.assertEqual(page.locator("[data-return]").count(), 1)
        # Canvas: Tab walks the marks, Enter selects and focuses the first field.
        page.keyboard.press("3")
        self.assertEqual(self.domain(page), "interior")
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("Tab")
        self.assertEqual(self.active(page, "data-qualified-ref"), FRONT)
        page.keyboard.press("Enter")
        self.wait_for(lambda: self.active(page, "data-layout-field") == "x", "Enter did not focus the first field")
        self.assertEqual(self.inspected(page), FRONT)
        # An incomplete number keeps focus and an inline error; input
        # Delete/undo stay local and never touch the selected room.
        field = page.locator('[data-layout-field="x"]')
        saved = field.input_value()
        page.keyboard.type("1o")
        page.keyboard.press("Enter")
        self.assertEqual(field.get_attribute("aria-invalid"), "true")
        self.assertEqual(self.active(page, "data-layout-field"), "x")
        page.keyboard.press("Delete")
        page.keyboard.press("Backspace")
        page.keyboard.press("Control+z")
        self.assertEqual(page.locator("[data-delete-refusal]").count(), 0)
        page.keyboard.press("Escape")
        self.assertEqual(field.input_value(), saved)
        self.assertEqual(self.active(page, "data-layout-field"), "x")
        self.assertEqual(self.inspected(page), FRONT)
        self.assertEqual(self.posts, [])
        self.disk_unchanged()
        page.context.close()

        # 200 % zoom: the columns are drawers; Escape closes one and returns
        # focus to its header toggle.
        page = self.open(ZOOM_200)
        self.assertEqual(page.locator(".editor").get_attribute("data-layout"), "drawers")
        page.keyboard.press("F6")
        self.tab_to(page, '[data-drawer-toggle="inspector"]')
        page.keyboard.press("Enter")
        self.wait_for(lambda: self.active_region(page) == "inspector", "the inspector drawer did not take focus")
        # Tab stays trapped inside the open drawer.
        for _ in range(4):
            page.keyboard.press("Tab")
            self.assertEqual(self.active_region(page), "inspector")
        page.keyboard.press("Escape")
        self.assertEqual(self.active(page, "data-drawer-toggle"), "inspector")
        self.assertEqual(page.locator('[data-drawer-toggle="inspector"]').get_attribute("aria-expanded"), "false")
        self.assertEqual(self.posts, [])


class MapEditorAccessibilityBrowserTest(_AccessibilityBrowser):
    def test_search_tells_equal_names_apart_and_alt_left_returns(self):
        self.start(add_annex)
        page = self.open()
        page.click('[data-domain-tab="settlement"]')
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("/")
        self.assertIsNotNone(self.active(page, "data-search"))
        page.keyboard.type(synthetic.interior_data()["rooms"]["front"]["name_zh"])
        results = page.locator("[data-search-result]")
        self.wait_for(lambda: results.count() == 2, "both equal names were not found")
        refs = [results.nth(index).get_attribute("data-search-result") for index in range(2)]
        self.assertEqual(sorted(refs), sorted([FRONT, ANNEX_FRONT]))
        parents = [results.nth(index).locator(".results__parent").text_content() for index in range(2)]
        paths = [results.nth(index).locator(".results__path").text_content() for index in range(2)]
        self.assertNotEqual(parents[0], parents[1])
        self.assertEqual(sorted(paths), sorted([INTERIOR, ANNEX]))
        page.click(f'[data-search-result="{ANNEX_FRONT}"]')
        self.wait_for(lambda: self.inspected(page) == ANNEX_FRONT, "the result was not opened")
        self.assertEqual(self.domain(page), "interior")
        self.assertIsNotNone(self.active(page, "data-inspector-title"))
        page.keyboard.press("Alt+ArrowLeft")
        self.wait_for(lambda: self.inspected(page) == YARD, "Alt+Left did not return")
        self.assertEqual(self.domain(page), "settlement")
        self.assertEqual(page.locator("[data-return]").count(), 0)
        self.assertEqual(self.posts, [])

    def test_diagnostics_locate_targets_and_reveal_a_hidden_layer(self):
        self.start(cut_gate_road, stale_partition)
        page = self.open()
        # Layer visibility filters the drawn marks and the object list.
        locations = len(self.editor.workspace_state()["world"]["locations"])
        self.assertEqual(page.locator('[data-kind="location"]').count(), locations)
        page.click('[data-layer="locations"]')
        self.assertEqual(page.locator('[data-kind="location"]').count(), 0)
        self.assertEqual(page.locator("[data-object]").count(), 0)
        page.click('[data-layer="locations"]')
        self.assertEqual(page.locator("[data-object]").count(), locations)
        page.click('[data-layer="partition"]')
        self.assertFalse(page.locator('[data-layer="partition"]').is_checked())
        page.click('[data-domain-tab="interior"]')
        page.click("[data-diagnostics-toggle]")
        stale = page.locator('[data-diagnostic="stale_partition"] [data-diagnostic-action]')
        self.assertEqual(stale.get_attribute("data-diagnostic-action"), "reveal-go")
        stale.click()
        self.wait_for(lambda: page.locator('[data-layer="partition"]').is_checked(), "the hidden layer was not revealed")
        self.assertEqual(self.domain(page), "continent")
        self.assertEqual(page.locator("[data-return]").count(), 1)
        landmark = page.locator('[data-diagnostic="unreachable_landmark"] [data-diagnostic-action]')
        self.assertEqual(landmark.get_attribute("data-diagnostic-action"), "go")
        landmark.click()
        self.wait_for(lambda: self.inspected(page) == YARD, "the diagnostic did not select its object")
        self.assertEqual(self.domain(page), "settlement")
        self.assertIsNotNone(self.active(page, "data-inspector-title"))
        self.assertEqual(self.posts, [])
        self.disk_unchanged()

    def test_an_unknown_index_explains_refused_deletion_and_editing_still_saves(self):
        self.start()
        page = self.open()
        self.assertFalse(self.editor.workspace_state()["external_context_status"]["current"])
        self.assertEqual(page.locator('[data-chip="index"]').get_attribute("data-chip-state"), "unavailable")
        page.click('[data-chip="index"]')
        self.assertGreaterEqual(page.locator('[data-diagnostic-class="external"]').count(), 1)
        page.click('[data-domain-tab="interior"]')
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Delete")
        self.assertEqual(page.locator('[data-delete-refusal="index-unavailable"]').count(), 1)
        self.assertEqual(self.posts, [])
        self.disk_unchanged()
        # Ordinary editing is not blocked: one nudge is one saved command.
        page.click(f'[data-object="{BACK}"]')
        page.keyboard.press("Shift+ArrowRight")
        layout = self.workspace / LAYOUT
        self.wait_for(layout.exists, "the nudge was not saved")
        self.assertEqual([url.rsplit("/", 1)[1] for url in self.posts], ["move_interior_layout"])

    def test_a_referenced_object_lists_its_references_inline_and_writes_nothing(self):
        record = {"source": "place:synthetic_front", "source_domain": "places", "source_file": "external/declarations.txt"}
        target = {"domain": "interior_room", "map_id": synthetic.INTERIOR_ID, "object_id": "front", "cell": None}
        self.start(lambda root: synthetic.write_reference_context(root, incoming={FRONT: [dict(record, target=target)]}))
        page = self.open()
        state = self.editor.workspace_state()
        self.assertTrue(state["external_context_status"]["current"])
        self.assertEqual(page.locator('[data-chip="index"]').get_attribute("data-chip-state"), "current")
        page.click('[data-domain-tab="interior"]')
        page.click(f'[data-object="{FRONT}"]')
        self.assertEqual(page.locator('[data-relation="in"][data-external="true"]').count(), 1)
        page.click('[data-action="delete"]')
        self.assertEqual(page.locator('[data-delete-refusal="referenced"]').count(), 1)
        self.assertEqual(page.locator("[data-refusal-reference]").count(), 1)
        internal = page.locator(f'[data-refusal-internal] [data-follow="{BACK}"]')
        self.assertEqual(internal.count(), 1)
        internal.click()
        self.wait_for(lambda: self.inspected(page) == BACK, "the reference was not followed")
        self.assertEqual(page.locator("[data-return]").count(), 1)
        page.keyboard.press("Alt+ArrowLeft")
        self.wait_for(lambda: self.inspected(page) == FRONT, "Alt+Left did not return to the refused object")
        self.assertEqual(self.posts, [])
        self.disk_unchanged()

    def test_a_stale_multi_selection_copies_every_source_without_secrets_or_actions(self):
        self.start()
        page = self.open(permissions=["clipboard-read", "clipboard-write"])
        page.click('[data-domain-tab="settlement"]')
        page.click(f'[data-object="{YARD}"]')
        page.fill("[data-search]", synthetic.interior_data()["rooms"]["back"]["name_zh"])
        page.click(f'[data-search-result="{BACK}"]', modifiers=["Control"])
        self.assertEqual(page.locator("[data-selection-member]").count(), 2)
        self.assertEqual(page.locator("[data-selection-reason]").count(), 1)

        def copied() -> str:
            page.locator('[data-region="canvas"]').focus()
            page.evaluate("() => navigator.clipboard.writeText('')")
            page.keyboard.press("Control+c")
            self.wait_for(lambda: page.evaluate("() => navigator.clipboard.readText()") != "", "nothing was copied")
            return page.evaluate("() => navigator.clipboard.readText()")

        current = copied()
        (self.workspace / SETTLEMENT).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
        session = self.editor.session()
        self.editor.reload(session["token"], session["session_generation"])
        page.wait_for_selector('[data-preview-state="stale"]', timeout=15000)
        self.posts.clear()
        text = copied()
        for expected in (YARD, BACK, SETTLEMENT, INTERIOR):
            self.assertIn(expected, text)
        # Only the currentness line changed, and it names the failing file.
        changed = [line for line in text.splitlines() if line not in current.splitlines()]
        self.assertEqual(len(changed), 1)
        self.assertIn(SETTLEMENT, changed[0])
        for secret in (session["token"], session["session_generation"], str(self.workspace)):
            self.assertNotIn(secret, text)
        self.assertEqual(page.locator('[data-copy-notice="ok"]').count(), 1)
        self.assertEqual(self.posts, [])

    def test_supported_viewports_keep_status_and_operations_reachable(self):
        self.start(dense_diagnostics)
        for viewport, layout in ((REFERENCE, "columns"), (LARGE, "columns"), (ZOOM_200, "drawers")):
            page = self.open(viewport)
            width, height = viewport[0], viewport[1]
            self.assertEqual(page.locator(".editor").get_attribute("data-layout"), layout)
            page.click("[data-diagnostics-toggle]")
            listing = page.locator("[data-diagnostics-list]")
            self.assertGreaterEqual(page.locator("[data-diagnostic]").count(), 60)
            self.assertTrue(listing.evaluate("el => el.scrollHeight > el.clientHeight"))
            for chip in ("save", "sync", "index", "partition"):
                box = page.locator(f'[data-chip="{chip}"]').bounding_box()
                self.assertIsNotNone(box)
                self.assertGreaterEqual(box["x"], 0)
                self.assertLessEqual(box["x"] + box["width"], width + 0.5)
                self.assertLessEqual(box["y"] + box["height"], height + 0.5)
            self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width)
            if layout == "drawers":
                self.assertEqual(page.locator("[data-drawer-toggle]").count(), 2)
                page.click('[data-drawer-toggle="nav"]')
            else:
                self.assertEqual(page.locator("[data-drawer-toggle]").count(), 0)
            row = page.locator(f'[data-tree="location:{synthetic.BARE_LOCATION_ID}"]')
            self.assertTrue(row.is_visible())
            self.assertTrue(row.evaluate("el => el.scrollWidth <= el.clientWidth + 1"))
            nav = page.locator('[data-region="nav"]').bounding_box()
            self.assertLessEqual(nav["x"] + nav["width"], width + 0.5)
            page.context.close()
        self.assertEqual(self.posts, [])

    def test_keyboard_only_workflow_in_chromium(self):
        self.keyboard_workflow()


class MapEditorAccessibilityFirefoxTest(_AccessibilityBrowser):
    BROWSER = "firefox"

    def test_keyboard_only_workflow_in_firefox(self):
        self.keyboard_workflow()


if __name__ == "__main__":
    unittest.main()
