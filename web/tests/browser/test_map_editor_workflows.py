"""Integrated acceptance of the standalone map editor in real browsers.

Every test starts the independently installed editor service as a separate
process (its own locked environment, scrubbed environment, empty ``PATH``, real
directory watcher, no game server, Evennia, Django or database) against a
fresh synthetic workspace and drives the built page in desktop Chromium or
Firefox.

* The authoring workflows chain the domain tools of one session. After every
  operation the test checks that exactly the owning document changed on disk
  and that the map core, run in the editor's own interpreter, reloads the
  files and reads the new value. The final files are then read again by a
  freshly started service.
* The following tests replace the withdrawn AI handoff/return smoke paths
  (frontend design §9): automatic external-change adoption, an external change
  held behind an open draft, the fingerprint-guard race, malformed-to-corrected
  stale recovery with semantic work in progress, and an old tab after a service
  restart, at 1451x790 and 2560x1440.

Assertions read the files, the core reload, the service state and ``data-*``
state hooks on the page; shipped wording is a human review matter
(``docs/design/map-editor-review.md``).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
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
CONTINENT = "content/maps/continent.yaml"
LOCATIONS = "content/maps/locations.yaml"
DISTRICTS = "content/maps/districts.yaml"
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
LAYOUT = f"content/map-editor-layouts/{HALL}.yaml"
RIVER = "continent:waterway:synthetic_river"
YARD = f"settlement_node:{TOWN}:yard"
GATE = f"settlement_node:{TOWN}:gate"
WELL = f"settlement_node:{TOWN}:well"
FRONT = f"interior_room:{HALL}:front"
BACK = f"interior_room:{HALL}:back"
STORE = f"interior_room:{HALL}:store"
EXTERIOR = f"exterior:{HALL}"

# Runs in the editor's interpreter: the core's own discovery and loader over
# the files on disk. A load failure exits non-zero.
_CORE_RELOAD = """
import json, sys
from elosern_map_core import discover_source_documents, load_authoring_world

