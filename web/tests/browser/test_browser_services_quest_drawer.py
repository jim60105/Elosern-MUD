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
    """quest-drawer-split task 4.3: the case that previously rendered
    ``尚未取得公會資料`` — an accepted guild quest held away from any clerk.
    The quest book (host-free) must read the record, the counter must be
    replaced by its explicit no-clerk marker, and tracking must dispatch with
    no guild host present (the host-independent panel contract's client face).
    """

    SERVICES_MODE = "quest_away_from_clerk"

    @covers_requirement("webclient-quest-log-panel::the-quest-log-panel-is-host-independent")
    def test_away_from_clerk_renders_book_with_no_clerk_marker(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._services_panel(page)
        # The fixture holds a quest but stands in no service interior.
        self.assertIsNone(panel["guild"])
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)
        body = page.locator('[data-testid="quest-drawer"]')
        # The book renders the stored record; the counter is absent, replaced
        # by the explicit clerk-needed marker.
        self.assertEqual(body.locator('[data-testid^="quest-log__row--"]').count(), 1)
        self.assertEqual(page.locator('[data-testid="quest-drawer__counter-absent"]').count(), 1)
        self.assertEqual(page.locator('[data-testid="guild-counter"]').count(), 0)
        self.assertNotIn("尚未取得公會資料", body.inner_text())
        # Away from any clerk the row still offers tracking, and activating it
        # submits exactly one host-free guild.quest_track.
        row = body.locator('[data-testid^="quest-log__row--"]').first
        track = row.locator('[data-testid="quest-log__track"]')
        self.assertEqual(track.count(), 1)
        track.click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "guild.quest_track") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "guild.quest_track"), 1)


class KeyboardServiceDrawerJourneys(ServicesBrowserTest):
    """H4 (task 9.4): the keyboard service journeys complete with arrows +
    Enter, the service frame renders inside the reference drawer, and the
    emitted payloads are unchanged."""

    SERVICES_MODE = "guild_hall"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_keyboard_service_journey_frames_render_inside_drawer(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["player"]["guild_registered"])

        # The gate already opened the reference (quest) drawer. Drive the
        # registration journey with arrow keys + Enter only.
        self._open_guild_menu(page)
        _press(page, "Enter")  # register row
        self._wait_panel(page, lambda p: p["player"]["guild_registered"] is True)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)

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

        # remove-redundant-dock-menu-layout: the drawer body that hosts the
        # service frame is itself the split owner — the row region (`.dock-menu`)
        # and the surface are direct children of `.hud-drawer__body--dock`, with
        # no component-level layout wrapper between the body and either child.
        drawer_split = page.evaluate(
            """() => {
              const body = document.querySelector('.hud-drawer__body');
              const list = document.querySelector('.dock-menu');
              const surface = document.querySelector('[data-testid="quest-drawer"]');
              if (!body || !list || !surface) return false;
              return body.classList.contains('hud-drawer__body--dock')
                && list.parentElement === body
                && surface.parentElement === body;
            }"""
        )
        self.assertTrue(
            drawer_split,
            "the drawer-hosted row region and surface are direct children of the drawer body",
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
                    "schema_version": 4,
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
        # The drawer body renders the registry-owned reason verbatim.
        self.assertIn(unavailable_reason, board_text)
        # No fabricated board / quest / rank rows: the unavailable form carries
        # no guild section, so the board and quest-detail rows are absent.
        self.assertEqual(
            page.locator('[data-testid^="guild-counter__board-row--"]').count(), 0,
            "no fabricated counter board rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid^="quest-log__row--"]').count(), 0,
            "no fabricated active-quest rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="guild-counter__rankblock"]').count(), 0,
            "no fabricated rank block in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="quest-log__abandon"]').count(), 0,
            "no fabricated abandon control in the unavailable form")
