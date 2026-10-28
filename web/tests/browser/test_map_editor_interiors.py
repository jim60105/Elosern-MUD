"""Interior tools of the map editor in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment, empty ``PATH``) against a fresh synthetic workspace and
drives the built page with real pointer and keyboard input. Assertions read
the source and layout files on disk and the service's workspace state: which
document changed, how many commands were posted, which IDs survived and that
no coordinate or distance entered a source. Shipped copy is never asserted.

The synthetic interior ``synthetic_hall`` has rooms ``front`` and ``back``
joined both ways (``in``/``out``) and its exterior opens ``front``.
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

HALL = synthetic.INTERIOR_ID
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
LAYOUT = f"content/map-editor-layouts/{HALL}.yaml"
FRONT = f"interior_room:{HALL}:front"
BACK = f"interior_room:{HALL}:back"


class MapEditorInteriorBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-interior-browser-"))
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

    def open(self, viewport=REFERENCE):
        context = self._browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        page.click('[data-domain-tab="interior"]')
        page.locator(f'[data-qualified-ref="{FRONT}"]').wait_for()
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

    def data(self, document: str = INTERIOR):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    def triples(self) -> set[tuple[str, str, str]]:
        return {(c["source"], c["destination"], c["label"]) for c in self.data()["connections"]}

    def drag(self, page, locator, dx: float, dy: float) -> None:
        box = locator.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x + dx * step / 5, y + dy * step / 5)
        page.mouse.up()

    # -- tests -----------------------------------------------------------
    def test_the_room_tool_creates_a_standalone_room_without_a_layout_write(self):
        self.start()
        page = self.open()
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("n")
        page.locator('[data-creation="room"]').wait_for()
        # Selecting a room while the form is open keeps what was typed.
        page.fill('[data-creation-field="name_zh"]', "草稿名")
        page.click(f'[data-object="{BACK}"]')
        self.assertEqual(page.locator('[data-creation-field="name_zh"]').input_value(), "草稿名")
        # A valid form cancelled with Enter must not submit before the native
        # button click. Cancellation returns to 選取, and N opens it again.
        page.fill('[data-creation-field="id"]', "cancelled_room")
        page.locator("[data-creation-submit]").press("Enter")
        self.assertEqual(page.locator('[data-creation="room"]').count(), 1)
        self.assertEqual(self.names(), [])
        page.locator("[data-creation-cancel]").press("Enter")
        self.assertEqual(page.locator('[data-creation="room"]').count(), 0)
        self.assertEqual(self.names(), [])
        self.assertEqual(self.changed(), set())
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("n")
        page.locator('[data-creation="room"]').wait_for()
        self.assertEqual(self.names(), [])
        page.fill('[data-creation-field="name_zh"]', "")
        page.fill('[data-creation-field="id"]', "store")
        page.click("[data-creation-submit]")
        # The name is required: nothing is sent yet.
        self.assertEqual(page.locator('[data-field-error="creation"]').count(), 1)
        page.fill('[data-creation-field="name_zh"]', "倉庫")
        page.locator('[data-creation-field="name_zh"]').press("Enter")
        self.wait_for(lambda: "store" in self.data()["rooms"], "the room was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_room"])
        self.assertEqual(self.changed(), {INTERIOR})
        self.assertFalse((self.workspace / "content/map-editor-layouts").exists())
        # The new room is selected and shows that nothing joins a service to it.
        self.assertEqual(page.locator("[data-inspector-ref]").inner_text(), f"interior_room:{HALL}:store")
        self.assertEqual(page.locator('[data-service-identity="none"]').count(), 1)
        # A later, distinct drag is the only layout write.
        self.drag(page, page.locator(f'[data-qualified-ref="interior_room:{HALL}:store"]'), 0, -150)
        self.wait_for(lambda: (self.workspace / LAYOUT).exists(), "the drag did not save a layout")
        self.settle(page)
        self.assertEqual(self.names(), ["create_room", "move_interior_layout"])
        self.assertEqual(self.changed(), {INTERIOR, LAYOUT})
        self.assertEqual(list(self.data(LAYOUT)["positions"]), ["store"])
        self.assertNotIn("x", self.data()["rooms"]["store"])

    def test_the_connection_tool_creates_a_two_way_pair_in_one_command_and_undo_removes_it(self):
        self.start()
        page = self.open()
        before = (self.workspace / INTERIOR).read_bytes()
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("r")
        page.click(f'[data-qualified-ref="{BACK}"]')
        page.click(f'[data-qualified-ref="{FRONT}"]')
        page.locator('[data-creation="connection"]').wait_for()
        page.fill('[data-creation-field="label"]', "門 / 前")
        page.check('[data-creation-field="two_way"]')
        page.click("[data-creation-submit]")
        # The return name is required with 建立雙向.
        self.assertEqual(page.locator('[data-field-error="creation"]').count(), 1)
        self.assertEqual(self.names(), [])
        page.fill('[data-creation-field="return_label"]', "門 / 後")
        page.locator('[data-creation-field="two_way"]').press("Enter")
        self.assertEqual(page.locator('[data-creation="connection"]').count(), 1)
        self.assertEqual(self.names(), [])
        page.click("[data-creation-submit]")
        self.wait_for(lambda: ("back", "front", "門 / 前") in self.triples(), "the connection was not created")
        self.settle(page)
        self.assertEqual(self.names(), ["create_connection"])
        self.assertEqual(self.changed(), {INTERIOR})
        self.assertIn(("front", "back", "門 / 後"), self.triples())
        # The new connection is selected: its canvas link is selectable and highlighted.
        self.wait_for(lambda: page.locator(".map-link--selected").count() == 1, "the new connection is not selected")
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("Control+z")
        self.wait_for(lambda: (self.workspace / INTERIOR).read_bytes() == before, "one undo did not remove both")
        self.settle(page)
        self.assertEqual(self.names(), ["create_connection", "undo"])

    def test_room_fields_by_keyboard_keep_the_id_and_a_connection_is_relabelled(self):
        self.start()
        page = self.open()
        row = page.locator(f'[data-object="{BACK}"]')
        row.focus()
        page.keyboard.press("Enter")
        name = page.locator('[data-field-input="room-name_zh"]')
        name.wait_for()
        name.fill("內室")
        name.press("Enter")
        self.wait_for(lambda: self.data()["rooms"]["back"]["name_zh"] == "內室", "the name was not saved")
        self.settle(page)
        description = page.locator('[data-field-input="room-desc_zh"]')
        description.fill("新的描述")
        description.press("Control+Enter")
        self.wait_for(lambda: self.data()["rooms"]["back"]["desc_zh"] == "新的描述", "the description was not saved")
        self.settle(page)
        self.assertEqual(list(self.data()["rooms"]), ["front", "back"])
        # Follow the outgoing connection row and relabel it: the selection follows.
        page.click('[data-connection-row="out"] [data-select-connection]')
        label = page.locator('[data-field-input="connection-label"]')
        label.wait_for()
        label.fill("出去")
        label.press("Enter")
        self.wait_for(lambda: ("back", "front", "出去") in self.triples(), "the label was not saved")
        self.settle(page)
        self.wait_for(lambda: page.locator('[data-field-input="connection-label"]').input_value() == "出去",
                      "the selection did not follow the relabelled connection")
        self.assertEqual(self.names(), ["set_room_fields", "set_room_fields", "set_connection"])
        self.assertEqual(self.changed(), {INTERIOR})

    def test_auto_arrange_writes_only_the_layout_and_names_it(self):
        self.start()
        page = self.open(LARGE)
        fingerprint = self.editor.workspace_state()["world"]["fingerprint"]
        page.click('[data-tool="arrange"]')
        self.wait_for(lambda: (self.workspace / LAYOUT).exists(), "the arrangement was not saved")
        self.settle(page)
        self.assertEqual(self.names(), ["arrange_interior_layout"])
        self.assertEqual(self.changed(), {LAYOUT})
        self.assertEqual(set(self.data(LAYOUT)["positions"]), {"front", "back"})
        self.assertEqual(self.editor.workspace_state()["world"]["fingerprint"], fingerprint)
        # The strip names the layout document after a layout save.
        self.assertIn(LAYOUT, page.locator("[data-last-saved]").inner_text())
        # The tool returned to 選取.
        self.assertEqual(page.locator('[data-tool="select"]').get_attribute("aria-pressed"), "true")

    def test_a_referenced_room_refuses_deletion_and_a_connection_is_deleted_directly(self):
        self.start(lambda workspace: synthetic.write_reference_context(workspace))
        page = self.open()
        page.click(f'[data-object="{FRONT}"]')
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("Delete")
        refusal = page.locator('[data-delete-refusal="referenced"]')
        refusal.wait_for()
        self.assertGreaterEqual(page.locator("[data-refusal-internal]").count(), 3)
        self.assertEqual(self.names(), [])
        self.assertEqual(self.changed(), set())
        # `front>back` named `in`: its editor-local reference percent-encodes the name.
        page.click(f'[data-object="connection:{HALL}:front>back/in"]')
        page.click('[data-action="delete-connection"]')
        self.wait_for(lambda: len(self.data()["connections"]) == 1, "the connection was not deleted")
        self.settle(page)
        self.assertEqual(self.names(), ["delete_connection"])
        self.assertEqual(self.changed(), {INTERIOR})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