def plain(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return value

world = load_authoring_world(discover_source_documents(sys.argv[1]))
print(json.dumps({
    "fingerprint": world.fingerprint,
    "documents": {document.relative_path: plain(document.data) for document in world.documents},
    "categories": sorted({item.category for item in world.diagnostics}),
    "codes": sorted({item.code for item in world.diagnostics}),
}))
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replace(path: Path, text: str) -> None:
    """An external writer's atomic replacement (temporary file, then rename)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.external")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _settlement_with_yard_at(x_m: int, **changes) -> str:
    data = synthetic.settlement_data()
    data["nodes"]["yard"]["x_m"] = x_m
    data.update(changes)
    return synthetic.yaml_text(data)


class _EditorBrowser(unittest.TestCase):
    BROWSER = "chromium"
    VIEWPORT = REFERENCE

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="map-editor-acceptance-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.workspace = synthetic.write_workspace(root / "workspace")
        self.port = harness.free_port()
        self.posts: list[str] = []
        self._playwright = sync_playwright().start()
        self._browser = getattr(self._playwright, self.BROWSER).launch(headless=True)
        self.addCleanup(self._close)

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def start(self):
        editor = harness.EditorProcess(self.workspace, port=self.port, frontend_dist=harness.FRONTEND_DIST)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        self.editor = editor
        self.mark()
        return editor

    def open(self, domain: str | None = None, *, permissions=None):
        context = self._browser.new_context(
            viewport={"width": self.VIEWPORT[0], "height": self.VIEWPORT[1]}, permissions=permissions or []
        )
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        self.page = page
        if domain:
            page.click(f'[data-domain-tab="{domain}"]')
        return page

    # -- observation helpers ----------------------------------------------
    def wait_for(self, predicate, message: str, timeout: float = 20) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            # Playwright delivers page events only while one of its calls runs.
            self.page.wait_for_timeout(50)
        self.fail(message)

    def settle(self) -> None:
        self.page.wait_for_function(
            "() => !document.querySelector('[data-chip=\"save\"].chip--busy')", timeout=15000
        )

    def names(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.posts]

    def mark(self) -> None:
        """Start a new step: the tree digest and POST log it is measured from."""

        self.baseline = synthetic.tree_digest(self.workspace)
        self.posts.clear()

    def changed(self) -> set[str]:
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(now) | set(self.baseline) if now.get(path) != self.baseline.get(path)}

    def data(self, document: str):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    def core(self) -> dict:
        """The map core's own reload of the files on disk (editor interpreter)."""

        result = subprocess.run(
            [str(harness.editor_python()), "-I", "-c", _CORE_RELOAD, str(self.workspace)],
            capture_output=True, text=True, env=harness.scrubbed_env(), cwd=harness.PROJECT, timeout=120,
        )
        self.assertEqual(result.returncode, 0, f"the core did not reload the files:\n{result.stderr[-3000:]}")
        return json.loads(result.stdout)

    def step(self, command: str, owner: str) -> dict:
        """One saved operation: one command, only its owner changed, core reloads it."""

        self.settle()
        self.assertEqual(self.names(), [command])
        self.assertEqual(self.changed(), {owner})
        reloaded = self.core()
        self.assertNotIn("structure", reloaded["categories"])
        self.mark()
        return reloaded

    def inspected(self):
        locator = self.page.locator("[data-inspector-ref]")
        return locator.text_content() if locator.count() else None

    def in_viewport(self, selector: str) -> None:
        box = self.page.locator(selector).bounding_box()
        self.assertIsNotNone(box, selector)
        self.assertGreaterEqual(box["x"], 0)
        self.assertGreaterEqual(box["y"], 0)
        self.assertLessEqual(box["x"] + box["width"], self.VIEWPORT[0] + 0.5)
        self.assertLessEqual(box["y"] + box["height"], self.VIEWPORT[1] + 0.5)

    def drag(self, locator, dx: float, dy: float) -> None:
        box = locator.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        self.page.mouse.move(x, y)
        self.page.mouse.down()
        for index in range(1, 6):
            self.page.mouse.move(x + dx * index / 5, y + dy * index / 5)
        self.page.mouse.up()


# -- manual authoring workflows -------------------------------------------------
class _AuthoringWorkflows(_EditorBrowser):
    def continental_workflow(self) -> None:
        self.start()
        page = self.open()
        # 1. A location without a local map, placed with the location tool.
        page.click('[data-tool="location"]')
        canvas = page.locator('[data-region="canvas"]').bounding_box()
        page.mouse.click(canvas["x"] + canvas["width"] * 0.7, canvas["y"] + canvas["height"] * 0.5)
        page.locator('[data-creation="location"]').wait_for()
        page.fill('[data-creation-field="id"]', "synthetic_ruin")
        page.fill('[data-creation-field="display_name_zh"]', "新廢墟")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: "synthetic_ruin" in self.data(LOCATIONS)["locations"], "the location was not created")
        core = self.step("create_location", LOCATIONS)
        self.assertIn("synthetic_ruin", core["documents"][LOCATIONS]["locations"])
        self.assertEqual(
            {path for path in core["documents"] if path.startswith("content/maps/settlements/")}, {SETTLEMENT}
        )
        page.keyboard.press("Escape")
        page.keyboard.press("Escape")

        # 2. A river control point typed in its inspector field.
        page.click(f'[data-object="{RIVER}"]')
        page.click(f'[data-object="{RIVER}#0"]')
        field = page.locator('[data-field-input="point-0"]')
        field.fill("18")
        field.press("Enter")
        self.wait_for(
            lambda: self.data(CONTINENT)["terrain"]["waterways"]["synthetic_river"]["route"][0]["cell_x"] == 18,
            "the control point was not saved",
        )
        core = self.step("move_control_point", CONTINENT)
        route = core["documents"][CONTINENT]["terrain"]["waterways"]["synthetic_river"]["route"]
        self.assertEqual(route[0]["cell_x"], 18)

        # 3. A footprint cell toggled from the keyboard grid.
        page.click('[data-layer="footprint"]')
        page.click(f'[data-object="footprint:{TOWN}"]')
        origin = page.locator('[data-footprint-cell="5,5"]')
        origin.wait_for()
        origin.focus()
        page.keyboard.press("ArrowRight")
        page.keyboard.press("Space")
        self.wait_for(lambda: self.data(SETTLEMENT)["wilderness_entry"]["shape"] == ["##"], "the cell was not saved")
        core = self.step("set_footprint_cell", SETTLEMENT)
        self.assertEqual(core["documents"][SETTLEMENT]["wilderness_entry"]["shape"], ["##"])

        # 4. A district landmark set through its structured fields.
        page.click('[data-object="district:synthetic_district"]')
        page.select_option('[data-landmark-field="domain"]', "wilderness_cell")
        page.fill('[data-landmark-field="x"]', "25")
        page.fill('[data-landmark-field="y"]', "25")
        page.press('[data-landmark-field="y"]', "Enter")
        self.wait_for(
            lambda: self.data(DISTRICTS)["districts"]["synthetic_district"]["landmark"]["domain"] == "wilderness_cell",
            "the landmark was not saved",
        )
        core = self.step("set_district_field", DISTRICTS)
        landmark = core["documents"][DISTRICTS]["districts"]["synthetic_district"]["landmark"]
        self.assertEqual((landmark["domain"], landmark["cell"]), ("wilderness_cell", {"cell_x": 25, "cell_y": 25}))
        final = core["fingerprint"]

        # A freshly started service reads the final files as one current world.
        self.editor.__exit__(None, None, None)
        with harness.EditorProcess(self.workspace) as fresh:
            state = fresh.workspace_state()
        self.assertEqual(state["preview_state"], "current")
        self.assertIn("synthetic_ruin", {row["id"] for row in state["world"]["locations"]})
        self.assertEqual(self.core()["fingerprint"], final)

    def local_map_workflow(self, *, copy_context: bool = False) -> None:
        self.start()
        page = self.open("settlement", permissions=["clipboard-read", "clipboard-write"] if copy_context else None)
        page.locator(f'[data-qualified-ref="{YARD}"]').wait_for()
        # 1. A node placed with the node tool.
        page.keyboard.press("n")
        canvas = page.locator('[data-region="canvas"]').bounding_box()
        page.mouse.click(canvas["x"] + canvas["width"] * 0.85, canvas["y"] + canvas["height"] * 0.8)
        page.locator('[data-creation="node"]').wait_for()
        page.fill('[data-creation-field="id"]', "well")
        page.fill('[data-creation-field="key"]', "Well")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: "well" in self.data(SETTLEMENT)["nodes"], "the node was not created")
        core = self.step("create_node", SETTLEMENT)
        self.assertIn("well", core["documents"][SETTLEMENT]["nodes"])

        # 2. A two-way street with explicit directions: one command, two rows.
        page.keyboard.press("Escape")
        page.keyboard.press("r")
        page.click(f'[data-qualified-ref="{GATE}"]')
        page.click(f'[data-qualified-ref="{WELL}"]')
        page.locator('[data-creation="road"]').wait_for()
        page.select_option('[data-creation-field="direction"]', "e")
        page.check('[data-creation-field="two_way"]')
        page.select_option('[data-creation-field="return_direction"]', "w")
        page.click("[data-creation-submit]")
        self.wait_for(
            lambda: any(road["source"] == "gate" and road["destination"] == "well"
                        for road in self.data(SETTLEMENT)["roads"]),
            "the road was not created",
        )
        core = self.step("create_road", SETTLEMENT)
        directions = {(road["source"], road["destination"]): road["direction"]
                      for road in core["documents"][SETTLEMENT]["roads"]}
        self.assertEqual((directions[("gate", "well")], directions[("well", "gate")]), ("e", "w"))
        lengths = {row["id"]: row["length_m"] for row in self.editor.workspace_state()["world"]["settlements"][0]["roads"]}
        self.assertEqual(lengths["gate>well"], lengths["well>gate"])
        page.keyboard.press("Escape")

        if copy_context:
            # A user gesture copies plain text naming identity, source and the
            # authored metres; nothing secret or local is in it.
            page.click(f'[data-object="{WELL}"]')
            page.locator('[data-region="canvas"]').focus()
            page.evaluate("() => navigator.clipboard.writeText('')")
            page.keyboard.press("Control+c")
            self.wait_for(lambda: page.evaluate("() => navigator.clipboard.readText()") != "", "nothing was copied")
            text = page.evaluate("() => navigator.clipboard.readText()")
            node = self.data(SETTLEMENT)["nodes"]["well"]
            for expected in (WELL, SETTLEMENT, str(node["x_m"]), str(node["y_m"])):
                self.assertIn(expected, text)
            session = self.editor.session()
            for secret in (session["token"], session["session_generation"], str(self.workspace)):
                self.assertNotIn(secret, text)
            self.assertEqual(self.names(), [])
            page.keyboard.press("Escape")

        # 3. A standalone room created with the room tool.
        page.click('[data-domain-tab="interior"]')
        page.locator(f'[data-qualified-ref="{FRONT}"]').wait_for()
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("n")
        page.locator('[data-creation="room"]').wait_for()
        page.fill('[data-creation-field="id"]', "store")
        page.fill('[data-creation-field="name_zh"]', "倉庫")
        page.click("[data-creation-submit]")
        self.wait_for(lambda: "store" in self.data(INTERIOR)["rooms"], "the room was not created")
        core = self.step("create_room", INTERIOR)
        self.assertIn("store", core["documents"][INTERIOR]["rooms"])

        # 4. A two-way connection with both names.
        page.keyboard.press("Escape")
        page.locator('[data-region="canvas"]').focus()
        page.keyboard.press("r")
        page.click(f'[data-qualified-ref="{FRONT}"]')
        page.click(f'[data-qualified-ref="{STORE}"]')
        page.locator('[data-creation="connection"]').wait_for()
        page.fill('[data-creation-field="label"]', "to store")
        page.check('[data-creation-field="two_way"]')
        page.fill('[data-creation-field="return_label"]', "to front")
        page.click("[data-creation-submit]")
        self.wait_for(
            lambda: any(row["destination"] == "store" for row in self.data(INTERIOR)["connections"]),
            "the connection was not created",
        )
        core = self.step("create_connection", INTERIOR)
        triples = {(row["source"], row["destination"], row["label"]) for row in core["documents"][INTERIOR]["connections"]}
        self.assertTrue({("front", "store", "to store"), ("store", "front", "to front")} <= triples)
        page.keyboard.press("Escape")

        # 5. The cross-layer entrance moved to the new node with the keyboard selector.
        page.locator(f'[data-object="{EXTERIOR}"]').focus()
        page.keyboard.press("Enter")
        trigger = page.locator('[data-change-endpoint="node"]')
        trigger.wait_for()
        trigger.focus()
        page.keyboard.press("Enter")
        query = page.locator('[data-selector="node"] [data-selector-query]')
        query.wait_for()
        page.keyboard.type("well")
        self.assertEqual(
            page.locator('[data-selector="node"] [data-selector-choice]').first.get_attribute("data-selector-choice"),
            WELL,
        )
        page.keyboard.press("Enter")
        self.wait_for(lambda: self.data(INTERIOR)["exterior"]["node"] == "well", "the endpoint was not changed")
        core = self.step("set_exterior", INTERIOR)
        self.assertEqual(core["documents"][INTERIOR]["exterior"]["node"], "well")
        world = core["fingerprint"]

        # 6. A layout drag writes only the editor layout; the world is unchanged.
        page.keyboard.press("Escape")
        self.drag(page.locator(f'[data-qualified-ref="{STORE}"]'), 0, -150)
        self.wait_for(lambda: (self.workspace / LAYOUT).exists(), "the drag did not save a layout")
        core = self.step("move_interior_layout", LAYOUT)
        self.assertEqual(core["fingerprint"], world)
        self.assertEqual(list(self.data(LAYOUT)["positions"]), ["store"])


