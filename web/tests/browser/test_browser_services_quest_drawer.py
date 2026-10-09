"""Quest-book reference-drawer services browser journeys: the host-free quest book
away from any clerk, the keyboard service journey framed inside the drawer, and the
registry-owned unavailable form rendering only its reason.

Every body is byte-identical to its pre-split home in
``test_browser_services.py``.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_helpers import (
    inject_update,
    install_outbound_recorder,
    sent_action_count,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class QuestBookAwayFromClerkJourneys(ServicesBrowserTest):
    """quest-drawer-split task 4.3, re-shaped by quest-drawer-book-tab: an
    accepted guild quest held away from any clerk. The quest book (host-free)
    must read the record, the counter tab must be disabled yet focusable with
    its no-clerk reason, and tracking must dispatch with no guild host present
    (the host-independent panel contract's client face).
    """

    SERVICES_MODE = "quest_away_from_clerk"

    def _open_quest_drawer(self, page):
        self._wait_services_available(page)
        panel = self._services_panel(page)
        # The fixture holds a quest but stands in no service interior.
        self.assertIsNone(panel["guild"])
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)
        return page.locator('[data-testid="quest-drawer"]')

    def _wait_track_sent(self, page):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "guild.quest_track") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "guild.quest_track"), 1)

    @covers_requirement("webclient-quest-log-panel::the-quest-log-panel-is-host-independent")
    def test_away_from_clerk_renders_book_with_no_clerk_marker(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        body = self._open_quest_drawer(page)
        # The book renders the stored record; the counter tab is disabled and
        # names the missing clerk as its reason.
        self.assertEqual(body.get_attribute("data-tab"), "book")
        self.assertEqual(body.locator('[data-testid^="quest-drawer__row--"]').count(), 1)
        counter_tab = page.locator('[data-testid="quest-drawer__top-tabs"] [data-tab-key="counter"]')
        self.assertEqual(counter_tab.get_attribute("aria-disabled"), "true")
        self.assertEqual(page.locator('[data-testid="quest-drawer__counter-absent"]').count(), 1)
        self.assertEqual(page.locator('[data-testid="guild-counter"]').count(), 0)
        self.assertNotIn("尚未取得公會資料", body.inner_text())
        # Away from any clerk the detail still offers tracking and no counter
        # action, and activating it submits exactly one host-free
        # guild.quest_track.
        self.assertEqual(page.locator('[data-testid="quest-drawer__abandon"]').count(), 0)
        track = body.locator('[data-testid="quest-drawer__track"]')
        self.assertEqual(track.count(), 1)
        track.click()
        self._wait_track_sent(page)

    @covers_requirement("webclient-quest-log-panel::the-quest-log-panel-is-host-independent")
    def test_keyboard_reaches_both_tablists_and_the_list(self):
        """quest-drawer-book-tab: Tab reaches each icon tablist once, the arrow
        keys move focus without selecting, a disabled counter tab is focusable
        but never selected, and the list and the tracking toggle complete by
        keyboard."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        body = self._open_quest_drawer(page)
        active_key = "() => document.activeElement && document.activeElement.dataset.tabKey"

        # First level: focus reaches the disabled counter tab, and Enter
        # leaves the book selected.
        self._tab_until_focused(page, '[data-testid="quest-drawer__top-tabs"] [role="tab"][tabindex="0"]')
        _press(page, "ArrowRight")
        self.assertEqual(page.evaluate(active_key), "counter")
        _press(page, "Enter")
        self.assertEqual(body.get_attribute("data-tab"), "book")

        # Second level: moving focus to 已完成 does not select it; Enter does.
        self._tab_until_focused(page, '[data-testid="quest-drawer__state-rail"] [role="tab"][tabindex="0"]')
        self.assertEqual(page.evaluate(active_key), "in_progress")
        _press(page, "ArrowDown")
        self.assertEqual(page.evaluate(active_key), "completed")
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__state-rail"] [data-tab-key="in_progress"]').get_attribute("aria-selected"),
            "true",
        )
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="quest-drawer__empty"]', timeout=5000)
        self.assertEqual(body.locator('[data-testid^="quest-drawer__row--"]').count(), 0)
        _press(page, "ArrowUp")
        _press(page, "Enter")
        page.wait_for_selector('[data-testid^="quest-drawer__row--"]', timeout=5000)

        # The list: the selected row holds the list's tab stop, and Enter on
        # it keeps it selected with its detail beside it.
        self._tab_until_focused(page, '[role="option"][tabindex="0"]')
        _press(page, "Enter")
        row = body.locator('[data-testid^="quest-drawer__row--"]').first
        self.assertEqual(row.get_attribute("aria-selected"), "true")
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__detail"]').get_attribute("data-quest-id"),
            row.get_attribute("data-quest-id"),
        )

        # The tracking toggle completes by keyboard, away from any clerk.
        self._tab_until_focused(page, '[data-testid="quest-drawer__track"]')
        _press(page, "Enter")
        self._wait_track_sent(page)


