"""Browser acceptance for inventory item actions (add-inventory-item-actions).

Journeys on the dedicated ``inventory_actions`` server, keyboard-first at
both desktop viewports (webclient-service-menus: keyboard-only,
confirmation-protected, desktop-bounded): an injured holder of two healing
potions and one sword. Keyboard activation of the enabled use tile opens the
labelled confirmation (Escape returns focus with nothing sent at 1440x900; a
1280x720 keyboard confirm dispatches exactly one ``inventory.use`` and the
committed ``hp_full`` refusal then governs the tile). A keyboard activation
of the enabled equipment row dispatches exactly one ``inventory.toggle_equip``
immediately, and the pointer affordance emits the identical envelope through
the same gates. Cancel, Escape, and an abnormal transport close all retire
the dialog without dispatching anything. In combat, the dock's frameless
背包 row opens the same drawer without inventing an action, and a
keyboard-confirmed potion use there dispatches exactly one ``inventory.use``.
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
from .test_browser_input_narrative import _wait_inp_line
from .test_browser_services import ServicesBrowserTest

TILE = "inventory-panel__tile--{}"
DIALOG = '[data-testid="inventory-panel__confirm"]'
DIALOG_OK = '[data-testid="inventory-panel__confirm-ok"]'


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


class _ItemActionBase(ServicesBrowserTest):
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

    def _wait_row(self, page, item_key, predicate, timeout=30000):
        def _ready(state):
            rows = state["panels"]["services"]["inventory"]["rows"]
            row = next((r for r in rows if r["item_key"] == item_key), None)
            return row is not None and predicate(row)

        wait_for_store_state(page, _ready, timeout=timeout)

    def _dialog_count(self, page):
        return page.locator(DIALOG).count()

    def _keyboard_activate_tile(self, page, item_key):
        page.focus(f'[data-testid="{TILE.format(item_key)}"]')
        _press(page, "Enter")

    def _keyboard_confirm_dialog(self, page):
        focused = page.evaluate(
            "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
        )
        self.assertEqual(focused, "inventory-panel__confirm-ok")
        _press(page, "Enter")


class InventoryActionJourneys(_ItemActionBase, ServicesBrowserTest):
    """Item-action keyboard/pointer journeys on the inventory_actions server."""

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment"
    )
    def test_keyboard_and_pointer_item_actions_are_confirmation_protected(self):
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

        # 1440x900, keyboard: activation opens the confirmation and Escape
        # returns focus to the tile with nothing dispatched.
        self._keyboard_activate_tile(page, "healing_potion")
        dialog = page.locator('[data-testid="inventory-panel__confirm-dialog"]')
        self.assertTrue(dialog.is_visible())
        self.assertIn("治療藥水", dialog.get_attribute("aria-label"))
        _press(page, "Escape")
        self.assertEqual(self._dialog_count(page), 0)
        focused = page.evaluate(
            "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
        )
        self.assertEqual(focused, TILE.format("healing_potion"))
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # 1280x720, keyboard: the confirmation stays fully operable and the
        # Enter on the focused 使用 control is the only submit path.
        page.set_viewport_size({"width": 1280, "height": 720})
        page.wait_for_timeout(120)
        self._keyboard_activate_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        self._keyboard_confirm_dialog(page)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)

        # The committed panel replaces the row: held 2 -> 1, and the first
        # use closed the seeded HP gap so the stable hp_full refusal governs.
        self._wait_row(page, "healing_potion", lambda row: row["held"] == 1)
        rows = self._services_rows(page)
        self.assertFalse(rows["healing_potion"]["action"]["enabled"])
        self.assertEqual(
            rows["healing_potion"]["action"]["disabled_reason"]["code"], "hp_full"
        )

        # Clicking the disabled tile opens no dialog and dispatches nothing.
        # (Playwright treats aria-disabled as "not enabled", so the click is
        # forced to exercise the app's own no-op handler.)
        self.assertEqual(self._dialog_count(page), 0, "dialog retires after commit")
        page.click(f'[data-testid="{TILE.format("healing_potion")}"]', force=True)
        page.wait_for_timeout(80)
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)

        # Focus spells the committed refusal verbatim in the shared inspector.
        page.focus(f'[data-testid="{TILE.format("healing_potion")}"]')
        page.wait_for_timeout(80)
        reason = page.locator('[data-testid="inventory-panel__inspector-reason"]')
        self.assertTrue(reason.is_visible())
        self.assertEqual(reason.text_content(), "你的體力已經全滿。")

        # Keyboard flow: Enter on the enabled equipment tile dispatches
        # exactly one toggle immediately — no confirmation opens.
        self._keyboard_activate_tile(page, "plain_sword")
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 1)
        self._wait_row(page, "plain_sword", lambda row: row["equipped"] is True)
        rows = self._services_rows(page)
        self.assertEqual(rows["plain_sword"]["action"]["label"], "卸下")

        # Pointer parity: the tile's pointer affordance emits the identical
        # envelope through the same dispatch entry and gates.
        page.click(f'[data-testid="{TILE.format("plain_sword")}"]')
        page.wait_for_timeout(80)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 2)
        envelopes = [
            args[0]
            for cmdname, args, _kwargs in (
                page.evaluate("window.__elosernSent || []")
            )
            if cmdname == "ui_action"
            and args
            and args[0].get("action_id") == "inventory.toggle_equip"
        ]
        self.assertEqual(len(envelopes), 2)
        # Same server-authored identifier and payload through the same gates;
        # each envelope pins its own live base revision by design.
        for env in envelopes:
            self.assertEqual(env["action_id"], "inventory.toggle_equip")
            self.assertEqual(env["payload"], {"item_key": "plain_sword"})
        self._wait_row(page, "plain_sword", lambda row: row["equipped"] is False)

    @covers_requirement(
        "webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_backpack_row_actions_echo_their_typed_commands(self):
        """Each deliberate backpack activation echoes exactly one typed line."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        self._open_inventory_drawer(page)

        # Equip: the toggle click dispatches once and echoes the typed
        # `equip <item_key>` — the exact text the 裝備/equip command accepts.
        self._keyboard_activate_tile(page, "plain_sword")
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 1)
        _wait_inp_line(page, 1, "equip plain_sword", exact=True)

        # Unequip direction: the same replayable line (the typed command IS
        # the toggle; no `unequip` line is ever printed).
        self._wait_row(page, "plain_sword", lambda row: row["equipped"] is True)
        self._keyboard_activate_tile(page, "plain_sword")
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 2)
        _wait_inp_line(page, 2, "equip plain_sword", exact=True)

        # Use: the confirmation-protected use echoes the typed `use <key>`.
        # The echo prints at dispatch, while the unequip's in-flight slot only
        # clears when its committed panel revision arrives — the store gate
        # drops any dispatch issued before then. Wait for the committed
        # unequip (row back to unequipped) before opening the use
        # confirmation, exactly as the equip/unequip pairs above do.
        self._wait_row(page, "plain_sword", lambda row: row["equipped"] is False)
        self._keyboard_activate_tile(page, "healing_potion")
        self._keyboard_confirm_dialog(page)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)
        _wait_inp_line(page, 3, "use healing_potion", exact=True)

        # The envelopes stay descriptor-free: the echo never enters the wire.
        envelopes = [
            args[0]
            for cmdname, args, _kwargs in page.evaluate("window.__elosernSent || []")
            if cmdname == "ui_action"
            and args
            and args[0].get("action_id")
            in {"inventory.use", "inventory.toggle_equip"}
        ]
        self.assertEqual(len(envelopes), 3)
        for envelope in envelopes:
            self.assertEqual(
                set(envelope),
                {
                    "protocol_version",
                    "presentation_epoch",
                    "request_id",
                    "base_revision",
                    "action_id",
                    "payload",
                },
            )

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
        self._keyboard_activate_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        _press(page, "Escape")
        self.assertEqual(self._dialog_count(page), 0)
        focused = page.evaluate(
            "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
        )
        self.assertEqual(focused, TILE.format("healing_potion"))
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # 取消 fails closed the same way.
        self._keyboard_activate_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        page.click('[data-testid="inventory-panel__confirm-cancel"]')
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # An abnormal transport close retires the dialog and the pending
        # intent; nothing is dispatched or replayed.
        self._keyboard_activate_tile(page, "healing_potion")
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


class CombatBagDrawerJourney(_ItemActionBase, ServicesBrowserTest):
    """The combat dock's frameless 背包 row and a keyboard-confirmed combat use."""

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
    def test_combat_bag_row_opens_the_drawer_and_confirms_one_item_use(self):
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

        # Combat item use through the same frameless surface: keyboard
        # activation opens the confirmation and the keyboard confirm
        # dispatches exactly one inventory.use.
        self._keyboard_activate_tile(page, "healing_potion")
        self.assertEqual(self._dialog_count(page), 1)
        self._keyboard_confirm_dialog(page)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)
        self._wait_row(page, "healing_potion", lambda row: row["held"] == 1)
