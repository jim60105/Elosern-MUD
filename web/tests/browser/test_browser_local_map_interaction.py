"""Local-map browser acceptance: keyboard/pointer interaction with the minimap island and the map drawer it opens, at both viewports.
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
    @covers_requirement("webclient-local-map::minimap-adjacent-movement-remains-bound-to-authoritative-descriptors")
    def test_adjacent_traversable_node_submits_explore_move(self):
        page = self.logged_in_page()
        from .browser_helpers import (
            install_outbound_recorder,
            sent_action_count,
            visible_minimap_actionable,
        )

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        action_ready = visible_minimap_actionable(page)
        self.assertIsNotNone(
            action_ready,
            "the island must show at least one actionable node unclipped",
        )
        action_ready.click()
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

    def _stand_on_gate_room(self, page) -> dict:
        """Teleport onto the fixture's one remembered gateway room and return
        its panel once the island shows the gate's exit stub."""
        from .browser_helpers import fixture_home_node_id, fixture_home_xyz_arg

        self._send(page, f"teleport {fixture_home_xyz_arg()}")
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
            == fixture_home_node_id(),
            timeout=15000,
        )
        panel = self._wait_local_map_available(page)
        gate_room = next(node for node in panel["nodes"] if node["visibility"] == "remembered")
        z_map = gate_room["id"].split(":")[1]
        self._send(page, f"teleport ({gate_room['x']}, {gate_room['y']}, {z_map})")
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("local_map") or {}).get("current_node")
            == gate_room["id"],
            timeout=20000,
        )
        page.wait_for_selector('[data-testid="local-map"] .local-map__stub-button', timeout=15000)
        return self._wait_local_map_available(page)

    @covers_requirement("webclient-local-map::island-gateways-expose-labelled-accessible-exit-ring-controls")
    @covers_requirement("webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure")
    def test_gateway_exit_stub_is_a_named_keyboard_button_moving_once(self):
        # label-minimap-exits-and-gateways: on the gate room the island's
        # cross-layer gate target is an exit-ring stub whose native button
        # follows the full-map affordance in tab order, is named
        # `往 <leads_to> 移動`, and on Space (then, back on the gate, Enter)
        # submits exactly one explore.move with the gate's own exit_ref and
        # the committed current node — never opening the full map too.
        from .browser_helpers import install_outbound_recorder, outbound_messages, sent_action_count

        page = self.logged_in_page()
        install_outbound_recorder(page)
        for key in (" ", "Enter"):
            with self.subTest(key=key):
                panel = self._stand_on_gate_room(page)
                current = next(node for node in panel["nodes"] if node["id"] == panel["current_node"])
                target = next(node for node in panel["nodes"] if node["id"].startswith("wild:"))
                self.assertIsNotNone(target["action"], "the seeded character may traverse the gate")
                name = f"往 {current['gateway']['leads_to']} 移動"
                page.locator('[data-testid="local-map__expand"]').focus()
                page.keyboard.press("Tab")
                focused = page.evaluate("document.activeElement && document.activeElement.getAttribute('aria-label')")
                self.assertEqual(focused, name)
                before = sent_action_count(page, "explore.move")
                page.keyboard.press(key)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and sent_action_count(page, "explore.move") == before:
                    page.wait_for_timeout(250)
                page.wait_for_timeout(500)
                self.assertEqual(sent_action_count(page, "explore.move"), before + 1)
                payload = [
                    args[0]["payload"]
                    for cmd, args, _kw in outbound_messages(page)
                    if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
                ][-1]
                self.assertEqual(
                    payload,
                    {"exit_ref": target["action"]["exit_ref"], "current_node": panel["current_node"]},
                )
                self.assertEqual(page.locator('[data-testid="map-drawer"]').count(), 0)
                wait_for_store_state(
                    page,
                    lambda s: (((s.get("panels") or {}).get("local_map") or {}).get("current_node") or "").startswith("wild:"),
                    timeout=20000,
                )

    def test_minimap_visible_and_keyboard_usable_at_both_viewports(self):
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                for selector in (
                    '[data-testid="message-window"]',
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} not visible at {viewport}",
                    )
                page.close()

    @covers_requirement(
        "webclient-local-map::minimap-presentation-retains-local-knowledge-and-readable-drawer-disclosure"
    )
    def test_minimap_pointer_events_blank_canvas_opens_overlay_while_actionable_moves(self):
        """Pointer-event contract: clicking blank canvas passes to affordance and opens the map drawer;

        clicking actionable node dispatches explore.move without opening the map drawer.
        """
        import time
        from .browser_helpers import (
            install_outbound_recorder,
            sent_action_count,
            visible_minimap_actionable,
        )
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
        page.wait_for_selector('[data-testid="map-drawer"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="map-drawer"]').count(), 1)

        # Close the drawer with Escape
        page.keyboard.press("Escape")
        page.wait_for_function(
            '() => document.querySelector(\'[data-testid="map-drawer"]\') === null',
            timeout=15000,
        )

        # The drawer's own map.view request settles before the island moves
        # (one in-flight request at a time).
        page.wait_for_function(
            "() => window.__elosernBridge.store.view.dispatch.inFlight === null",
            timeout=15000,
        )

        # 2. Click actionable node: dispatches move without opening the map drawer
        actionable = visible_minimap_actionable(page)
        self.assertIsNotNone(
            actionable,
            "the island must show at least one actionable node unclipped",
        )
        moves_before = sent_action_count(page, "explore.move")
        actionable.click()
        self.assertEqual(page.locator('[data-testid="map-drawer"]').count(), 0)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= moves_before + 1:
                break
            page.wait_for_timeout(250)

        self.assertEqual(
            sent_action_count(page, "explore.move"),
            moves_before + 1,
            "clicking actionable node must dispatch move without opening the map drawer",
        )
