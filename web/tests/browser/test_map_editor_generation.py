"""Explicit partition jobs of the map editor in a real browser.

Each test starts the standalone editor service as a separate process (its own
locked environment with the core generation extra, empty ``PATH``) against a
fresh synthetic workspace and drives the built page with real pointer input.
Assertions read the artifact and source files on disk, the posted routes and
the service's state; shipped copy is never asserted.

- only the 分區 chip and the inspector's regenerate control start a job: a
  control-point drag saves one command and regenerates nothing;
- a successful job draws the derived district outlines; a later relevant
  edit keeps them, marked as older input, until the next explicit job;
- while an OS-observed worker is stopped the page stays usable, a world edit is
  refused by the service and shown, and the chip's cancel keeps the last artifact;
- an external source change during a job ends it as failed, never current.
"""

from __future__ import annotations

import shutil
import tempfile
import time
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright
from ruamel.yaml import YAML

from tests.test_map_editor_generation import held_partition_job

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

CONTINENT = "content/maps/continent.yaml"
DISTRICTS = "content/maps/districts.yaml"
PARTITION = "world/maps/data/district_partition.json"
RIVER = "continent:waterway:synthetic_river"
CHIP = '[data-chip="partition"]'


class MapEditorGenerationBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not (harness.FRONTEND_DIST / "index.html").is_file():
            raise RuntimeError(
                "the editor frontend is not built: pnpm --dir tools/map-editor/frontend install "
                "--frozen-lockfile && pnpm --dir tools/map-editor/frontend run build"
            )

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-generation-browser-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self.addCleanup(self._close)
        self.posts: list[str] = []

    def _close(self) -> None:
        try:
            self._browser.close()
        finally:
            self._playwright.stop()

    def start(self, workspace: Path) -> None:
        self.workspace = workspace
        self.editor = harness.EditorProcess(workspace, frontend_dist=harness.FRONTEND_DIST)
        self.editor.__enter__()
        self.addCleanup(self.editor.__exit__, None, None, None)

    def open(self):
        context = self._browser.new_context(viewport={"width": REFERENCE[0], "height": REFERENCE[1]})
        page = context.new_page()
        page.on("request", lambda request: request.method == "POST" and self.posts.append(request.url))
        page.goto(self.editor.origin + "/")
        page.wait_for_selector('[data-preview-state="current"]', timeout=15000)
        self.page = page
        return page

    def wait_for(self, predicate, message: str, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            self.page.wait_for_timeout(50)
        self.fail(message)

    def chip(self) -> str | None:
        return self.page.locator(CHIP).get_attribute("data-chip-state")

    def names(self) -> list[str]:
        return [url.rsplit("/", 1)[1] for url in self.posts]

    def route(self):
        data = YAML(typ="safe", pure=True).load((self.workspace / CONTINENT).read_text(encoding="utf-8"))
        return data["terrain"]["waterways"]["synthetic_river"]["route"]

    def drag_river_point(self, dy: float) -> None:
        page = self.page
        page.click(f'[data-object="{RIVER}"]')
        handle = page.locator(f'[data-qualified-ref="{RIVER}#0"][data-kind="handle"]')
        handle.wait_for()
        box = handle.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.mouse.move(x, y)
        page.mouse.down()
        for step in range(1, 6):
            page.mouse.move(x, y + dy * step / 5)
        page.mouse.up()

    # -- tests -----------------------------------------------------------
    def test_only_the_explicit_controls_regenerate_and_old_outlines_are_labelled(self):
        self.start(synthetic.write_partitionable_workspace(self.root / "workspace"))
        page = self.open()
        self.assertEqual(self.chip(), "unavailable")
        before = self.route()[0]
        self.drag_river_point(-60)
        self.wait_for(lambda: self.route()[0] != before, "the drag did not save")
        self.wait_for(lambda: self.names() == ["move_control_point"], "the drag posted something else")
        page.wait_for_timeout(500)
        self.assertEqual(self.names(), ["move_control_point"])
        self.assertFalse((self.workspace / PARTITION).exists())
        self.assertEqual(self.editor.workspace_state()["partition_job"]["state"], "idle")

        page.click(CHIP)
        self.wait_for(lambda: self.chip() == "current", "the chip did not regenerate")
        self.assertEqual(self.names(), ["move_control_point", "generate"])
        self.assertTrue((self.workspace / PARTITION).is_file())
        outlines = page.locator('[data-district]')
        self.wait_for(lambda: outlines.count() > 0, "no district outline was drawn")
        self.assertEqual(outlines.evaluate_all("els => els.filter((e) => e.hasAttribute('data-shape-ref')).length"), 0)
        self.assertEqual(page.locator('[data-older-input="true"]').count(), 0)
        self.assertEqual(page.locator("[data-older-partition]").count(), 0)

        published = (self.workspace / PARTITION).read_bytes()
        moved = self.route()[0]
        self.drag_river_point(-40)
        self.wait_for(lambda: self.route()[0] != moved, "the second drag did not save")
        self.wait_for(lambda: self.chip() == "stale", "the chip did not turn stale")
        self.assertEqual((self.workspace / PARTITION).read_bytes(), published)
        self.wait_for(
            lambda: page.locator('[data-older-input="true"]').count() == outlines.count() > 0,
            "the old outlines are not labelled as older input",
        )
        self.assertEqual(page.locator("[data-older-partition]").count(), 1)
        self.assertEqual(page.locator("[data-partition-older]").count(), 1)
        self.assertEqual(self.names(), ["move_control_point", "generate", "move_control_point"])

        page.click('[data-action="partition-generate"]')
        self.wait_for(lambda: self.chip() == "current", "the inspector control did not regenerate")
        self.assertEqual(self.names()[-1], "generate")
        self.assertNotEqual((self.workspace / PARTITION).read_bytes(), published)
        self.wait_for(lambda: page.locator("[data-older-partition]").count() == 0, "the older-input label stayed")

    def test_browsing_then_cancelling_keeps_the_last_artifact_and_refuses_world_edits(self):
        workspace = synthetic.write_slow_partition_workspace(self.root / "workspace")
        prior = b'{"sentinel": "prior artifact"}\n'
        (workspace / PARTITION).parent.mkdir(parents=True, exist_ok=True)
        (workspace / PARTITION).write_bytes(prior)
        self.start(workspace)
        page = self.open()
        page.click(CHIP)
        with held_partition_job(self.editor) as generating:
            self.wait_for(lambda: self.chip() == "generating", "the job did not start")
            # Browsing stays useful: another domain opens and the continent returns.
            page.click('[data-domain-tab="settlement"]')
            self.wait_for(
                lambda: page.locator('[data-domain-tab="settlement"]').get_attribute("aria-pressed") == "true",
                "browsing stalled while generating",
            )
            page.click('[data-domain-tab="continent"]')
            continent = (workspace / CONTINENT).read_bytes()
            self.drag_river_point(-60)
            self.wait_for(lambda: page.locator('[data-banner="partition-generating"]').count() == 1,
                          "the refused world edit was not shown")
            self.assertEqual((workspace / CONTINENT).read_bytes(), continent)
            self.assertEqual(self.chip(), "generating")
            page.click(CHIP)
            self.wait_for(lambda: self.chip() == "cancelled", "the chip did not cancel")
            job = self.editor.workspace_state()["partition_job"]
            self.assertEqual((job["state"], job["job_id"]), ("cancelled", generating["job_id"]))
        self.assertEqual(self.names(), ["generate", "move_control_point", "cancel"])
        self.assertEqual((workspace / PARTITION).read_bytes(), prior)

    def test_an_external_source_change_during_a_job_never_shows_it_current(self):
        workspace = synthetic.write_slow_partition_workspace(self.root / "workspace")
        self.start(workspace)
        page = self.open()
        page.click(CHIP)
        with held_partition_job(self.editor) as generating:
            self.wait_for(lambda: self.chip() == "generating", "the job did not start")
            data = synthetic.partitionable_districts_data()
            data["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
            (workspace / DISTRICTS).write_text(synthetic.yaml_text(data), encoding="utf-8")
            self.wait_for(lambda: self.chip() == "failed", "the invalidated job was not reported as failed")
            job = self.editor.workspace_state()["partition_job"]
            self.assertEqual((job["state"], job["reason"]), ("failed", "inputs_changed"))
            self.assertEqual(job["job_id"], generating["job_id"])
        self.assertFalse((workspace / PARTITION).exists())
        self.assertEqual(page.locator("[data-older-partition]").count(), 0)


if __name__ == "__main__":
    unittest.main()
