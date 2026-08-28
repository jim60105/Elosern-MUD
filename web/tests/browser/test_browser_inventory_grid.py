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

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
)
from .test_browser_services import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class InventoryGridJourneys(ServicesBrowserTest):
    """Inventory item-grid journeys on the dedicated store_open server."""

    SERVICES_MODE = "store_open"

    def _open_inventory_drawer(self, page):
        """Open the re-homed inventory drawer from the exploration root."""
        focus_action_dock(page)
        # Move, Look, Interact, Character, Quests, Inventory
        for _ in range(5):
            _press(page, "ArrowRight")
        _press(page, "Enter")
        page.wait_for_timeout(120)
        return self._services_panel(page)

    @covers_requirement(
        "webclient-contextual-hud::the-bag-renders-the-bounded-inventory-rows-without-inventing-a-total-or-a-rarity",
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully",
    )
    def test_grid_renders_only_committed_rows_without_invented_total_or_rarity(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._open_inventory_drawer(page)

        # The committed panel is the source of truth: two held item keys,
        # with exact held counts and committed presentation metadata.
        committed = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        self.assertEqual(committed["meal"]["held"], 2)
        self.assertEqual(committed["healing_potion"]["held"], 1)
        self.assertEqual(committed["meal"]["presentation"]["rarity"], "common")
        self.assertEqual(committed["healing_potion"]["presentation"]["rarity"], "rare")
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
            [
                "inventory-panel__tile--healing_potion",
                "inventory-panel__tile--meal",
            ],
        )
        rarities = page.evaluate(
            """() => {
                return Array.from(
                    document.querySelectorAll('[data-testid^="inventory-panel__tile--"]')
                ).map((t) => t.getAttribute("data-rarity"));
            }"""
        )
        self.assertEqual(sorted(rarities), ["common", "rare"])

        # The lower-corner held count is the committed ``held`` value, never
        # a fabricated total.
        counts = page.evaluate(
            """() => {
                const meal = document.querySelector('[data-testid="inventory-panel__count--meal"]');
                const potion = document.querySelector('[data-testid="inventory-panel__count--healing_potion"]');
                return [meal.textContent, potion.textContent];
            }"""
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
        page.evaluate(
            """() => {
                const tile = document.querySelector('[data-testid="inventory-panel__tile--healing_potion"]');
                tile.focus();
                return true;
            }"""
        )
        page.wait_for_timeout(120)
        describedby = page.evaluate(
            """() => document.querySelector('[data-testid="inventory-panel__tile--healing_potion"]').getAttribute("aria-describedby")"""
        )
        self.assertEqual(describedby, "inventory-panel-inspector")
        name = page.evaluate(
            """() => document.querySelector('[data-testid="inventory-panel__inspector-name"]').textContent"""
        )
        self.assertEqual(name, "治療藥水")
        rarity = page.evaluate(
            """() => {
                const el = document.querySelector('[data-testid="inventory-panel__inspector-rarity"]');
                return el ? el.textContent : null;
            }"""
        )
        self.assertEqual(rarity, "稀有")
        kind = page.evaluate(
            """() => {
                const el = document.querySelector('[data-testid="inventory-panel__inspector-kind"]');
                return el ? el.textContent : null;
            }"""
        )
        self.assertEqual(kind, "藥水")
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
            """() => {
                const tile = document.querySelector('[data-testid="inventory-panel__tile--meal"]');
                tile.click();
                return true;
            }"""
        )
        page.wait_for_timeout(120)
        self.assertEqual(sent_action_count(page), 0)

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
