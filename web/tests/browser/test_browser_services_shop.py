"""Shop window browser journeys (webclient-shop-window): buy/sell quantity
validation with exact copper/stock/wallet outcomes through the action bar's
quantity entry, the party window's bag after a trade, the closed shop disabling
every trade, and buying potions for a companion chosen on the member rail.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import store_fixture_values

from .browser_base import ACCEPTANCE_VIEWPORTS
from .browser_helpers import (
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


FRAME_JS = "() => ({ depth: window.__elosernBridge.router.depth(), trail: window.__elosernBridge.router.trail() })"
HOSTED_JS = """() => {
  const drawer = document.querySelector('[data-testid="hud-drawer"]');
  return {
    menu: drawer.querySelectorAll('[data-testid="dock-menu"]').length,
    detail: drawer.querySelectorAll('[data-testid="dock-detail"]').length,
  };
}"""
QUANTITY = '[data-testid="shop-window__quantity"]'
TRADE = '[data-testid="action-bar__btn--trade"]'


def _sent_payload(page, action_id):
    sent = page.evaluate("window.__elosernSent || []")
    return next(
        args[0]["payload"]
        for cmd, args, _kw in sent
        if cmd == "ui_action" and args[0]["action_id"] == action_id
    )


class ShopJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_open"

    @covers_requirement(
        "webclient-shop-window::the-buy-view-shows-one-price-and-the-recipient-s-facts",
    )
    def test_buy_quantity_validation_exact_copper(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertTrue(panel["shop"]["open"])
        self.assertEqual(panel["player"]["wallet"], 1000)
        # Every number the journey asserts is derived from the committed
        # panel: the first shelf row's identity, unit price and bounds.
        shelf = panel["shop"]["stock"][0]
        first_key, unit_buy = shelf["item_key"], shelf["buy_copper"]
        maximum = shelf["buy"]["quantity"]["max"]
        self.assertGreater(unit_buy, 0)
        self.assertGreaterEqual(maximum, 2)
        expected_wallet = panel["player"]["wallet"] - 2 * unit_buy
        # The shop window names the viewed member (services v7
        # shop.member_id), which falls back to the commander, as recipient.
        actor_id = panel["shop"]["member_id"]
        self.assertEqual(
            actor_id, int(store_state(page)["panels"]["status"]["actor"]["identity"])
        )

        frame_before = page.evaluate(FRAME_JS)
        self._open_surface(page, "shop")
        self.assertEqual(page.evaluate(HOSTED_JS), {"menu": 0, "detail": 0})
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)
        # One price per view: the 購買 rows carry buy prices only.
        prices = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-testid="shop-rows__price"]'))
              .map((n) => n.textContent.replace(/[^0-9]/g, ''))"""
        )
        self.assertEqual(prices, [str(row["buy_copper"]) for row in panel["shop"]["stock"]])

        # Select the first stock row, then Tab to the action bar's entry.
        self._select_shop_row(page, first_key)
        self._tab_until_focused(page, QUANTITY)
        self._replace_focused_number(page, str(maximum + 5))
        _press(page, "Tab")  # leaving the entry clamps it
        self.assertEqual(
            page.evaluate(f"() => document.querySelector('{QUANTITY}').value"), str(maximum)
        )
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)

        # Replace with 2, Tab to 買給, Enter.
        page.locator(QUANTITY).focus()
        self._replace_focused_number(page, "2")
        self._tab_until_focused(page, TRADE)
        _press(page, "Enter")

        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_wallet)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)
        self.assertEqual(
            _sent_payload(page, "shop.buy"),
            {"item_key": first_key, "quantity": 2, "recipient_id": actor_id},
        )
        self.assertEqual(self._services_panel(page)["player"]["wallet"], expected_wallet)
        # The header purse is the shop window's only balance.
        wait_for_store_state(page, lambda s: True, dom_readiness={
            "selector": '[data-testid="shop-window__purse"]',
            "predicate": f"() => document.querySelector('[data-testid=\"shop-window__purse\"]').textContent.replace(/[^0-9]/g, '') === '{expected_wallet}'",
            "description": "header purse shows the committed wallet",
        })

        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)

    @covers_requirement(
        "webclient-shop-window::the-sell-view-lists-the-seller-s-unequipped-items-with-one-price",
    )
    def test_sell_and_repeated_inventory_without_use_control(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        # services v7 carries no inventory: the bag rows are party_inventory's.
        rows = self._bag_rows(page)
        STORE = store_fixture_values()
        potion, staple = STORE["potion_key"], STORE["staple_key"]
        actor_id = panel["shop"]["member_id"]
        self.assertEqual(
            actor_id, int(store_state(page)["panels"]["status"]["actor"]["identity"])
        )
        self.assertEqual(rows[staple]["held"], 2)
        # The full-HP store fixture refuses the potion's use descriptor.
        self.assertFalse(rows[potion]["use"]["enabled"])

        # The merchant is at its staple stock cap, so the potion is the only
        # sellable offer (its held unit fits under the stock ceiling).
        sellable = {row["item_key"]: row for row in panel["shop"]["sellable"]}
        potion_row = sellable[potion]
        self.assertEqual(potion_row["held"], 1)
        expected_wallet = panel["player"]["wallet"] + potion_row["sell_copper"]

        frame_before = page.evaluate(FRAME_JS)
        self._open_surface(page, "shop")
        self.assertEqual(page.evaluate(HOSTED_JS), {"menu": 0, "detail": 0})
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)

        self._select_shop_tab(page, "sell")
        prices = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-testid="shop-rows__price"]'))
              .map((n) => n.textContent.replace(/[^0-9]/g, ''))"""
        )
        self.assertEqual(prices, [str(row["sell_copper"]) for row in panel["shop"]["sellable"]])
        self._select_shop_row(page, potion)
        self._tab_until_focused(page, QUANTITY)
        self._replace_focused_number(page, "1")
        self._tab_until_focused(page, TRADE)
        _press(page, "Enter")

        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_wallet)
        self.assertEqual(sent_action_count(page, "shop.sell"), 1)
        self.assertEqual(
            _sent_payload(page, "shop.sell"),
            {"item_key": potion, "quantity": 1, "seller_id": actor_id},
        )
        # The republished shop rows report the seller's remaining copies: the
        # potion left the sellable list and the staple count is untouched.
        shop = self._services_panel(page)["shop"]
        self.assertNotIn(potion, {row["item_key"] for row in shop["sellable"]})
        staple_stock = next(row for row in shop["stock"] if row["item_key"] == staple)
        self.assertEqual(staple_stock["viewed"]["held"], 2)
        # The trade republished the viewed member's bag and purse.
        bag = store_state(page)["panels"]["party_inventory"]
        self.assertNotIn(potion, {row["item_key"] for row in bag["rows"]})
        self.assertEqual(bag["purse"], expected_wallet)

        # Close the shop window (frameless close).
        page.locator('[data-testid="hud-drawer-close"]').click()
        page.wait_for_timeout(120)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)

        # The 背包 entry opens the party window's 背包 tab with exactly the
        # committed rows, the doll, and the header purse as the only balance.
        sent_before = sent_action_count(page)
        bag_panel = self._open_surface(page, "inventory")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") == "party")
        committed = sorted("party-bag-tab__row--" + row["item_key"] for row in bag_panel["rows"])
        tiles = page.evaluate(
            """() => Array.from(
                document.querySelectorAll('[data-testid^="party-bag-tab__row--"]')
              ).map((t) => t.getAttribute("data-testid")).sort()"""
        )
        self.assertEqual(tiles, committed, "the bag rows are exactly the committed rows")
        sections = page.evaluate(
            """() => ({
              equipment: !!document.querySelector('[data-testid="party-bag-tab__doll"]'),
              items: !!document.querySelector('[data-testid="party-bag-tab__rows"]'),
              money: document.querySelectorAll('[data-testid="party-window__purse"]').length,
            })"""
        )
        self.assertEqual(sections, {"equipment": True, "items": True, "money": 1})
        self.assertEqual(page.evaluate(HOSTED_JS), {"menu": 0, "detail": 0})
        _press(page, "Escape", wait_ms=120)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(sent_action_count(page), sent_before, "the frameless 背包 entry dispatches no action")

        # No submitted service payload carries a host/branch/actor field.
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


class ShopCompanionJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_open_companion"

    def _enter_companion_possession(self, page, companion_id):
        """Select the companion and enter real possession."""
        page.evaluate("window.__elosernBridge.store.openHudDrawer('party')")
        page.locator('[data-testid="icon-tabs__tab--member"]').click()
        entry = page.locator(f'[data-testid="member-rail__entry--{companion_id}"]')
        entry.wait_for(timeout=30000)
        if entry.get_attribute("aria-current") != "true":
            entry.click()
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party") or {}).get(
                "viewed_member_id"
            )
            == companion_id,
        )
        page.locator('[data-testid="action-bar__btn--possess"]').click()
        self.assertEqual(sent_action_count(page, "explore.possess"), 1)
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("possession_banner") or {}).get(
                    "available"
                )
                and ((s.get("panels") or {}).get("services") or {}).get("available")
            ),
        )
        exploration = store_state(page)["panels"]["exploration"]
        service_entries = [
            affordance
            for target in exploration.get("interact") or []
            for affordance in target.get("affordances") or []
            if affordance.get("surface") in {"guild", "shop"}
        ]
        return self._services_panel(page), service_entries

    @covers_requirement(
        "webclient-shop-window::the-shop-window-uses-the-frame-with-buy-and-sell-tabs-and-the-member-rail",
        "webclient-shop-window::the-buy-view-shows-one-price-and-the-recipient-s-facts",
    )
    def test_buy_potions_for_a_companion(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        STORE = store_fixture_values()
        potion = STORE["potion_key"]
        party = store_state(page)["panels"]["party"]
        commander_id = party["slots"][0]["identity"]
        # The seed's co-located companion (艾拉, or the first companion moved
        # into the store when the preset party was already full).
        companions = [row for row in party["slots"] if row["role"] == "companion"]
        companion = next((row for row in companions if row["display_name"] == "艾拉"), companions[0])
        companion_id, companion_name = companion["identity"], companion["display_name"]
        # The shop opens on the commander (the session's viewed member).
        self.assertEqual(panel["shop"]["member_id"], commander_id)

        # Enter real possession with the companion selected, so the viewed
        # member survives the transition and the shop opens on her.
        possessed_services, service_entries = self._enter_companion_possession(
            page, companion_id
        )
        self.assertIsNone(possessed_services["guild"])
        self.assertEqual(
            [entry["surface"] for entry in service_entries], ["shop"]
        )
        self.assertTrue(service_entries[0]["enabled"])
        self.assertIsNone(service_entries[0]["disabled_reason"])

        self._open_surface(page, "shop")
        # The viewed-member selection survives possession; the journey never
        # re-selects the companion to make this pass.
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party") or {}).get(
                "viewed_member_id"
            )
            == companion_id
            and (((s.get("panels") or {}).get("services") or {}).get("shop") or {}).get(
                "member_id"
            )
            == companion_id,
        )
        title = page.evaluate(
            "() => document.querySelector('[data-testid=\"shop-window__list-title\"]').textContent"
        )
        self.assertEqual(title, f"為{companion_name}挑選")
        shelf = next(
            row for row in self._services_panel(page)["shop"]["stock"] if row["item_key"] == potion
        )
        held_before = shelf["viewed"]["held"]
        self.assertGreaterEqual(shelf["buy"]["quantity"]["max"], 2)
        wallet_before = self._services_panel(page)["player"]["wallet"]
        expected_wallet = wallet_before - 2 * shelf["buy_copper"]

        self._select_shop_row(page, potion)
        self._tab_until_focused(page, QUANTITY)
        self._replace_focused_number(page, "2")
        _press(page, "Tab")
        remaining = page.evaluate(
            "() => document.querySelector('[data-testid=\"shop-window__remaining\"]').textContent"
        )
        self.assertEqual(remaining.replace(",", ""), f"剩餘 {expected_wallet} 銅")
        self._tab_until_focused(page, TRADE)
        self.assertEqual(
            page.evaluate(f"() => document.querySelector('{TRADE}').textContent.trim()"),
            f"買給{companion_name}",
        )
        _press(page, "Enter")

        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_wallet)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)
        self.assertEqual(
            _sent_payload(page, "shop.buy"),
            {"item_key": potion, "quantity": 2, "recipient_id": companion_id},
        )
        # The companion (still the viewed member) holds two more, and the
        # republished bag and purse agree without a full snapshot.
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party_inventory") or {}).get("member_id") == companion_id
            and any(
                row["item_key"] == potion and row["held"] == held_before + 2
                for row in (s["panels"]["party_inventory"].get("rows") or [])
            ),
        )
        state = store_state(page)
        self.assertEqual(state["panels"]["party_inventory"]["purse"], expected_wallet)
        holding = next(
            row for row in state["panels"]["item_holdings"]["rows"] if row["member_id"] == companion_id
        )
        self.assertEqual(holding["held"], held_before + 2)
        self.assertEqual(
            next(row for row in state["panels"]["services"]["shop"]["stock"] if row["item_key"] == potion)["viewed"]["held"],
            held_before + 2,
        )
        self.assertEqual(
            page.evaluate("() => document.querySelectorAll('[data-testid=\"shop-window__purse\"]').length"), 1
        )

        # Sell one of the bought potions back from the same acting puppet.
        sell_row = next(
            row
            for row in self._services_panel(page)["shop"]["sellable"]
            if row["item_key"] == potion
        )
        sale_copper = sell_row["sell_copper"]
        expected_after_sale = expected_wallet + sale_copper
        self._select_shop_tab(page, "sell")
        self._select_shop_row(page, potion)
        self._tab_until_focused(page, QUANTITY)
        self._replace_focused_number(page, "1")
        _press(page, "Tab")
        self._tab_until_focused(page, TRADE)
        _press(page, "Enter")

        self._wait_panel(page, lambda p: p["player"]["wallet"] == expected_after_sale)
        self.assertEqual(sent_action_count(page, "shop.sell"), 1)
        self.assertEqual(
            _sent_payload(page, "shop.sell"),
            {"item_key": potion, "quantity": 1, "seller_id": companion_id},
        )
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("party_inventory") or {}).get(
                "purse"
            )
            == expected_after_sale,
        )
        state = store_state(page)
        self.assertEqual(
            state["panels"]["party_inventory"]["purse"], expected_after_sale
        )
        self.assertEqual(
            next(
                row
                for row in state["panels"]["party_inventory"]["rows"]
                if row["item_key"] == potion
            )["held"],
            held_before + 1,
        )

    @covers_requirement(
        "webclient-shop-window::the-shop-window-uses-the-frame-with-buy-and-sell-tabs-and-the-member-rail",
        "webclient-shop-window::the-buy-view-shows-one-price-and-the-recipient-s-facts",
    )
    def test_possessed_shop_opens_at_the_large_acceptance_viewport(self):
        page = self.logged_in_page(ACCEPTANCE_VIEWPORTS[1])
        install_outbound_recorder(page)
        self._wait_services_available(page)
        party = store_state(page)["panels"]["party"]
        companions = [row for row in party["slots"] if row["role"] == "companion"]
        companion = next(
            (row for row in companions if row["display_name"] == "艾拉"),
            companions[0],
        )
        companion_id = companion["identity"]
        panel, service_entries = self._enter_companion_possession(page, companion_id)
        self.assertIsNone(panel["guild"])
        self.assertEqual(
            [entry["surface"] for entry in service_entries], ["shop"]
        )
        self.assertTrue(service_entries[0]["enabled"])
        self._open_surface(page, "shop")
        wait_for_store_state(
            page,
            lambda s: (((s.get("panels") or {}).get("services") or {}).get("shop") or {}).get(
                "member_id"
            )
            == companion_id,
        )
        self.assertTrue(page.locator('[data-testid="shop-window"]').is_visible())
        self.assertEqual(
            page.evaluate(
                "() => document.querySelectorAll('[data-testid=\"shop-window__purse\"]').length"
            ),
            1,
        )


class ShopClosedJourneys(ServicesBrowserTest):
    SERVICES_MODE = "store_closed"

    @covers_requirement(
        "webclient-shop-window::the-shop-window-explains-no-rules",
    )
    def test_closed_shop_disables_all_trades(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_services_available(page)
        self.assertFalse(panel["shop"]["open"])

        frame_before = page.evaluate(FRAME_JS)
        self._open_surface(page, "shop")
        self.assertEqual(page.evaluate(HOSTED_JS), {"menu": 0, "detail": 0})
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)
        self.assertIn("已打烊", page.locator('[data-testid="hud-drawer"]').inner_text())

        # Every stock row's trade control is disabled with the committed reason.
        for row in panel["shop"]["stock"]:
            self._select_shop_row(page, row["item_key"])
            state = page.evaluate(
                f"""() => {{
                  const btn = document.querySelector('{TRADE}');
                  const reason = document.querySelector('[data-testid="action-bar__reason"]');
                  return {{
                    disabled: btn.getAttribute('aria-disabled') === 'true',
                    reason: reason ? reason.textContent.trim() : null,
                    stepper: !!document.querySelector('[data-testid="shop-window__stepper"]'),
                  }};
                }}"""
            )
            self.assertTrue(state["disabled"], f"{row['item_key']} must be disabled when closed")
            self.assertEqual(state["reason"], row["buy"]["disabled_reason"]["message"])
            self.assertFalse(state["stepper"])
            page.locator(TRADE).focus()
            _press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)
        self.assertEqual(sent_action_count(page, "shop.sell"), 0)

        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        self.assertEqual(page.evaluate(FRAME_JS), frame_before)
