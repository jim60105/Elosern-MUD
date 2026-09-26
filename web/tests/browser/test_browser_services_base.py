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

        The target's verb popover carries the host's single 交談
        `explore.talk_open` row followed by its navigate-kind service entry
        (exploration_menu.js targetMenuFor; the panel's per-host keyword list
        left the wire in exploration panel v3), so both hops are focused by
        their stable keys through the store (focusItemByKey + Enter: the same
        keyboard-parity path tabToRootAndConfirm uses, through the frozen
        KeyboardRouter façade members — no pointer path and no OOB emission
        beyond the journey's own later steps). The host's chip key is read from
        the committed exploration panel, never guessed.
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
        # guild/shop: the overview's person chip -> the host's verb popover ->
        # the navigate-kind service entry. Both hops are addressed by their
        # stable keys through the store (focusItemByKey + Enter) because the
        # popover's row order is server-authored (交談 leads, then the target's
        # own affordances), so a fixed arrow walk cannot name the service row.
        # The chip's identity is read from the committed panel, never guessed.
        target_key = page.evaluate(
            """(surface) => {
                const s = window.__elosernBridge && window.__elosernBridge.store;
                const panels = (s && s.view && s.view.panels) || {};
                const panel = panels.exploration || null;
                for (const target of (panel && panel.interact) || []) {
                    for (const affordance of target.affordances || []) {
                        if (affordance.surface === surface) {
                            return 'target-' + target.identity;
                        }
                    }
                }
                return null;
            }""",
            surface_key,
        )
        self.assertTrue(
            target_key,
            f"no committed interact target carries the {surface_key} service entry",
        )
        opened = page.evaluate(
            """(key) => {
                const s = window.__elosernBridge && window.__elosernBridge.store;
                return s && s.focusItemByKey(key);
            }""",
            target_key,
        )
        self.assertTrue(
            opened,
            f"the {surface_key} host's overview chip ({target_key}) is not in "
            "the current frame",
        )
        _press(page, "Enter")  # open the host's verb popover (no dispatch)
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
            "open target's verb popover",
        )
        _press(page, "Enter")  # open the frameless service drawer
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
        # Reaching the navigate row needed the host's verb popover, which is a
        # pushed frame; the drawer's own open pushes nothing. Restore the
        # committed root before returning so the helper's postcondition is the
        # one the journeys assert — opening a frameless surface leaves the
        # router's frame and trail untouched (resetFramesToRoot is the
        # browser-helper stack normalizer; it never closes a drawer).
        page.evaluate("window.__elosernBridge.store.resetFramesToRoot()")
        page.wait_for_timeout(80)
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
