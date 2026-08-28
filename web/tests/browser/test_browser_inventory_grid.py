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
