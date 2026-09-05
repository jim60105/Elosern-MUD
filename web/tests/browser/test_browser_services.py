"""Keyboard-only services browser acceptance (webclient-service-menus 5.2-5.5).

These journeys drive the real Evennia server's guild/quest/shop/inventory
services through the Vue services panels (ShopPanel, QuestBoard, InventoryPanel):
registration and idempotent
re-registration, board accept, abandon behind an explicit confirmation,
completed-quest turn-in, exam-to-combat mode transition with the service dock
torn down, shop open/closed at fixed world times, buy/sell quantity validation
with exact copper/stock/wallet outcomes, repeated-inventory display with no
use/equip control, and reconnect retention.

Each service journey boots its own dedicated isolated server so the mutated
character state (registration, wallet, inventory, quest log, exam session)
never leaks into another journey. All fixtures are deterministic; no remote,
LLM, or image service is involved.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import DEFAULT_VIEWPORT, BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_update,
    login_and_open,
    outbound_messages,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ServicesBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with a services fixture."""

    SERVICES_MODE = ""

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    # Extra seed env vars a subclass can add (e.g. ELOSERN_BROWSER_CREATION
    # to boot a creation-pending character whose services panel is unavailable).
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

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

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
        # First step of the journey: open the reference drawer that hosts the
        # service frame (H4 task 4.3). The body's own testid is then the
        # drawer-body readiness gate.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        wait_for_store_state(
            page,
            lambda s: True,
            dom_readiness={
                "selector": '[data-testid="quest-board"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"quest-board\"]'); "
                    "if (!el) { return false; } "
                    "const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "quest drawer body (quest-board) rendered inside the open drawer",
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
        and inventory through the exploration root's Inventory entry — which
        opens the 背包 drawer frameless (make-inventory-drawer-frameless): no
        keyboard frame is pushed and the router's stack is unchanged. The root
        is a single seven-column row (grid geometry), so horizontal arrows
        move across it; submenus are 2-column grids.
        """
        focus_action_dock(page)
        if surface_key == "inventory":
            # Navigate to the Inventory tab by the store's committed focus
            # KEY: the declarative root's tab set is capability-driven (H3
            # design D5 appends the 建議 tab when the suggestions envelope is
            # not `unavailable`) and a drawer-close pop restores focus to the
            # opener's key, so focus may start on any root tab). Step by
            # computed index delta — the tab row wraps, so step toward the
            # target in whichever direction is nearer and assert arrival.
            layout = page.evaluate(
                """() => ({
                  keys: Array.from(document.querySelectorAll(
                    '#action-dock [data-item-key]')).map(
                      (el) => el.getAttribute('data-item-key')),
                  focus: window.__elosernBridge.store.view.focus.key,
                })"""
            )
            target = layout["keys"].index("inventory")
            start = layout["keys"].index(layout["focus"])
            step = "ArrowRight" if target >= start else "ArrowLeft"
            for _ in range(abs(target - start)):
                _press(page, step)
            focused = page.evaluate(
                "() => window.__elosernBridge.store.view.focus.key"
            )
            assert focused == "inventory", focused
            _press(page, "Enter")
            return self._services_panel(page)
        # guild/shop: Interact -> first target -> navigate service entry.
        _press(page, "ArrowRight")  # Look
        _press(page, "ArrowRight")  # Interact
        _press(page, "Enter")  # open Interact
        _press(page, "Enter")  # select the first present target
        if surface_key == "guild":
            # The guild staff carries scripted talk first; the navigate entry
            # follows it in the second grid column.
            _press(page, "ArrowRight")
        _press(page, "Enter")  # open the service submenu
        return self._services_panel(page)

    def _open_guild_menu(self, page):
        return self._open_surface(page, "guild")

    def _open_shop_menu(self, page):
        return self._open_surface(page, "shop")


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
        self.assertEqual(payload, {"definition_key": "introductory_hunt"})

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
        self.assertEqual(offer[0]["payload"], {"definition_key": "introductory_hunt"})
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
        self.assertEqual(page.locator('[data-testid="quest-board"]').count(), 0)
        # Neither pop dispatched anything.
        self.assertEqual(
            len([m for m in outbound_messages(page) if m[0] == "ui_action"]), sent_before
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

        self._open_guild_menu(page)
        _press(page, "ArrowRight")  # board (second grid column)
        _press(page, "ArrowDown")  # exam_start (second grid row)
        _press(page, "ArrowLeft")  # quests (second grid row, first column)
        _press(page, "Enter")
        _press(page, "Enter")  # the quest row
        _press(page, "ArrowDown")  # 回報 (first column, second row)
        _press(page, "Enter")
        self._wait_panel(page, lambda p: p["player"]["wallet"] == 1050)
        self.assertEqual(sent_action_count(page, "guild.quest_turnin"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "guild.quest_turnin"
        )
        self.assertEqual(payload, {"quest_id": "introductory_hunt:1"})


class GuildDialogueTurninJourneys(ServicesBrowserTest):
    """The guild staff's 回報 dialogue chip reports reportable quests."""

    SERVICES_MODE = "guild_completed_quest"

    @covers_requirement("webclient-exploration-menu::explore-talk-scripted-invokes-the-deterministic-dialogue-api-with-keyword-buttons")
    def test_turnin_keyword_reports_listing_without_state_change(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["player"]["wallet"], 1000)
        self.assertEqual(panel["guild"]["quests"][0]["state"], "completed")
        _talk_before = store_state(page).get("lastActionResult")
        _talk_before_request = _talk_before["requestId"] if _talk_before else None

        # Interact -> the guild staff (first present target) -> 交談 -> 回報.
        focus_action_dock(page)
        _press(page, "ArrowRight")  # Look
        _press(page, "ArrowRight")  # Interact
        _press(page, "Enter")  # open Interact
        _press(page, "Enter")  # select the guild staff
        _press(page, "Enter")  # 交談 (scripted affordance)
        _press(page, "ArrowDown")  # 公會 (second keyword row)
        _press(page, "ArrowDown")  # 回報 (third keyword row)
        _press(page, "Enter")  # tap the 回報 chip
        wait_for_store_state(
            page,
            lambda s: (
                s.get("lastActionResult") is not None
                and s["lastActionResult"]["requestId"] != _talk_before_request
            ),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const n = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return !!n && n.innerText.indexOf('可以交回') !== -1; }"
                ),
                "description": "narrative-feed shows 可以交回",
            },
            timeout=30000,
        )
        sent = page.evaluate("window.__elosernSent || []")
        talk = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.talk_scripted"
        ]
        self.assertEqual(len(talk), 1)
        self.assertEqual(talk[0]["payload"]["keyword_id"], "回報")
        # The listing never settles: wallet, quest state, and claims stay put
        # and no turn-in action crosses the wire.
        self.assertEqual(sent_action_count(page, "guild.quest_turnin"), 0)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["player"]["wallet"], 1000)
        self.assertEqual(panel["guild"]["quests"][0]["state"], "completed")
        self.assertTrue(panel["guild"]["quests"][0]["turnin"]["enabled"])


