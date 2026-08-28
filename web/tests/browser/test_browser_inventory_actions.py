"""Browser acceptance for inventory item actions (add-inventory-item-actions).

Journeys on the dedicated ``inventory_actions`` server: an injured holder of
two healing potions and one sword. A pointer click on an enabled use row
opens the labelled confirmation and dispatches exactly one ``inventory.use``
on 使用; the committed panel then governs (held count drops, the stable
``hp_full`` refusal disables the tile and the inspector spells it, and a
later click dispatches nothing). A keyboard activation of the enabled
equipment row dispatches exactly one ``inventory.toggle_equip`` immediately
(no confirmation). Cancel, Escape, and an abnormal transport close all
retire the dialog without dispatching anything. The combat dock's frameless
背包 row opens the same drawer without inventing an action.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_store_state,
)
from .test_browser_services import ServicesBrowserTest


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class InventoryActionJourneys(ServicesBrowserTest):
    """Item-action pointer/keyboard journeys on the inventory_actions server."""

    SERVICES_MODE = "inventory_actions"

    def _open_inventory_drawer(self, page):
        focus_action_dock(page)
        # Move, Look, Interact, Character, Quests, Inventory
        for _ in range(5):
            _press(page, "ArrowRight")
        _press(page, "Enter")
        page.wait_for_timeout(120)
        return self._services_panel(page)

    def _services_rows(self, page):
        rows = store_state(page)["panels"]["services"]["inventory"]["rows"]
        return {row["item_key"]: row for row in rows}

    def _dialog_count(self, page):
        return page.locator('[data-testid="inventory-panel__confirm"]').count()

    def _click_tile(self, page, item_key):
        page.click(f'[data-testid="inventory-panel__tile--{item_key}"]')
        page.wait_for_timeout(80)

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment"
    )
    def test_pointer_confirm_use_and_keyboard_toggle_dispatch_exactly_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._open_inventory_drawer(page)

        committed = {row["item_key"]: row for row in panel["inventory"]["rows"]}
        self.assertEqual(committed["healing_potion"]["held"], 2)
        self.assertEqual(
            committed["healing_potion"]["action"]["action_id"], "inventory.use"
        )
        self.assertTrue(committed["healing_potion"]["action"]["enabled"])
        self.assertEqual(
            committed["plain_sword"]["action"]["action_id"], "inventory.toggle_equip"
        )
        self.assertTrue(committed["plain_sword"]["action"]["enabled"])

        # Pointer flow: clicking the enabled use tile opens the labelled
        # confirmation and dispatches nothing until 使用 confirms.
        self._click_tile(page, "healing_potion")
        dialog = page.locator('[data-testid="inventory-panel__confirm-dialog"]')
        self.assertTrue(dialog.is_visible())
        self.assertIn("治療藥水", dialog.get_attribute("aria-label"))
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        page.click('[data-testid="inventory-panel__confirm-ok"]')
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)

        # The committed panel replaces the row: held 2 -> 1, and the first
        # use closes the seeded HP gap so the stable hp_full refusal governs.
        wait_for_store_state(
            page,
            lambda s: (
                {r["item_key"]: r for r in s["panels"]["services"]["inventory"]["rows"]}
                .get("healing_potion", {})
                .get("held")
                == 1
            ),
            timeout=30000,
        )
        rows = self._services_rows(page)
        self.assertEqual(rows["healing_potion"]["held"], 1)
        self.assertFalse(rows["healing_potion"]["action"]["enabled"])
        self.assertEqual(
            rows["healing_potion"]["action"]["disabled_reason"]["code"], "hp_full"
        )

        # Clicking the disabled tile opens no dialog and dispatches nothing.
        # (Playwright treats aria-disabled as "not enabled", so the click is
        # forced to exercise the app's own no-op handler.)
        self.assertEqual(self._dialog_count(page), 0, "dialog retires after commit")
        page.click(
            '[data-testid="inventory-panel__tile--healing_potion"]', force=True
        )
        page.wait_for_timeout(80)
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)

        # Focus spells the committed refusal verbatim in the shared inspector.
        page.focus('[data-testid="inventory-panel__tile--healing_potion"]')
        page.wait_for_timeout(80)
        reason = page.locator('[data-testid="inventory-panel__inspector-reason"]')
        self.assertTrue(reason.is_visible())
        self.assertEqual(reason.text_content(), "你的體力已經全滿。")

        # Keyboard flow: Enter on the enabled equipment tile dispatches
        # exactly one toggle immediately — no confirmation opens.
        page.focus('[data-testid="inventory-panel__tile--plain_sword"]')
        _press(page, "Enter")
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 1)
        wait_for_store_state(
            page,
            lambda s: (
                {r["item_key"]: r for r in s["panels"]["services"]["inventory"]["rows"]}
                .get("plain_sword", {})
                .get("equipped")
                is True
            ),
            timeout=30000,
        )
        rows = self._services_rows(page)
        self.assertTrue(rows["plain_sword"]["equipped"])
        self.assertEqual(rows["plain_sword"]["action"]["label"], "卸下")

    @covers_requirement(
        "inventory-item-actions::item-dialogs-and-dispatch-state-fail-closed-across-replacement-and-transport-changes"
    )
    def test_dialogs_and_dispatch_state_fail_closed_across_interruptions(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        self._open_inventory_drawer(page)

        # Escape closes the dialog, dispatches nothing, and returns focus to
        # the originating tile.
        self._click_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        _press(page, "Escape")
        self.assertEqual(self._dialog_count(page), 0)
        focused = page.evaluate(
            "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
        )
        self.assertEqual(focused, "inventory-panel__tile--healing_potion")
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # 取消 fails closed the same way.
        self._click_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        page.click('[data-testid="inventory-panel__confirm-cancel"]')
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # An abnormal transport close retires the dialog and the pending
        # intent; nothing is dispatched or replayed.
        self._click_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            timeout=30000,
        )
        self.assertEqual(self._dialog_count(page), 0, "transport loss retires dialog")
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)


class CombatBagDrawerJourney(ServicesBrowserTest):
    """The combat dock's frameless 背包 row opens the drawer without a dispatch."""

    SERVICES_MODE = "inventory_actions"

    def _wait_combat_mode(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state_or_none(page) or {}
            panel = (state.get("panels") or {}).get("context_actions")
            if state.get("mode") == "combat" and (panel or {}).get("available") is True:
                return
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment"
    )
    def test_combat_bag_row_opens_the_drawer_without_any_dispatch(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)

        page.evaluate("Evennia.msg('text', ['engage goblin'], {})")
        self._wait_combat_mode(page)

        focus_action_dock(page)
        # Walk the root row ring until the client-local 背包 row is focused.
        focused_key = None
        for _ in range(12):
            focused_key = (store_state_or_none(page) or {}).get("focus", {}).get("key")
            if focused_key == "bag":
                break
            _press(page, "ArrowRight")
        self.assertEqual(focused_key, "bag", "the combat dock exposes the 背包 row")

        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "inventory",
            dom_readiness={
                "selector": '[data-testid="inventory-panel"]',
                "predicate": (
                    "() => !!document.querySelector('[data-testid=\"inventory-panel\"]')"
                ),
                "description": "inventory drawer body mounted during combat",
            },
            timeout=30000,
        )
        # The row opens the drawer client-locally: no dispatch, no frame.
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(store_state(page).get("dockDepth"), 1)
