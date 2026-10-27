"""The NPC interaction card's integrated service journeys
(npc-interaction-service-card, slice U).

These journeys run the real production surface, not the prototype: the
presence rail's medallion opens the card for a committed interact target, the
card's own service entry opens the provider's existing drawer, the existing
shop/rank flow completes, and closing it hands focus back to the entry that
opened it. The synthetic overflow case injects a committed exploration panel
whose target carries more entries than the card has digits, and never sends a
service action: it exists to prove the grouped card and its keyboard reach.
"""

from __future__ import annotations

from .browser_base import ACCEPTANCE_VIEWPORTS
from .browser_helpers import (
    CARD_SELECTOR,
    activate_card_row,
    activate_presence_entry,
    card_row_keys,
    inject_update,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest


def _assert_group_headings(case, card):
    """Every group is named by its own non-empty, distinct heading.

    The heading copy is presentation; the contract is the grouping and its
    accessible name, so only those are asserted.
    """
    headings = card["headings"]
    case.assertEqual(len(headings), len(card["groups"]))
    for heading in headings:
        case.assertTrue(heading and heading.strip(), "a group heading is empty")
    case.assertEqual(len(set(headings)), len(headings), "two groups share a heading")


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


QUANTITY = '[data-testid="shop-window__quantity"]'
TRADE = '[data-testid="action-bar__btn--trade"]'

# The enabled service entry of the committed room whose route opens `surface`,
# with the rail key of the target that owns it and the card row key.
_LOOKUP_JS = """
(surface) => {
    const s = window.__elosernBridge && window.__elosernBridge.store;
    const panels = (s && s.view && s.view.panels) || {};
    const panel = panels.exploration || null;
    for (const target of (panel && panel.interact) || []) {
        const entries = (target.services && target.services.entries) || [];
        for (const entry of entries) {
            const route = entry.route || {};
            if (route.kind !== 'services' || !entry.enabled) { continue; }
            const matches = surface === 'shop'
                ? route.section === 'shop'
                : ['registration', 'board', 'report'].indexOf(route.section) !== -1;
            if (matches) {
                return {
                    target: 'target-' + target.identity,
                    key: 'service-' + entry.key,
                    label: target.display_name,
                };
            }
        }
    }
    return null;
}
"""

# The card's active row key (the composite's one tab stop names it).
ACTIVE_ROW_JS = """
() => {
    const card = document.querySelector('%s');
    const id = card && card.getAttribute('aria-activedescendant');
    const row = id ? document.getElementById(id) : null;
    return {
        focused: !!card && document.activeElement === card,
        key: row ? row.getAttribute('data-row-key') : null,
        headings: Array.from(card ? card.querySelectorAll('[data-testid="choice-card-group-heading"]') : [])
            .map((el) => el.textContent),
        groups: Array.from(card ? card.querySelectorAll('[role="group"]') : [])
            .map((el) => el.getAttribute('data-group')),
    };
}
""" % CARD_SELECTOR


class MerchantServiceCardJourneys(ServicesBrowserTest):
    """A real merchant: the card's own shop entry, a purchase, the return."""

    SERVICES_MODE = "store_open"

    def _open_merchant_card(self, page):
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("services") or {}).get("available") is True,
        )
        lookup = page.evaluate(_LOOKUP_JS, "shop")
        self.assertIsNotNone(lookup, "the fixture must offer an enabled shop service entry")
        activate_presence_entry(page, lookup["target"])
        page.wait_for_selector(CARD_SELECTOR, timeout=30000)
        return lookup

    def test_merchant_purchase_returns_focus_to_its_service_row(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        lookup = self._open_merchant_card(page)
        # The card groups its rows and keeps the fixed common slots first.
        card = page.evaluate(ACTIVE_ROW_JS)
        # Every NPC descriptor carries the author-editor conditional row, so
        # the merchant's card holds all three labelled groups in order.
        self.assertEqual(card["groups"], ["common", "conditional", "services"])
        _assert_group_headings(self, card)
        keys = card_row_keys(page)
        self.assertEqual(keys[:2], ["talk-open", "look-target"])
        self.assertIn(lookup["key"], keys)
        self.assertEqual(keys[-1], "back")

        panel = self._services_panel(page)
        shelf = panel["shop"]["stock"][0]
        item_key = shelf["item_key"]
        wallet_before = panel["player"]["wallet"]

        # The card's own row opens the existing shop drawer (no router frame).
        depth = page.evaluate("() => window.__elosernBridge.router.depth()")
        activate_card_row(page, lookup["key"])
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "shop",
            dom_readiness={
                "selector": '[data-testid="shop-window"]',
                "predicate": "() => !!document.querySelector('[data-testid=\"shop-window\"]')",
                "description": "shop window rendered",
            },
        )
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), depth)

        # One real purchase through the existing quantity and confirm controls.
        self._select_shop_row(page, item_key)
        self._tab_until_focused(page, QUANTITY)
        self._replace_focused_number(page, "1")
        self._tab_until_focused(page, TRADE)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (((s.get("panels") or {}).get("services") or {}).get("player") or {}).get("wallet")
            != wallet_before,
        )
        self.assertEqual(sent_action_count(page, "shop.buy"), 1)

        # Closing the drawer returns focus to the originating service row.
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        wait_for_store_state(
            page,
            lambda s: True,
            dom_readiness={
                "selector": CARD_SELECTOR,
                "predicate": "() => { const c = document.querySelector('%s'); return !!c && document.activeElement === c; }" % CARD_SELECTOR,
                "description": "the open card holds focus after the drawer closes",
            },
        )
        card = page.evaluate(ACTIVE_ROW_JS)
        self.assertTrue(card["focused"], "the drawer's flow returns focus to its card")
        self.assertEqual(card["key"], lookup["key"], "focus returns to the originating entry")
        # The card is still open on the same target: the return is not a reopen.
        self.assertEqual(
            page.evaluate(
                "() => window.__elosernBridge.store.view.presenceCard?.identity ?? null"
            ),
            int(lookup["target"].split("-", 1)[1]),
        )

    def test_a_departed_provider_retires_the_card_and_its_drawer(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        lookup = self._open_merchant_card(page)
        activate_card_row(page, lookup["key"])
        wait_for_store_state(page, lambda s: s.get("hudDrawer") == "shop")

        # A committed exploration publication that no longer lists the provider
        # is the first and final word: the card and its flow go in that commit.
        panel = dict(store_state(page)["panels"]["exploration"])
        identity = int(lookup["target"].split("-", 1)[1])
        panel["interact"] = [t for t in panel["interact"] if t["identity"] != identity]
        remaining = []
        for entity in panel["look"]["entities"]:
            if entity["identity"] == identity:
                continue
            remaining.append(entity)
        panel["look"] = dict(panel["look"], entities=remaining)
        inject_update(page, {"exploration": panel})
        wait_for_store_state(page, lambda s: s.get("presenceCard") is None)
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        # A late read for the departed provider cannot reopen anything.
        page.wait_for_timeout(400)
        self.assertIsNone(store_state(page)["presenceCard"])
        self.assertIsNone(store_state(page)["hudDrawer"])
        # The journey's own reads are the only actions it sent for the provider.
        for envelope in outbound_messages(page):
            self.assertNotEqual(
                envelope[1][0].get("action_id"),
                "shop.buy",
                "a departed provider's flow never falls through to a trade",
            )


class ReceptionServiceCardJourneys(ServicesBrowserTest):
    """The guild counter: the reception host's own entry opens its rank flow."""

    SERVICES_MODE = "guild_hall"

    def test_reception_row_opens_the_rank_flow_without_starting_an_exam(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("services") or {}).get("available") is True,
        )
        lookup = page.evaluate(
            """() => {
                const s = window.__elosernBridge && window.__elosernBridge.store;
                const panels = (s && s.view && s.view.panels) || {};
                for (const target of ((panels.exploration || {}).interact) || []) {
                    for (const entry of ((target.services || {}).entries) || []) {
                        const route = entry.route || {};
                        if (route.kind === 'services' && route.section === 'rank' && entry.enabled) {
                            return { target: 'target-' + target.identity, key: 'service-' + entry.key };
                        }
                    }
                }
                return null;
            }"""
        )
        self.assertIsNotNone(lookup, "the fixture must offer the reception host's rank entry")
        activate_presence_entry(page, lookup["target"])
        page.wait_for_selector(CARD_SELECTOR, timeout=30000)
        activate_card_row(page, lookup["key"])
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "quest",
            dom_readiness={
                "selector": '[data-testid="quest-drawer"]',
                "predicate": "() => !!document.querySelector('[data-testid=\"quest-drawer\"]')",
                "description": "the existing quest/counter drawer rendered",
            },
        )
        # Selecting the entry reads that provider; it never starts the exam.
        sent = [
            envelope[1][0].get("action_id")
            for envelope in outbound_messages(page)
            if envelope[0] == "ui_action"
        ]
        self.assertIn("services.open", sent)
        self.assertNotIn("services.exam_request", sent)
        self.assertNotIn("services.exam_start", sent)
        card = page.evaluate(ACTIVE_ROW_JS)
        self.assertEqual(card["groups"], ["common", "conditional", "services"])
        _assert_group_headings(self, card)


