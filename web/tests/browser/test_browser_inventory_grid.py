"""Focused browser acceptance for the redesigned inventory item grid (H4 + redesign-inventory-item-grid).

Journey: open the inventory drawer through the exploration root's Inventory
entry, then assert that the responsive tile grid renders exactly the
committed ``services.inventory`` rows (no invented total or rarity), with
per-tile held counts, the non-colour rarity treatment, and the shared
hover/focus inspector spelling the committed kind/rarity words. Clicking or
focusing a tile never dispatches a ``ui_action`` — the drawer body is a
purely presentational surface.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import kind_word, rarity_word, store_fixture_values

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .test_browser_services import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class InventoryGridJourneys(ServicesBrowserTest):
    """Inventory item-grid journeys on the dedicated store_open server."""

    SERVICES_MODE = "store_open"

    def _open_inventory_drawer(self, page):
        """Open the frameless inventory drawer from the exploration root.

        make-inventory-drawer-frameless: the 背包 entry opens the drawer as a
        client-local open — no keyboard frame is pushed and the router's
        frame stack stays at the root.
        """
        focus_action_dock(page)
        # The base class's `_wait_services_available` opened the reference
        # quest drawer as its journey's first step (H4 task 4.3). The drawer
        # is the design's modal surface (HudDrawer.vue: the blurred scrim
        # covers the whole stage while open), so the nav click must follow a
        # close — Escape is the keyboard close the drawer owns (design D4).
        # The store's single close entry (the same entry the drawer's own
        # close control, scrim, and Escape handler funnel through): the
        # focus-trap makes raw key dispatch focus-dependent, so the close
        # goes through the store entry the gate used to open the drawer.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.closeHudDrawer({ popFrame: true }); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        # The desktop redesign re-homed the 背包 entry into the top
        # navigation (webclient-desktop-shell, acd3790): the dock root is the
        # capability-driven [move, look, interact, wait, suggestions], so the
        # drawer opens from the DesktopNavigation 背包 click — the same
        # client-local openHudDrawer('inventory') the old dock row submitted
        # (make-inventory-drawer-frameless: no keyboard frame is pushed).
        page.locator('.desktop-navigation button', has_text="背包").click()
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "inventory",
            dom_readiness={
                "selector": '[data-testid="inventory-panel"]',
                "predicate": (
                    "() => !!document.querySelector('[data-testid=\"inventory-panel\"]')"
                ),
                "description": "frameless inventory drawer rendered",
            },
        )
        return self._services_panel(page)

    @covers_requirement(
        "webclient-contextual-hud::the-bag-renders-the-bounded-inventory-rows-without-inventing-a-total-or-a-rarity",
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully",
        "webclient-contextual-hud::the-bag-drawer-opens-without-a-router-frame-and-hosts-no-row-region",
    )
    def test_grid_renders_only_committed_rows_without_invented_total_or_rarity(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._open_inventory_drawer(page)

        # The committed panel is the source of truth: two held item keys,
        # with exact held counts and committed presentation metadata.
        STORE = store_fixture_values()
        potion, staple = STORE["potion_key"], STORE["staple_key"]
        committed = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        self.assertEqual(committed[staple]["held"], 2)
        self.assertEqual(committed[potion]["held"], 1)
        self.assertEqual(committed[staple]["presentation"]["rarity"], STORE["staple_rarity"])
        self.assertEqual(committed[potion]["presentation"]["rarity"], STORE["potion_rarity"])
        self.assertNotIn("total", panel["inventory"])

        # The grid renders exactly the committed rows: one tile per committed
        # item key, each carrying its committed presentation rarity.
        tiles = page.evaluate(
            """() => {
                const rows = Array.from(
                    document.querySelectorAll('[data-testid^="inventory-panel__tile--"]')
                ).map((t) => t.getAttribute("data-testid"));
                return rows;
            }"""
        )
        self.assertEqual(
            sorted(tiles),
            sorted(
                f"inventory-panel__tile--{key}" for key in (potion, staple)
            ),
        )
        rarities = page.evaluate(
            """() => {
                return Array.from(
                    document.querySelectorAll('[data-testid^="inventory-panel__tile--"]')
                ).map((t) => t.getAttribute("data-rarity"));
            }"""
        )
        self.assertEqual(
            sorted(rarities),
            sorted([STORE["potion_rarity"], STORE["staple_rarity"]]),
        )

        # The lower-corner held count is the committed ``held`` value, never
        # a fabricated total.
        counts = page.evaluate(
            """({staple, potion}) => {
                const Staple = document.querySelector(
                    `[data-testid="inventory-panel__count--${staple}"]`);
                const Potion = document.querySelector(
                    `[data-testid="inventory-panel__count--${potion}"]`);
                return [Staple.textContent, Potion.textContent];
            }""",
            {"staple": staple, "potion": potion},
        )
        self.assertEqual(counts, ["2", "1"])

        # No state-changing control (use/equip/drag/sort/filter/search) is
        # rendered inside the drawer body — only the tile buttons.
        button_count = page.evaluate(
            """() => {
                const panel = document.querySelector('[data-testid="inventory-panel"]');
                return panel.querySelectorAll("button").length;
            }"""
        )
        self.assertEqual(button_count, 2)

        # Focus a tile: the shared inspector spells the committed kind and
        # rarity words, the held count, and the equipped state.
        # Playwright's locator focus waits for the element to be actionable —
        # the raw evaluate focus raced the drawer's mounting re-render (the
        # focused node was replaced before Vue's @focus listener ran). The
        # bound attribute is then awaited deterministically instead of a
        # fixed sleep.
        potion_tile = f'[data-testid="inventory-panel__tile--{potion}"]'
        page.locator(potion_tile).focus()
        page.wait_for_function(
            f"() => document.querySelector('[data-testid=\"inventory-panel__tile--{potion}\"]')"
            ".getAttribute('aria-describedby') === 'inventory-panel-inspector'",
            timeout=10000,
        )
        describedby = page.evaluate(
            f"""() => document.querySelector('[data-testid="inventory-panel__tile--{potion}"]').getAttribute("aria-describedby")"""
        )
        self.assertEqual(describedby, "inventory-panel-inspector")
        name = page.evaluate(
            """() => document.querySelector('[data-testid="inventory-panel__inspector-name"]').textContent"""
        )
        self.assertEqual(name, STORE["potion_display"])
        rarity = page.evaluate(
            """() => {
                const el = document.querySelector('[data-testid="inventory-panel__inspector-rarity"]');
                return el ? el.textContent : null;
            }"""
        )
        self.assertEqual(rarity, rarity_word(STORE["potion_rarity"]))
        kind = page.evaluate(
            """() => {
                const el = document.querySelector('[data-testid="inventory-panel__inspector-kind"]');
                return el ? el.textContent : null;
            }"""
        )
        self.assertEqual(kind, kind_word(STORE["potion_kind"]))
        held = page.evaluate(
            """() => document.querySelector('[data-testid="inventory-panel__inspector-held"]').textContent"""
        )
        self.assertEqual(held, "1")
        equipped = page.evaluate(
            """() => document.querySelector('[data-testid="inventory-panel__inspector-equipped"]').textContent"""
        )
        self.assertEqual(equipped, "未裝備")

        # Presentational only: neither hover/focus nor a tile click dispatches
        # a ui_action (no use/equip is ever offered from the bag).
        page.evaluate(
            """({staple}) => {
                const tile = document.querySelector(
                    `[data-testid="inventory-panel__tile--${staple}"]`);
                tile.click();
                return true;
            }""",
            {"staple": staple},
        )
        page.wait_for_timeout(120)
        self.assertEqual(sent_action_count(page), 0)

        # Keyboard reachability (make-inventory-drawer-frameless): the tiles
        # are the drawer's only row surface. Tab traversal through the focus
        # trap reaches every committed row with the shared inspector following
        # focus — the removed keyboard row list is not needed to reach them.
        page.evaluate(
            """() => {
                document.querySelector('[data-testid="hud-drawer-close"]').focus();
                return true;
            }"""
        )
        visited = []
        for _ in range(2):
            page.keyboard.press("Tab")
            page.wait_for_timeout(60)
            visited.append(
                page.evaluate(
                    """() => {
                        const el = document.activeElement;
                        return el && el.getAttribute
                            ? el.getAttribute("data-testid")
                            : null;
                    }"""
                )
            )
        self.assertEqual(
            sorted(visited),
            sorted(f"inventory-panel__tile--{key}" for key in (potion, staple)),
        )
        focused_state = page.evaluate(
            """() => ({
                describedby: document.activeElement.getAttribute("aria-describedby"),
                testid: document.activeElement.getAttribute("data-testid"),
                name: document.querySelector('[data-testid="inventory-panel__inspector-name"]').textContent,
            })"""
        )
        self.assertEqual(focused_state["describedby"], "inventory-panel-inspector")
        # The shared inspector followed focus onto the last Tab stop: its
        # committed display name, whatever the shipped row order is.
        last_key = focused_state["testid"].split("--", 1)[1]
        self.assertEqual(focused_state["name"], committed[last_key]["display_name"])

    @covers_requirement(
        "webclient-contextual-hud::the-bag-renders-the-bounded-inventory-rows-without-inventing-a-total-or-a-rarity",
        "webclient-contextual-hud::the-equipment-doll-renders-only-server-authored-slots-and-drops-nothing",
        "webclient-contextual-hud::the-drawer-layer-renders-the-wallet-exactly-once",
    )
    def test_bag_is_the_three_section_stack_with_description_column_and_wallet_row(self):
        """realign-inventory-drawer-layout: mock-faithful bag structure."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._open_inventory_drawer(page)

        # The store-open fixture carries two rows and an empty equipment set;
        # the character panel owns the committed wallet figure.
        self.assertEqual(len(panel["inventory"]["rows"]), 2)
        character = (store_state(page).get("panels") or {}).get("character") or {}
        self.assertTrue(character.get("available"), "exploration commits the character panel")
        wallet = character.get("wallet")
        self.assertIsInstance(wallet, int)

        # The body is the redesign's three-section stack: the equipment
        # section (the doll), then `物品` (heading tagged with the shipped
        # listing size over the tile grid), then `金錢`.
        order = page.evaluate(
            """() => {
                const before = (a, b) => {
                    const x = document.querySelector(a);
                    const y = document.querySelector(b);
                    if (!x || !y) return null;
                    return (x.compareDocumentPosition(y) & Node.DOCUMENT_POSITION_FOLLOWING)
                        === Node.DOCUMENT_POSITION_FOLLOWING;
                };
                return {
                    items: !!document.querySelector('[data-testid="inventory-panel__section--items"]'),
                    wallet: !!document.querySelector('[data-testid="inventory-panel__section--wallet"]'),
                    dollThenItems: before(
                        '[data-testid="equipment-doll"]',
                        '[data-testid="inventory-panel__section--items"]'
                    ),
                    itemsThenWallet: before(
                        '[data-testid="inventory-panel__section--items"]',
                        '[data-testid="inventory-panel__section--wallet"]'
                    ),
                    itemsCount: (
                        document.querySelector('[data-testid="inventory-panel__items-count"]') || {}
                    ).textContent,
                };
            }"""
        )
        self.assertEqual(
            order,
            {"items": True, "wallet": True, "dollThenItems": True, "itemsThenWallet": True, "itemsCount": "2"},
        )

        # The doll renders the mock's `.doll` row: the square slot grid
        # beside the 裝備描述 column. The fixture carries no equipment, so
        # the column states the honest empty statement beside the dashed
        # empty cells (never a fabricated item).
        description = page.evaluate(
            """() => {
                const column = document.querySelector('[data-testid="equipment-doll__description"]');
                const title = document.querySelector('[data-testid="equipment-doll__title"]');
                return {
                    text: column ? column.textContent.trim() : null,
                    title: title ? title.textContent.trim() : null,
                    emptyMain: !!document.querySelector('[data-testid="equipment-doll__slot-empty--weapon_main"]'),
                };
            }"""
        )
        self.assertIsNotNone(description["text"])
        self.assertIn("目前沒有裝備任何物品。", description["text"])
        self.assertEqual(description["title"], "裝備真值 · 偽裝不影響")
        self.assertTrue(description["emptyMain"])
        body_text = page.evaluate(
            "() => document.querySelector('[data-testid=\"inventory-panel\"]').textContent"
        )
        self.assertNotIn("裝備人偶", body_text)

        # The wallet renders exactly twice in the drawer: the head subtitle
        # and the `金錢` row, both the character-panel figure (the
        # thousands-grouped integer), and no sort/filter/search pill exists.
        balance = page.evaluate(
            """() => ({
                subtitle: (document.querySelector('.hud-drawer__subtitle') || {}).textContent,
                value: (document.querySelector('[data-testid="inventory-panel__wallet-value"]') || {}).textContent,
                nodes: document.querySelectorAll('[data-testid="inventory-panel__wallet-value"]').length,
            })"""
        )
        grouped = f"{wallet:,}"
        self.assertEqual(balance["subtitle"], f"錢袋 {grouped} 銅")
        self.assertEqual(balance["value"], grouped)
        self.assertEqual(balance["nodes"], 1)
        drawer_text = page.evaluate(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]').textContent"
        )
        for pill in ("排序", "篩選", "找尋"):
            self.assertNotIn(pill, drawer_text)
