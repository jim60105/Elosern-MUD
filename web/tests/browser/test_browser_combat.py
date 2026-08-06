"""Keyboard-only combat menu browser acceptance (webclient-combat-menu 5.2-5.5).

These journeys drive the real Evennia server's combat sessions through the
GoldenLayout action dock: the seeded character owns fire_ball (SINGLE),
wind_blade (AREA), status_disguise (SELF), concentration (NONE), and the innate
basic_attack (SINGLE) and flee (SELF). Each test starts combat by engaging a
fixture monster through the ordinary drawer, then drives the combat dock with
arrows and Enter, asserting the exact OOB payloads and ordinary narrative
delivery.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
)


class CombatMenuBrowserTest(BrowserAcceptanceTest):
    """Engages a fixture monster and drives the combat dock with the keyboard.

    Each test boots its own dedicated isolated server: an active combat session
    leaves the Evennia server session in a state that a later fresh login on
    the same server cannot reuse cleanly, so combat tests never share a server
    with each other or with the foundation suite.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _engage(self, page, name="goblin"):
        """Send the engage command through the ordinary text transport."""
        page.evaluate("Evennia.msg('text', ['engage %s'], {})" % name)
        self._wait_combat_mode(page)

    def _wait_combat_mode(self, page, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = state["panels"] and state["panels"].get("context_actions")
            if (
                state["mode"] == "combat"
                and panel
                and panel.get("available") is True
            ):
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

    def _dock_mode(self, page):
        return page.evaluate(
            "document.getElementById('action-dock').getAttribute('data-mode')"
        )

    def _combat_panel(self, page):
        return store_state(page)["panels"]["context_actions"]

    def _ui_actions(self, page):
        """Return the list of (cmdname, args, kwargs) ui_action records."""
        sent = page.evaluate("window.__elosernSent || []")
        return [
            (cmd, args, kwargs)
            for cmd, args, kwargs in sent
            if cmd == "ui_action"
        ]

    def _press(self, page, key):
        page.keyboard.press(key)
        page.wait_for_timeout(80)

    def _basic_attack_target_identity(self, page):
        panel = self._combat_panel(page)
        for participant in panel["participants"]:
            if participant["team"] == "foes":
                return participant["identity"]
        raise AssertionError("no enemy participant")

    def _fire_ball_identity(self, page):
        panel = self._combat_panel(page)
        for participant in panel["participants"]:
            if participant["team"] == "foes":
                return participant["identity"]
        raise AssertionError("no enemy participant")

    def test_focus_stays_on_action_dock_in_combat(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self.assertEqual(self._dock_mode(page), "combat")
        page.evaluate("document.getElementById('action-dock').focus()")
        # The action dock remains the documented focus target and forwards
        # focus to the mounted listbox row container (composite widget).
        self.assertEqual(
            page.evaluate(
                """() => {
                  const active = document.activeElement;
                  const dock = document.getElementById('action-dock');
                  return active === dock || (active && dock.contains(active));
                }"""
            ),
            True,
        )

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_attack_flow_submits_basic_attack_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        target = self._basic_attack_target_identity(page)

        # Root: first item is Attack. Open it, then the single target.
        self._press(page, "ArrowDown")  # skills
        self._press(page, "ArrowUp")  # back to attack
        self._press(page, "Enter")  # open attack
        self._press(page, "Enter")  # select the first valid target

        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "basic_attack")
        self.assertEqual(envelope["payload"]["target_ids"], [target])

    @covers_requirement("webclient-combat-menu::combat-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_single_skill_target_flow(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        target = self._fire_ball_identity(page)

        self._press(page, "ArrowDown")  # skills
        self._press(page, "Enter")  # open skills list
        # Skills list starts at fire_ball (first owned active skill).
        self._press(page, "Enter")  # open fire_ball targets
        self._press(page, "Enter")  # select first target

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "fire_ball")
        self.assertEqual(envelope["payload"]["target_ids"], [target])

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_self_skill_submits_no_target_field(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # status_disguise is the third owned skill in the skills list.
        self._press(page, "ArrowDown")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # wind_blade
        self._press(page, "ArrowDown")  # status_disguise
        self._press(page, "Enter")  # open status_disguise
        self._press(page, "Enter")  # confirm self-cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "status_disguise")
        self.assertNotIn("target_ids", envelope["payload"])
        self.assertNotIn("target_shorthand", envelope["payload"])
        self.assertNotIn("actor", envelope["payload"])

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_none_skill_submits_skill_key_only(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # concentration is the fourth owned active skill in the skills list.
        self._press(page, "ArrowDown")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # wind_blade
        self._press(page, "ArrowDown")  # status_disguise
        self._press(page, "ArrowDown")  # concentration
        self._press(page, "Enter")  # open concentration (NONE)
        self._press(page, "Enter")  # confirm the single 施展 item

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "concentration")
        self.assertNotIn("target_ids", envelope["payload"])
        self.assertNotIn("target_shorthand", envelope["payload"])
        self.assertNotIn("actor", envelope["payload"])

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_area_shorthand_flow(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # Skills -> wind_blade (AREA) -> all-enemies shorthand -> confirm.
        self._press(page, "ArrowDown")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # wind_blade
        self._press(page, "Enter")  # open wind_blade
        # AREA menu: candidate targets, then shorthands, then confirm.
        self._press(page, "ArrowDown")  # first shorthand
        self._press(page, "Enter")  # choose shorthand
        self._press(page, "ArrowDown")  # second shorthand (if present)
        self._press(page, "ArrowDown")  # confirm
        self._press(page, "Enter")  # confirm cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "wind_blade")
        self.assertEqual(envelope["payload"]["target_shorthand"], "all-enemies")
        self.assertNotIn("target_ids", envelope["payload"])

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_disabled_items_defend_send_no_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._press(page, "ArrowDown")  # skills
        self._press(page, "ArrowDown")  # items (disabled)
        self._press(page, "Enter")
        self._press(page, "ArrowDown")  # defend (disabled)
        self._press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_flee_flow_submits_empty_payload(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._press(page, "ArrowDown")
        self._press(page, "ArrowDown")
        self._press(page, "ArrowDown")
        self._press(page, "ArrowDown")  # flee is the last root item
        self._press(page, "Enter")

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.flee")
        self.assertEqual(envelope["payload"], {})

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_forfeit_requires_confirmation(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        session_id = self._combat_panel(page)["session"]["session_id"]
        # Root order: attack, skills, items, defend, flee, forfeit.
        for _ in range(5):
            self._press(page, "ArrowDown")
        self._press(page, "Enter")  # open the secondary Forfeit menu
        self.assertEqual(
            sent_action_count(page), 0, "opening Forfeit must not mutate"
        )
        # Escape cancels back to the root without ending combat.
        self._press(page, "Escape")
        self.assertEqual(sent_action_count(page), 0)
        self.assertEqual(self._dock_mode(page), "combat")
        # Reopen and confirm: exactly one combat.forfeit with the current ID.
        self._press(page, "Enter")  # forfeit still focused in the root
        self._press(page, "Enter")  # confirm-forfeit
        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.forfeit")
        self.assertEqual(envelope["payload"]["session_id"], session_id)
        # The confirmed forfeit ends the session.
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); "
            "const p = s.panels && s.panels['context_actions']; "
            "return p && p.available === false; }",
            timeout=15000,
        )

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_area_explicit_multi_selection(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        enemy_ids = [
            p["identity"] for p in panel["participants"] if p["team"] == "foes"
        ]
        self.assertEqual(len(enemy_ids), 1, "engage opens a single-enemy battle")
        wind = next(s for s in panel["skills"] if s["key"] == "wind_blade")

        self._press(page, "ArrowDown")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # wind_blade
        self._press(page, "Enter")  # open wind_blade target menu
        # AREA menu: candidate targets first, then shorthands, then confirm.
        self._press(page, "Space")  # toggle the explicit candidate
        for _ in range(len(wind["shorthands"]) + 1):
            self._press(page, "ArrowDown")  # past shorthands to confirm
        self._press(page, "Enter")  # confirm cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "wind_blade")
        self.assertEqual(envelope["payload"]["target_ids"], enemy_ids)
        self.assertNotIn("target_shorthand", envelope["payload"])

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_disabled_reason_is_visible_without_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._press(page, "ArrowDown")  # skills
        self._press(page, "ArrowDown")  # items (disabled)
        detail = page.evaluate(
            "document.getElementById('combat-detail').innerText"
        )
        self.assertIn("道具功能尚未開放", detail)
        self._press(page, "Enter")  # disabled confirm -> explanation, no packet
        self._press(page, "ArrowDown")  # defend (disabled)
        self._press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)
        detail = page.evaluate(
            "document.getElementById('combat-detail').innerText"
        )
        self.assertIn("防禦功能尚未開放", detail)

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_combat_rebuilds_keyboard_menu_after_round(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # Wait for the dock to install the keyboard root before driving it; the
        # subscription that installs it may not have run the moment combat mode
        # becomes available.
        page.wait_for_function(
            "() => Elosern._combat && Elosern.keyboard && "
            "Elosern.keyboard.depth() >= 1",
            timeout=15000,
        )
        self._press(page, "Enter")  # attack (first root item) -> target menu
        self._press(page, "Enter")  # select the first valid target
        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        # The accepted panel advances the round; the keyboard model must be
        # rebuilt from that panel, not the stale pre-round selection.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            panel = self._combat_panel(page)
            if panel.get("available") and panel["session"]["round"] >= 1:
                rebuilt = page.evaluate(
                    "() => { const p = Elosern.StateController.getState()"
                    ".panels['context_actions']; return Elosern._combat && "
                    "Elosern._combat.panel.session.round === p.session.round; }"
                )
                if rebuilt:
                    break
            page.wait_for_timeout(250)
        else:
            panel = self._combat_panel(page)
            result = store_state(page)["lastActionResult"]
            raise AssertionError(
                "keyboard menu was not rebuilt from the accepted panel: "
                f"panel={panel!r} lastActionResult={result!r}"
            )
        # The rebuilt root lets another action submit from fresh data.
        self._press(page, "Enter")  # attack again
        self._press(page, "Enter")  # select the first valid target
        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 2, actions)

    @covers_requirement("webclient-combat-menu::combat-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_combat_renders_at_minimum_viewport(self):
        page = self.logged_in_page(viewport=(1280, 720))
        install_outbound_recorder(page)
        self._engage(page)
        self.assertEqual(self._dock_mode(page), "combat")
        narrative = page.locator(".elosern-narrative").inner_text()
        self.assertTrue(narrative.strip())
        # True numeric resources remain visible.
        for key in ("hp", "mp", "sp"):
            value = page.locator(
                f".status-resources .resource-{key} .resource-value"
            ).inner_text()
            self.assertRegex(
                value,
                r"^\d+ / \d+$",
                f"{key} resource must render current/maximum values",
            )
        # The seeded poisoned buff surfaces applied modifier text.
        conditions = page.locator(".status-conditions").inner_text()
        self.assertIn("agility", conditions)
        self.assertIn("-10%", conditions)
        # Action controls stay usable and disabled entries explain themselves.
        self.assertTrue(page.locator(".combat-controls").is_visible())
        self._press(page, "ArrowDown")  # skills
        self._press(page, "ArrowDown")  # items (disabled)
        self.assertIn(
            "道具功能尚未開放",
            page.evaluate("document.getElementById('combat-detail').innerText"),
        )
        self.assertEqual(
            page.evaluate("document.getElementById('action-dock').scrollWidth <= "
                          "document.getElementById('action-dock').clientWidth"),
            True,
        )
