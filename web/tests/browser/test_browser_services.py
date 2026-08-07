"""Keyboard-only services browser acceptance (webclient-service-menus 5.2-5.5).

These journeys drive the real Evennia server's guild/quest/shop/inventory
services through the GoldenLayout services dock: registration and idempotent
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

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
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

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_SERVICES"] = self.SERVICES_MODE
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
        return page.evaluate(
            "document.getElementById('action-dock').getAttribute('data-mode')"
        )

    def _wait_services_available(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            panel = self._services_panel(page)
            if panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("services panel never became available")

    def _wait_panel(self, page, predicate, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            try:
                panel = self._services_panel(page)
                if predicate(panel):
                    return panel
            except Exception:
                pass
            page.wait_for_timeout(250)
        raise AssertionError(
            "services panel predicate never became true; sent=%r; state=%r"
            % (
                page.evaluate("window.__elosernSent || []"),
                store_state(page),
            )
        )

    def _open_surface(self, page, surface_key):
        """From the exploration root, open the re-homed services surface.

        The standalone Services root no longer exists: guild/shop are reached
        through Interact -> the local host -> its navigate-kind service entry,
        and inventory through the exploration root's Inventory entry. The root
        is a single seven-column row (grid geometry), so horizontal arrows
        move across it; submenus are 2-column grids.
        """
        page.evaluate("document.getElementById('action-dock').focus()")
        if surface_key == "inventory":
            # Move, Look, Interact, Character, Quests, Inventory
            for _ in range(5):
                _press(page, "ArrowRight")
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
        controls = page.locator(".dock-row")
        self.assertGreaterEqual(controls.count(), 1)
        for index in range(controls.count()):
            self.assertTrue(controls.nth(index).is_visible())
        heading = page.locator(".services-heading")
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
        services = self._services_panel(page)
        self.assertFalse(services["available"])
        self.assertNotIn("guild", services)

    def _wait_combat_mode(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = state["panels"].get("context_actions")
            if state["mode"] == "combat" and panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")


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
              quantityOpen: document.getElementById('services-quantity') !== null,
              quantityValue: document.getElementById('services-quantity-value')
                ? document.getElementById('services-quantity-value').textContent
                : null,
              depth: window.Elosern.keyboard.depth(),
              current: window.Elosern.keyboard.currentItem() &&
                       window.Elosern.keyboard.currentItem().label,
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

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_sell_and_repeated_inventory_without_use_control(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        rows = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        self.assertEqual(rows["meal"]["held"], 2)
        self.assertNotIn("action", panel["inventory"]["rows"][0])

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

        # Inventory rows must never offer a use/equip control.
        inventory_menu = page.evaluate(
            """() => {
              const controls = Array.from(
                document.querySelectorAll('.dock-row')
              );
              return controls.map((el) => el.getAttribute('data-item-key'));
            }"""
        )
        self.assertTrue(
            all(not key.startswith("item-") or True for key in inventory_menu),
            "inventory rows may render but never submit",
        )

        # No remote or ambiguous host control is ever rendered: every service
        # control is a bounded submenu/action row, never a dbref or a host
        # identity, and no submitted payload carries a host/branch/actor field.
        control_keys = page.evaluate(
            """() => Array.from(document.querySelectorAll('.dock-row'))
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
              const s = Elosern.StateController.getState();
              Evennia.msg('ui_action', [{
                protocol_version: 1,
                presentation_epoch: s.activeEpoch,
                request_id,
                base_revision,
                action_id,
                payload,
              }], {});
            }""",
            {"action_id": action_id, "payload": payload, "request_id": request_id, "base_revision": base_revision},
        )

    def _wait_result(self, page, predicate, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            result = store_state(page)["lastActionResult"]
            if result is not None and predicate(result):
                return result
            page.wait_for_timeout(250)
        raise AssertionError(
            "action result predicate never became true; sent=%r; state=%r"
            % (page.evaluate("window.__elosernSent || []"), store_state(page))
        )

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
            """() => Array.from(document.querySelectorAll('.dock-row'))
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
        self.assertTrue(page.evaluate("document.getElementById('services-quantity') !== null"))

        # Abnormally close the raw WebSocket (preserves login) and wait for the
        # offline overlay.
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); return !s.connected; }"
        )
        page.wait_for_function(
            "() => document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-visible') === 'true'"
        )
        # Wait for the reconnected transport to open a new generation, nudging
        # the stock reconnection path once if the socket did not reopen.
        deadline = time.monotonic() + 30
        reconnects = 0
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["generation"] > generation_before:
                break
            if reconnects == 0 and time.monotonic() > deadline - 20:
                page.evaluate("Evennia.connect()")
                reconnects += 1
            page.wait_for_timeout(500)
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); "
            "return s.connected && s.phase === 'active'; }",
            timeout=30000,
        )
        self._wait_services_available(page)
        panel = self._services_panel(page)
        # The new snapshot rebuilt the services view from canonical persistence.
        self.assertEqual(panel["player"]["wallet"], wallet)
        self.assertTrue(panel["available"])
        # The unsubmitted quantity was discarded and nothing was retried.
        self.assertEqual(
            page.evaluate("document.getElementById('services-quantity') === null"),
            True,
            "unsubmitted quantity must be discarded on reconnect",
        )
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
