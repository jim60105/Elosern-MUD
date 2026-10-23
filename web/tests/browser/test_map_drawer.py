"""Map drawer live walk (redesign-map-drawer).

One managed server boots on synthetic catalogs, so the drawer reads the
real on-demand ``area_map`` and ``world_map`` the live coordinator publishes.
The journeys open the map in the starting settlement with the M hotkey,
switch tabs with the 1 / 2 keys, take one adjacent step through the drawer's
own 前往, and unwind the drawer with Escape, asserting the exact ``map.view``
requests on the real socket at each step.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from . import fixtures
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import install_outbound_recorder, outbound_messages, wait_for_store_state
from .harness import ManagedServer


def _store_active(state: dict) -> bool:
    return bool(state.get("connected")) and state.get("phase") == "active" and state.get("mutationsLocked") is not True


def _map_views(page) -> list[str]:
    return [
        args[0]["payload"]["scope"]
        for cmd, args, _kw in outbound_messages(page)
        if cmd == "ui_action" and args[0]["action_id"] == "map.view"
    ]


def _moves(page) -> list[dict]:
    return [
        args[0]["payload"]
        for cmd, args, _kw in outbound_messages(page)
        if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
    ]


_LOCK_FREE = "() => window.__elosernBridge.store.view.dispatch.inFlight === null"


class MapDrawerWalkTests(BrowserAcceptanceTest):
    """The real drawer over real map panels, using synthetic world fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-map-drawer-")
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

    def _open_map(self, page) -> None:
        wait_for_store_state(page, _store_active, timeout=45000)
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("local_map") or {}).get("available") is True,
            timeout=45000,
        )
        page.wait_for_function(_LOCK_FREE, timeout=20000)
        install_outbound_recorder(page)
        page.locator("body").focus()
        page.keyboard.press("m")
        page.wait_for_selector('[data-testid="map-drawer"]', timeout=15000)

    @covers_requirement(
        "webclient-map-drawer::the-map-drawer-opens-the-appropriate-scope-and-preserves-session-views"
    )
    @covers_requirement(
        "webclient-map-drawer::map-requests-follow-explicit-scope-and-committed-moves-only-while-open"
    )
    def test_open_switch_tabs_and_refresh_after_a_committed_move(self):
        page = self.logged_in_page()
        self._open_map(page)
        # A settlement opens on the area tab, which requests exactly its scope.
        area_tab = page.locator('[data-testid="map-drawer-tab--area"]')
        self.assertEqual(area_tab.get_attribute("aria-selected"), "true")
        page.wait_for_selector('[data-testid="area-map"]', timeout=20000)
        self.assertEqual(_map_views(page), ["area"])
        self.assertEqual(
            page.locator('[data-testid="area-map__node"][aria-current="location"]').count(), 1
        )

        # 2 switches to the world tab and asks for the world once.
        page.wait_for_function(_LOCK_FREE, timeout=20000)
        page.keyboard.press("2")
        # Synthetic settlements have no continental anchor. The server's
        # unavailable response must still settle the request and keep the
        # world tab usable; production geography is exercised in the live walk.
        page.wait_for_selector('[data-testid="map-drawer-unavailable"]', timeout=30000)
        self.assertEqual(page.locator('[data-testid="map-drawer-tab--world"]').get_attribute("aria-selected"), "true")
        self.assertEqual(_map_views(page), ["area", "world"])
        self.assertTrue(page.locator('[data-testid="map-drawer-unavailable"]').inner_text().strip())

        # Back to the area tab; select an adjacent exit and take it.
        page.wait_for_function(_LOCK_FREE, timeout=30000)
        page.keyboard.press("1")
        page.wait_for_selector('[data-testid="area-map"]', timeout=20000)
        page.wait_for_function(_LOCK_FREE, timeout=20000)
        before = _map_views(page)
        start = page.evaluate("window.__elosernBridge.store.view.maps.area_map.current_node")
        travel = page.locator('[data-testid="area-map__node"].is-travel').first
        travel.wait_for(timeout=15000)
        destination = travel.get_attribute("data-node-id")
        travel.focus()
        page.keyboard.press("Enter")
        page.wait_for_selector('[data-testid="area-map-detail__go"]', timeout=15000)
        page.locator('[data-testid="area-map-detail__go"]').click()

        def arrived(_state) -> bool:
            maps = page.evaluate("window.__elosernBridge.store.view.maps")
            return (maps.get("area_map") or {}).get("current_node") == destination

        wait_for_store_state(page, arrived, timeout=45000)
        moves = _moves(page)
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves[0]["current_node"], start)
        # Exactly one refresh of the active scope followed the committed move.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            page.wait_for_timeout(250)
        self.assertEqual(_map_views(page), [*before, "area"])
        page.close()

    @covers_requirement(
        "webclient-map-drawer::map-keyboard-and-pointer-interaction-remains-modal-and-accessible"
    )
    @covers_requirement(
        "webclient-map-drawer::floating-map-chrome-avoids-selected-details"
    )
    def test_escape_unwinds_legend_selection_then_map(self):
        page = self.logged_in_page()
        self._open_map(page)
        page.wait_for_selector('[data-testid="map-drawer-pill"]', timeout=20000)
        # Selecting the current node opens the ~360 px card; the pill steps
        # left of it.
        page.locator('[data-testid="area-map__node"][aria-current="location"]').focus()
        page.keyboard.press("Enter")
        page.wait_for_selector('[data-testid="area-map-detail"]', timeout=15000)
        page.wait_for_timeout(500)
        card = page.locator(".area-map__detail").bounding_box()
        pill = page.locator('[data-testid="map-drawer-pill"]').bounding_box()
        self.assertLessEqual(pill["x"] + pill["width"], card["x"] + 0.5)

        toggle = page.locator('[data-testid="map-drawer-legend-toggle"]')
        toggle.click()
        page.wait_for_selector('[data-testid="map-drawer-legend"]', state="visible", timeout=15000)
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="map-drawer-legend"]', state="hidden", timeout=15000)
        self.assertEqual(page.locator('[data-testid="area-map-detail"]').count(), 1)
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="area-map-detail"]', state="detached", timeout=15000)
        self.assertEqual(page.locator('[data-testid="map-drawer"]').count(), 1)
        # The map keys never reach the game behind the modal: C recentres the
        # map instead of opening the party window.
        page.keyboard.press("c")
        self.assertEqual(page.locator('[data-testid="party-window"]').count(), 0)
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="map-drawer"]', state="detached", timeout=15000)
        page.close()