class KeyboardServiceDrawerJourneys(ServicesBrowserTest):
    """H4 (task 9.4): the keyboard service journeys complete with arrows +
    Enter, the frameless quest drawer renders the counter, and the
    emitted payloads are unchanged."""

    SERVICES_MODE = "guild_hall"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_keyboard_service_journey_frameless_drawer(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["player"]["guild_registered"])

        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")
        trail_before = page.evaluate("() => window.__elosernBridge.router.trail()")

        self._open_guild_menu(page)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.trail()"), trail_before
        )
        self.assertEqual(
            page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0
        )
        self.assertEqual(
            page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0
        )

        # The service frame (quest-drawer) renders inside the reference drawer
        # (H4: the right-column panels were emptied into drawers).
        inside_drawer = page.evaluate(
            """() => {
              const drawer = document.querySelector('[data-testid="hud-drawer"]');
              const body = document.querySelector('[data-testid="quest-drawer"]');
              return !!(drawer && body && drawer.contains(body));
            }"""
        )
        self.assertTrue(inside_drawer, "the guild service frame renders inside the open reference drawer")

        self._select_quest_tab(page, "counter")
        self._tab_until_focused(page, '[data-testid="guild-counter__register"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["guild_registered"] is True)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)

        # Close drawer and verify depth and trail are still unchanged. The
        # commit unmounts the register button (v-if), so DOM focus drops to
        # <body> and the drawer's Escape owner (its focus-trapped root,
        # design D4) never sees the key — the same focus-dependency the
        # sibling inventory journeys document. The store's single close
        # entry is exactly what the drawer's close control, scrim, and
        # Escape handler funnel through, so the frameless-close contract is
        # asserted through it.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s && s.view && s.view.hudDrawer) s.closeHudDrawer(); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before
        )
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.trail()"), trail_before
        )

        # The emitted payload is unchanged: the exact server-authored
        # guild.register action with an empty payload.
        sent = page.evaluate("window.__elosernSent || []")
        registers = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.register"
        ]
        self.assertEqual(len(registers), 1)
        self.assertEqual(registers[0]["payload"], {})


class ServicesUnavailableJourney(ServicesBrowserTest):
    """H4 (task 9.8): with the `services` panel in its registry-owned
    unavailable form, the reference drawers render only the reason — no
    fabricated wallet, stock, quest, or lore rows."""

    SERVICES_MODE = ""

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_unavailable_services_drawer_renders_reason_only(self):
        page = self.logged_in_page()
        unavailable_reason = "服務選單目前無法顯示"
        inject_update(
            page,
            {
                "services": {
                    "schema_version": 6,
                    "available": False,
                    "reason": {
                        "code": "services_unavailable",
                        "message": unavailable_reason,
                    },
                }
            },
        )
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("services", {}).get("available") is False
            and ((s.get("panels") or {}).get("services", {}).get("reason") or {}).get("code")
            == "services_unavailable",
        )

        # Open the quest reference drawer (the gate's first step).
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)
        board = page.locator('[data-testid="quest-drawer"]')
        board_text = board.inner_text()
        # The disabled counter tab carries the registry-owned reason verbatim.
        self.assertIn(unavailable_reason, board_text)
        reason = page.locator('[data-testid="quest-drawer__counter-unavailable"]')
        self.assertEqual(reason.inner_text().strip(), unavailable_reason)
        self.assertEqual(reason.get_attribute("data-reason-code"), "services_unavailable")
        # No fabricated board / quest / rank rows: the unavailable form carries
        # no guild section, so the board and quest-detail rows are absent.
        self.assertEqual(
            page.locator('[data-testid^="guild-counter__board-row--"]').count(), 0,
            "no fabricated counter board rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid^="quest-drawer__row--"]').count(), 0,
            "no fabricated active-quest rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="guild-counter__rankblock"]').count(), 0,
            "no fabricated rank block in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__abandon"]').count(), 0,
            "no fabricated abandon control in the unavailable form")