class MapEditorWorkflowsChromiumTest(_AuthoringWorkflows):
    def test_continental_authoring_reloads_in_the_core_after_every_operation(self):
        self.continental_workflow()

    def test_local_map_and_interior_authoring_reloads_in_the_core_after_every_operation(self):
        self.local_map_workflow(copy_context=True)


class MapEditorWorkflowsFirefoxTest(_AuthoringWorkflows):
    BROWSER = "firefox"

    def test_continental_authoring_reloads_in_the_core_after_every_operation(self):
        self.continental_workflow()

    def test_local_map_and_interior_authoring_reloads_in_the_core_after_every_operation(self):
        # Playwright grants no clipboard permissions in Firefox: the copied
        # context is checked in Chromium only.
        self.local_map_workflow()


# -- continuous file following ---------------------------------------------------
class _FollowingAcceptance(_EditorBrowser):
    def open_yard(self):
        page = self.open("settlement")
        page.click(f'[data-object="{YARD}"]')
        page.locator('[data-field-input="node-position-0"]').wait_for()
        return page

    def position(self) -> str:
        return self.page.locator('[data-field-input="node-position-0"]').input_value()

    def adoption_and_draft_hold(self):
        self.start()
        page = self.open_yard()
        settlement = self.workspace / SETTLEMENT
        # Without a draft an external change is adopted at once, selection kept.
        _replace(settlement, _settlement_with_yard_at(320))
        self.wait_for(lambda: self.position() == "320", "the external change was not adopted")
        self.assertEqual(self.inspected(), YARD)
        self.assertEqual(page.locator("[data-banner]").count(), 0)

        # An open draft holds the next change until 載入新版 discards it.
        field = page.locator('[data-field-input="node-position-0"]')
        field.fill("999")
        _replace(settlement, _settlement_with_yard_at(340))
        external = settlement.read_bytes()
        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
        self.in_viewport('[data-banner="external-draft"]')
        self.in_viewport('[data-banner-action="adopt"]')
        self.assertEqual(field.input_value(), "999")
        self.assertEqual(field.get_attribute("data-draft"), "true")
        page.click('[data-banner-action="adopt"]')
        self.wait_for(lambda: page.locator("[data-banner]").count() == 0, "the held change was not loaded")
        self.assertEqual(self.position(), "340")
        self.assertIsNone(page.locator('[data-field-input="node-position-0"]').get_attribute("data-draft"))

        # By keyboard: Esc discards the draft and the held change follows.
        field = page.locator('[data-field-input="node-position-0"]')
        field.fill("777")
        _replace(settlement, _settlement_with_yard_at(360))
        page.wait_for_selector('[data-banner="external-draft"]', timeout=20000)
        field.press("Escape")
        self.wait_for(lambda: self.position() == "360", "the held change did not follow the discarded draft")
        self.assertEqual(page.locator("[data-banner]").count(), 0)
        self.assertEqual(self.names(), [])
        self.assertNotEqual(settlement.read_bytes(), external)
        self.assertEqual(self.data(SETTLEMENT)["nodes"]["yard"]["x_m"], 360)

        # An externally removed selection is cleared and named.
        page.click('[data-domain-tab="interior"]')
        page.click(f'[data-object="{BACK}"]')
        data = synthetic.interior_data()
        del data["rooms"]["back"]
        data["connections"] = []
        _replace(self.workspace / INTERIOR, synthetic.yaml_text(data))
        page.wait_for_selector("[data-selection-removed]", timeout=20000)
        self.assertIn(BACK, page.locator("[data-selection-removed]").text_content())
        self.assertIsNone(self.inspected())
        self.assertEqual(self.names(), [])

    def fingerprint_guard_race(self):
        self.start()
        page = self.open_yard()
        settlement = self.workspace / SETTLEMENT
        observed: dict = {}

        def external_write_first(route):
            # The external writer lands after the page built its command and
            # before the service checks the disk, inside the settle interval.
            if not observed:
                _replace(settlement, _settlement_with_yard_at(330))
                observed["bytes"] = settlement.read_bytes()
                observed["sequence"] = self.editor.workspace_state()["external_change"]["sequence"]
            route.continue_()

        page.route("**/api/commands/*", external_write_first)
        field = page.locator('[data-field-input="node-position-0"]')
        field.fill("250")
        with page.expect_response(lambda response: "/api/commands/" in response.url) as answer:
            field.press("Enter")
        response = answer.value
        # The service had not adopted the external write when the command was
        # admitted, so the document fingerprint guard, not the snapshot check,
        # refused it.
        self.assertEqual(observed["sequence"], 0)
        self.assertEqual((response.status, response.json()["error"]["code"]), (409, "stale_document"))
        self.assertEqual(settlement.read_bytes(), observed["bytes"])
        # The page then follows the external content; nothing merged or retried.
        self.wait_for(lambda: self.position() == "330", "the external write was not followed")
        self.settle()
        page.wait_for_timeout(500)
        self.assertEqual(self.names(), ["move_nodes"])
        self.assertEqual(settlement.read_bytes(), observed["bytes"])

    def stale_to_current_recovery(self):
        self.start()
        page = self.open_yard()
        settlement = self.workspace / SETTLEMENT
        _replace(settlement, "version: 1\nkind: [unclosed\n")
        page.wait_for_selector('[data-preview-state="stale"]', timeout=20000)
        self.in_viewport('[data-banner="stale"]')
        self.assertIn(SETTLEMENT, page.locator('[data-banner="stale"]').text_content())
        # No control is pre-disabled; the service refuses and nothing is written.
        self.mark()
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_selector('[data-banner="save-rejected"]', timeout=15000)
        self.settle()
        self.assertEqual(self.changed(), set())

        # The corrected file is a loadable work in progress: an unreachable
        # landmark is a semantic diagnostic, and the preview is current again.
        roads = [road for road in synthetic.settlement_data()["roads"] if road["source"] != "gate"]
        _replace(settlement, _settlement_with_yard_at(300, roads=roads))
        page.wait_for_selector('[data-preview-state="current"]', timeout=20000)
        self.wait_for(lambda: page.locator("[data-banner]").count() == 0, "the stale banner stayed")
        state = self.editor.workspace_state()
        self.assertEqual(state["preview_state"], "current")
        self.assertIn("unreachable_landmark", {row["code"] for row in state["diagnostics"]})
        self.assertEqual(self.names(), ["move_nodes"])

        # Writes resume on the adopted version.
        self.mark()
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(lambda: self.data(SETTLEMENT)["nodes"]["yard"]["x_m"] == 310, "the write did not resume")
        self.settle()
        self.assertEqual(self.changed(), {SETTLEMENT})
        self.assertEqual(self.data(SETTLEMENT)["roads"], roads)

    def old_tab_after_restart(self):
        self.start()
        page = self.open_yard()
        self.editor.__exit__(None, None, None)
        page.wait_for_selector('[data-connection="disconnected"]', timeout=20000)
        self.start()
        page.wait_for_selector('[data-connection="restarted"]', timeout=20000)
        self.in_viewport('[data-banner="restarted"]')
        # A write from the old session is refused and never replayed.
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Shift+ArrowRight")
        page.wait_for_timeout(1000)
        self.settle()
        self.assertEqual(self.changed(), set())
        attempted = len(self.posts)
        page.click('[data-banner-action="reconnect"]')
        page.wait_for_selector('[data-connection="connected"]', timeout=15000)
        self.wait_for(lambda: page.locator("[data-banner]").count() == 0, "the restart banner stayed")
        page.click(f'[data-object="{YARD}"]')
        page.keyboard.press("Shift+ArrowRight")
        self.wait_for(lambda: self.data(SETTLEMENT)["nodes"]["yard"]["x_m"] == 310, "the fresh write did not land")
        self.settle()
        self.assertEqual(len(self.posts), attempted + 1)
        self.assertEqual(self.changed(), {SETTLEMENT})


