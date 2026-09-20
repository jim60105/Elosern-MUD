"""Shop services browser journeys: buy/sell quantity validation with exact
copper/stock/wallet outcomes, the frameless bag-drawer inventory check, and the
closed shop disabling every trade.

Every body is byte-identical to its pre-split home in
``test_browser_services.py``.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import store_fixture_values

from .browser_helpers import (
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class ShopJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_open"

    @covers_requirement("webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded")
    def test_buy_quantity_validation_exact_copper(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertTrue(panel["shop"]["open"])
        self.assertEqual(panel["player"]["wallet"], 1000)
        # Every number the journey asserts is derived from the committed
        # panel: the first shelf row's identity and unit price.
        shelf = panel["shop"]["stock"][0]
        first_key, unit_buy = shelf["item_key"], shelf["buy_copper"]
        self.assertGreater(unit_buy, 0)
        expected_wallet = panel["player"]["wallet"] - 2 * unit_buy

        self._open_surface(page, "shop")
        _press(page, "Enter")  # 貨架
        _press(page, "Enter")  # first shelf buy row
        # Quantity form: an oversized value is rejected before sending.
        _press(page, "3", wait_ms=40)
        _press(page, "0", wait_ms=40)
        _press(page, "Enter", wait_ms=40)
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)
        # Cancel the form and re-enter a valid bounded quantity.
        _press(page, "Escape", wait_ms=40)
        _press(page, "Enter", wait_ms=40)  # first shelf buy row again
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
        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_wallet)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "shop.buy"
        )
        self.assertEqual(payload, {"item_key": first_key, "quantity": 2})
        self.assertEqual(self._services_panel(page)["player"]["wallet"], expected_wallet)

    @covers_requirement(
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
        "webclient-contextual-hud::the-bag-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
    )
    def test_sell_and_repeated_inventory_without_use_control(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        rows = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        STORE = store_fixture_values()
        potion, staple = STORE["potion_key"], STORE["staple_key"]
        self.assertEqual(rows[staple]["held"], 2)
        # services v3 ships a server-authored action on every inventory row;
        # the full-HP store fixture refuses the potion with the stable
        # hp_full reason.
        self.assertEqual(rows[potion]["action"]["action_id"], "inventory.use")
        self.assertFalse(rows[potion]["action"]["enabled"])
        self.assertEqual(
            rows[potion]["action"]["disabled_reason"]["code"], "hp_full"
        )

        # The merchant is at its staple stock cap, so the potion is the only
        # sellable offer (its held unit fits under the stock ceiling).
        sellable = {row["item_key"]: row for row in panel["shop"]["sellable"]}
        potion_row = sellable[potion]
        potion_index = list(sellable).index(potion)
        self.assertEqual(potion_row["held"], 1)
        wallet_before = panel["player"]["wallet"]
        expected_wallet = wallet_before + potion_row["sell_copper"]
        self._open_surface(page, "shop")
        _press(page, "ArrowRight")  # 販賣 (second grid column)
        _press(page, "Enter")
        for _ in range(potion_index):
            _press(page, "ArrowDown", wait_ms=40)
        _press(page, "Enter")  # the potion sell row
        _press(page, "1", wait_ms=40)
        _press(page, "Enter", wait_ms=40)
        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_wallet)
        self.assertEqual(sent_action_count(page, "shop.sell"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "shop.sell"
        )
        self.assertEqual(payload, {"item_key": potion, "quantity": 1})
        rows = {row["item_key"]: row for row in self._services_panel(page)["inventory"]["rows"]}
        self.assertNotIn(potion, rows)
        self.assertEqual(rows[staple]["held"], 2)

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
