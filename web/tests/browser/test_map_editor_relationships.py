"""Entrance relationships of the map editor in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``) against a fresh synthetic workspace and
drives the built page with real pointer and keyboard input. Assertions read
the source files on disk and the posted command names: which one document
changed, that a two-way meaning is one record, that navigation keeps its
return context and that removing a reference and deleting its target are
separate operations. Shipped copy is never asserted.

The synthetic settlement ``synthetic_town`` has nodes ``gate`` and ``yard``,
one wilderness gate ``n`` and the starting-room entry onto ``gate``; the
interior ``synthetic_hall`` (rooms ``front``, ``back``) opens ``front`` onto
``yard`` through its exterior.
"""

from __future__ import annotations

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

TOWN = synthetic.SETTLEMENT_ID
HALL = synthetic.INTERIOR_ID
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
ANNEX = "content/maps/interiors/synthetic_annex.yaml"
YARD = f"settlement_node:{TOWN}:yard"
GATE = f"settlement_node:{TOWN}:gate"
FRONT = f"interior_room:{HALL}:front"
BACK = f"interior_room:{HALL}:back"
EXTERIOR = f"exterior:{HALL}"


def add_annex(root: Path) -> None:
    annex = synthetic.interior_data()
    annex.update(id="synthetic_annex", connections=[], exterior=None,
                 rooms={"annex_lobby": dict(annex["rooms"]["front"], name_zh="別館大廳")})
    (root / ANNEX).write_text(synthetic.yaml_text(annex), encoding="utf-8")


def free_yard(root: Path) -> None:
    """A current index, and the district landmark moved off ``yard``."""

    synthetic.write_reference_context(root)
    districts = synthetic.districts_data()
    districts["districts"]["synthetic_district"]["landmark"] = {
        "domain": "wilderness_cell", "map_id": None, "object_id": None, "cell": {"cell_x": 20, "cell_y": 30}}
    (root / "content/maps/districts.yaml").write_text(synthetic.yaml_text(districts), encoding="utf-8")


class MapEditorRelationshipBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-relationship-browser-"))
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

    def open(self, domain: str, viewport=REFERENCE):
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        page.click(f'[data-domain-tab="{domain}"]')
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

    def inspected(self, page):
        locator = page.locator("[data-inspector-ref]")
        return locator.text_content() if locator.count() else None

    def domain(self, page):
        tabs = page.locator("[data-domain-tab]")
        for index in range(tabs.count()):
            if tabs.nth(index).get_attribute("aria-pressed") == "true":
                return tabs.nth(index).get_attribute("data-domain-tab")
        return None

    # -- tests -----------------------------------------------------------
    def test_the_settlement_entrance_tool_adds_a_gate_with_one_settlement_write(self):
        self.start()
        page = self.open("settlement")
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("e")
        page.click(f'[data-object="{YARD}"]')
        page.locator('[data-creation="entrance"]').wait_for()
        self.assertEqual(page.locator('[data-creation-field="node"]').input_value(), YARD)
        page.click("[data-creation-submit]")
        # The return direction is required and never inferred: nothing sent.
        self.assertEqual(page.locator('[data-field-error="creation"]').count(), 1)
        page.select_option('[data-creation-field="direction"]', "e")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: len(self.data(SETTLEMENT)["wilderness_entry"]["gates"]) == 2, "the gate was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_wilderness_gate"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        self.wait_for(lambda: self.inspected(page) == f"gate:{TOWN}:e", "the new gate is not selected")
        # The relationship names its one owning record and both endpoints.
        self.assertEqual(page.locator('[data-endpoint="node"] [data-follow]').get_attribute("data-follow"), YARD)

    def test_the_exterior_card_leads_to_the_other_end_and_alt_left_returns(self):
        self.start()
        page = self.open("interior")
        page.click(f'[data-qualified-ref="{EXTERIOR}"]')
        self.wait_for(lambda: self.inspected(page) == EXTERIOR, "the exterior card did not select the relationship")
        self.assertEqual(page.locator('[data-endpoint="room"] [data-follow]').get_attribute("data-follow"), FRONT)
        page.click('[data-action="other-end"]')
        self.wait_for(lambda: self.inspected(page) == YARD, "前往另一端 did not reach the settlement node")
        self.assertEqual(self.domain(page), "settlement")
        # The node lists the incoming exterior, linked to the relationship.
        self.assertEqual(page.locator(f'[data-relation="in"] [data-follow="{EXTERIOR}"]').count(), 1)
        self.assertEqual(page.locator("[data-return]").count(), 1)
        page.keyboard.press("Alt+ArrowLeft")
        self.wait_for(lambda: self.inspected(page) == EXTERIOR, "Alt+Left did not return to the relationship")
        self.assertEqual(self.domain(page), "interior")
        self.assertEqual(self.names(), [])
        self.assertEqual(self.changed(), set())

    def test_changing_an_endpoint_with_the_selector_by_keyboard_writes_the_qualified_id(self):
        self.start()
        page = self.open("interior", LARGE)
        page.locator(f'[data-object="{EXTERIOR}"]').focus()
        page.keyboard.press("Enter")
        trigger = page.locator('[data-change-endpoint="node"]')
        trigger.wait_for()
        trigger.focus()
        page.keyboard.press("Enter")
        query = page.locator('[data-selector="node"] [data-selector-query]')
        query.wait_for()
        # Single-key shortcuts stay quiet while typing in the selector.
        page.keyboard.type("gate")
        self.assertEqual(page.locator('[data-selector="node"] [data-selector-choice]').first.get_attribute(
            "data-selector-choice"), GATE)
        page.keyboard.press("Enter")
        self.wait_for(lambda: self.data(INTERIOR)["exterior"]["node"] == "gate", "the endpoint was not changed")
        self.settle(page)
        self.assertEqual(self.names(), ["set_exterior"])
        self.assertEqual(self.changed(), {INTERIOR})
        exterior = self.data(INTERIOR)["exterior"]
        self.assertEqual((exterior["settlement"], exterior["room"]), (TOWN, "front"))
        # Escape closes a reopened selector and returns focus to its trigger.
        page.click('[data-change-endpoint="node"]')
        page.locator('[data-selector="node"] [data-selector-query]').wait_for()
        page.keyboard.press("Escape")
        self.wait_for(lambda: page.locator("[data-object-selector]").count() == 0, "Escape did not close the selector")
        self.assertEqual(page.evaluate("() => document.activeElement?.dataset?.changeEndpoint"), "node")
        self.assertEqual(self.names(), ["set_exterior"])

    def test_the_interior_entrance_tool_creates_a_two_way_link_as_one_record(self):
        self.start(add_annex)
        page = self.open("interior")
        page.select_option(".nav__map-select", HALL)
        page.locator(f'[data-object="{BACK}"]').wait_for()
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("e")
        page.click(f'[data-object="{BACK}"]')
        page.locator('[data-creation="entrance"]').wait_for()
        page.check('[data-creation-field="kind-link"]')
        # Enter on the focused 選擇… button opens the selector; it never submits the form.
        page.locator('[data-creation-choose="target"]').focus()
        page.keyboard.press("Enter")
        page.locator('[data-selector="creation-target"] [data-selector-query]').wait_for()
        self.assertEqual(self.names(), [])
        page.locator('[data-selector="creation-target"] [data-selector-query]').fill("annex_lobby")
        page.click('[data-selector-choice="interior_room:synthetic_annex:annex_lobby"]')
        page.fill('[data-creation-field="label"]', "passage")
        page.check('[data-creation-field="two_way"]')
        page.fill('[data-creation-field="return_label"]', "hall")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: self.data(INTERIOR)["interior_links"], "the link was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_interior_link"])
        self.assertEqual(self.changed(), {INTERIOR})
        self.assertEqual(self.data(INTERIOR)["interior_links"], [{
            "source_room": "back", "target_interior": "synthetic_annex", "target_room": "annex_lobby",
            "label": "passage", "return_label": "hall"}])
        # 前往另一端 opens the target interior; the annex document was not written.
        page.click('[data-action="other-end"]')
        self.wait_for(lambda: self.inspected(page) == "interior_room:synthetic_annex:annex_lobby",
                      "前往另一端 did not reach the target room")

    def test_a_referenced_node_locates_its_exterior_which_is_removed_before_the_node(self):
        self.start(free_yard)
        page = self.open("settlement")
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Delete")
        page.locator('[data-delete-refusal="referenced"]').wait_for()
        self.assertEqual(self.names(), [])
        page.click(f'[data-refusal-internal] [data-follow="{EXTERIOR}"]')
        self.wait_for(lambda: self.inspected(page) == EXTERIOR, "the exterior was not located")
        page.click('[data-action="delete-relationship"]')
        self.wait_for(lambda: self.data(INTERIOR)["exterior"] is None, "the exterior was not removed")
        self.settle(page)
        self.assertEqual(self.names(), ["set_exterior"])
        self.assertEqual(self.changed(), {INTERIOR})
        self.assertEqual(list(self.data(INTERIOR)["rooms"]), ["front", "back"])
        page.keyboard.press("Alt+ArrowLeft")
        self.wait_for(lambda: self.inspected(page) == YARD, "Alt+Left did not return to the node")
        for road in (f"road:{TOWN}:gate>yard", f"road:{TOWN}:yard>gate"):
            page.click(f'[data-object="{road}"]')
            page.keyboard.press("Delete")
            self.wait_for(lambda road=road: road.split(":")[-1] not in
                          {f"{r['source']}>{r['destination']}" for r in self.data(SETTLEMENT)["roads"]},
                          "the road was not deleted")
            self.settle(page)
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Delete")
        self.wait_for(lambda: "yard" not in self.data(SETTLEMENT)["nodes"], "the node was not deleted")
        self.settle(page)
        self.assertEqual(self.names(), ["set_exterior", "delete_road", "delete_road", "delete_nodes"])
        self.assertEqual(self.changed(), {INTERIOR, SETTLEMENT})

    def test_an_unavailable_index_refuses_deletion_at_the_action_while_entrance_edits_save(self):
        self.start()
        page = self.open("interior")
        page.click(f'[data-object="{EXTERIOR}"]')
        field = page.locator('[data-field-input="exterior-doorway_key"]')
        field.wait_for()
        field.fill("Side door")
        field.press("Enter")
        self.wait_for(lambda: self.data(INTERIOR)["exterior"]["doorway_key"] == "Side door", "the edit was not saved")
        self.settle(page)
        page.fill("[data-search]", synthetic.BARE_LOCATION_ID)
        page.click(f'[data-search-result="location:{synthetic.BARE_LOCATION_ID}"]')
        page.click('[data-action="delete"]')
        page.locator('[data-delete-refusal="index-unavailable"]').wait_for()
        self.assertEqual(self.names(), ["set_exterior"])
        self.assertEqual(self.changed(), {INTERIOR})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
