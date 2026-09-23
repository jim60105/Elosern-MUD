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

    @covers_requirement(
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
        "webclient-contextual-hud::the-shop-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
        )
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

        frame_before = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self._open_surface(page, "shop")

        # Zero dock-menu / dock-detail inside the shop drawer
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

        # Router depth and trail unchanged across open
        frame_open = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_open["depth"], frame_before["depth"])
        self.assertEqual(frame_open["trail"], frame_before["trail"])

        # Tab to the first stock row's quantity input
        first_stock_input_sel = f'[data-testid="shop-panel__stock--{first_key}"] input.shop-row__qty'
        self._tab_until_focused(page, first_stock_input_sel)

        # Type an out-of-bounds value, Tab away
        self._replace_focused_number(page, "30")
        _press(page, "Tab")  # Tab away to the buy button

        # Assert clamped display and zero shop.buy
        clamped_val = page.evaluate(
            f"() => document.querySelector('{first_stock_input_sel}').value"
        )
        self.assertEqual(clamped_val, str(shelf["buy"]["quantity"]["max"]))
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)

        # Focus input again, replace with 2, Tab to buy button, Enter
        page.locator(first_stock_input_sel).focus()
        self._replace_focused_number(page, "2")
        _press(page, "Tab")
        first_buy_btn_sel = f'[data-testid="shop-panel__stock--{first_key}"] button.shop-row__buy'
        active_is_buy = page.evaluate(
            f"(sel) => document.activeElement && document.activeElement.matches(sel)",
            first_buy_btn_sel,
        )
        if not active_is_buy:
            self._tab_until_focused(page, first_buy_btn_sel)
        _press(page, "Enter")

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

        # Close drawer and verify router state unchanged
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        frame_after = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_after["depth"], frame_before["depth"])
        self.assertEqual(frame_after["trail"], frame_before["trail"])

    @covers_requirement(
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
        "webclient-contextual-hud::the-bag-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
        "webclient-contextual-hud::the-shop-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
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

        frame_before = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self._open_surface(page, "shop")

        # Zero dock-menu / dock-detail inside the shop drawer
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
        frame_open = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_open["depth"], frame_before["depth"])
        self.assertEqual(frame_open["trail"], frame_before["trail"])

        # Tab to potion's sellable row quantity input, set 1, activate 賣出
        potion_input_sel = f'[data-testid="shop-panel__sellable--{potion}"] input.shop-row__qty'
        self._tab_until_focused(page, potion_input_sel)
        self._replace_focused_number(page, "1")
        _press(page, "Tab")  # Tab to the sell button
        potion_sell_btn_sel = f'[data-testid="shop-panel__sellable--{potion}"] button.shop-row__sell'
        active_is_sell = page.evaluate(
            f"(sel) => document.activeElement && document.activeElement.matches(sel)",
            potion_sell_btn_sel,
        )
        if not active_is_sell:
            self._tab_until_focused(page, potion_sell_btn_sel)
        _press(page, "Enter")

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

        # Close the shop drawer (frameless close)
        page.locator('[data-testid="hud-drawer-close"]').click()
        page.wait_for_timeout(120)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        frame_closed = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_closed["depth"], frame_before["depth"])
        self.assertEqual(frame_closed["trail"], frame_before["trail"])

        # Keyboard back to the exploration root (Escape pops without dispatching) before using the 背包 entry.
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
             """() => Array.from(
                 document.querySelectorAll('[data-testid="hud-drawer"] button, [data-testid="hud-drawer"] input')
               ).map((el) => el.getAttribute('data-item-key') || el.getAttribute('data-testid') || '')"""
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

    @covers_requirement(
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
        "webclient-contextual-hud::the-shop-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
        )
    def test_closed_shop_disables_all_trades(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["shop"]["open"])

        frame_before = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self._open_surface(page, "shop")

        # Zero dock-menu / dock-detail inside the shop drawer
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
        frame_open = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_open["depth"], frame_before["depth"])
        self.assertEqual(frame_open["trail"], frame_before["trail"])

        # Assert every buy/sell button in the drawer is disabled with its reason and nothing is sent
        buttons_state = page.evaluate(
            """() => Array.from(
                document.querySelectorAll('[data-testid="shop-panel"] button')
              ).map((btn) => ({
                text: btn.textContent.trim(),
                disabled: btn.disabled,
                reason: btn.closest('.shop-row')?.querySelector('.shop-row__reason')?.textContent.trim() || null,
              }))"""
        )
        self.assertTrue(len(buttons_state) > 0, "shop must render buy/sell buttons")
        for btn in buttons_state:
            self.assertTrue(btn["disabled"], f"button {btn['text']} must be disabled when shop is closed")
            self.assertTrue(bool(btn["reason"]), f"button {btn['text']} must render a disabled reason")

        _press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)

        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        frame_after = page.evaluate(
            "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
        )
        self.assertEqual(frame_after["depth"], frame_before["depth"])
        self.assertEqual(frame_after["trail"], frame_before["trail"])
