"""Guild-counter services browser journeys: registration, board accept, quest
abandon, completed-quest turn-in, and the exam-to-combat transition, each on its
dedicated isolated server.

Every body is byte-identical to its pre-split home in
``test_browser_services.py``.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import (
    guild_offer_quest_key,
    guild_offer_reward_copper,
)

from .browser_helpers import (
    inject_update,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class GuildRegistrationJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_hall"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_register_and_idempotent_reregister(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["player"]["guild_registered"])

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="guild-counter__register"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["guild_registered"] is True)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)
        self.assertEqual(self._services_panel(page)["player"]["guild_rank"], "F")
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

        # A stale/replayed client re-submits the empty payload; the server is
        # idempotent and returns the original record without replacing it.
        page.evaluate("Elosern.actions.submit('guild.register', {})")
        page.wait_for_timeout(800)
        self.assertEqual(sent_action_count(page, "guild.register"), 2)
        self.assertEqual(self._services_panel(page)["player"]["guild_rank"], "F")
        self.assertEqual(self._services_panel(page)["player"]["wallet"], 1000)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_viewport_1280x720_keeps_controls_visible(self):
        page = self.logged_in_page((1280, 720))
        panel = self._wait_services_available(page)
        self._open_guild_menu(page)
        self.assertTrue(page.locator('[data-testid="quest-drawer"]').is_visible())
        self.assertTrue(page.locator('[data-testid="guild-counter"]').is_visible())
        self.assertTrue(page.locator('[data-testid="guild-counter__register"]').is_visible())
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        # H4 (task 9.2): the heading is now the open reference drawer's own
        # title (the `#panel-right` reference panels were emptied into drawers).
        heading = page.locator(".hud-drawer__title")
        self.assertTrue(heading.is_visible())


class GuildBoardJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_registered_board"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_board_list_to_accept(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="guild-counter__accept"]')
        _press(page, "Enter")  # accept the eligible offer row
        self._wait_panel(page, lambda p: p["pagination"]["quest_total"] == 1)
        self.assertEqual(sent_action_count(page, "guild.quest_accept"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.quest_accept"
        )
        self.assertEqual(payload, {"definition_key": guild_offer_quest_key()})
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_board_frame_refreshes_on_committed_update(self):
        """The guild counter's board re-renders on a committed update."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        old_name = panel["guild"]["board"][0]["display_name"]
        board_row = page.locator(f'[data-testid="guild-counter__board-row--{guild_offer_quest_key()}"]')
        self.assertTrue(board_row.is_visible())
        self.assertIn(old_name, board_row.inner_text())
        before = page.evaluate("() => window.__elosernBridge.router.depth()")
        sent_before = len([m for m in outbound_messages(page) if m[0] == "ui_action"])

        updated = self._services_panel(page)
        new_name = "新增任務委託"
        updated["guild"]["board"][0]["display_name"] = new_name
        inject_update(page, {"services": updated})
        page.wait_for_timeout(200)
        self.assertIn(new_name, board_row.inner_text())
        self.assertNotIn(old_name, board_row.inner_text())
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), before)
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)


class GuildQuestJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_active_quest"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_abandon_requires_confirmation(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="quest-log__abandon"]')
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 0)

        # Reveal confirmation
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="quest-log__abandon-confirm"]', timeout=5000)
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 0)

        # Confirm abandon
        self._tab_until_focused(page, '[data-testid="quest-log__abandon-confirm-yes"]')
        _press(page, "Enter")  # 確認放棄
        self._wait_panel(page, lambda p: p["guild"]["quests"][0]["state"] == "failed")
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 1)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_quest_vanishes_book_drops_row_drawer_stays_open(self):
        """Frameless drawer retention: when a committed update removes a quest,
        the quest book drops the row and the drawer stays open without a frame pop."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid^="quest-log__row--"]').count(), 1)
        self.assertEqual(store_state(page)["hudDrawer"], "quest")
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")

        # Injection: the quest disappears from the committed panel.
        updated = self._services_panel(page)
        updated["guild"]["quests"] = []
        updated["pagination"]["quest_total"] = 0
        inject_update(page, {"services": updated})

        # The quest row drops from the book, and the drawer stays open at unchanged depth.
        page.wait_for_selector('[data-testid="quest-log__empty"]', timeout=5000)
        self.assertEqual(page.locator('[data-testid^="quest-log__row--"]').count(), 0)
        self.assertEqual(store_state(page)["hudDrawer"], "quest")
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement(
        "webclient-service-menus::the-quest-drawer-separates-the-player-s-quest-book-from-the-guild-counter",
    )
    def test_drawer_renders_book_and_counter_without_duplication(self):
        """quest-drawer-split: in front of the clerk the drawer hosts both
        surfaces — the quest book and the counter — and the accepted quest
        appears exactly once: the counter lists no quest-record rows."""
        page = self.logged_in_page()
        self._wait_services_available(page)
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)
        body = page.locator('[data-testid="quest-drawer"]')
        # Exactly one book row for the held quest; the counter surface is
        # present but carries no quest-record rows at all.
        self.assertEqual(body.locator('[data-testid^="quest-log__row--"]').count(), 1)
        self.assertEqual(page.locator('[data-testid="guild-counter"]').count(), 1)
        self.assertEqual(
            page.locator('[data-testid^="guild-counter__quest-row--"]').count(), 0
        )


class GuildTurninJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_completed_quest"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_completed_quest_turnin(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)
        self.assertEqual(panel["player"]["wallet"], 1000)
        # The wallet delta is the registered offer's copper reward, which the
        # boot mode's catalog authors (shipped rulebook row vs kit reward).
        wallet_after = 1000 + guild_offer_reward_copper()

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="quest-log__turnin"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["wallet"] == wallet_after)
        self.assertEqual(sent_action_count(page, "guild.quest_turnin"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.quest_turnin"
        )
        self.assertEqual(payload, {"quest_id": f"{guild_offer_quest_key()}:1"})
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)


class GuildExamJourney(ServicesBrowserTest):
    SERVICES_MODE = "guild_exam"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    def test_exam_eligibility_transitions_into_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        # The promotion target is the registry-derived next rank the server
        # presents (E in shipped mode, the kit's second rank under the
        # synthetic install) — the journey pins its propagation into the
        # submitted payload, not a rank literal.
        next_rank = panel["guild"]["rank"]["next_rank"]
        self.assertTrue(next_rank)
        self.assertTrue(panel["guild"]["rank"]["eligible"])

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="guild-counter__exam"]')
        _press(page, "Enter")
        # The exam transitions the shell into the ordinary combat menu and the
        # services dock must tear down.
        self._wait_combat_mode(page)
        self.assertEqual(sent_action_count(page, "guild.exam_start"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.exam_start"
        )
        self.assertEqual(payload, {"target_rank": next_rank})
        self.assertEqual(self._dock_mode(page), "combat")
        # services v3 keeps the personal surfaces available through combat
        # and forces host/guild/shop null: the exam's remote service dock is
        # gone even though the bag drawer stays usable for item actions.
        services = self._services_panel(page)
        self.assertTrue(services["available"])
        self.assertIsNone(services["host"])
        self.assertIsNone(services["guild"])
        self.assertIsNone(services["shop"])
        self.assertIsNotNone(services["player"])

    def _wait_combat_mode(self, page, timeout=30000):
        def _combat_ready(state):
            if state.get("mode") != "combat":
                return False
            panel = (state.get("panels") or {}).get("context_actions") or {}
            return panel.get("available") is True
        wait_for_store_state(
            page,
            _combat_ready,
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.querySelector('#action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible in combat mode",
            },
            timeout=timeout,
        )
        state = store_state_or_none(page) or {}
        return (state.get("panels") or {}).get("context_actions")
