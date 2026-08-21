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
    wait_for_presentation_settled,
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

        # Root: first item is Attack. Open it, then its single-target menu
        # lists the actor and the monster (both valid for ANY scope); move
        # past the actor to select the monster.
        self._press(page, "ArrowRight")  # skills
        self._press(page, "ArrowLeft")  # back to attack
        self._press(page, "Enter")  # open attack
        self._press(page, "ArrowRight")  # past the actor to the monster
        self._press(page, "Enter")  # select the monster target

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

        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills list
        # Skills list starts at fire_ball (first owned active skill).
        self._press(page, "Enter")  # open fire_ball targets
        # The single-target menu lists the actor and the monster (both valid
        # for ANY scope); move past the actor to select the monster.
        self._press(page, "ArrowRight")
        self._press(page, "Enter")  # select the monster target

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
        # status_disguise (SELF) is now disabled in combat: the session context
        # cannot supply its disguise key, so the menu exposes the disabled
        # explanation instead of a cast. flee is the enabled SELF skill (third
        # grid row, first column of the 2-column skills grid).
        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # status_disguise (second grid row)
        self._press(page, "ArrowDown")  # flee (third grid row)
        self._press(page, "Enter")  # open flee
        self._press(page, "Enter")  # confirm self-cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "flee")
        self.assertNotIn("target_ids", envelope["payload"])
        self.assertNotIn("target_shorthand", envelope["payload"])
        self.assertNotIn("actor", envelope["payload"])

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_none_skill_submits_skill_key_only(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # concentration is the fourth owned active skill (second grid row,
        # second column).
        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowDown")  # status_disguise (second grid row)
        self._press(page, "ArrowRight")  # concentration (second grid column)
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
        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowRight")  # wind_blade
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # AREA grid: candidate targets (col 0) then shorthands, then confirm.
        # The actor is a valid candidate for ANY scope, so the first grid row
        # holds the two candidates; the shorthand rows follow.
        self._press(page, "ArrowDown")  # first shorthand row (all-enemies)
        self._press(page, "Enter")  # choose shorthand
        self._press(page, "ArrowDown")  # shorthand row two
        self._press(page, "ArrowRight")  # confirm (last grid cell)
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
        self._press(page, "ArrowRight")  # skills
        self._press(page, "ArrowRight")  # items (disabled)
        self._press(page, "Enter")
        self._press(page, "ArrowRight")  # defend (disabled)
        self._press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_flee_flow_submits_empty_payload(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._press(page, "ArrowRight")
        self._press(page, "ArrowRight")
        self._press(page, "ArrowRight")
        self._press(page, "ArrowRight")  # flee is the last root cell
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
        # Root grid: attack..flee in the first row, forfeit below the first
        # cell (six items across five columns).
        self._press(page, "ArrowDown")  # forfeit (second grid row)
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
        # The confirmed forfeit ends the session; the panel reverts to the
        # exploration available form.
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); "
            "const p = s.panels && s.panels['context_actions']; "
            "return p && p.available === true && p.kind === 'exploration'; }",
            timeout=30000,
        )

    @covers_requirement(
        "webclient-combat-menu::terminal-combat-outcomes-refresh-all-mode-relevant-panels"
    )
    def test_terminal_outcome_publishes_fresh_exploration_panels(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # During combat the exploration-mode panels render unavailable; only a
        # full post-settlement snapshot can restore them.
        state = store_state(page)
        for name in ("exploration", "character", "services"):
            self.assertIn(name, state["panels"])
            self.assertFalse(state["panels"][name]["available"], f"{name} must be combat-unavailable")
        self.assertEqual(state["mode"], "combat")

        session_id = self._combat_panel(page)["session"]["session_id"]
        # Settle before submitting: a forfeit naming the pre-burst revision is
        # rejected stale and the session never ends, so the exploration panels
        # would never come back available.
        wait_for_presentation_settled(page)
        page.evaluate(
            "(sessionId) => Elosern.actions.submit('combat.forfeit', "
            "{ session_id: sessionId })",
            session_id,
        )
        # Poll until the full post-settlement end state holds: on a loaded
        # runner the context panel can flip to exploration availability
        # before the sibling panels of the same snapshot are observed, and
        # the assertion set below must not race that intermediate state.
        deadline = time.monotonic() + 30000 / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            if (
                state["mode"] == "exploration"
                and state["panels"]
                .get("context_actions", {})
                .get("available") is True
                and state["panels"]["context_actions"].get("kind") == "exploration"
                and all(
                    state["panels"].get(name, {}).get("available") is True
                    for name in ("exploration", "character", "services", "status")
                )
            ):
                break
            page.wait_for_timeout(250)
        # Every mode-relevant panel is fresh post-settlement canonical state:
        # the combat-era unavailable forms were replaced by the full snapshot.
        # local_map availability depends on map knowledge, so only the
        # guaranteed exploration-mode panels are asserted as available.
        for name in ("exploration", "character", "services", "status"):
            self.assertIn(name, state["panels"])
            self.assertTrue(
                state["panels"][name]["available"], f"{name} panel must be fresh"
            )
        self.assertEqual(state["mode"], "exploration")
        # The exploration dock mounts from the fresh state.
        self.assertEqual(self._dock_mode(page), "exploration")

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

        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowRight")  # wind_blade
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # AREA grid: candidate targets (col 0) then shorthands, then confirm.
        # The actor is now a valid candidate, so the first grid row holds the
        # two candidates; the confirm cell sits at the last grid row, second
        # column. Move past the actor to the monster candidate and toggle it.
        self._press(page, "ArrowRight")  # monster candidate
        self._press(page, "Space")  # toggle the explicit monster candidate
        self._press(page, "ArrowDown")  # shorthand row two
        self._press(page, "ArrowDown")  # confirm row
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
        self._press(page, "ArrowRight")  # skills
        self._press(page, "ArrowRight")  # items (disabled)
        detail = page.evaluate(
            "document.getElementById('combat-detail').innerText"
        )
        self.assertIn("道具功能尚未開放", detail)
        self._press(page, "Enter")  # disabled confirm -> explanation, no packet
        self._press(page, "ArrowRight")  # defend (disabled)
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
            timeout=30000,
        )
        self._press(page, "Enter")  # attack (first root item) -> target menu
        self._press(page, "Enter")  # select the first valid target
        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        # The accepted panel advances the round; the keyboard model must be
        # rebuilt from that panel, not the stale pre-round selection. The 30s
        # budget matches the action-result waits: round settlement polling
        # CPU-starves the same way on a loaded CI runner.
        deadline = time.monotonic() + 30
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
        self._press(page, "ArrowRight")  # skills
        self._press(page, "ArrowRight")  # items (disabled)
        self.assertIn(
            "道具功能尚未開放",
            page.evaluate("document.getElementById('combat-detail').innerText"),
        )
        self.assertEqual(
            page.evaluate("document.getElementById('action-dock').scrollWidth <= "
                          "document.getElementById('action-dock').clientWidth"),
            True,
        )

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    @covers_requirement("webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable")
    def test_combat_dock_renders_mockup_grid_and_detail_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            install_outbound_recorder(page)
            self._engage(page)
            # The dock body carries the split: item grid left, detail pane
            # right.
            self.assertEqual(page.locator(".combat-layout").count(), 1)
            self.assertTrue(page.locator(".combat-controls").is_visible())
            self.assertTrue(page.locator("#combat-detail").is_visible())
            # The skills submenu renders a 2-column grid with a detail pane
            # naming the focused skill's cost and the next key action.
            self._press(page, "ArrowRight")  # skills
            self._press(page, "Enter")
            self.assertEqual(
                page.evaluate(
                    "document.querySelector('.combat-controls')"
                    ".classList.contains('dock-grid')"
                ),
                True,
                "the skills list must render as a CSS grid",
            )
            self.assertEqual(
                page.evaluate(
                    "getComputedStyle(document.querySelector('.combat-controls'))"
                    ".gridTemplateColumns.split(' ').length"
                ),
                2,
                "the skills grid must use two columns",
            )
            page.wait_for_timeout(150)
            detail = page.evaluate(
                "document.getElementById('combat-detail').innerText"
            )
            self.assertIn("MP ", detail, "the detail pane names the skill cost")
            self.assertIn("Enter → 開啟", detail, "the detail pane names the next key action")
            focused = page.locator(".combat-controls .dock-row.focused").first
            self.assertTrue(
                "▶" in focused.evaluate("el => getComputedStyle(el, '::before').content")
            )
            self.assertEqual(
                focused.evaluate("el => getComputedStyle(el).backgroundColor"),
                "rgb(169, 50, 42)",
            )
            # Disabled cells are dimmed (dimmer border + dimmer text) but
            # still focusable for their explanation.
            self._press(page, "Escape")
            self._press(page, "ArrowRight")  # skills
            self._press(page, "ArrowRight")  # items (disabled)
            disabled = page.locator(".combat-controls .dock-row.disabled").first
            self.assertEqual(disabled.get_attribute("aria-disabled"), "true")
            self.assertEqual(disabled.get_attribute("tabindex"), "-1")
            self.assertNotEqual(
                page.evaluate(
                    "() => { const el = document.querySelector("
                    "'.combat-controls .dock-row.disabled');"
                    "return getComputedStyle(el).borderColor; }"
                ),
                "rgb(81, 76, 67)",
                "disabled cells use the dimmer border",
            )

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    @covers_requirement("webclient-desktop-shell::keyboard-routing-is-menu-first-and-submission-safe")
    def test_area_space_selects_once_even_when_held(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        enemy_ids = [
            p["identity"] for p in panel["participants"] if p["team"] == "foes"
        ]
        self.assertEqual(len(enemy_ids), 1, "engage opens a single-enemy battle")

        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")
        self._press(page, "ArrowRight")  # wind_blade
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # The actor is now a valid candidate, so the first grid row holds the
        # two candidates; move to the monster candidate before toggling.
        self._press(page, "ArrowRight")  # monster candidate

        # Space once toggles the candidate: the selection marker appears and
        # the client-local selection has exactly one identity.
        self._press(page, "Space")
        marker = page.locator(".combat-controls .dock-row.selected")
        self.assertEqual(marker.count(), 1)
        self.assertTrue(marker.first.inner_text().startswith("✓"))
        selected_count = page.evaluate(
            "() => Elosern._combat.skillByKey['wind_blade'].selected.length"
        )
        self.assertEqual(selected_count, 1)

        # Held/repeated Space is suppressed by the router: a synthetic repeat
        # keydown must not toggle again.
        page.evaluate(
            """() => {
              document.dispatchEvent(new KeyboardEvent('keydown', {
                key: ' ', repeat: true, bubbles: true, cancelable: true,
              }));
            }"""
        )
        page.wait_for_timeout(150)
        selected_count = page.evaluate(
            "() => Elosern._combat.skillByKey['wind_blade'].selected.length"
        )
        self.assertEqual(
            selected_count, 1, "held Space must not repeatedly toggle candidates"
        )

        # Confirm casts exactly the one selected target.
        self._press(page, "ArrowDown")  # shorthand row two
        self._press(page, "ArrowDown")  # confirm row
        self._press(page, "Enter")
        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "wind_blade")
        self.assertEqual(envelope["payload"]["target_ids"], enemy_ids)

    @covers_requirement("webclient-combat-menu::the-combat-dock-offers-a-scale-choice-step-only-for-masters")
    def test_master_scale_step_casts_at_the_chosen_magnitude(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        target = self._fire_ball_identity(page)
        mp_before = page.locator(
            ".status-resources .resource-mp .resource-value"
        ).inner_text()

        # Skills -> wind_blade opens the 威力 scale step (the seeded character
        # owns wind_mastery); 威力×2 is the fourth cell of the five-cell grid.
        self._press(page, "ArrowRight")  # skills
        self._press(page, "Enter")  # open skills
        self._press(page, "ArrowRight")  # wind_blade
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        scale_rows = page.locator(".combat-controls .dock-row")
        self.assertGreaterEqual(scale_rows.count(), 5)
        self.assertIn(
            "威力×",
            scale_rows.first.inner_text(),
            "the scale step labels the power choice",
        )
        self._press(page, "ArrowRight")  # 威力×2 (right of the preselected ×1)
        self._press(page, "Enter")  # choose 威力×2 -> target flow
        self._press(page, "ArrowRight")  # the monster candidate
        self._press(page, "Space")  # toggle the explicit monster candidate
        self._press(page, "ArrowDown")  # shorthand row
        self._press(page, "ArrowDown")  # confirm row
        self._press(page, "Enter")  # cast at scale 2

        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], "wind_blade")
        self.assertEqual(envelope["payload"]["scale"], 2)
        self.assertEqual(envelope["payload"]["target_ids"], [target])
        # The scaled cast deducts 28 MP (wind_blade costs 14 at 2×); the
        # status panel reflects the true resource pool after the round.
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            mp_after = page.locator(
                ".status-resources .resource-mp .resource-value"
            ).inner_text()
            if mp_after != mp_before:
                break
            page.wait_for_timeout(250)
        mp_before_value = int(mp_before.split(" / ")[0])
        mp_after_value = int(mp_after.split(" / ")[0])
        self.assertEqual(mp_before_value - mp_after_value, 28)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_panel_groups_skills_by_category_in_enum_order(self):
        page = self.logged_in_page()
        self._engage(page)
        panel = self._combat_panel(page)
        # The seeded character owns elemental spells, martial-arts innates,
        # enhancement, utility, movement, and the seven unconditionally-owned
        # seed acts; the payload lists only the categories that have owned
        # active skills, in SkillCategory declaration order.
        self.assertEqual(
            [category["category"] for category in panel["skills"]],
            [
                "elemental_magic",
                "martial_arts",
                "enhancement",
                "movement",
                "utility",
                "sexual_act",
            ],
        )
        elemental = panel["skills"][0]
        self.assertEqual(elemental["label"], "元素魔法")
        # Element sub-groups follow ELEMENT_REGISTRY declaration order
        # (fire before wind), not ownership order.
        self.assertEqual(
            [group["group"] for group in elemental["groups"]],
            ["fire", "wind"],
        )
        fire = elemental["groups"][0]
        self.assertEqual(fire["label"], "火")
        self.assertEqual(
            [skill["key"] for skill in fire["skills"]],
            ["fire_ball"],
        )
        # A category without a group carries exactly one null-keyed sub-group.
        enhancement = panel["skills"][2]
        self.assertEqual(enhancement["category"], "enhancement")
        self.assertEqual(len(enhancement["groups"]), 1)
        self.assertIsNone(enhancement["groups"][0]["group"])
        self.assertIsNone(enhancement["groups"][0]["label"])
        self.assertEqual(
            [skill["key"] for skill in enhancement["groups"][0]["skills"]],
            ["concentration"],
        )

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_panel_advertises_scales_only_for_the_mastered_element(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        by_key = {
            skill["key"]: skill
            for category in panel["skills"]
            for group in category["groups"]
            for skill in group["skills"]
        }
        # The seeded wind_mastery entitles only wind_blade; every other skill
        # omits the field entirely, so a non-master's panel would reveal
        # nothing at all.
        self.assertIn("freeform_scales", by_key["wind_blade"])
        self.assertEqual(
            [entry["scale"] for entry in by_key["wind_blade"]["freeform_scales"]],
            [0.25, 0.5, 1, 2, 4],
        )
        for key in ("fire_ball", "concentration", "flee", "basic_attack"):
            self.assertNotIn("freeform_scales", by_key[key])