class GuildExamJourney(ServicesBrowserTest):
    SERVICES_MODE = "guild_exam"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_exam_eligibility_transitions_into_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["guild"]["rank"]["next_rank"], "E")
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
        self.assertEqual(payload, {"target_rank": "E"})
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


class ShopJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_open"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_buy_quantity_validation_exact_copper(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertTrue(panel["shop"]["open"])
        self.assertEqual(panel["player"]["wallet"], 1000)

        self._open_surface(page, "shop")
        _press(page, "Enter")  # 貨架
        _press(page, "Enter")  # meal buy row
        # Quantity form: an oversized value is rejected before sending.
        _press(page, "3", wait_ms=40)
        _press(page, "0", wait_ms=40)
        _press(page, "Enter", wait_ms=40)
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)
        # Cancel the form and re-enter a valid bounded quantity.
        _press(page, "Escape", wait_ms=40)
        _press(page, "Enter", wait_ms=40)  # meal buy row again
        _press(page, "2", wait_ms=40)
        _press(page, "Enter", wait_ms=40)
        page.wait_for_timeout(500)
        debug = page.evaluate(
            """() => ({
              sent: window.__elosernSent || [],
              quantityOpen: document.querySelector('[data-testid=\"services-quantity\"]') !== null,
              quantityValue: document.querySelector('[data-testid=\"services-quantity-value\"]')
                ? document.querySelector('[data-testid=\"services-quantity-value\"]').textContent
                : null,
              depth: window.__elosernBridge.router.depth(),
              current: window.__elosernBridge.router.currentItem() &&
                       window.__elosernBridge.router.currentItem().label,
            })"""
        )
        self.assertEqual(
            debug["quantityOpen"], False, "quantity form must close on submit: %r" % (debug,)
        )
        self._wait_panel(page, lambda p: p["player"]["wallet"] == 980)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "shop.buy"
        )
        self.assertEqual(payload, {"item_key": "meal", "quantity": 2})
        self.assertEqual(self._services_panel(page)["player"]["wallet"], 980)

    @covers_requirement(
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
        "webclient-contextual-hud::the-bag-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
    )
    def test_sell_and_repeated_inventory_without_use_control(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        rows = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        self.assertEqual(rows["meal"]["held"], 2)
        # services v3 ships a server-authored action on every inventory row;
        # the full-HP store fixture refuses the potion with the stable
        # hp_full reason.
        self.assertEqual(rows["healing_potion"]["action"]["action_id"], "inventory.use")
        self.assertFalse(rows["healing_potion"]["action"]["enabled"])
        self.assertEqual(
            rows["healing_potion"]["action"]["disabled_reason"]["code"], "hp_full"
        )

        # The merchant is at its meal stock cap, so the sellable row is the
        # held healing_potion (stock 3/5, sellable and offered).
        self._open_surface(page, "shop")
        _press(page, "ArrowRight")  # 販賣 (second grid column)
        _press(page, "Enter")
        _press(page, "Enter")  # healing_potion sell row
        _press(page, "1", wait_ms=40)
        _press(page, "Enter", wait_ms=40)
        self._wait_panel(page, lambda p: p["player"]["wallet"] == 1050)
        self.assertEqual(sent_action_count(page, "shop.sell"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "shop.sell"
        )
        self.assertEqual(payload, {"item_key": "healing_potion", "quantity": 1})
        rows = {row["item_key"]: row for row in self._services_panel(page)["inventory"]["rows"]}
        self.assertNotIn("healing_potion", rows)
        self.assertEqual(rows["meal"]["held"], 2)

        # make-inventory-drawer-frameless: the 背包 entry opens the bag
        # drawer frameless. The drawer body is only its own three-section
        # stack — the committed rows render as tiles, never as a hosted
        # keyboard row region — and the router's frame stack is exactly the
        # same around open+close. The close control closes the hosted 商店
        # drawer first (its pop + re-home is unchanged behavior; the click is
        # focus-independent), then the exploration root's 背包 entry (sixth
        # grid cell) opens the bag.
        page.locator('[data-testid="hud-drawer-close"]').click()
        page.wait_for_timeout(120)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        # Declarative pop (webclient-frame-resolution): closing the drawer
        # pops exactly the hosted shop frame; the exploration frames opened
        # on the way in (Interact -> target) remain and the pop restores
        # focus to the navigate row. Keyboard back to the exploration root
        # (Escape pops without dispatching) before using the 背包 entry.
        sent_before_rehome = sent_action_count(page)
        deadline_depth = time.monotonic() + 10
        while (
            page.evaluate("() => window.__elosernBridge.router.depth()") > 1
            and time.monotonic() < deadline_depth
        ):
            _press(page, "Escape", wait_ms=120)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.depth()"),
            1,
            "Escape must pop back to the exploration root",
        )
        self.assertEqual(
            sent_action_count(page),
            sent_before_rehome,
            "Escape re-homing to the root dispatches no action",
        )

        def _frame_state():
            return page.evaluate(
                """() => ({
                  depth: window.__elosernBridge.router.depth(),
                  trail: window.__elosernBridge.router.trail(),
                })"""
            )

        frame_before = _frame_state()
        sent_before = sent_action_count(page)
        bag_panel = self._open_surface(page, "inventory")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") == "inventory")
        committed = sorted(
            "inventory-panel__tile--" + row["item_key"]
            for row in bag_panel["inventory"]["rows"]
        )
        tiles = page.evaluate(
            """() => Array.from(
                document.querySelectorAll('[data-testid^="inventory-panel__tile--"]')
              ).map((t) => t.getAttribute("data-testid")).sort()"""
        )
        self.assertEqual(tiles, committed, "the bag tiles are exactly the committed rows")
        sections = page.evaluate(
            """() => ({
              equipment: !!document.querySelector('[data-testid="equipment-doll"]'),
              items: !!document.querySelector('[data-testid="inventory-panel__section--items"]'),
              money: !!document.querySelector('[data-testid="inventory-panel__section--wallet"]'),
            })"""
        )
        self.assertEqual(sections, {"equipment": True, "items": True, "money": True})
        hosted = page.evaluate(
            """() => {
              const drawer = document.querySelector('[data-testid="hud-drawer"]');
              return {
                menu: drawer.querySelectorAll('[data-testid="dock-menu"]').length,
                detail: drawer.querySelectorAll('[data-testid="dock-detail"]').length,
              };
            }"""
        )
        self.assertEqual(hosted, {"menu": 0, "detail": 0})
        # The open pushed nothing: same stack, same breadcrumb, same focused
        # row, and it dispatched no action.
        frame_open = _frame_state()
        self.assertEqual(frame_open["depth"], frame_before["depth"])
        self.assertEqual(frame_open["trail"], frame_before["trail"])
        _press(page, "Escape", wait_ms=120)  # close the bag (frameless close)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(_frame_state(), frame_before, "closing the bag moved the router")
        self.assertEqual(sent_action_count(page), sent_before, "the frameless 背包 entry dispatches no action")

        # No remote or ambiguous host control is ever rendered: every service
        # control is a bounded submenu/action row, never a dbref or a host
        # identity, and no submitted payload carries a host/branch/actor field.
        control_keys = page.evaluate(
            """() => Array.from(document.querySelectorAll('.dock-menu-item'))
              .map((el) => el.getAttribute('data-item-key'))"""
        )
        host_like = [k for k in control_keys if k and "#" in k or (k and k.isdigit())]
        self.assertEqual(
            host_like,
            [],
            "a remote or ambiguous host must never render as a service control",
        )
        for cmdname, args, _kwargs in outbound_messages(page):
            if cmdname != "ui_action" or not args:
                continue
            action_id = args[0].get("action_id", "")
            if not action_id.startswith(("guild.", "shop.")):
                continue
            submitted = args[0].get("payload", {})
            for forbidden in ("host", "branch", "session", "actor", "dbref", "identity"):
                self.assertNotIn(
                    forbidden,
                    submitted,
                    f"{action_id} payload must never carry a {forbidden} field",
                )


class ServiceDispatchJourneys(ServicesBrowserTest):
    """Stale and duplicate submission through the real server dispatcher.

    A raw ``ui_action`` envelope is delivered over the same WebSocket the
    client uses. An older ``base_revision`` must return the dispatcher's
    ``stale`` outcome with a fresh full snapshot and no adapter invocation;
    a replayed ``request_id`` must return the cached first result without a
    second execution.
    """

    SERVICES_MODE = "store_open"

    def _raw_ui_action(self, page, action_id, payload, request_id, base_revision):
        page.evaluate(
            """({action_id, payload, request_id, base_revision}) => {
              const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.epoch,
                request_id,
                base_revision,
                action_id,
                payload,
              }], {});
            }""",
            {"action_id": action_id, "payload": payload, "request_id": request_id, "base_revision": base_revision},
        )

    def _wait_result(self, page, predicate, timeout=30000):
        def _result_ready(state):
            result = state.get("lastActionResult")
            return result is not None and bool(predicate(result))
        wait_for_store_state(page, _result_ready, timeout=timeout)
        # The store-state gate returns None; read the committed result directly.
        return store_state(page).get("lastActionResult")

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_stale_revision_returns_stale_without_mutation(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["player"]["wallet"], 1000)
        stale_revision = store_state(page)["revision"] - 1

        self._raw_ui_action(
            page, "shop.buy", {"item_key": "meal", "quantity": 1}, "stale-buy-1", stale_revision
        )
        result = self._wait_result(page, lambda r: r["requestId"] == "stale-buy-1")
        self.assertEqual(result["outcome"], "stale")
        self.assertEqual(result["code"], "stale")
        # No adapter ran and canonical state is unchanged: the wallet is still
        # 1000 and the refreshed panel reports the same stock.
        panel = self._services_panel(page)
        self.assertEqual(panel["player"]["wallet"], 1000)

    @covers_requirement("webclient-service-menus::service-actions-reject-stale-duplicate-and-tampered-input-without-mutation")
    def test_duplicate_request_executes_buy_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertEqual(panel["player"]["wallet"], 1000)
        revision = store_state(page)["revision"]

        # First delivery executes the buy exactly once.
        self._raw_ui_action(
            page, "shop.buy", {"item_key": "meal", "quantity": 1}, "dup-buy-1", revision
        )
        first = self._wait_result(
            page, lambda r: r["requestId"] == "dup-buy-1" and r["outcome"] == "success"
        )
        self._wait_panel(page, lambda p: p["player"]["wallet"] == 990)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)

        # A replayed live request ID returns the cached result and never
        # re-executes the trade: the same envelope is delivered again, the
        # second result arrives, and the wallet stays at exactly one purchase.
        self._raw_ui_action(
            page, "shop.buy", {"item_key": "meal", "quantity": 1}, "dup-buy-1", revision
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if sent_action_count(page, "shop.buy") >= 2:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "shop.buy"), 2)
        page.wait_for_timeout(800)
        self.assertEqual(self._services_panel(page)["player"]["wallet"], 990)


class ShopClosedJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_closed"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_closed_shop_disables_all_trades(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["shop"]["open"])

        self._open_surface(page, "shop")
        _press(page, "Enter")  # 貨架
        for _ in range(3):
            _press(page, "Enter")
        page.wait_for_timeout(400)
        self.assertEqual(sent_action_count(page), 0)
        stock = page.evaluate(
            """() => Array.from(document.querySelectorAll('.dock-menu-item'))
              .map((el) => ({ key: el.getAttribute('data-item-key'),
                              disabled: el.getAttribute('aria-disabled') === 'true' }))"""
        )
        disabled = [entry for entry in stock if entry["key"].startswith("stock-")]
        self.assertTrue(disabled, "stock rows must render")
        for entry in disabled:
            self.assertTrue(entry["disabled"], "closed shop rows must be disabled")


class ReconnectJourney(ServicesBrowserTest):
    SERVICES_MODE = "store_open"

    @covers_requirement(
        "webclient-service-menus::reconnect-rebuilds-services-without-replaying-intent",
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
    )
    def test_reconnect_rebuilds_services_and_discards_unsubmitted_quantity(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        wallet = panel["player"]["wallet"]
        generation_before = store_state(page)["generation"]

        # Enter the quantity form but do not submit; the value is local.
        self._open_surface(page, "shop")
        _press(page, "Enter")  # 貨架
        _press(page, "Enter")  # meal buy row
        _press(page, "5", wait_ms=40)
        self.assertTrue(page.evaluate("document.querySelector('[data-testid=\"services-quantity\"]') !== null"))

        # Abnormally close the raw WebSocket (preserves login) and wait for the
        # offline overlay.
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const o = document.getElementById('elosern-offline-overlay'); "
                    "return !!o && o.getAttribute('data-visible') === 'true'; }"
                ),
                "description": "offline overlay visible while disconnected",
            },
            timeout=30000,
        )
        # Wait for the reconnected transport to open a new generation, nudging
        # the stock reconnection path once if the socket did not reopen.
        deadline = time.monotonic() + 30
        reconnects = 0
        while time.monotonic() < deadline:
            state = store_state_or_none(page)
            if state and state["generation"] > generation_before:
                break
            if reconnects == 0 and time.monotonic() > deadline - 20:
                page.evaluate("Evennia.connect()")
                reconnects += 1
            page.wait_for_timeout(500)
        wait_for_store_state(
            page,
            lambda s: s.get("connected") and s.get("phase") == "active",
            timeout=30000,
        )
        self._wait_services_available(page)
        panel = self._services_panel(page)
        # The new snapshot rebuilt the services view from canonical persistence.
        self.assertEqual(panel["player"]["wallet"], wallet)
        self.assertTrue(panel["available"])
        # The unsubmitted quantity was discarded and nothing was retried.
        self.assertEqual(
            page.evaluate("document.querySelector('[data-testid=\"services-quantity\"]') === null"),
            True,
            "unsubmitted quantity must be discarded on reconnect",
        )
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)


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

        # The service frame (quest-board) renders inside the reference drawer
        # (H4: the right-column panels were emptied into drawers).
        inside_drawer = page.evaluate(
            """() => {
              const drawer = document.querySelector('[data-testid="hud-drawer"]');
              const body = document.querySelector('[data-testid="quest-board"]');
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
              const surface = document.querySelector('[data-testid="quest-board"]');
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
    fabricated wallet, stock, quest, or lore rows.

    The `services` panel is only unavailable outside exploration mode, so this
    journey boots a creation-pending character (``ELOSERN_BROWSER_CREATION=1``)
    and logs in with the dedicated creation account; the pending-creation
    character is not in exploration, so the panel commits its registry-owned
    ``services_unavailable`` form.
    """

    SERVICES_MODE = ""
    # Boot the creation-pending fixture so the character is non-exploration.
    EXTRA_ENV = {"ELOSERN_BROWSER_CREATION": "1"}
    CREATION_ACCOUNT = "browsercreator"
    CREATION_PASSWORD = "CreationBrowserTest!2026"

    def logged_in_page(self, viewport: tuple[int, int] = DEFAULT_VIEWPORT):
        """Log in with the creation account (a creation-pending character)."""
        page = self.new_page(viewport)
        login_and_open(
            page,
            self.webclient_url,
            self.base_url,
            account=self.CREATION_ACCOUNT,
            password=self.CREATION_PASSWORD,
        )
        return page

    def _wait_services_committed(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("services") is not None,
            timeout=timeout,
        )
        return self._services_panel(page)

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_unavailable_services_drawer_renders_reason_only(self):
        page = self.logged_in_page()
        panel = self._wait_services_committed(page)
        # The character is at the exploration root (no service interior), so
        # the services panel is the registry-owned unavailable form.
        self.assertFalse(panel["available"])
        self.assertIsNotNone(panel.get("reason"))

        # Open the quest reference drawer (the gate's first step).
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        page.wait_for_selector('[data-testid="quest-board"]', timeout=15000)
        board = page.locator('[data-testid="quest-board"]')
        board_text = board.inner_text()
        # The drawer body renders the registry-owned reason verbatim.
        self.assertIn(panel["reason"]["message"], board_text)
        # No fabricated board / quest / rank rows: the unavailable form carries
        # no guild section, so the board and quest-detail rows are absent.
        self.assertEqual(
            page.locator('[data-testid="quest-board__board-row--"]').count(), 0,
            "no fabricated quest-board rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="quest-board__quest-row--"]').count(), 0,
            "no fabricated active-quest rows in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="quest-board__rankblock"]').count(), 0,
            "no fabricated rank block in the unavailable form")
        self.assertEqual(
            page.locator('[data-testid="quest-board__abandon"]').count(), 0,
            "no fabricated abandon control in the unavailable form")


if __name__ == "__main__":
    import unittest

    unittest.main()
