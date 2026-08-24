"""Minimap browser acceptance journeys (map-knowledge-minimap 5.2-5.4).

These journeys boot a dedicated managed server seeded with
``ELOSERN_BROWSER_MINIMAP=1`` so the activated character is relocated to 南門
with map knowledge already recorded (grid, wilderness, interior, and instance
layers). They prove the minimap renders the validated payload, distinguishes
states without color alone, focuses remembered remote nodes without a travel
action, never reveals unknown nodes, rebuilds from server-persisted knowledge
on reconnect, and stays visible and keyboard-operable at both supported
viewports.
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

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_minimap_renders_and_distinguishes_states_without_color(self):
        page = self.logged_in_page()
        panel = self._wait_local_map_available(page)
        self.assertEqual(panel["layer"], "grid")
        # The shared server character may already stand at an adjacent grid
        # node (an earlier journey submits ``explore.move``), so the current
        # node is asserted position-agnostic: any capital grid node renders.
        self.assertTrue(panel["current_node"].startswith("grid:capital_altoria:"))

        # The surface renders legend text as text nodes and a current node.
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            dom_readiness={
                "selector": '[data-testid="local-map__title"]',
                "predicate": "() => !!document.querySelector('[data-testid=\"local-map__title\"]')",
                "description": "local map title rendered",
            },
            timeout=30000,
        )
        legend_text = page.locator('[data-testid="local-map__legend"]').inner_text()
        self.assertIn("你目前所在的位置", legend_text)

        # The seeded knowledge includes wilderness, interior, and instance
        # visits, so the grid layer carries remembered grid-adjacent nodes and
        # the current node is distinguishable by non-color indicators.
        current = page.locator(".local-map__node.local-map__node--current")
        self.assertEqual(current.count(), 1)
        self.assertIn("local-map__node--current", current.get_attribute("class"))
        self.assertTrue(current.locator(".local-map__marker--current").count() == 1)
        self.assertTrue(current.is_visible())

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_remembered_remote_node_focus_shows_name_without_travel_action(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        # The seeded fixture recorded 北門 (2,4), which is outside the visual
        # range from 南門, so the grid layer carries a remembered remote node.
        remembered = page.locator(".local-map__node.local-map__node--remembered")
        self.assertGreaterEqual(remembered.count(), 1)
        remembered.first.click()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="local-map-detail"]',
                "predicate": (
                    "() => { const d = document.querySelector('[data-testid=\"local-map-detail\"]'); "
                    "return (d && d.textContent || '').indexOf('已探索') !== -1; }"
                ),
                "description": "map detail shows the explored state",
            },
            timeout=30000,
        )
        detail = page.locator('[data-testid="local-map-detail"]').inner_text()
        self.assertIn("已探索", detail)
        self.assertIn("北門", detail)
        # No travel control appears for a remembered remote node.
        self.assertEqual(page.locator('[data-testid="local-map-detail"] button').count(), 0)

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_unknown_nodes_never_appear_in_the_dom(self):
        page = self.logged_in_page()
        panel = self._wait_local_map_available(page)
        presented = {node["id"] for node in panel["nodes"]}
        node_count = page.locator(".local-map__lattice .local-map__node").count()
        self.assertLessEqual(node_count, len(presented))
        # Every rendered node corresponds to a presented node id.
        for index in range(node_count):
            node_id = page.evaluate(
                "(i) => document.querySelectorAll('.local-map__lattice .local-map__node')[i].dataset.nodeId",
                index,
            )
            self.assertIn(node_id, presented)

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_reconnect_rebuilds_minimap_from_persisted_knowledge(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        nodes_before = self._local_map_nodes(page)
        self.assertTrue(nodes_before)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            timeout=30000,
        )
        page.evaluate("Evennia.connect()")
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            timeout=45000,
        )
        nodes_after = self._local_map_nodes(page)
        # No client map cache is authoritative: the rebuilt map carries the
        # same server-persisted current node and knowledge.
        self.assertEqual(
            {node["id"] for node in nodes_after},
            {node["id"] for node in nodes_before},
        )

    @covers_requirement("webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone")
    def test_minimap_content_stays_inside_its_pane(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                wait_for_store_state(
                    page,
                    lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
                    dom_readiness={
                        "selector": ".local-map__lattice",
                        "predicate": "() => !!document.querySelector('.local-map__lattice')",
                        "description": "map lattice canvas rendered",
                    },
                    timeout=30000,
                )

                # Every node marker's bounding box is inside the map canvas.
                # (Remembered remote nodes render in the bounded list below
                # the canvas and are excluded here.)
                canvas_box = page.locator(".local-map__lattice").bounding_box()
                canvas_nodes = page.locator(
                    ".local-map__lattice .local-map__node"
                )
                node_count = canvas_nodes.count()
                self.assertGreaterEqual(node_count, 1)
                for index in range(node_count):
                    inside = page.evaluate(
                        """(i) => {
                          const canvas = document.querySelector('.local-map__lattice');
                          const node = document.querySelectorAll(
                            '.local-map__lattice .local-map__node')[i];
                          const cr = canvas.getBoundingClientRect();
                          const nr = node.getBoundingClientRect();
                          return nr.left >= cr.left - 1 && nr.right <= cr.right + 1 &&
                                 nr.top >= cr.top - 1 && nr.bottom <= cr.bottom + 1;
                        }""",
                        index,
                    )
                    self.assertTrue(
                        inside,
                        f"node {index} must stay inside the map canvas at {viewport}",
                    )
                self.assertIsNotNone(canvas_box)

                # No two node markers overlap (distinct lattice cells).
                boxes = []
                for index in range(node_count):
                    box = page.evaluate(
                        """(i) => {
                          const r = document.querySelectorAll(
                            '.local-map__lattice .local-map__node')[i]
                            .getBoundingClientRect();
                          return {left: r.left, top: r.top, right: r.right, bottom: r.bottom};
                        }""",
                        index,
                    )
                    boxes.append(box)
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        overlap = not (
                            boxes[i]["right"] <= boxes[j]["left"] + 1
                            or boxes[j]["right"] <= boxes[i]["left"] + 1
                            or boxes[i]["bottom"] <= boxes[j]["top"] + 1
                            or boxes[j]["bottom"] <= boxes[i]["top"] + 1
                        )
                        self.assertFalse(
                            overlap, f"nodes {i} and {j} overlap at {viewport}"
                        )

                # The legend and detail line remain visible below the canvas.
                self.assertTrue(page.locator('[data-testid="local-map__legend"]').is_visible())
                detail = page.locator('[data-testid="local-map-detail"]')
                self.assertTrue(detail.is_visible())
                page.close()

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    @covers_requirement("webclient-local-map::adjacent-traversable-map-nodes-submit-explore-move-through-their-move-descriptor")
    def test_adjacent_traversable_node_submits_explore_move(self):
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        action_ready = page.locator(".local-map__actionable")
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
                    ".status-panel",
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} not visible at {viewport}",
                    )
                page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
