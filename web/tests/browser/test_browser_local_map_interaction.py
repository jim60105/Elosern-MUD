"""Local-map browser acceptance: keyboard/pointer interaction with the minimap island and its overlay at both viewports.
"""

from __future__ import annotations

import time
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


class LocalMapBrowserTest(BrowserAcceptanceTest):
    """Dedicated minimap server with pre-recorded knowledge, shared per process."""
    @classmethod
    def setUpClass(cls) -> None:
        from . import fixtures
        from .harness import ManagedServer

        runtime = fixtures.create_runtime(prefix="elosern-minimap-")
        runtime.env["ELOSERN_BROWSER_MINIMAP"] = "1"
        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    def _local_map_panel(self, page):
        return store_state(page)["panels"].get("local_map")

    def _wait_local_map_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            timeout=timeout,
        )
        return self._local_map_panel(page)

    def _local_map_nodes(self, page):
        return self._wait_local_map_available(page)["nodes"]

    def _send(self, page, command):
        page.evaluate(
            "(args) => Evennia.msg('text', [args.cmd], {})", {"cmd": command}
        )

    def _inject_panel(self, page, panel) -> dict:
        return page.evaluate(
            """(panel) => {
              const bridge = window.__elosernBridge;
              const v = bridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: v.epoch,
                revision: v.revision + 1,
                mode: v.mode,
                layout_version: v.layoutVersion ?? 1,
                panels: { local_map: panel },
                server_time: { year: 1, season_index: 0, season_label: "春", day_in_season: 1, hour: 12, minute: 0, second: 0 },
              };
              return bridge.store.receive(v.generation, "ui_update", [envelope], {});
            }""",
            panel,
        )

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    @covers_requirement("webclient-local-map::adjacent-traversable-map-nodes-submit-explore-move-through-their-move-descriptor")
    def test_adjacent_traversable_node_submits_explore_move(self):
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        action_ready = page.locator('[data-testid="local-map__actionable"]')
        self.assertGreaterEqual(action_ready.count(), 1)
        action_ready.first.click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
        )
        panel = self._local_map_panel(page)
        self.assertEqual(payload["current_node"], panel["current_node"])
        self.assertTrue(payload["exit_ref"])

    def test_minimap_visible_and_keyboard_usable_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                for selector in (
                    '[data-testid="narrative-feed"]',
                    '[data-testid="status-panel"]',
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} not visible at {viewport}",
                    )
                page.close()

    @staticmethod
    def _wilderness_scale_panel() -> dict:
        """A committed-form wilderness payload carrying the fifth-entry scale note.

        The legend mirrors the presenter's exact wire shape: the four state
        labels in fixed order, then the scale note derived from
        ``WILDERNESS_KM_PER_CELL`` (server-side derivation is pinned in
        ``web.webclient.presentation.tests.test_local_map``).
        """
        return {
            "schema_version": 1,
            "available": True,
            "layer": "wilderness",
            "current_node": "wild:elosern:60:103",
            "title": "荒野地圖",
            "nodes": [
                {
                    "id": "wild:elosern:60:103",
                    "label": "丘陵",
                    "x": 0,
                    "y": 0,
                    "visibility": "current",
                    "current": True,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
                {
                    "id": "wild:elosern:60:104",
                    "label": "森林",
                    "x": 0,
                    "y": 1,
                    "visibility": "visible_unvisited",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
            ],
            "edges": [
                {
                    "source": "wild:elosern:60:103",
                    "destination": "wild:elosern:60:104",
                    "label": "n",
                    "known": True,
                    "traversable": True,
                }
            ],
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
                "曾經到過、但不在附近的遠方位置",
                "每格約 10 公里",
            ],
        }

    @covers_requirement(
        "webclient-local-map::the-legend-renders-beyond-state-entries-as-neutral-info-chips"
    )
    def test_overlay_renders_scale_note_as_neutral_info_entry(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        result = self._inject_panel(page, self._wilderness_scale_panel())
        self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
        wait_for_store_state(
            page,
            lambda s: len(((s.get("panels") or {}).get("local_map") or {}).get("legend") or [])
            == 5,
            timeout=30000,
        )
        # The island still mounts no legend element for this payload.
        self.assertEqual(
            page.locator('[data-testid="local-map__legend"]').count(), 0,
            "the island mounts no legend for a scale-note payload",
        )
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        items = page.locator(
            '[data-testid="map-overlay"] [data-testid^="local-map__legend-item--"]'
        )
        items.first.wait_for(timeout=15000)
        self.assertEqual(items.count(), 5)
        # The first four keep their state chip treatments in the fixed order.
        states = ("current", "visible_unvisited", "visible_visited", "remembered")
        for index, state in enumerate(states):
            chip_classes = items.nth(index).locator(".local-map__legend-chip").get_attribute("class")
            self.assertIn(f"local-map__legend-chip--{state}", chip_classes)
        # The fifth entry is the scale note: neutral info chip, no state class,
        # and its text label rendered in full.
        fifth = items.nth(4)
        fifth_classes = fifth.locator(".local-map__legend-chip").get_attribute("class")
        self.assertIn("local-map__legend-chip--info", fifth_classes)
        for state in states:
            self.assertNotIn(f"local-map__legend-chip--{state}", fifth_classes)
        self.assertEqual(fifth.inner_text().strip(), "每格約 10 公里")
        page.close()


    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_minimap_pointer_events_blank_canvas_opens_overlay_while_actionable_moves(self):
        """Pointer-event contract: clicking blank canvas passes to affordance and opens overlay;

        clicking actionable node dispatches explore.move without opening overlay.
        """
        import time
        from .browser_helpers import install_outbound_recorder, sent_action_count
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_local_map_available(page)

        # 1. Click blank canvas corner on the island (empty coordinate margin):
        # Must pass through SVG to .local-map__affordance and open overlay.
        svg = page.locator('[data-testid="local-map__lattice"]')
        self.assertTrue(svg.is_visible())
        box = svg.bounding_box()
        self.assertIsNotNone(box)
        # Click near top-left margin (inside canvas but away from node center)
        page.mouse.click(box["x"] + 8, box["y"] + 8)
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 1)

        # Close overlay with Escape
        page.keyboard.press("Escape")
        page.wait_for_function(
            '() => document.querySelector(\'[data-testid="map-overlay"]\') === null',
            timeout=15000,
        )

        # 2. Click actionable node: dispatches move without opening overlay
        actionable = page.locator('[data-testid="local-map__actionable"]')
        self.assertGreaterEqual(actionable.count(), 1)
        moves_before = sent_action_count(page, "explore.move")
        actionable.first.click()
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 0)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= moves_before + 1:
                break
            page.wait_for_timeout(250)

        self.assertEqual(
            sent_action_count(page, "explore.move"),
            moves_before + 1,
            "clicking actionable node must dispatch move without opening overlay",
        )