# Each concrete class names its own test methods: the browser shard manifest
# owns methods by the class that defines them.
class MapEditorFollowingReferenceChromiumTest(_FollowingAcceptance):
    def test_external_changes_are_adopted_or_held_behind_an_open_draft(self):
        self.adoption_and_draft_hold()

    def test_a_save_racing_an_external_write_is_refused_by_the_fingerprint_guard(self):
        self.fingerprint_guard_race()

    def test_malformed_then_corrected_files_recover_and_semantic_work_in_progress_loads(self):
        self.stale_to_current_recovery()

    def test_an_old_tab_after_a_restart_reads_again_before_writing(self):
        self.old_tab_after_restart()


class MapEditorFollowingLargeChromiumTest(_FollowingAcceptance):
    VIEWPORT = LARGE

    def test_external_changes_are_adopted_or_held_behind_an_open_draft(self):
        self.adoption_and_draft_hold()

    def test_a_save_racing_an_external_write_is_refused_by_the_fingerprint_guard(self):
        self.fingerprint_guard_race()

    def test_malformed_then_corrected_files_recover_and_semantic_work_in_progress_loads(self):
        self.stale_to_current_recovery()

    def test_an_old_tab_after_a_restart_reads_again_before_writing(self):
        self.old_tab_after_restart()


class MapEditorFollowingReferenceFirefoxTest(_FollowingAcceptance):
    BROWSER = "firefox"

    def test_external_changes_are_adopted_or_held_behind_an_open_draft(self):
        self.adoption_and_draft_hold()

    def test_a_save_racing_an_external_write_is_refused_by_the_fingerprint_guard(self):
        self.fingerprint_guard_race()

    def test_malformed_then_corrected_files_recover_and_semantic_work_in_progress_loads(self):
        self.stale_to_current_recovery()

    def test_an_old_tab_after_a_restart_reads_again_before_writing(self):
        self.old_tab_after_restart()


if __name__ == "__main__":
    unittest.main()
