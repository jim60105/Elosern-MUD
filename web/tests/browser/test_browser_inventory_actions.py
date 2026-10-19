"""Browser acceptance for item actions in the party window's 背包 tab.

Journeys on the dedicated ``inventory_actions`` server, keyboard-first at
both desktop viewports (webclient-service-menus: keyboard-only,
confirmation-protected, desktop-bounded): an injured holder of two healing
potions and one sword, with the kit companion in the party. The old bag
drawer is retired (webclient-party-bag-retire): the top navigation's 背包
entry opens the party window on its 背包 tab, a row selection asks the server
for that item, and the pinned action bar carries 使用… (behind a labelled
confirmation; Escape returns focus with nothing sent at 1451x790, a
2560x1440 keyboard confirm dispatches exactly one ``inventory.use`` for the
viewed member and the committed refusal then governs it) and 裝備 / 卸下
(one ``inventory.toggle_equip`` at once, pointer and keyboard alike). Cancel,
Escape and an abnormal transport close retire the dialog without
dispatching. In combat the dock's client-local 背包 row opens the same tab,
設為 X 本回合的行動… yields to the commanded member's own item review step
(one ``combat.command`` item draft, never ``inventory.use``), and a party
journey gives potions to the companion, equips the companion, and observes
in combat that transfer is gone while the companion's toggle stays free.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import bag_action_fixture_values

from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_presentation_settled,
    wait_for_store_state,
)
from .test_browser_input_narrative import _wait_inp_line
from .test_browser_services_base import ServicesBrowserTest

ROW = "party-bag-tab__row--{}"
DIALOG = '[data-testid="party-bag-tab__confirm-dialog"]'
USE = "action-bar__btn--use"
TOGGLE = "action-bar__btn--toggle"
DRAFT = "action-bar__btn--draft"


def _press(page, key, wait_ms=80):
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _focused_testid(page):
    return page.evaluate(
        "() => document.activeElement && document.activeElement.getAttribute('data-testid')"
    )


def _panel(state, name):
    return (state.get("panels") or {}).get(name) or {}


def _idle(state):
    return not (state.get("dispatch") or {}).get("inFlight")


class _ItemActionBase(ServicesBrowserTest):
    SERVICES_MODE = "inventory_actions"

    def _open_inventory_drawer(self, page):
        """Open the party window on its 背包 tab from the top navigation."""
        # The base gate opened the quest drawer (a modal surface), so the
        # navigation click follows the store's single close entry.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.closeHudDrawer({ popFrame: true }); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        panel = self._open_surface(page, "inventory")
        # The post-login presentation burst must land before the first
        # activation: a party_inventory replacement retires an open
        # confirmation (stale-before-adapter guarantee).
        wait_for_presentation_settled(page)
        return panel

    def _viewed(self, page):
        return int(_panel(store_state(page), "party")["viewed_member_id"])

    def _rows(self, page):
        return {row["item_key"]: row for row in _panel(store_state(page), "party_inventory")["rows"]}

    def _wait_row(self, page, item_key, predicate, timeout=30000):
        def _ready(state):
            rows = _panel(state, "party_inventory").get("rows") or []
            row = next((r for r in rows if r["item_key"] == item_key), None)
            return row is not None and predicate(row)

        wait_for_store_state(page, _ready, timeout=timeout)

    def _select_row(self, page, item_key):
        """Select a bag row by keyboard: one party.view_member, then its answer."""
        wait_for_store_state(page, _idle, timeout=30000)
        holdings = _panel(store_state(page), "item_holdings")
        if holdings.get("item_key") != item_key:
            page.locator(f'[data-testid="{ROW.format(item_key)}"]').focus()
            page.wait_for_function(
                f"() => document.activeElement && document.activeElement.getAttribute('data-testid') === '{ROW.format(item_key)}'"
            )
            _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: _panel(s, "item_holdings").get("item_key") == item_key and _idle(s),
            timeout=30000,
        )
        wait_for_presentation_settled(page)
        page.wait_for_selector(f'[data-testid="{ROW.format(item_key)}"][aria-selected="true"]')

    def _dialog_count(self, page):
        return page.locator(DIALOG).count()

    def _keyboard_activate(self, page, testid):
        page.locator(f'[data-testid="{testid}"]').focus()
        page.wait_for_function(
            f"() => document.activeElement && document.activeElement.getAttribute('data-testid') === '{testid}'"
        )
        _press(page, "Enter")

    def _keyboard_confirm_dialog(self, page):
        self.assertEqual(_focused_testid(page), "party-bag-tab__confirm-ok")
        _press(page, "Enter")

    def _ui_actions(self, page, action_id):
        return [
            args[0]
            for cmdname, args, _kwargs in page.evaluate("window.__elosernSent || []")
            if cmdname == "ui_action" and args and args[0].get("action_id") == action_id
        ]


class InventoryActionJourneys(_ItemActionBase, ServicesBrowserTest):
    """Item-action keyboard/pointer journeys on the inventory_actions server."""

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment",
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
    )
    def test_keyboard_and_pointer_item_actions_are_confirmation_protected(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        panel = self._open_inventory_drawer(page)

        BAG = bag_action_fixture_values()
        potion, weapon = BAG["potion_key"], BAG["weapon_key"]
        committed = {row["item_key"]: row for row in panel["rows"]}
        self.assertEqual(committed[potion]["held"], 2)
        self.assertEqual(committed[potion]["use"]["route"], "field_use")
        self.assertTrue(committed[potion]["use"]["enabled"])
        self.assertTrue(committed[weapon]["toggle"]["enabled"])
        viewed = self._viewed(page)

        # 1451x790, keyboard: 使用… opens the labelled confirmation, and
        # Escape returns focus to 使用… with nothing dispatched.
        self._select_row(page, potion)
        self._keyboard_activate(page, USE)
        dialog = page.locator(DIALOG)
        self.assertTrue(dialog.is_visible())
        self.assertIn(BAG["potion_display"], dialog.get_attribute("aria-label"))
        _press(page, "Escape")
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(_focused_testid(page), USE)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # 2560x1440, keyboard: the confirmation stays fully operable and the
        # Enter on the focused 使用 control is the only submit path.
        page.set_viewport_size({"width": 2560, "height": 1440})
        page.wait_for_timeout(120)
        self._keyboard_activate(page, USE)
        self.assertEqual(self._dialog_count(page), 1)
        self._keyboard_confirm_dialog(page)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)
        self.assertEqual(
            self._ui_actions(page, "inventory.use")[0]["payload"],
            {"item_key": potion, "actor_id": viewed},
        )

        # The committed panel replaces the row: held 2 -> 1, and the first
        # use closed the seeded HP gap so the committed refusal governs.
        self._wait_row(page, potion, lambda row: row["held"] == 1 and row["use"]["enabled"] is False)
        reason = self._rows(page)[potion]["use"]["reason"]
        self.assertTrue(reason)
        page.wait_for_selector(f'[data-testid="{USE}"][aria-disabled="true"]')
        self.assertEqual(self._dialog_count(page), 0, "the dialog retires after the commit")
        # The disabled control keeps focus, spells the committed reason, and
        # dispatches nothing (Playwright treats aria-disabled as not enabled,
        # so the click is forced to exercise the app's own no-op).
        reasons = page.locator('[data-testid="action-bar__reason"]').all_text_contents()
        self.assertIn(reason if isinstance(reason, str) else reason["message"], reasons)
        page.click(f'[data-testid="{USE}"]', force=True)
        page.wait_for_timeout(80)
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)

        # Keyboard: 裝備 on the equipment row dispatches exactly one toggle
        # for the viewed member at once — no confirmation opens.
        page.set_viewport_size({"width": 1451, "height": 790})
        self._select_row(page, weapon)
        self._keyboard_activate(page, TOGGLE)
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 1)
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 1)
        page.wait_for_function(
            f"() => (document.querySelector('[data-testid=\"{TOGGLE}\"]') || {{}}).textContent?.trim() === '卸下'"
        )

        # Pointer parity: the same control's click emits the identical
        # envelope through the same gates.
        wait_for_store_state(page, _idle, timeout=30000)
        page.click(f'[data-testid="{TOGGLE}"]')
        page.wait_for_timeout(80)
        envelopes = self._ui_actions(page, "inventory.toggle_equip")
        self.assertEqual(len(envelopes), 2)
        for envelope in envelopes:
            self.assertEqual(envelope["payload"], {"item_key": weapon, "actor_id": viewed})
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 0)

    @covers_requirement(
        "webclient-input-narrative::a-deliberate-mutation-echo-appears-exactly-once-at-dispatch"
    )
    def test_backpack_row_actions_echo_their_typed_commands(self):
        """Each deliberate bag activation echoes exactly one typed line."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        self._open_inventory_drawer(page)

        BAG = bag_action_fixture_values()
        potion, weapon = BAG["potion_key"], BAG["weapon_key"]

        def reopen():
            # The full log closes over the window; reopen it on 背包.
            if page.locator('[data-testid="party-bag-tab"]').count() == 0:
                self._open_inventory_drawer(page)

        # Equip: the toggle dispatches once and echoes the typed
        # `equip <item_key>`; the row selection itself echoes nothing.
        self._select_row(page, weapon)
        self._keyboard_activate(page, TOGGLE)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 1)
        _wait_inp_line(page, 1, f"equip {weapon}", exact=True)

        # Unequip: the same replayable line.
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 1)
        reopen()
        self._select_row(page, weapon)
        self._keyboard_activate(page, TOGGLE)
        self.assertEqual(sent_action_count(page, "inventory.toggle_equip"), 2)
        _wait_inp_line(page, 2, f"equip {weapon}", exact=True)

        # Use: the confirmation-protected use echoes the typed `use <key>`.
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 0)
        reopen()
        self._select_row(page, potion)
        self._keyboard_activate(page, USE)
        self._keyboard_confirm_dialog(page)
        self.assertEqual(sent_action_count(page, "inventory.use"), 1)
        _wait_inp_line(page, 3, f"use {potion}", exact=True)

        # The envelopes stay descriptor-free: the echo never enters the wire.
        envelopes = self._ui_actions(page, "inventory.use") + self._ui_actions(page, "inventory.toggle_equip")
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

        potion = bag_action_fixture_values()["potion_key"]
        self._select_row(page, potion)
        # Escape closes the dialog, dispatches nothing, and returns focus to
        # the control that opened it.
        self._keyboard_activate(page, USE)
        self.assertEqual(self._dialog_count(page), 1)
        _press(page, "Escape")
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(_focused_testid(page), USE)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # 取消 fails closed the same way.
        self._keyboard_activate(page, USE)
        self.assertEqual(self._dialog_count(page), 1)
        page.click('[data-testid="party-bag-tab__confirm-cancel"]')
        self.assertEqual(self._dialog_count(page), 0)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # An abnormal transport close retires the dialog and the pending
        # intent; nothing is dispatched or replayed.
        self._keyboard_activate(page, USE)
        self.assertEqual(self._dialog_count(page), 1)
        page.evaluate("() => { if (window.__elosernWs) window.__elosernWs.close(4001); }")
        wait_for_store_state(page, lambda s: not s.get("connected"), timeout=30000)
        self.assertEqual(self._dialog_count(page), 0, "transport loss retires the dialog")
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)


