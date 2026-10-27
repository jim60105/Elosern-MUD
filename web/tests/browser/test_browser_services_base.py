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
    activate_card_row,
    activate_presence_entry,
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

    def _bag_rows(self, page):
        """The viewed member's committed bag rows (``party_inventory``).

        services v7 carries no personal inventory; the bag panel owns it.
        """
        panel = store_state(page)["panels"].get("party_inventory") or {}
        return {row["item_key"]: row for row in panel.get("rows") or []}

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
        and inventory through the DesktopNavigation 背包 click, which opens
        the party window on its 背包 tab (webclient-party-bag-retire): no
        keyboard frame is pushed and the router's stack is unchanged.

        The host's verb card (exploration-presence-rail) carries its single
        交談 `explore.talk_open` row followed by its navigate-kind service
        entry (exploration_menu.js verbMenuFor), so both hops are reached by
        their stable keys with the keyboard (no OOB emission beyond the
        journey's own later steps). The host's medallion key is read from the
        committed exploration panel, never guessed.
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
            # The B window hotkey (webclient-main-navigation-hotkeys) opens
            # the party window on its 背包 tab (webclient-party-bag-retire):
            # the store aliases the retired bag drawer's name, so no keyboard
            # frame is pushed and the router's stack is unchanged. Returns the
            # committed `party_inventory` panel the tab renders.
            page.keyboard.press("b")
            wait_for_store_state(
                page,
                lambda s: s.get("hudDrawer") == "party"
                and ((s.get("panels") or {}).get("party_inventory") or {}).get("available") is True,
                dom_readiness={
                    "selector": '[data-testid="party-bag-tab"]',
                    "predicate": (
                        "() => !!document.querySelector('[data-testid=\"party-bag-tab\"]')"
                    ),
                    "description": "party window 背包 tab rendered",
                },
            )
            return store_state(page)["panels"]["party_inventory"]
        # guild/shop: the host's medallion on the presence rail -> the host's
        # verb card -> that host's own contextual service row
        # (exploration-presence-rail + npc-contextual-service-projection). Both
        # hops are addressed by their stable keys with the keyboard (the rail's
        # and the card's arrow walks) because the card's row order is
        # server-authored. The provider identity and the row key are read from
        # the committed panel's target-bound services field, never guessed: the
        # version-5 cutover removed the coarse guild/shop navigation rows.
        lookup = page.evaluate(
            """(surface) => {
                const s = window.__elosernBridge && window.__elosernBridge.store;
                const panels = (s && s.view && s.view.panels) || {};
                const panel = panels.exploration || null;
                for (const target of (panel && panel.interact) || []) {
                    const entries = (target.services && target.services.entries) || [];
                    for (const entry of entries) {
                        const route = entry.route || {};
                        if (route.kind !== 'services' || !entry.enabled) {
                            continue;
                        }
                        // The shop surface opens the merchant's shop section;
                        // the guild surface opens a guild counter section
                        // (registration/board/report) — never the independent
                        // rank request or a dialogue association, whose
                        // providers carry no guild section at all.
                        const matches = surface === 'shop'
                            ? route.section === 'shop'
                            : ['registration', 'board', 'report'].indexOf(route.section) !== -1;
                        if (matches) {
                            return { target: 'target-' + target.identity,
                                     key: 'service-' + entry.key };
                        }
                    }
                }
                return null;
            }""",
            surface_key,
        )
        self.assertIsNotNone(
            lookup,
            f"no committed interact target carries an enabled {surface_key} service entry",
        )
        activate_presence_entry(page, lookup["target"])  # open the verb card
        activate_card_row(page, lookup["key"])  # open the frameless service drawer
        if surface_key == "shop":
            wait_for_store_state(
                page,
                lambda s: s.get("hudDrawer") == "shop",
                dom_readiness={
                    "selector": '[data-testid="shop-window"]',
                    "predicate": (
                        "() => !!document.querySelector('[data-testid=\"shop-window\"]')"
                    ),
                    "description": "shop window rendered (webclient-shop-window)",
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
        # Reaching the navigate row opened the host's verb card (client-local,
        # no frame); the drawer's own open pushes nothing either. Normalize to
        # the committed root with no card before returning, so the helper's
        # postcondition is the one the journeys assert (resetFramesToRoot is
        # the browser-helper normalizer; it never closes a drawer).
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

    def _select_in_quest_tablist(self, page, tablist_testid, key, next_key):
        """Select one tab of a quest-drawer tablist by keyboard only.

        quest-drawer-book-tab: each icon tablist keeps one roving tab stop, so
        Tab reaches the list once, the arrow keys move focus along it, and
        Enter selects (moving focus alone never selects).
        """
        tablist = f'[data-testid="{tablist_testid}"]'
        self._tab_until_focused(page, f'{tablist} [role="tab"][tabindex="0"]', max_presses=40)
        for _ in range(8):
            if page.evaluate("() => document.activeElement && document.activeElement.dataset.tabKey") == key:
                break
            _press(page, next_key)
        else:
            self.fail(f"{tablist} has no tab {key!r} reachable by {next_key}")
        _press(page, "Enter")
        page.wait_for_selector(f'{tablist} [data-tab-key="{key}"][aria-selected="true"]', timeout=5000)

    def _select_quest_tab(self, page, key):
        """Select the quest drawer's book or counter tab (the drawer always
        lands on the book)."""
        self._select_in_quest_tablist(page, "quest-drawer__top-tabs", key, "ArrowRight")

    def _select_quest_state(self, page, state):
        """Select a quest book state tab (in_progress, completed, failed)."""
        self._select_in_quest_tablist(page, "quest-drawer__state-rail", state, "ArrowDown")

    def _select_board_grade(self, page, grade):
        """Select a guild board grade tab on the counter tab's grade rail."""
        self._select_in_quest_tablist(page, "quest-drawer__grade-rail", grade, "ArrowDown")

    def _replace_focused_number(self, page, value):
        """Replace the currently focused number entry's value using the keyboard."""
        page.keyboard.press("Control+A")
        page.keyboard.type(str(value))

    # -- shop window (webclient-shop-window) ------------------------------------

    def _focus_roving(self, page, container, item_selector, target_selector, keys=("ArrowDown",)):
        """Tab to a roving composite's tab stop, then walk it to the target."""
        self._tab_until_focused(page, f"{container} {item_selector}[tabindex=\"0\"]", max_presses=40)
        for _ in range(20):
            if page.evaluate("(sel) => document.activeElement && document.activeElement.matches(sel)", target_selector):
                return
            for key in keys:
                _press(page, key)
        self.fail(f"{target_selector} is not reachable in {container}")

    def _select_shop_tab(self, page, key):
        """Select 購買 or 出售 by keyboard (one roving stop; Enter selects)."""
        tabs = '[data-testid="window-frame__tabs"]'
        self._focus_roving(page, tabs, '[role="tab"]', f'{tabs} [data-tab-key="{key}"]', keys=("ArrowRight",))
        _press(page, "Enter")
        page.wait_for_selector(f'{tabs} [data-tab-key="{key}"][aria-selected="true"]', timeout=5000)

    def _select_shop_member(self, page, member_id):
        """Select a rail member by keyboard; waits for the server's adoption."""
        entry = f'[data-testid="member-rail__entry--{member_id}"]'
        self._focus_roving(page, '[data-testid="shop-window"] .member-rail', ".member-rail__entry", entry)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party") or {}).get("viewed_member_id") == member_id
            and (((s.get("panels") or {}).get("services") or {}).get("shop") or {}).get("member_id") == member_id,
            dom_readiness={
                "selector": entry,
                "predicate": f"() => document.querySelector('{entry}')?.getAttribute('aria-current') === 'true'",
                "description": "rail entry adopted as the viewed member",
            },
        )

    def _select_shop_row(self, page, item_key):
        """Select a shop row by keyboard; waits for its holdings answer."""
        rows = '[data-testid="shop-rows"]'
        row = f'[data-testid="shop-rows__row--{item_key}"]'
        self._focus_roving(page, rows, '[role="option"]', row)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("item_holdings") or {}).get("item_key") == item_key
            and not ((s.get("dispatch") or {}).get("inFlight")),
            dom_readiness={
                "selector": row,
                "predicate": f"() => document.querySelector('{row}')?.getAttribute('aria-selected') === 'true'",
                "description": "shop row selected",
            },
        )

    def _open_guild_menu(self, page):
        return self._open_surface(page, "guild")

    def _open_shop_menu(self, page):
        return self._open_surface(page, "shop")
