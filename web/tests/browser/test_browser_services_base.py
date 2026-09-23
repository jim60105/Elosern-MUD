"""Shared services browser fixture: the dedicated-server boot, the services drawer
gate, the keyboard surface navigation, and the panel helpers every services
journey class inherits.

This module is named ``test_browser_services_base`` (no test_* methods, the
test_browser_creation_base precedent); the services sibling family plus
``test_browser_inventory_actions`` and ``test_browser_inventory_grid`` import
``ServicesBrowserTest`` from here. Every body is byte-identical to its
pre-split home in ``test_browser_services.py``."""

from __future__ import annotations

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ServicesBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with a services fixture."""

    SERVICES_MODE = ""

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    # Extra seed env vars a subclass can add if needed by its journey fixture.
    EXTRA_ENV: dict[str, str] = {}

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_SERVICES"] = self.SERVICES_MODE
        runtime.env["ELOSERN_BROWSER_ART"] = ""
        for key, value in self.EXTRA_ENV.items():
            runtime.env[key] = value
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # -- navigation helpers ---------------------------------------------------

    def _services_panel(self, page):
        panels = store_state(page)["panels"]
        return panels["services"]

    def _dock_mode(self, page):
        return page.locator("#action-dock").get_attribute("data-mode")

    def _wait_services_available(self, page, timeout=30000):
        # H4 (task 9.1): the reference surfaces now render only inside the
        # open reference drawer. The gate is re-mapped onto the committed
        # store state (services panel available) plus the drawer's own
        # data-testid; opening the drawer is the journey's first step.
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("services") or {}).get("available") is True,
            timeout=timeout,
        )
        # First step of the journey: verify the reference drawer is openable
        # and renders its body (the quest drawer opens frameless and no longer
        # hosts a router frame). The body's own testid is the readiness gate.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        wait_for_store_state(
            page,
            lambda s: True,
            dom_readiness={
                "selector": '[data-testid="quest-drawer"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"quest-drawer\"]'); "
                    "if (!el) { return false; } "
                    "const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "quest drawer body (quest-drawer) rendered inside the open drawer",
            },
            timeout=timeout,
        )
        return self._services_panel(page)

    def _wait_panel(self, page, predicate, timeout=30000):
        def _panel_ready(state):
            panel = (state.get("panels") or {}).get("services") or {}
            try:
                return bool(predicate(panel))
            except (KeyError, TypeError):
                return False
        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _open_surface(self, page, surface_key):
        """From the exploration root, open the re-homed services surface.

        The standalone Services root no longer exists: guild/shop are reached
        through Interact -> the local host -> its navigate-kind service entry,
        and inventory through the DesktopNavigation 背包 click (the desktop
        redesign re-homed the entry into the top navigation,
        webclient-desktop-shell acd3790) — which opens the 背包 drawer
        frameless (make-inventory-drawer-frameless): no keyboard frame is
        pushed and the router's stack is unchanged.

        The target's affordance frame renders ONE `talk-scripted` row per
        server talk affordance (exploration_menu.js: one row per authored
        keyword — the guild staff's six keywords fill the grid rows before
        the `service-<surface>` row), so the service entry is NOT reachable
        by a fixed arrow walk. The dock-navigation row is focused by its
        stable key through the store (focusItemByKey + focusConfirm: the
        same keyboard-parity fallback tabToRootAndConfirm uses; the frozen
        KeyboardRouter.confirm façade member, so no pointer path and no OOB
        emission beyond the journey's own later steps).
        """
        # Close any open drawer first so its scrim does not cover the stage or
        # block the dock arrow walk.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s && s.view && s.view.hudDrawer) s.closeHudDrawer({ popFrame: true }); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        focus_action_dock(page)
        if surface_key == "inventory":
            # The desktop redesign re-homed the 背包 entry into the top
            # navigation (webclient-desktop-shell, acd3790): the dock root is
            # the capability-driven [move, look, interact, wait,
            # suggestions], so the drawer opens from the DesktopNavigation
            # 背包 click — the same client-local openHudDrawer('inventory')
            # the old dock row submitted (no keyboard frame is pushed).
            page.locator('.desktop-navigation button', has_text="背包").click()
            wait_for_store_state(
                page,
                lambda s: s.get("hudDrawer") == "inventory",
                dom_readiness={
                    "selector": '[data-testid="inventory-panel"]',
                    "predicate": (
                        "() => !!document.querySelector('[data-testid=\"inventory-panel\"]')"
                    ),
                    "description": "frameless inventory drawer rendered",
                },
            )
            return self._services_panel(page)
        # guild/shop: Interact -> first target -> navigate service entry by
        # its stable key (the service row's position depends on the host's
        # keyword count; the key does not).
        _press(page, "ArrowRight")  # Look
        _press(page, "ArrowRight")  # Interact
        _press(page, "Enter")  # open Interact
        _press(page, "Enter")  # select the first present target
        item_key = "service-" + surface_key
        focused = page.evaluate(
            """(key) => {
                const s = window.__elosernBridge && window.__elosernBridge.store;
                return s && s.focusItemByKey(key);
            }""",
            item_key,
        )
        self.assertTrue(
            focused,
            f"the {surface_key} host's navigate row ({item_key}) is not in the "
            "open target's affordance frame",
        )
        _press(page, "Enter")  # open the service submenu / frameless drawer
        if surface_key == "shop":
            wait_for_store_state(
                page,
                lambda s: s.get("hudDrawer") == "shop",
                dom_readiness={
                    "selector": '[data-testid="shop-panel"]',
                    "predicate": (
                        "() => !!document.querySelector('[data-testid=\"shop-panel\"]')"
                    ),
                    "description": "frameless shop drawer rendered",
                },
            )
        elif surface_key == "guild":
            wait_for_store_state(
                page,
                lambda s: s.get("hudDrawer") == "quest",
                dom_readiness={
                    "selector": '[data-testid="quest-drawer"]',
                    "predicate": (
                        "() => !!document.querySelector('[data-testid=\"quest-drawer\"]')"
                    ),
                    "description": "frameless quest drawer rendered",
                },
            )
        return self._services_panel(page)

    def _tab_until_focused(self, page, selector, max_presses=30):
        """Press Tab until document.activeElement matches selector inside the drawer."""
        for _ in range(max_presses):
            _press(page, "Tab")
            matched = page.evaluate(
                "(sel) => document.activeElement && document.activeElement.matches(sel)",
                selector,
            )
            if matched:
                return True
        active_tag = page.evaluate(
            "() => document.activeElement ? "
            "(document.activeElement.getAttribute('data-testid') || document.activeElement.tagName) : 'none'"
        )
        self.fail(
            f"Tab did not reach element matching {selector} after {max_presses} presses (landed on: {active_tag})"
        )

    def _replace_focused_number(self, page, value):
        """Replace the currently focused number entry's value using the keyboard."""
        page.keyboard.press("Control+A")
        page.keyboard.type(str(value))

    def _open_guild_menu(self, page):
        return self._open_surface(page, "guild")

    def _open_shop_menu(self, page):
        return self._open_surface(page, "shop")