class _CombatBagBase(_ItemActionBase):
    def _wait_combat_mode(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state_or_none(page) or {}
            panel = (state.get("panels") or {}).get("context_actions")
            if state.get("mode") == "combat" and (panel or {}).get("available") is True:
                return
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

    def _engage(self, page):
        engage_target = bag_action_fixture_values()["engage_target"]
        page.evaluate("([target]) => Evennia.msg('text', [`engage ${target}`], {})", [engage_target])
        self._wait_combat_mode(page)

    def _combat_panel(self, page) -> dict:
        return store_state(page)["panels"]["context_actions"]

    def _focus_ring_row(self, page, key: str, limit: int = 20) -> None:
        """Walk the mounted single-column ring (Down wraps) until ``key`` holds focus."""
        for _ in range(limit):
            if (store_state_or_none(page) or {}).get("focus", {}).get("key") == key:
                return
            _press(page, "ArrowDown")


class CombatBagDrawerJourney(_CombatBagBase, ServicesBrowserTest):
    """The combat dock's client-local 背包 row and one actor-commanded combat use."""

    SERVICES_MODE = "inventory_actions"

    def _foe_identity(self, page) -> int:
        for participant in self._combat_panel(page)["participants"]:
            if participant["team"] == "foes" and participant["state"] == "active":
                return int(participant["identity"])
        raise AssertionError("no active foe")

    def _wait_beat_settled(self, page, timeout: int = 60000) -> None:
        """Wait until the resolved round's playback finished and the card is ready."""
        page.wait_for_timeout(600)
        wait_for_store_state(
            page,
            lambda s: (
                s.get("beatPlayback") is None
                or (s.get("beatPlayback") or {}).get("phase") == "done"
            )
            and not s.get("beatHold")
            and not (s.get("dispatch") or {}).get("beatLocked")
            and s.get("combatProgress") is not None,
            timeout=timeout,
        )

    def _settle_round_with_companion_attack(self, page) -> None:
        """Complete the round by commanding the next member's basic attack."""
        wait_for_store_state(page, _idle, timeout=30000)
        for _ in range(3):
            if (store_state_or_none(page) or {}).get("dockSource") == "combat.root":
                break
            _press(page, "Escape")
        self.assertEqual((store_state_or_none(page) or {}).get("dockSource"), "combat.root")
        foe = self._foe_identity(page)
        self._focus_ring_row(page, "attack")
        _press(page, "Enter")
        self._focus_ring_row(page, f"target-{foe}")
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: ((_panel(s, "context_actions").get("session")) or {}).get("round", 0) >= 1,
            timeout=30000,
        )
        self._wait_beat_settled(page)

    @covers_requirement(
        "inventory-item-actions::inventory-tiles-confirm-use-and-directly-toggle-equipment",
        "webclient-service-menus::service-browser-acceptance-is-keyboard-only-confirmation-protected-and-desktop-bounded",
    )
    def test_combat_bag_row_opens_the_drawer_and_confirms_one_item_use(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.closeHudDrawer({ popFrame: true }); }"
        )
        self._engage(page)

        focus_action_dock(page)
        self._focus_ring_row(page, "bag", limit=12)
        self.assertEqual(
            (store_state_or_none(page) or {}).get("focus", {}).get("key"),
            "bag",
            "the combat dock exposes the 背包 row",
        )
        sent_before = sent_action_count(page)
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "party",
            dom_readiness={
                "selector": '[data-testid="party-bag-tab"]',
                "predicate": "() => !!document.querySelector('[data-testid=\"party-bag-tab\"]')",
                "description": "the party window's 背包 tab mounted during combat",
            },
            timeout=30000,
        )
        # The row opens the window client-locally: no dispatch, no frame.
        self.assertEqual(sent_action_count(page), sent_before)
        self.assertEqual(store_state(page).get("dockDepth"), 1)

        # 設為 X 本回合的行動… for the commanded member yields the window to the
        # card's own item review step, never the actorless inventory.use.
        potion = bag_action_fixture_values()["potion_key"]
        wait_for_presentation_settled(page)
        self._select_row(page, potion)
        self.assertEqual(self._rows(page)[potion]["use"]["route"], "combat_draft")
        self.assertEqual(page.locator(f'[data-testid="{USE}"]').count(), 0)
        self._keyboard_activate(page, DRAFT)
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") is None
            and s.get("dockSource") == "combat.item"
            and s.get("dockDepth") == 2,
            dom_readiness={
                "selector": '#action-dock [data-testid="dock-menu"] [data-item-key]',
                "predicate": (
                    "() => !!document.querySelector("
                    "'#action-dock [data-testid=\"dock-menu\"] [data-item-key]')"
                ),
                "description": "the card's own item step mounted",
            },
            timeout=30000,
        )
        self.assertEqual(self._dialog_count(page), 0, "combat use opens no window-local confirmation")
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)
        self.assertEqual(sent_action_count(page, "party.transfer"), 0)

        # The SELF item's own review row is the confirmation: exactly one
        # guarded combat.command item draft, and nothing else.
        _press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: any(
                entry["command"].get("kind") == "item"
                for entry in (_panel(s, "context_actions").get("draft") or {}).get("entries", [])
            ),
            timeout=30000,
        )
        item_commands = [
            envelope
            for envelope in self._ui_actions(page, "combat.command")
            if envelope["payload"]["command"]["kind"] == "item"
        ]
        self.assertEqual(len(item_commands), 1, item_commands)
        self.assertEqual(item_commands[0]["payload"]["command"]["payload"], {"item_key": potion})

        # One settlement consumes exactly one potion.
        self._settle_round_with_companion_attack(page)
        self._wait_row(page, potion, lambda row: row["held"] == 1)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)


