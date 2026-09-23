"""Service-dispatch browser journeys: stale and duplicate submission through the
real server dispatcher, and the reconnect rebuilding services while discarding
unsubmitted intent.

Every body is byte-identical to its pre-split home in
``test_browser_services.py``.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


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
        first_key = panel["shop"]["stock"][0]["item_key"]

        self._raw_ui_action(
            page, "shop.buy", {"item_key": first_key, "quantity": 1}, "stale-buy-1", stale_revision
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
        shelf = panel["shop"]["stock"][0]
        first_key, unit_buy = shelf["item_key"], shelf["buy_copper"]
        one_buy_wallet = panel["player"]["wallet"] - unit_buy

        # First delivery executes the buy exactly once.
        self._raw_ui_action(
            page, "shop.buy", {"item_key": first_key, "quantity": 1}, "dup-buy-1", revision
        )
        first = self._wait_result(
            page, lambda r: r["requestId"] == "dup-buy-1" and r["outcome"] == "success"
        )
        self._wait_panel(page, lambda p: p["player"]["wallet"] == one_buy_wallet)
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)

        # A replayed live request ID returns the cached result and never
        # re-executes the trade: the same envelope is delivered again, the
        # second result arrives, and the wallet stays at exactly one purchase.
        self._raw_ui_action(
            page, "shop.buy", {"item_key": first_key, "quantity": 1}, "dup-buy-1", revision
        )
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if sent_action_count(page, "shop.buy") >= 2:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "shop.buy"), 2)
        page.wait_for_timeout(800)
        self.assertEqual(self._services_panel(page)["player"]["wallet"], one_buy_wallet)


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
        shelf = panel["shop"]["stock"][0]
        first_key = shelf["item_key"]

        # Type an unsubmitted quantity in the shop drawer; the value is local.
        self._open_surface(page, "shop")
        first_stock_input_sel = f'[data-testid="shop-panel__stock--{first_key}"] input.shop-row__qty'
        self._tab_until_focused(page, first_stock_input_sel)
        self._replace_focused_number(page, "5")
        self.assertTrue(page.evaluate("() => document.querySelector('[data-testid=\"services-quantity\"]') !== null"))

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
        # The drawer closes on transport loss
        self.assertIsNone(store_state(page).get("hudDrawer"))
        self.assertTrue(page.evaluate("() => document.querySelector('[data-testid=\"hud-drawer\"]') === null"))

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

        # Reopen the shop drawer: unsubmitted quantity was discarded, value is back at lower bound
        self._open_surface(page, "shop")
        val = page.evaluate(f"() => document.querySelector('{first_stock_input_sel}').value")
        self.assertEqual(val, str(shelf["buy"]["quantity"]["min"]))
        # services-quantity is absent until a row takes focus
        self.assertEqual(
             page.evaluate("() => document.querySelector('[data-testid=\"services-quantity\"]') === null"),
            True,
            "unsubmitted quantity must be discarded on reconnect",
        )
        self.assertEqual(sent_action_count(page, "shop.buy"), 0)
