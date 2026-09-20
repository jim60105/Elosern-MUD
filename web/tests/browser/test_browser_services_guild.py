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
    def test_register_and_idempotent_reregister(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["player"]["guild_registered"])

        self._open_guild_menu(page)
        _press(page, "Enter")  # register row
        self._wait_panel(page, lambda p: p["player"]["guild_registered"] is True)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)
        self.assertEqual(self._services_panel(page)["player"]["guild_rank"], "F")

        # A stale/replayed client re-submits the empty payload; the server is
        # idempotent and returns the original record without replacing it.
        page.evaluate("Elosern.actions.submit('guild.register', {})")
        page.wait_for_timeout(800)
        self.assertEqual(sent_action_count(page, "guild.register"), 2)
        self.assertEqual(self._services_panel(page)["player"]["guild_rank"], "F")
        self.assertEqual(self._services_panel(page)["player"]["wallet"], 1000)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_viewport_1280x720_keeps_controls_visible(self):
        page = self.logged_in_page((1280, 720))
        panel = self._wait_services_available(page)
        self._open_guild_menu(page)
        controls = page.locator(".dock-menu-item")
        self.assertGreaterEqual(controls.count(), 1)
        for index in range(controls.count()):
            self.assertTrue(controls.nth(index).is_visible())
        # H4 (task 9.2): the heading is now the open reference drawer's own
        # title (the `#panel-right` reference panels were emptied into drawers).
        heading = page.locator(".hud-drawer__title")
        self.assertTrue(heading.is_visible())


class GuildBoardJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_registered_board"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_board_list_to_accept(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "Enter")
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

    @covers_requirement("webclient-frame-resolution::the-resolver-table-completes-with-the-services-combat-and-creation-families")
    def test_board_frame_refreshes_on_committed_update(self):
        """Declarative-frame freshness: an open board frame re-resolves its
        rows from the NEXT committed panel — no re-push, no copy.

        A partial ``ui_update`` replaces only the ``services`` panel with a
        renamed offer row. The committed panel is not the frame's data: the
        board frame's next read enumerates the updated label with the row's
        payload untouched, and no action is dispatched by the injection.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "Enter")  # open the board frame (hosted by the drawer)
        old_name = panel["guild"]["board"][0]["display_name"]
        before = page.evaluate("() => window.__elosernBridge.router.depth()")
        sent_before = len([m for m in outbound_messages(page) if m[0] == "ui_action"])

        updated = self._services_panel(page)
        new_name = "新增任務委託"
        updated["guild"]["board"][0]["display_name"] = new_name
        inject_update(page, {"services": updated})

        rows = page.evaluate(
            "() => window.__elosernBridge.router.currentMenu().items.map("
            "(i) => ({ key: i.key, label: i.label, payload: i.payload }))"
        )
        offer = [row for row in rows if row["key"] == "board-0"]
        self.assertEqual(len(offer), 1, rows)
        self.assertEqual(offer[0]["label"], new_name)
        self.assertNotEqual(offer[0]["label"], old_name)
        self.assertEqual(offer[0]["payload"], {"definition_key": guild_offer_quest_key()})
        # The frame stayed exactly where it was, and the injection dispatched
        # nothing.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), before)
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
        )


class GuildQuestJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_active_quest"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_abandon_requires_confirmation(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        self._open_guild_menu(page)
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "ArrowDown")  # exam_start (second grid row)
        _press(page, "ArrowLeft")  # quests (second grid row, first column)
        _press(page, "Enter")
        _press(page, "Enter")  # the quest row
        _press(page, "ArrowRight")  # 放棄 (second grid column)
        _press(page, "Enter")  # open confirmation screen
        page.wait_for_timeout(400)
        # No mutation may be sent before the explicit confirmation.
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 0)
        confirm = page.locator(".services-confirm")
        self.assertEqual(confirm.count(), 1, "abandon confirmation screen must render")
        _press(page, "Enter")  # 確認放棄
        self._wait_panel(page, lambda p: p["guild"]["quests"][0]["state"] == "failed")
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 1)

    @covers_requirement("webclient-frame-resolution::a-drawer-follows-the-stack-when-its-hosted-frame-pops")
    @covers_requirement("webclient-frame-resolution::the-resolver-table-completes-with-the-services-combat-and-creation-families")
    def test_quest_drawer_closes_with_the_hosted_frame(self):
        """Drawer coupling: quest loss pops the detail frame to the hosted
        parent (drawer KEPT); losing the whole hosted surface closes the
        drawer with its frame gone and its component-local state discarded.

        Injection 1 removes the quest: the quest-detail descriptor becomes
        unresolvable and pops exactly one level to the hosted `services.quests`
        frame — the quest drawer stays open. Injection 2 withdraws the whole
        services panel: the cascade pops every services frame back to the
        exploration root, and the settle-driven hosting watcher closes the
        drawer whose hosted frame is gone (the drawer body unmounts, which is
        where the selection and confirmation state live).
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        # root -> interact -> target -> keywords -> services.guild -> quests
        # -> quest-detail, mirroring the abandon journey's navigation up to
        # the detail frame (the confirmation step is NOT opened).
        self._open_guild_menu(page)
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "ArrowDown")  # exam_start (second grid row)
        _press(page, "ArrowLeft")  # quests (second grid row, first column)
        _press(page, "Enter")  # quests frame
        _press(page, "Enter")  # the quest row -> hosted quest-detail frame
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentDescriptor().source"),
            "services.quest-detail",
        )
        self.assertEqual(store_state(page)["hudDrawer"], "quest")
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")
        sent_before = len([m for m in outbound_messages(page) if m[0] == "ui_action"])

        # Injection 1: the quest disappears from the committed panel.
        updated = self._services_panel(page)
        updated["guild"]["quests"] = []
        updated["pagination"]["quest_total"] = 0
        inject_update(page, {"services": updated})

        # One level down: the hosted parent surface stands, drawer kept.
        current = page.evaluate(
            "() => window.__elosernBridge.router.currentDescriptor()"
        )
        self.assertEqual(current["source"], "services.quests")
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            depth_before - 1,
        )
        self.assertEqual(store_state(page)["hudDrawer"], "quest")

        # Injection 2: the whole hosted surface is withdrawn.
        inject_update(
            page,
            {
                "services": {
                    "schema_version": 4,
                    "available": False,
                    "reason": {
                        "code": "registry_unavailable",
                        "message": "服務暫不可用。",
                    },
                }
            },
        )
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") is None
            and (s.get("panels") or {}).get("services", {}).get("available") is False,
        )
        current = page.evaluate(
            "() => window.__elosernBridge.router.currentDescriptor()"
        )
        self.assertTrue(current["source"].startswith("exploration"), current)
        # The drawer's frame is gone, so no open drawer renders a service
        # surface: the body unmounts (discarding its local state with it).
        self.assertEqual(page.locator('[data-testid="quest-drawer"]').count(), 0)
        # Neither pop dispatched anything.
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
        )

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
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "ArrowDown")  # exam_start (second grid row)
        _press(page, "ArrowLeft")  # quests (second grid row, first column)
        _press(page, "Enter")
        _press(page, "Enter")  # the quest row
        _press(page, "ArrowDown")  # 回報 (first column, second row)
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


class GuildExamJourney(ServicesBrowserTest):
    SERVICES_MODE = "guild_exam"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
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
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "ArrowDown")  # exam_start (second grid row, second column)
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