class PartyBagTransferJourney(_CombatBagBase, ServicesBrowserTest):
    """Give and equip a companion from the bag, then lose transfer in combat."""

    SERVICES_MODE = "inventory_actions"

    @covers_requirement(
        "webclient-party-window::giving-from-the-bag-uses-the-committed-receive-facts",
        "webclient-party-window::the-bag-action-bar-uses-or-equips-for-the-viewed-member",
    )
    def test_give_and_equip_a_companion_then_combat_disables_transfer(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)
        self._open_inventory_drawer(page)

        BAG = bag_action_fixture_values()
        potion, weapon = BAG["potion_key"], BAG["weapon_key"]
        party = _panel(store_state(page), "party")
        commander = int(party["slots"][0]["identity"])
        companions = [int(slot["identity"]) for slot in party["slots"][1:] if slot.get("identity") is not None]
        self.assertTrue(companions, "the kit party carries a companion")
        companion = companions[0]
        self.assertEqual(self._viewed(page), commander)

        # Give two potions: the stepper raises the quantity, and the
        # companion's cell sends exactly one party.transfer naming both.
        self._select_row(page, potion)
        give = f'[data-testid="holdings-strip__give--{companion}"]'
        page.wait_for_selector(give)
        page.click('[data-testid="party-bag-tab__stepper-up"]')
        self.assertEqual(page.locator('[data-testid="party-bag-tab__quantity"]').text_content(), "2")
        page.click(give)
        wait_for_store_state(page, _idle, timeout=30000)
        transfers = self._ui_actions(page, "party.transfer")
        self.assertEqual(len(transfers), 1)
        self.assertEqual(
            transfers[0]["payload"],
            {"giver_id": commander, "receiver_id": companion, "item_key": potion, "quantity": 2},
        )
        wait_for_store_state(
            page,
            lambda s: not any(r["item_key"] == potion for r in (_panel(s, "party_inventory").get("rows") or [])),
            timeout=30000,
        )

        # Give the sword, then view the companion and equip it there: the
        # toggle names the companion as its actor.
        self._select_row(page, weapon)
        page.wait_for_selector(give)
        page.click(give)
        wait_for_store_state(
            page,
            lambda s: _idle(s)
            and not any(r["item_key"] == weapon for r in (_panel(s, "party_inventory").get("rows") or [])),
            timeout=30000,
        )
        page.click(f'[data-testid="member-rail__entry--{companion}"]')
        wait_for_store_state(
            page,
            lambda s: _panel(s, "party").get("viewed_member_id") == companion
            and _panel(s, "party_inventory").get("member_id") == companion
            and _idle(s),
            timeout=30000,
        )
        rows = self._rows(page)
        self.assertEqual(rows[potion]["held"], 2)
        self.assertTrue(rows[weapon]["toggle"]["enabled"], rows[weapon]["toggle"])
        self._select_row(page, weapon)
        self._keyboard_activate(page, TOGGLE)
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 1)
        toggles = self._ui_actions(page, "inventory.toggle_equip")
        self.assertEqual(toggles[-1]["payload"], {"item_key": weapon, "actor_id": companion})

        # Combat: the window stays open on the companion's bag; the strip
        # shows counts only, no give control or stepper remains, the bar
        # states the committed transfer reason, and the companion's toggle
        # stays free.
        wait_for_store_state(page, _idle, timeout=30000)
        self._engage(page)
        wait_for_store_state(
            page,
            lambda s: s.get("hudDrawer") == "party"
            and any(
                r["item_key"] == weapon and r["give"]["enabled"] is False
                for r in (_panel(s, "party_inventory").get("rows") or [])
            ),
            timeout=30000,
        )
        wait_for_presentation_settled(page)
        self._select_row(page, potion)
        page.wait_for_selector('[data-testid="holdings-strip"][data-combat="true"]')
        self.assertEqual(page.locator('[data-testid^="holdings-strip__give--"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="party-bag-tab__stepper"]').count(), 0)
        reason = self._rows(page)[potion]["give"]["reason"]
        self.assertIn(reason, page.locator('[data-testid="action-bar__reason"]').all_text_contents())
        self.assertEqual(page.locator(f'[data-testid="{USE}"]').count(), 0)
        self.assertEqual(page.locator(f'[data-testid="{DRAFT}"]').count(), 1)

        transfers_before = sent_action_count(page, "party.transfer")
        self._select_row(page, weapon)
        self._keyboard_activate(page, TOGGLE)
        self._wait_row(page, weapon, lambda row: row["equipped_count"] == 0)
        self.assertEqual(
            self._ui_actions(page, "inventory.toggle_equip")[-1]["payload"],
            {"item_key": weapon, "actor_id": companion},
        )
        self.assertEqual(sent_action_count(page, "party.transfer"), transfers_before)
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)
