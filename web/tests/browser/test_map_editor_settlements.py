"""Settlement tools of the map editor in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``) against a fresh synthetic workspace and
drives the built page with real pointer and keyboard input. Assertions read
the source files on disk and the service's workspace state: which document
changed, how many commands were posted, which IDs and authored directions
survived, and what the core derived. Shipped copy is never asserted.
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
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
NEW_MAP = "content/maps/settlements/wild_camp.yaml"
GATE = f"settlement_node:{TOWN}:gate"
YARD = f"settlement_node:{TOWN}:yard"
BACK_ROAD = f"road:{TOWN}:yard>gate"


class MapEditorSettlementBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-settlement-browser-"))
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

    def open(self, viewport=REFERENCE, *, settlement=True):
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        if settlement:
            page.click('[data-domain-tab="settlement"]')
            page.locator(f'[data-qualified-ref="{YARD}"]').wait_for()
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

    def data(self, document: str = SETTLEMENT):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    def directions(self) -> dict:
        return {(road["source"], road["destination"]): road["direction"] for road in self.data()["roads"]}

    def drag(self, page, locator, dx: float, dy: float) -> None:
        box = locator.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x + dx * step / 5, y + dy * step / 5)
        page.mouse.up()

    # -- tests -----------------------------------------------------------
    def test_dragging_a_referenced_node_is_one_command_that_keeps_its_relations(self):
        self.start()
        page = self.open()
        page.click(f'[data-object="{YARD}"]')
        relations = page.locator("[data-relation]").all_inner_texts()
        self.assertTrue(any("synthetic_hall" in text for text in relations), relations)
        directions = self.directions()
        self.drag(page, page.locator(f'[data-qualified-ref="{YARD}"]'), 80, 40)
        self.wait_for(lambda: self.data()["nodes"]["yard"]["x_m"] != 300, "the release did not save the node")
        self.settle(page)
        self.assertEqual(self.names(), ["move_nodes"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        self.assertEqual(self.directions(), directions)
        state = self.editor.workspace_state()
        self.assertEqual([row for row in state["diagnostics"] if row["category"] == "structure"], [])
        self.assertEqual(state["world"]["interiors"][0]["exterior"]["node"], "yard")
        # The inspector still names the same node and lists the same relations.
        self.assertEqual(page.locator("[data-inspector-ref]").inner_text(), YARD)
        self.wait_for(lambda: len(page.locator("[data-relation]").all_inner_texts()) == len(relations),
                      "the relations changed after the move")
        # A typed position is a second command on the same identity.
        field = page.locator('[data-field-input="node-position-0"]')
        field.fill("250")
        field.press("Enter")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["x_m"] == 250, "the numeric entry was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_nodes", "move_nodes"])
        self.assertEqual(self.directions(), directions)
        # Undo (outside the field, whose own undo applies) returns the
        # previous position, as one step.
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("Control+z")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["x_m"] != 250, "undo did not restore the drag position")

    def test_the_road_tool_creates_a_two_way_street_in_one_command(self):
        self.start()
        page = self.open()
        # Place a node with the node tool (N), completing its form.
        page.keyboard.press("n")
        canvas = page.locator('[data-region="canvas"]').bounding_box()
        page.mouse.click(canvas["x"] + canvas["width"] * 0.85, canvas["y"] + canvas["height"] * 0.8)
        page.locator('[data-creation="node"]').wait_for()
        page.fill('[data-creation-field="id"]', "well")
        page.fill('[data-creation-field="key"]', "Well")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: "well" in self.data()["nodes"], "the node was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_node"])
        # Road tool (R): source, then destination, then explicit directions.
        page.keyboard.press("Escape")
        page.keyboard.press("r")
        page.click(f'[data-qualified-ref="{GATE}"]')
        page.click(f'[data-qualified-ref="settlement_node:{TOWN}:well"]')
        form = page.locator('[data-creation="road"]')
        form.wait_for()
        page.click("[data-creation-submit]")
        self.assertEqual(page.locator('[data-field-error="creation"]').count(), 1)
        page.select_option('[data-creation-field="direction"]', "e")
        page.check('[data-creation-field="two_way"]')
        page.click("[data-creation-submit]")
        self.assertEqual(page.locator('[data-field-error="creation"]').count(), 1)
        self.assertEqual(self.names(), ["create_node"])
        page.select_option('[data-creation-field="return_direction"]', "w")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: ("gate", "well") in self.directions(), "the road was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_node", "create_road"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        directions = self.directions()
        self.assertEqual((directions[("gate", "well")], directions[("well", "gate")]), ("e", "w"))
        lengths = {row["id"]: row["length_m"] for row in self.editor.workspace_state()["world"]["settlements"][0]["roads"]}
        self.assertIsNotNone(lengths["gate>well"])
        self.assertEqual(lengths["gate>well"], lengths["well>gate"])
        # Two directed rows on the source node: outgoing and incoming.
        page.keyboard.press("Escape")
        page.click(f'[data-object="{GATE}"]')
        rows = page.locator(f'[data-select-road="road:{TOWN}:gate>well"], [data-select-road="road:{TOWN}:well>gate"]')
        self.wait_for(lambda: rows.count() == 2, "both directed rows were not listed")

    def test_prototype_name_and_scene_fields_by_keyboard(self):
        self.start()
        page = self.open()
        row = page.locator(f'[data-object="{YARD}"]')
        row.focus()
        page.keyboard.press("Enter")
        name = page.locator('[data-field-input="node-key"]')
        name.wait_for()
        name.fill("Courtyard")
        name.press("Enter")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["key"] == "Courtyard", "the name was not saved")
        self.settle(page)
        page.select_option('[data-field-input="node-prototype_parent"]', "anchor_room")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["prototype_parent"] == "anchor_room", "prototype not saved")
        self.settle(page)
        # The anchor key travelled with the prototype as the core requires.
        self.assertEqual(self.data()["nodes"]["yard"]["anchor_key"], synthetic.LOCATION_ID)
        scene = page.locator('[data-field-input="node-scene_archetype"]')
        scene.fill("city_street")
        scene.press("Enter")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["scene_archetype"] == "city_street", "scene not saved")
        self.settle(page)
        # No index: the scene is reported unavailable, never valid.
        self.wait_for(lambda: page.locator('[data-scene-status="unavailable"]').count() == 1, "scene status missing")
        self.assertEqual(self.names(), ["set_node_fields", "set_node_fields", "set_node_fields"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        self.assertEqual(set(self.data()["nodes"]), {"gate", "yard"})

    def test_list_multi_selection_moves_as_one_command_and_cross_document_is_inspect_only(self):
        self.start()
        page = self.open()
        page.click(f'[data-object="{GATE}"]')
        page.click(f'[data-object="{YARD}"]', modifiers=["Control"])
        self.assertEqual(page.locator("[data-selection-member]").count(), 2)
        self.assertEqual(page.locator('[data-mixed="prototype_parent"]').inner_text(), "—")
        before = {node_id: (node["x_m"], node["y_m"]) for node_id, node in self.data()["nodes"].items()}
        page.locator(f'[data-object="{YARD}"]').focus()
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(lambda: self.data()["nodes"]["gate"]["x_m"] != before["gate"][0], "the nudge was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_nodes"])
        nodes = self.data()["nodes"]
        self.assertEqual(nodes["gate"]["x_m"] - before["gate"][0], nodes["yard"]["x_m"] - before["yard"][0])
        page.fill('[data-group-field="y"]', "-40")
        page.click("[data-group-submit]")
        self.wait_for(lambda: self.data()["nodes"]["yard"]["y_m"] == before["yard"][1] - 40, "group delta not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_nodes", "move_nodes"])
        self.assertEqual(self.changed(), {SETTLEMENT})
        # Adding a room of an interior makes the selection cross-document.
        page.fill("[data-search]", "前廳")
        page.click(f'[data-search-result="interior_room:{synthetic.INTERIOR_ID}:front"]', modifiers=["Control"])
        self.assertEqual(page.locator("[data-selection-reason]").count(), 1)
        self.assertEqual(page.locator("[data-group-move]").count(), 0)
        page.keyboard.press("Delete")
        self.assertEqual(page.locator('[data-delete-refusal="cross-document"]').count(), 1)
        self.assertEqual(self.names(), ["move_nodes", "move_nodes"])

    def test_a_referenced_node_refuses_deletion_and_an_unreferenced_one_is_deleted(self):
        self.start(synthetic.write_reference_context)
        page = self.open()
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Delete")
        refusal = page.locator('[data-delete-refusal="referenced"]')
        refusal.wait_for()
        self.assertGreaterEqual(page.locator("[data-refusal-internal]").count(), 3)
        self.assertEqual(self.posts, [])
        # Removing the referenced roads is explicit; nothing cascades.
        page.keyboard.press("Escape")
        page.click(f'[data-object="{BACK_ROAD}"]')
        self.assertEqual(page.locator("[data-road-length]").count(), 1)
        page.click('[data-action="delete-road"]')
        self.wait_for(lambda: ("yard", "gate") not in self.directions(), "the road was not deleted")
        self.settle(page)
        self.assertEqual(self.names(), ["delete_road"])
        self.assertIn("yard", self.data()["nodes"])
        # A new unconnected node is deleted with one command.
        page.keyboard.press("n")
        canvas = page.locator('[data-region="canvas"]').bounding_box()
        page.mouse.click(canvas["x"] + canvas["width"] * 0.85, canvas["y"] + canvas["height"] * 0.8)
        # An existing ID is refused in the form, with no command posted.
        page.fill('[data-creation-field="id"]', "yard")
        page.fill('[data-creation-field="key"]', "Shed")
        page.press('[data-creation-field="key"]', "Enter")
        self.assertEqual(page.locator(f'[data-field-error="creation"] [data-follow="{YARD}"]').count(), 1)
        self.assertEqual(self.names(), ["delete_road"])
        page.fill('[data-creation-field="id"]', "shed")
        page.press('[data-creation-field="key"]', "Enter")
        self.wait_for(lambda: "shed" in self.data()["nodes"], "the node was not created")
        self.settle(page)
        page.keyboard.press("Escape")
        page.click(f'[data-object="settlement_node:{TOWN}:shed"]')
        page.keyboard.press("Delete")
        self.wait_for(lambda: "shed" not in self.data()["nodes"], "the unreferenced node was not deleted")
        self.settle(page)
        self.assertEqual(self.names(), ["delete_road", "create_node", "delete_nodes"])
        self.assertEqual(self.changed(), {SETTLEMENT})

    def test_a_bend_drag_is_one_command_and_keeps_the_direction_at_the_large_viewport(self):
        self.start()
        page = self.open(LARGE)
        page.click(f'[data-object="{BACK_ROAD}"]')
        self.assertGreaterEqual(page.locator("[data-direction-chevron]").count(), 1)
        handle = page.locator(f'[data-qualified-ref="{BACK_ROAD}#0"][data-kind="handle"]')
        handle.wait_for()
        directions = self.directions()
        self.drag(page, handle, -60, 0)
        self.wait_for(lambda: self.data()["roads"][1]["bends"][0]["x_m"] != 300, "the bend drag was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["move_bend"])
        self.assertEqual(self.directions(), directions)
        # The dragged bend is selected: its inspector inserts a neighbour.
        self.assertEqual(page.locator("[data-inspector-ref]").inner_text(), f"{BACK_ROAD}#0")
        page.click('[data-action="insert-bend-after"]')
        self.wait_for(lambda: len(self.data()["roads"][1]["bends"]) == 2, "the bend was not inserted")
        self.settle(page)
        self.assertEqual(self.names(), ["move_bend", "insert_bend"])
        self.assertEqual(self.changed(), {SETTLEMENT})

    def test_a_new_local_map_from_a_location_is_empty_and_unfinished(self):
        self.start()
        page = self.open(settlement=False)
        page.click(f'[data-object="location:{synthetic.BARE_LOCATION_ID}"]')
        page.click('[data-action="create-local-map"]')
        page.fill('[data-map-field="id"]', "wild_camp")
        page.click("[data-map-submit]")
        self.wait_for(lambda: (self.workspace / NEW_MAP).exists(), "the local map was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_settlement"])
        self.assertEqual(self.changed(), {NEW_MAP})
        self.wait_for(
            lambda: page.locator('[data-domain-tab="settlement"]').get_attribute("aria-pressed") == "true",
            "the new local map did not open",
        )
        self.wait_for(lambda: page.locator("[data-unfinished-map]").count() == 1, "the map was not shown unfinished")
        self.assertEqual(page.locator('[data-kind="node"]').count(), 0)
        codes = {row["code"] for row in self.editor.workspace_state()["diagnostics"]}
        self.assertIn("empty_graph", codes)
