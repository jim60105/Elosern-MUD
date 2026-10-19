"""Focused browser acceptance for the party window's 背包 rows (webclient-party-bag-retire).

The old frameless bag drawer and its tile grid are retired: the top
navigation's 背包 entry opens the party window on its 背包 tab. Journey: open
it from the exploration root, then assert that the tab lists exactly the
viewed member's committed ``party_inventory`` rows (held counts, no invented
total), that each committed rarity draws its own non-colour border pattern,
that one tab stop and the arrow keys reach every row, and that selecting a
row asks the server for that item once and shows its committed kind and
rarity words. Opening and arrowing dispatch nothing.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import kind_word, rarity_word, store_fixture_values

from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .test_browser_services_base import ServicesBrowserTest

ROW = "party-bag-tab__row--{}"


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _focused_testid(page):
    return page.evaluate(
        "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
    )


class InventoryGridJourneys(ServicesBrowserTest):
    """The 背包 tab's committed rows on the dedicated store_open server."""

    SERVICES_MODE = "store_open"

    def _open_bag_tab(self, page):
        # The base gate opened the quest drawer; the drawer is modal, so the
        # navigation click follows the store's single close entry.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.closeHudDrawer({ popFrame: true }); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        return self._open_surface(page, "inventory")

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully",
        "webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region",
        "webclient-contextual-hud::lineage-identity-and-inventory-rarity-use-backed-fields",
        "webclient-party-window::the-bag-tab-presents-the-viewed-member-s-doll-bag-and-holdings",
    )
    def test_bag_tab_lists_the_committed_rows_with_keyboard_reach(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")
        sent_before = sent_action_count(page)
        panel = self._open_bag_tab(page)

        # The open is client-local: no frame, no dispatch.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before)
        self.assertEqual(sent_action_count(page), sent_before)
        self.assertEqual(
            page.evaluate(
                """() => {
                  const drawer = document.querySelector('[data-testid="hud-drawer"]');
                  return drawer.querySelectorAll('[data-testid="dock-menu"], [data-testid="dock-detail"]').length;
                }"""
            ),
            0,
        )

        # The committed panel is the source of truth: the viewed member (the
        # commander by default) holds the two fixture items.
        STORE = store_fixture_values()
        potion, staple = STORE["potion_key"], STORE["staple_key"]
        committed = {row["item_key"]: row for row in panel["rows"]}
        self.assertEqual(committed[staple]["held"], 2)
        self.assertEqual(committed[potion]["held"], 1)
        self.assertEqual(committed[potion]["presentation"]["rarity"], STORE["potion_rarity"])
        self.assertNotIn("total", panel)

        rows = page.evaluate(
            """() => Array.from(
                document.querySelectorAll('[data-testid^="party-bag-tab__row--"]')
              ).map((row) => ({
                id: row.getAttribute("data-testid"),
                held: row.querySelector('[data-testid^="party-bag-tab__held--"]').textContent,
                rarity: row.querySelector(".party-bag-tab__icon").getAttribute("data-rarity"),
              }))"""
        )
        self.assertEqual(sorted(r["id"] for r in rows), sorted(ROW.format(k) for k in committed))
        held = {r["id"]: r["held"] for r in rows}
        self.assertEqual(held[ROW.format(staple)], "×2")
        self.assertEqual(held[ROW.format(potion)], "×1")
        # The tab's count is the shipped row count, never a holdings total.
        self.assertEqual(
            page.locator('[data-testid="party-bag-tab__count"]').text_content(),
            f"{len(committed)} 種",
        )

        # Each committed rarity draws its own border pattern at a width where
        # it shows; common stays a neutral 1px solid line.
        frame_patterns = {
            "common": ("solid", "1px"),
            "uncommon": ("dotted", "2px"),
            "rare": ("dashed", "2px"),
            "epic": ("double", "3px"),
            "legendary": ("ridge", "3px"),
        }
        frames = page.evaluate(
            """() => Array.from(document.querySelectorAll('.party-bag-tab__icon')).map((icon) => {
                const cs = getComputedStyle(icon);
                return [icon.getAttribute("data-rarity"), cs.borderTopStyle, cs.borderTopWidth];
            })"""
        )
        for rarity, style, width in frames:
            if rarity in frame_patterns:
                self.assertEqual((style, width), frame_patterns[rarity], rarity)

        # One tab stop: exactly one row is tabbable, and the arrow keys reach
        # every row without dispatching anything.
        tab_stops = page.evaluate(
            """() => Array.from(document.querySelectorAll('[role="option"]'))
                .filter((row) => row.tabIndex === 0).map((row) => row.getAttribute("data-testid"))"""
        )
        self.assertEqual(len(tab_stops), 1)
        page.locator(f'[data-testid="{tab_stops[0]}"]').focus()
        reached = {_focused_testid(page)}
        for _ in range(len(committed)):
            _press(page, "ArrowDown")
            reached.add(_focused_testid(page))
        self.assertEqual(reached, {ROW.format(k) for k in committed})
        self.assertEqual(sent_action_count(page), sent_before)

        # Enter selects: exactly one party.view_member for the viewed member
        # with that item, after which the detail shows its committed words.
        page.locator(f'[data-testid="{ROW.format(potion)}"]').focus()
        _press(page, "Enter")
        self.assertEqual(sent_action_count(page, "party.view_member"), 1)
        viewed = store_state(page)["panels"]["party"]["viewed_member_id"]
        envelope = next(
            args[0]
            for cmd, args, _kw in page.evaluate("window.__elosernSent || []")
            if cmd == "ui_action" and args and args[0].get("action_id") == "party.view_member"
        )
        self.assertEqual(
            envelope["payload"],
            {"member_id": viewed, "tab": "bag", "skill_key": None, "item_key": potion},
        )
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("item_holdings") or {}).get("item_key") == potion
            and not (s.get("dispatch") or {}).get("inFlight"),
        )
        page.wait_for_selector('[data-testid="party-bag-tab__title"]')
        self.assertEqual(
            page.locator('[data-testid="party-bag-tab__title"]').text_content(), STORE["potion_display"]
        )
        self.assertIn(kind_word(STORE["potion_kind"]), page.locator('[data-testid="party-bag-tab__ribbon"]').text_content())
        self.assertEqual(
            page.locator('[data-testid="party-bag-tab__rarity"]').text_content(), rarity_word(STORE["potion_rarity"])
        )
        self.assertEqual(page.locator(f'[data-testid="{ROW.format(potion)}"]').get_attribute("aria-selected"), "true")
