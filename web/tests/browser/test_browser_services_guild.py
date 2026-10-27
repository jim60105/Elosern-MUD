"""Guild-counter services browser journeys: registration, board accept, quest
abandon, completed-quest turn-in, and the exam-to-combat transition, each on its
dedicated isolated server.

Every body is byte-identical to its pre-split home in
``test_browser_services.py``.
"""

from __future__ import annotations

import json

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import (
    SYNTH_EXAM_APPOINTMENT,
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
    @covers_requirement("webclient-quest-drawer::an-unregistered-holder-sees-registration-instead-of-the-board")
    def test_register_and_idempotent_reregister(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["player"]["guild_registered"])

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        self._select_quest_tab(page, "counter")
        # An unregistered holder sees only the registration card.
        self.assertEqual(page.locator('[data-testid="quest-drawer__grade-rail"]').count(), 0)
        self._tab_until_focused(page, '[data-testid="quest-drawer__register"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["guild_registered"] is True)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)
        self.assertEqual(self._services_panel(page)["player"]["guild_rank"], "F")
        # The commit swaps the card for the grade-tabbed board, and focus
        # stays inside the drawer on the selected grade tab.
        page.wait_for_selector('[data-testid="quest-drawer__grade-rail"]', timeout=5000)
        self.assertEqual(page.locator('[data-testid="quest-drawer__registration"]').count(), 0)
        self.assertTrue(
            page.evaluate(
                "() => !!document.activeElement && !!document.activeElement.closest("
                "'[data-testid=\"quest-drawer__grade-rail\"]')"
            )
        )
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
    @covers_requirement("webclient-quest-drawer::an-unregistered-holder-sees-registration-instead-of-the-board")
    def test_viewport_reference_keeps_controls_visible(self):
        page = self.logged_in_page((1451, 790))
        panel = self._wait_services_available(page)
        self._open_guild_menu(page)
        self.assertTrue(page.locator('[data-testid="quest-drawer"]').is_visible())
        self._select_quest_tab(page, "counter")
        self.assertTrue(page.locator('[data-testid="quest-drawer__registration"]').is_visible())
        self.assertTrue(page.locator('[data-testid="quest-drawer__register"]').is_visible())
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        # H4 (task 9.2): the heading is now the open reference drawer's own
        # title (the `#panel-right` reference panels were emptied into drawers).
        heading = page.locator("[data-testid=\"hud-drawer__title\"]")
        self.assertTrue(heading.is_visible())


class GuildBoardJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_registered_board"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    @covers_requirement("webclient-quest-drawer::the-guild-board-is-organized-by-difficulty-grade-tabs")
    @covers_requirement("webclient-quest-drawer::selecting-a-board-offer-shows-its-detail-and-the-accept-action")
    def test_board_list_to_accept(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        # npc-targeted-service-flows: the drawer renders only the selected
        # clerk's own read, so the counter is usable once that read lands.
        page.wait_for_selector('[data-testid="quest-drawer__grade-rail"]', timeout=15000)
        self._select_quest_tab(page, "counter")
        # The default grade is the holder's own grade with its one offer,
        # which the detail shows.
        offer_key = guild_offer_quest_key()
        offer_rank = panel["guild"]["board"][0]["rank"]
        self.assertEqual(
            page.locator(
                f'[data-testid="quest-drawer__grade-rail"] [data-tab-key="{offer_rank}"]'
            ).get_attribute("aria-selected"),
            "true",
        )
        # A GuildStaff provider owns registration and the board only: the
        # independent rank surface belongs to the separate examination
        # reception, so this counter carries no rank card at all — and never
        # the reception-only body either.
        counter = page.locator('[data-testid="quest-drawer__counter"]')
        self.assertEqual(counter.locator('[data-testid="guild-rank-card"]').count(), 0)
        self.assertEqual(counter.locator('[data-testid="quest-drawer__reception-rank"]').count(), 0)
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__detail"]').get_attribute("data-quest-id"), offer_key
        )
        self._tab_until_focused(page, '[data-testid="quest-drawer__accept"]', max_presses=40)
        _press(page, "Enter")  # accept the selected offer
        self._wait_panel(page, lambda p: p["pagination"]["quest_total"] == 1)
        self.assertEqual(sent_action_count(page, "guild.quest_accept"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.quest_accept"
        )
        # guild.quest_accept names its exact provider (services v8,
        # npc-targeted-service-flows): the board was read from the clerk whose
        # identity the commit revalidates.
        self.assertEqual(
            payload,
            {
                "definition_key": guild_offer_quest_key(),
                "npc_id": panel["guild"]["provider_id"],
            },
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    @covers_requirement("webclient-quest-drawer::the-counter-tab-shows-the-rank-card-above-the-board")
    def test_reception_counter_shows_the_independent_rank_card(self):
        """The rank surface is the reception host's own read.

        The hall's reception counter owns the independent top-level `rank`
        section; opening its own service entry targets exactly that provider,
        so the counter renders the rank card alone (no grade rail, board row,
        or registration) and the examination request names the reception.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        rank = panel["rank"]
        reception_id = rank["provider_id"]
        self.assertNotEqual(reception_id, panel["guild"]["provider_id"])
        self.assertTrue(rank["next_rank"])

        self._open_reception_counter(page)
        counter = page.locator('[data-testid="quest-drawer__counter"]')
        rank_card = counter.locator('[data-testid="quest-drawer__reception-rank"]')
        rank_card.wait_for(state="visible", timeout=15000)
        # The card is the shipped rank card: rank level, merit meter and the
        # examination request, unchanged in content.
        self.assertIn(
            f'等級 {rank["rank"]}',
            rank_card.locator('[data-testid="guild-counter__rank-level"]').inner_text(),
        )
        self.assertTrue(rank_card.locator('[data-testid="guild-counter__merit-meter"]').is_visible())
        # The reception provider carries no board and no staff section.
        self.assertEqual(counter.locator('[data-testid="quest-drawer__grade-rail"]').count(), 0)
        self.assertEqual(counter.locator('[data-testid^="quest-drawer__row--"]').count(), 0)
        self.assertEqual(counter.locator('[data-testid="quest-drawer__registration"]').count(), 0)

        # The examination request dispatches the selected reception provider.
        self.assertTrue(rank["exam_request"]["enabled"])
        self._tab_until_focused(page, '[data-testid="guild-counter__exam"]', max_presses=60)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: sent_action_count(page, "guild.exam_request") == 1,
        )
        sent = page.evaluate("window.__elosernSent || []")
        payloads = [
            args[0]["payload"] for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.exam_request"
        ]
        self.assertEqual(
            payloads,
            [{"target_rank": rank["next_rank"], "npc_id": reception_id}],
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-quest-drawer::the-guild-board-is-organized-by-difficulty-grade-tabs")
    @covers_requirement("webclient-quest-drawer::selecting-a-board-offer-shows-its-detail-and-the-accept-action")
    def test_board_frame_refreshes_on_committed_update(self):
        """The guild counter follows its own provider's read on a commit."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["board_total"], 1)

        self._open_guild_menu(page)
        offer_key = guild_offer_quest_key()
        page.wait_for_selector(f'[data-testid="quest-drawer__grade-rail"]', timeout=15000)
        self._select_quest_tab(page, "counter")
        old_name = panel["guild"]["board"][0]["display_name"]
        board_row = page.locator(f'[data-testid="quest-drawer__row--{offer_key}"]')
        self.assertTrue(board_row.is_visible())
        self.assertIn(old_name, board_row.inner_text())
        before = page.evaluate("() => window.__elosernBridge.router.depth()")
        sent_before = len([m for m in outbound_messages(page) if m[0] == "ui_action"])
        wait_for_store_state(page, lambda s: not (s.get("dispatch") or {}).get("inFlight"))

        # A committed presentation revision makes the open slot repeat its own
        # correlated read. This journey stands where the server would answer
        # that read: it records the one `services.open` the commit triggers and
        # answers it with the clerk's own board, so the injected revision never
        # has to exist on the live server.
        page.evaluate(
            """() => {
              window.__elosernServiceReads = [];
              const recorded = Evennia.msg.bind(Evennia);
              Evennia.msg = function (cmdname, args, kwargs, callback) {
                const envelope = args && args[0];
                if (cmdname === 'ui_action' && envelope && envelope.action_id === 'services.open') {
                  window.__elosernServiceReads.push(envelope);
                  return undefined;
                }
                return recorded(cmdname, args, kwargs, callback);
              };
            }"""
        )

        # The committed update the server would publish: the room-wide summary
        # names a decoy title the drawer must never render, because it renders
        # its own slot's read and not the summary.
        updated = self._services_panel(page)
        decoy_name = "舊看板委託"
        updated["guild"]["board"][0]["display_name"] = decoy_name
        inject_update(page, {"services": updated})
        page.wait_for_function(
            "() => (window.__elosernServiceReads || []).length === 1", timeout=15000
        )

        # The read is the exact provider the drawer selected, and there is no
        # second one: no other `ui_action` left the client for the commit.
        read = page.evaluate("() => window.__elosernServiceReads[0]")
        self.assertEqual(read["action_id"], "services.open")
        provider_id = panel["guild"]["provider_id"]
        self.assertEqual(read["payload"], {"npc_id": provider_id})
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
        )

        # The clerk's own correlated answer: its guild section and no rank or
        # shop section, exactly the shape `services.open` returns.
        new_name = "新增任務委託"
        answer = json.loads(json.dumps(self._services_panel(page)))
        answer["rank"] = None
        answer["shop"] = None
        answer["guild"]["board"][0]["display_name"] = new_name
        accepted = page.evaluate(
            """(args) => {
              const store = window.__elosernBridge.store;
              const view = store.view;
              return store.receive(view.generation, 'ui_action_result', [{
                protocol_version: 1,
                presentation_epoch: view.epoch,
                request_id: args.requestId,
                outcome: 'success',
                code: 'services_open',
                message: '服務資訊',
                presentation_revision: view.revision,
                data: { npc_id: args.providerId, services: args.services },
              }], {});
            }""",
            {
                "requestId": read["request_id"],
                "providerId": provider_id,
                "services": answer,
            },
        )
        self.assertTrue(accepted.get("accepted"), accepted)
        page.wait_for_function(
            "([selector, title]) => {"
            " const el = document.querySelector(selector);"
            " return !!el && el.innerText.indexOf(title) !== -1; }",
            arg=[f'[data-testid="quest-drawer__row--{offer_key}"]', new_name],
            timeout=15000,
        )
        self.assertIn(new_name, board_row.inner_text())
        self.assertNotIn(old_name, board_row.inner_text())
        self.assertNotIn(decoy_name, board_row.inner_text())
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), before)
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
        )
        self.assertEqual(page.evaluate("() => window.__elosernServiceReads.length"), 1)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)


    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-quest-drawer::the-guild-board-is-organized-by-difficulty-grade-tabs")
    def test_grade_rail_reaches_a_locked_grade_by_keyboard(self):
        """The grade above the holder's rank is locked: selecting it by
        keyboard lists no offer, shows no detail or accept, and says the grade
        opens after a promotion."""
        page = self.logged_in_page()
        panel = self._wait_services_available(page)
        ladder = panel["guild"]["rank_ladder"]
        rank = panel["player"]["guild_rank"]
        locked = ladder[ladder.index(rank) + 1]

        self._open_guild_menu(page)
        # The counter exists only once the selected clerk's own read lands.
        page.wait_for_selector('[data-testid="quest-drawer__grade-rail"]', timeout=15000)
        self._select_quest_tab(page, "counter")
        tab = page.locator(f'[data-testid="quest-drawer__grade-rail"] [data-tab-key="{locked}"]')
        self.assertIn("is-locked", tab.get_attribute("class"))
        self.assertIsNone(tab.get_attribute("aria-disabled"))
        own = page.locator(f'[data-testid="quest-drawer__grade-rail"] [data-tab-key="{rank}"]')
        self.assertIn("is-mark", own.get_attribute("class"))
        self._select_board_grade(page, locked)
        page.wait_for_selector('[data-testid="quest-drawer__empty"]', timeout=5000)
        self.assertIn(f"{locked} 級委託要等你的公會等級提升後才會開放", page.locator('[data-testid="quest-drawer__empty"]').inner_text())
        self.assertEqual(page.locator('[data-testid^="quest-drawer__row--"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="quest-drawer__detail"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="quest-drawer__accept"]').count(), 0)
        # The clerk's own read carries the board only, so no rank card renders
        # beside it on any grade: the independent rank surface belongs to the
        # examination reception's provider, not this one.
        self.assertEqual(page.locator('[data-testid="guild-rank-card"]').count(), 0)
        self.assertTrue(tab.is_visible())


class GuildQuestJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_active_quest"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    @covers_requirement(
        "webclient-quest-drawer::the-detail-action-bar-mirrors-server-descriptors",
    )
    def test_abandon_requires_confirmation(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        self._open_guild_menu(page)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)
        # The drawer opens on the guild entry's own section; this journey walks
        # the quest book, so select its tab explicitly.
        self._select_quest_tab(page, "book")
        # The book lands on the in-progress state with the held quest
        # selected; its detail mirrors the counter's abandon descriptor.
        self._tab_until_focused(page, '[data-testid="quest-drawer__abandon"]', max_presses=40)
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 0)

        # Reveal confirmation: it names the quest, and focus moves to cancel.
        _press(page, "Enter")
        page.wait_for_selector('[data-testid="quest-drawer__abandon-confirm"]', timeout=5000)
        quest_name = page.locator('[data-testid="quest-drawer__detail"] .quest-detail__title').inner_text().strip()
        self.assertIn(f"放棄「{quest_name}」", page.locator('[data-testid="quest-drawer__abandon-confirm"]').inner_text())
        self.assertTrue(
            page.evaluate(
                "() => document.activeElement && document.activeElement.matches("
                "'[data-testid=\"quest-drawer__abandon-confirm-no\"]')"
            )
        )
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 0)

        # Confirm abandon
        self._tab_until_focused(page, '[data-testid="quest-drawer__abandon-confirm-yes"]')
        _press(page, "Enter")  # 確認放棄
        self._wait_panel(page, lambda p: p["guild"]["quests"][0]["state"] == "failed")
        self.assertEqual(sent_action_count(page, "guild.quest_abandon"), 1)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    @covers_requirement(
        "webclient-quest-drawer::selecting-a-quest-shows-its-full-detail-beside-the-list",
    )
    def test_quest_vanishes_book_drops_row_drawer_stays_open(self):
        """Frameless drawer retention: when a committed update removes a quest,
        the quest book drops the row and the drawer stays open without a frame pop."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["pagination"]["quest_total"], 1)

        self._open_guild_menu(page)
        # The drawer opens on the guild entry's own section; this journey walks
        # the quest book, whose rows come from the committed quest_log panel.
        self._select_quest_tab(page, "book")
        self.assertEqual(page.locator('[data-testid^="quest-drawer__row--"]').count(), 1)
        self.assertEqual(store_state(page)["hudDrawer"], "quest")
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")

        # Injection: the quest disappears from the committed panel.
        updated = self._services_panel(page)
        updated["guild"]["quests"] = []
        updated["pagination"]["quest_total"] = 0
        # The quest book reads the dedicated quest_log panel (quest-drawer
        # split): the committed update must empty that panel too, exactly as
        # the server's affected-panel set does for a quest mutation.
        quest_log = dict(
            (store_state(page)["panels"] or {}).get("quest_log") or {}
        )
        quest_log["rows"] = []
        inject_update(page, {"services": updated, "quest_log": quest_log})

        # The quest row drops from the book, and the drawer stays open at unchanged depth.
        page.wait_for_selector('[data-testid="quest-drawer__empty"]', timeout=5000)
        self.assertEqual(page.locator('[data-testid^="quest-drawer__row--"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="quest-drawer__detail"]').count(), 0)
        self.assertEqual(store_state(page)["hudDrawer"], "quest")
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)

    @covers_requirement(
        "webclient-quest-drawer::the-guild-counter-tab-presents-counter-business-only",
        "webclient-quest-drawer::the-quest-drawer-is-a-two-level-icon-tabbed-surface",
    )
    def test_drawer_renders_book_and_counter_without_duplication(self):
        """quest-drawer-split, re-shaped by quest-drawer-book-tab: in front of
        the clerk the drawer hosts both tabs — the quest book and the
        counter — and the accepted quest appears exactly once: the counter
        tab lists no quest-record rows."""
        page = self.logged_in_page()
        self._wait_services_available(page)
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-drawer"]', timeout=15000)
        body = page.locator('[data-testid="quest-drawer"]')
        # Exactly one book row for the held quest.
        book_rows = body.locator('[data-testid^="quest-drawer__row--"]')
        self.assertEqual(book_rows.count(), 1)
        held_id = book_rows.first.get_attribute("data-quest-id")
        self.assertEqual(page.locator('[data-testid="quest-drawer__counter"]').count(), 0)
        # The counter tab is enabled in front of the clerk; its rows are
        # board offers only, never the held quest record.
        self._select_quest_tab(page, "counter")
        self.assertEqual(page.locator('[data-testid="quest-drawer__counter"]').count(), 1)
        offered = [
            row.get_attribute("data-quest-id")
            for row in body.locator('[data-testid^="quest-drawer__row--"]').all()
        ]
        self.assertNotIn(held_id, offered)


class GuildTurninJourneys(ServicesBrowserTest):
    SERVICES_MODE = "guild_completed_quest"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region")
    @covers_requirement(
        "webclient-quest-drawer::the-detail-action-bar-mirrors-server-descriptors",
        "webclient-quest-drawer::the-quest-book-shows-one-quest-state-at-a-time",
    )
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
        # The drawer opens on the guild entry's own section; the book carries
        # the completed quest's counters, so select its tab explicitly.
        self._select_quest_tab(page, "book")
        # The completed quest's detail carries the counter's enabled turn-in,
        # and the completed count is emphasized while it waits.
        completed_count = page.locator(
            '[data-testid="quest-drawer__state-rail"] [data-tab-key="completed"] .icon-tabs__count'
        )
        self.assertIn("icon-tabs__count--hot", completed_count.get_attribute("class"))
        self._select_quest_state(page, "completed")
        self._tab_until_focused(page, '[data-testid="quest-drawer__turnin"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["wallet"] == wallet_after)
        self.assertEqual(sent_action_count(page, "guild.quest_turnin"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.quest_turnin"
        )
        # The turn-in is a provider mutation: it names the clerk whose own
        # read carried the enabled descriptor.
        self.assertEqual(
            payload,
            {
                "quest_id": f"{guild_offer_quest_key()}:1",
                "npc_id": panel["guild"]["provider_id"],
            },
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-menu"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="hud-drawer"] [data-testid="dock-detail"]').count(), 0)


class GuildExamAppointmentJourney(ServicesBrowserTest):
    """Presence-first appointment: absent-host schedule, merit rejection, start.

    One keyboard journey per acceptance viewport observes the enabled
    below-threshold request answering planned attendance with byte-equal
    canonical state, the host's real weekly traversal into the hall, the
    present-host merit rejection, and the eligible start into combat.
    """

    SERVICES_MODE = "guild_exam_appointment"

    def _ensure_reception_counter(self, page):
        # The examination request is the independent rank surface's own
        # action (npc-targeted-service-flows): the drawer renders it only when
        # its slot read the examination reception's provider, so reopen the
        # drawer through that host's entry whenever the request is not there.
        if page.locator('[data-testid="guild-counter__exam"]').count() == 0:
            self._open_reception_counter(page)
        page.locator('[data-testid="guild-counter__exam"]').wait_for(state="visible")

    def _request_exam(self, page, expected_code):
        before = sent_action_count(page, "guild.exam_request")
        self._ensure_reception_counter(page)
        self._tab_until_focused(page, '[data-testid="guild-counter__exam"]')
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: sent_action_count(page, "guild.exam_request") == before + 1
            and (s.get("lastActionResult") or {}).get("code") == expected_code,
        )
        return store_state(page)["lastActionResult"]

    def _journey(self, viewport):
        page = self.logged_in_page(viewport)
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        rank = panel["rank"]
        reception_id = rank["provider_id"]
        next_rank = rank["next_rank"]
        self.assertTrue(next_rank)
        # Below threshold the request stays available: merit qualification
        # and request availability are distinct facts.
        self.assertFalse(rank["merit_qualified"])
        self.assertTrue(rank["exam_request"]["enabled"])
        self.assertEqual(rank["exam_request"]["action_id"], "guild.exam_request")

        # 1. Absent host: planned attendance, read-only, still exploring.
        result = self._request_exam(page, "exam_schedule")
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(self._services_panel(page), panel)
        self.assertNotEqual(self._dock_mode(page), "combat")
        sent = page.evaluate("window.__elosernSent || []")
        payloads = [
            args[0]["payload"] for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.exam_request"
        ]
        # The request names the reception provider whose rank surface it was
        # activated from (the rank payload's own provider_id).
        self.assertEqual(payloads, [{"target_rank": next_rank, "npc_id": reception_id}])

        # 2. Time passes; the weekly schedule walks the host into the hall
        # through its real Exit. The same request now reaches the merit gate.
        page.evaluate(
            "(s) => Elosern.actions.submit('explore.wait', { seconds: s })",
            SYNTH_EXAM_APPOINTMENT["wait_seconds"],
        )
        request_before = store_state(page)["lastActionResult"]["requestId"]
        wait_for_store_state(
            page,
            lambda s: (s.get("lastActionResult") or {}).get("requestId") != request_before
            and (s.get("lastActionResult") or {}).get("outcome") == "success"
            and (s.get("serverTime") or {}).get("hour")
            # A skip is bounded by the next registered schedule boundary
            # (mental-time contract): the host's own arrival time is exactly
            # that boundary here, so the wait lands on it rather than running
            # the requested three hours through the appointment it proves.
            == SYNTH_EXAM_APPOINTMENT["arrive_offset"] // 3600,
        )
        result = self._request_exam(page, "below_threshold")
        self.assertEqual(result["outcome"], "rejected")
        self.assertNotEqual(self._dock_mode(page), "combat")

        # 3. The completed board quest's merit reaches the threshold; the
        # present qualified host now starts the simulated examination. The
        # turn-in belongs to the clerk's own board read, so that step reopens
        # the drawer through the clerk before the request returns to the
        # reception counter.
        self._open_guild_menu(page)
        page.wait_for_selector('[data-testid="quest-drawer__grade-rail"]', timeout=15000)
        self._select_quest_tab(page, "book")
        self._select_quest_state(page, "completed")
        self._tab_until_focused(page, '[data-testid="quest-drawer__turnin"]')
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["rank"]["merit_qualified"] is True)
        self._request_exam(page, "exam_started")
        self._wait_combat_mode(page)
        self.assertEqual(sent_action_count(page, "guild.exam_request"), 3)
        services = self._services_panel(page)
        self.assertTrue(services["available"])
        self.assertIsNone(services["guild"])
        self.assertIsNotNone(services["player"])

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    @covers_requirement("webclient-service-menus::service-action-completion-updates-canonical-panels-and-preserves-narrative")
    def test_appointment_journey_at_the_reference_viewport(self):
        self._journey((1451, 790))

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_appointment_journey_at_the_wide_viewport(self):
        self._journey((2560, 1440))

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