class GroupedCardOverflowJourneys(ServicesBrowserTest):
    """A synthetic committed target with more entries than the card has digits."""

    SERVICES_MODE = "store_open"

    def _inject_crowded_target(self, page):
        panel = store_state(page)["panels"]["exploration"]
        base = panel["interact"][0]
        entries = []
        for index in range(11):
            entries.append(
                {
                    "key": "synthetic.%02d" % index,
                    "label": "測試服務 %d" % (index + 1),
                    # Every route is a valid descriptor; the journey never
                    # activates them, so nothing is dispatched.
                    "enabled": True,
                    "disabled_reason": None,
                    "route": {"kind": "services", "npc_id": base["identity"], "section": "board"},
                }
            )
        # The ninth card row (overall index 8: two common slots, the base's
        # one conditional row, then the sixth synthetic service) is the
        # paused one, so a digit can prove it selects a row without acting.
        entries[5] = {
            "key": "synthetic.paused",
            "label": "測試服務 6",
            "enabled": False,
            "disabled_reason": {"code": "paused", "message": "這項服務暫時停止。"},
            "route": {"kind": "services", "npc_id": base["identity"], "section": "board"},
        }
        crowded = dict(base, services={"state": "ready", "entries": entries})
        injected = dict(panel, interact=[crowded])
        inject_update(page, {"exploration": injected})
        return crowded

    def test_the_card_groups_eleven_services_and_digits_stop_at_nine(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("services") or {}).get("available") is True,
        )
        crowded = self._inject_crowded_target(page)
        activate_presence_entry(page, "target-%s" % crowded["identity"])
        page.wait_for_selector(CARD_SELECTOR, timeout=30000)

        keys = card_row_keys(page)
        # The base descriptor's own conditional rows stay in place; the
        # synthetic services follow them in the server's order.
        conditional = [
            "service-npc_persona"
            if affordance.get("surface") == "npc_persona"
            else "talk-open"
            for affordance in crowded["affordances"]
            if affordance.get("surface") == "npc_persona"
        ]
        expected = ["talk-open", "look-target"] + conditional + [
            "service-" + entry["key"] for entry in crowded["services"]["entries"]
        ] + ["back"]
        self.assertEqual(keys, expected)
        card = page.evaluate(ACTIVE_ROW_JS)
        _assert_group_headings(self, card)
        self.assertEqual(card["groups"], ["common", "conditional", "services"])
        # Only the first nine rows advertise a digit.
        badges = page.evaluate(
            """() => Array.from(document.querySelectorAll('%s [role="menuitem"]'))
              .map((row) => {
                  const badge = row.querySelector('.choice-card__badge');
                  return badge ? badge.getAttribute('data-badge') : null;
              })"""
            % CARD_SELECTOR
        )
        self.assertEqual(badges[:9], [str(n) for n in range(1, 10)])
        self.assertEqual([badge for badge in badges[9:-1]], [None] * (len(badges) - 10))
        self.assertEqual(badges[-1], "✕")

        # A digit addresses its labelled row — here the disabled ninth row, so
        # the press selects it and sends nothing.
        self.assertEqual(keys[8], "service-synthetic.paused")
        _press(page, "9")
        self.assertEqual(page.evaluate(ACTIVE_ROW_JS)["key"], keys[8])

        # The disabled row keeps its inline reason and submits nothing.
        paused = "service-synthetic.paused"
        row = page.locator('%s [data-row-key="%s"]' % (CARD_SELECTOR, paused))
        self.assertEqual(row.get_attribute("aria-disabled"), "true")
        self.assertIn("這項服務暫時停止。", row.inner_text())
        _press(page, "Enter")
        page.wait_for_timeout(120)
        self.assertEqual(sent_action_count(page, "services.open"), 0)

        # A row after the ninth is reached by arrows, never by a digit.
        for _ in range(20):
            if page.evaluate(ACTIVE_ROW_JS)["key"] == "service-synthetic.10":
                break
            _press(page, "ArrowDown")
        self.assertEqual(page.evaluate(ACTIVE_ROW_JS)["key"], "service-synthetic.10")

        # End selects the unnumbered return.
        _press(page, "End")
        self.assertEqual(page.evaluate(ACTIVE_ROW_JS)["key"], "back")
        _press(page, "Escape")
        wait_for_store_state(page, lambda s: s.get("presenceCard") is None)
