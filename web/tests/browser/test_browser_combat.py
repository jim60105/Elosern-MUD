"""Keyboard-only combat menu browser acceptance (webclient-combat-menu 5.2-5.5).

These journeys drive the real Evennia server's combat sessions through the
Vue action dock (ActionDock): the seeded character owns fire_ball (SINGLE),
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
    focus_action_dock,
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
        return page.locator("#action-dock").get_attribute("data-mode")

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
        # The dock's data-mode can lag the committed mode on a loaded CI
        # runner; a single get_attribute auto-wait can time out. Poll until
        # the dock exposes the combat mode before asserting.
        page.wait_for_function(
            "() => { const d = document.querySelector('#action-dock'); "
            "return d && d.getAttribute('data-mode') === 'combat'; }",
            timeout=30000,
        )
        self.assertEqual(self._dock_mode(page), "combat")
        focus_action_dock(page)
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

    @covers_requirement("webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces")
    def test_crumb_absent_at_depth_one_present_at_depth_two_and_back_pops_one_level(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        # Depth 1 (the combat root frame): the breadcrumb is hidden (no parent
        # frame to return to).
        self.assertTrue(
            page.locator('[data-testid="dock-crumb"]').evaluate(
                "el => el.hidden || getComputedStyle(el).display === 'none'"
            ),
            "the crumb must be hidden at depth 1",
        )

        # Open the skills tab to push the category frame (depth 2).
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame

        crumb = page.locator('[data-testid="dock-crumb"]')
        self.assertFalse(
            crumb.evaluate("el => el.hidden"),
            "the crumb must be visible at depth >= 2",
        )
        # It names the parent frame (戰鬥) and the current frame (技能).
        self.assertIn("戰鬥", crumb.inner_text())
        self.assertIn("技能", crumb.inner_text())

        # The back chevron pops exactly one router level (the store's
        # `focusEscape()` path — the keyboard and pointer parity).
        crumb.locator(".dock-crumb__back").click()
        page.wait_for_timeout(120)
        self.assertTrue(
            page.locator('[data-testid="dock-crumb"]').evaluate("el => el.hidden"),
            "the crumb must be hidden again after the back chevron pops one level",
        )

    @covers_requirement("webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation")
    def test_pointer_tab_click_pops_to_root_and_activates_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        # Navigate to the skills category frame (depth 2).
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame
        self.assertEqual(store_state(page)["dockDepth"], 2)

        # Pointer click on a non-current tab (the 逃跑 tab) at depth 2: the
        # store pops the router back to the root frame, focuses the clicked
        # item, and confirms it with `source="pointer"` — exactly one
        # deliberate activation, no stray `ui_action`.
        # Wait for the flee tab to be present before clicking; on a loaded
        # runner the dock's tab bar can lag behind the committed depth change,
        # so an immediate click can race the render.
        page.wait_for_selector("#dock-tab-flee", timeout=30000)
        page.locator("#dock-tab-flee").click()

        # The router returned to the root frame (depth 1) and the clicked tab is
        # the open/focused tab. The click's `tabToRootAndConfirm` pops to root and
        # focuses `flee` synchronously, but the confirmed `combat.flee` ends the
        # session, so the store reverts to exploration (focus back to `move`) and
        # the combat dock's flee tab is replaced by the exploration dock. The
        # focused-flee state (store focus + depth + DOM selected) is therefore
        # transient: it exists only during the short window before the
        # exploration snapshot arrives. Poll tightly (5ms) in a single evaluate
        # that reads the store state and the DOM attribute together, so the
        # transient state is observed before the mode revert overwrites it.
        observed = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            observed = page.evaluate(
                """() => {
                  const b = window.__elosernBridge;
                  const v = b && b.store.view;
                  const t = document.querySelector('#dock-tab-flee');
                  return {
                    focusKey: v && v.focus && v.focus.key,
                    depth: v && v.dockDepth,
                    selected: t ? t.getAttribute('aria-selected') : null,
                  };
                }"""
            )
            if (
                observed
                and observed["focusKey"] == "flee"
                and observed["depth"] == 1
                and observed["selected"] == "true"
            ):
                break
            page.wait_for_timeout(5)
        self.assertEqual(observed["focusKey"], "flee", "the clicked tab is focused")
        self.assertEqual(observed["depth"], 1, "the router returned to the root frame")
        self.assertEqual(observed["selected"], "true", "the clicked tab is marked selected")
        # Exactly one `combat.flee` ui_action was dispatched (no stray actions).
        self.assertEqual(sent_action_count(page, "combat.flee"), 1)

    @covers_requirement("webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable")
    def test_dock_and_participant_frame_geometry_at_both_desktop_viewports(self):
        # H3 task 8.8: at both 1440x900 and 1280x720, the dock panel must
        # stay inside its anchor, the deepest combat frame's cast/confirm
        # control must be reachable without clipping, and the participant
        # frame must not intersect the dock or the narrative caption.
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                install_outbound_recorder(page)
                self._engage(page)

                # Navigate to the deepest combat frame (the fire_ball target
                # frame): skills tab -> category -> group -> skill -> target.
                self._press(page, "ArrowRight")  # skills tab
                self._press(page, "Enter")  # category frame
                self._press(page, "Enter")  # group frame
                self._press(page, "Enter")  # skill frame
                self._press(page, "Enter")  # target frame (deepest)

                geo = page.evaluate(
                    """() => {
                      const rectOf = (sel) => {
                        const el = document.querySelector(sel);
                        if (!el) { return null; }
                        const r = el.getBoundingClientRect();
                        return { x: r.left, y: r.top, w: r.width, h: r.height };
                      };
                      // The participant frame sits in the bounded hud-left anchor
                      // (`max-height` + `overflow-y:auto`), so only the portion
                      // of the frame inside the anchor is visible.
                      const clampTo = (inner, outer) => {
                        if (!inner || !outer) { return inner; }
                        const x = Math.max(inner.x, outer.x);
                        const y = Math.max(inner.y, outer.y);
                        const x2 = Math.min(inner.x + inner.w, outer.x + outer.w);
                        const y2 = Math.min(inner.y + inner.h, outer.y + outer.h);
                        if (x2 <= x || y2 <= y) { return null; }
                        return { x, y, w: x2 - x, h: y2 - y };
                      };
                      const noIntersect = (a, b) => !(a && b)
                        || a.x >= b.x + b.w || b.x >= a.x + a.w
                        || a.y >= b.y + b.h || b.y >= a.y + a.h;
                      const inside = (inner, outer) => !!(inner && outer
                        && inner.x >= outer.x && inner.y >= outer.y
                        && (inner.x + inner.w) <= (outer.x + outer.w)
                        && (inner.y + inner.h) <= (outer.y + outer.h));
                      const withinViewport = (r) => !!(r && r.x >= 0 && r.y >= 0
                        && (r.x + r.w) <= window.innerWidth
                        && (r.y + r.h) <= window.innerHeight);
                      const dock = rectOf('#action-dock');
                      const anchor = rectOf('[data-testid="anchor-dock"]');
                      const hudLeft = rectOf('[data-anchor="hud-left"]');
                      const participantRaw = rectOf('[data-testid="participant-frame"]');
                      const participant = clampTo(participantRaw, hudLeft);
                      const caption = rectOf('[data-testid="narrative-feed"]');
                      const confirm = rectOf('.dock-menu-item--focused');
                      return {
                        dockInsideAnchor: inside(dock, anchor),
                        confirmReachable: withinViewport(confirm),
                        participantNoDock: noIntersect(participant, dock),
                        participantNoCaption: noIntersect(participant, caption),
                        hasParticipant: !!participantRaw,
                        hasConfirm: !!confirm,
                        hasAnchor: !!anchor,
                      };
                    }"""
                )
                self.assertTrue(geo["hasAnchor"], f"missing dock anchor at {viewport}")
                self.assertTrue(geo["hasParticipant"], f"missing participant frame at {viewport}")
                self.assertTrue(geo["hasConfirm"], f"missing confirm control at {viewport}")
                self.assertTrue(geo["dockInsideAnchor"], f"dock not inside anchor at {viewport}")
                self.assertTrue(geo["confirmReachable"], f"confirm control clipped at {viewport}")
                self.assertTrue(geo["participantNoDock"], f"participant frame intersects dock at {viewport}")
                self.assertTrue(geo["participantNoCaption"], f"participant frame intersects caption at {viewport}")

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

        # H3 skill master-detail (design D11): the skills tab opens the
        # category frame, then the group frame (elemental_magic has two
        # sub-groups), then the skill frame. fire_ball is the first skill of
        # the fire group.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire focused)
        self._press(page, "Enter")  # open fire group -> skill frame (fire_ball focused)
        self._press(page, "Enter")  # open fire_ball -> target frame
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
        # H3 (design D11): skills tab -> category frame (a single row of
        # category tabs). flee lives in the 移動 (movement) category, index 3,
        # which is single-group and opens the skill frame directly.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open category frame (elemental_magic focused)
        self._press(page, "ArrowRight")  # martial_arts (index 1)
        self._press(page, "ArrowRight")  # enhancement (index 2)
        self._press(page, "ArrowRight")  # movement (index 3)
        self._press(page, "Enter")  # single-group -> skill frame (flee)
        self._press(page, "Enter")  # open-skill (flee) -> self-confirm
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
        # H3 (design D11): concentration lives in the 強化 (enhancement)
        # category, index 2 (single-group), which opens the skill frame
        # directly.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open category frame (elemental_magic focused)
        self._press(page, "ArrowRight")  # martial_arts (index 1)
        self._press(page, "ArrowRight")  # enhancement (index 2)
        self._press(page, "Enter")  # single-group -> skill frame (concentration)
        self._press(page, "Enter")  # open-skill (concentration) -> 施展 item
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
        # H3 (design D11): wind_blade is the elemental_magic / wind group.
        # Skills tab -> category frame (elemental_magic focused) -> group frame
        # (fire + wind) -> select the wind group -> skill frame (wind_blade) ->
        # 威力 scale step (preselected ×1) -> all-enemies shorthand.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowRight")  # select the wind group (index 1)
        self._press(page, "Enter")  # open the wind group -> skill frame (wind_blade)
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
        # H3 (design D2): the combat root is a single-row tab bar (attack,
        # skills, items, defend, flee, forfeit) — navigation is horizontal.
        # Focus reaches `forfeit` (index 5) by pressing ArrowRight five times.
        self._press(page, "ArrowRight")  # skills (1)
        self._press(page, "ArrowRight")  # items (2)
        self._press(page, "ArrowRight")  # defend (3)
        self._press(page, "ArrowRight")  # flee (4)
        self._press(page, "ArrowRight")  # forfeit (5)
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
            "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null); "
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

        # H3 (design D11): wind_blade is the elemental_magic / wind group.
        # Skills tab -> category frame (elemental_magic focused) -> group frame
        # (fire + wind) -> wind group -> skill frame (wind_blade) -> 威力 scale
        # step (preselected ×1) -> target flow.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open category frame (elemental_magic focused)
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowRight")  # wind group (index 1)
        self._press(page, "Enter")  # open the wind group -> skill frame (wind_blade)
        self._press(page, "Enter")  # open-skill (wind_blade): 威力 scale step
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
        # H3 (design D2/D11): a disabled entry explains itself through the
        # detail pane (`SkillDetailPane`, `combat-detail`) in the skill frame.
        # status_disguise (SELF) is disabled in combat (the session context
        # cannot supply its disguise key), so the pane exposes its disabled
        # explanation instead of a cast. Navigate: skills tab -> category frame
        # -> 特殊 (utility, index 4, single-group) -> skill frame.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # category frame (elemental_magic focused)
        self._press(page, "ArrowRight")  # martial_arts (index 1)
        self._press(page, "ArrowRight")  # enhancement (index 2)
        self._press(page, "ArrowRight")  # movement (index 3)
        self._press(page, "ArrowRight")  # utility (index 4)
        self._press(page, "Enter")  # single-group -> skill frame (status_disguise focused)
        # Focusing the disabled skill row sets the focused-skill model, so the
        # detail pane (SkillDetailPane, `combat-detail`) renders its reason.
        self.assertTrue(
            page.locator(".skill-detail-pane__disabled").count() == 1,
            "the detail pane names the disabled skill's reason",
        )
        # Enter on a disabled skill submits no packet.
        self._press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0, "a disabled skill submits no packet")

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    def test_combat_rebuilds_keyboard_menu_after_round(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # Wait for the dock to install the keyboard root before driving it; the
        # subscription that installs it may not have run the moment combat mode
        # becomes available.
        page.wait_for_function(
            "() => { const b = window.__elosernBridge; "
            "const s = b && b.store.view; "
            "const p = s && s.panels && s.panels['context_actions']; "
            "return p && p.available === true && p.kind === 'combat' && b.router.depth() >= 1; }",
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
                    "() => { const s = ((window.__elosernBridge && window.__elosernBridge.store.view) || null);"
                    "const p = s && s.panels && s.panels['context_actions']; "
                    "return p && p.available === true && p.kind === 'combat'; }"
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
    @covers_requirement(
        "webclient-contextual-hud::condition-chips-carry-a-severity-glyph-a-payload-duration-and-a-bounded-overflow",
    )
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
                f'[data-testid="status-panel__gauge-value--{key}"]'
            ).inner_text()
            self.assertRegex(
                value,
                r"^\d+ / \d+$",
                f"{key} resource must render current/maximum values",
            )
        # The seeded poisoned buff surfaces applied modifier text.
        # H2 re-map (task 9.3): the condition area is now icon chips; the
        # modifier text lives in the chip's aria-label. The agility penalty
        # is its own condition row (``poison_agility_penalty``), which carries
        # the ``modifiers`` field — the ``poisoned`` buff code alone only
        # carries the label and remaining seconds.
        chip_label = page.locator(
            '[data-testid="status-panel__condition--poison_agility_penalty"]'
        ).get_attribute("aria-label")
        self.assertIn("agility", chip_label)
        self.assertIn("-10%", chip_label)
        # Action controls stay usable and disabled entries explain themselves.
        # H3: at the combat root (depth 1) only the tab bar renders; the pane
        # (`.dock-menu`) appears at depth >= 2. Navigate into the skill frame so
        # the dock's action controls (the pane) are visible.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # category frame (elemental_magic focused)
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowRight")  # wind group (index 1)
        self._press(page, "Enter")  # skill frame (wind_blade)
        self.assertTrue(page.locator(".dock-menu").is_visible())
        # Disabled root tabs (`items` / `defend`) are dimmed and marked
        # disabled at the combat root. Pop back to the root and check the
        # disabled `items` tab is present and disabled.
        self._press(page, "Escape")
        self._press(page, "Escape")
        self._press(page, "Escape")
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "ArrowRight")  # items (disabled)
        disabled_tab = page.locator("#action-dock .dock-tab-bar__tab[disabled]").first
        self.assertEqual(disabled_tab.get_attribute("disabled"), "", "the disabled `items` tab is disabled")
        self.assertEqual(disabled_tab.get_attribute("tabindex"), "-1")
        self.assertEqual(
            page.locator("#action-dock").evaluate("el => el.scrollWidth <= el.clientWidth"),
            True,
        )
        self.assertEqual(
            page.locator("#action-dock").evaluate("el => el.scrollWidth <= el.clientWidth"),
            True,
        )

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    @covers_requirement("webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable")
    def test_combat_dock_renders_mockup_grid_and_detail_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            install_outbound_recorder(page)
            self._engage(page)
            # H3 (design D2/D11): the combat root is a single-row tab bar
            # (depth 1); the pane (DockMenu + SkillDetailPane) renders only at
            # depth >= 2. Navigate into the skill frame: skills tab -> category
            # -> group -> skill (wind_blade).
            self._press(page, "ArrowRight")  # skills tab
            self._press(page, "Enter")  # open category frame (elemental_magic focused)
            self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
            self._press(page, "ArrowRight")  # focus the wind group (index 1)
            self._press(page, "Enter")  # open the wind group -> skill frame (wind_blade)
            # The dock body carries the split: item list left, detail pane right.
            self.assertEqual(page.locator(".dock-menu-layout").count(), 1)
            self.assertTrue(page.locator(".dock-menu").is_visible())
            self.assertTrue(page.locator('[data-testid="combat-detail"]').is_visible())
            # The skill frame's row group (the variant container) uses the pane
            # kind's CSS layout (H3: `.dock-menu__skills` is a flex column).
            pane_display = page.evaluate(
                "() => { const el = document.querySelector('[data-testid=\"dock-menu\"]');"
                " const v = el && el.firstElementChild;"
                " return v ? getComputedStyle(v).display : null }"
            )
            self.assertIn(
                pane_display,
                ("grid", "block", "flex"),
                "the skill frame's row group uses its pane kind's CSS layout",
            )
            page.wait_for_timeout(150)
            detail = page.evaluate(
                "document.querySelector('[data-testid=\"combat-detail\"]').innerText"
            )
            self.assertIn("MP ", detail, "the detail pane names the skill cost")
            # H3: the detail pane's "next key action" is now the 威力 scale
            # choice (not the legacy "Enter → 開啟" line). Assert a scale option.
            self.assertIn("MP 28", detail, "the detail pane shows the 威力 scale options")
            # H3: the skill frame's focused row carries the gold border and
            # the `dock-menu__skill--on` class (not the legacy `dock-menu-item--focused`).
            focused = page.locator(".dock-menu .dock-menu__skill--on").first
            self.assertEqual(focused.count(), 1, "the focused skill row is rendered")
            self.assertEqual(
                focused.evaluate("el => getComputedStyle(el).borderColor"),
                "rgb(203, 161, 53)",
                "the focused skill row uses the gold border",
            )
            # Disabled cells are dimmed (dimmer border + dimmer text) but
            # still focusable for their explanation. Pop back to the combat root
            # (three Escapes: skill -> group -> category -> root) and focus the
            # disabled `items` root tab.
            self._press(page, "Escape")  # -> group frame
            self._press(page, "Escape")  # -> category frame
            self._press(page, "Escape")  # -> combat root (depth 1)
            self._press(page, "ArrowRight")  # skills tab
            self._press(page, "ArrowRight")  # items tab (disabled)
            disabled = page.locator("#action-dock .dock-tab-bar__tab[disabled]").first
            self.assertTrue(disabled.evaluate("el => el.disabled"), "disabled root tab is disabled")
            self.assertEqual(disabled.get_attribute("tabindex"), "-1")

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

        # H3 (design D11): wind_blade is the elemental_magic / wind group.
        # Skills tab -> category frame -> group frame (fire + wind) -> wind group
        # -> skill frame (wind_blade) -> 威力 scale step (preselected ×1) -> target flow.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowRight")  # select the wind group (index 1)
        self._press(page, "Enter")  # open the wind group -> skill frame (wind_blade)
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # The actor is now a valid candidate, so the first grid row holds the
        # two candidates; move to the monster candidate before toggling.
        self._press(page, "ArrowRight")  # monster candidate

        # Space once toggles the candidate: the selection marker appears and
        # the client-local selection has exactly one identity.
        self._press(page, "Space")
        # H3: the target frame's rows are the `.dock-menu__token` rows; the
        # Space toggle marks the selected candidate with the `✓` pressed token.
        marker = page.locator(".dock-menu .dock-menu__token--pressed")
        self.assertEqual(marker.count(), 1)
        # H3: the pressed token carries `aria-pressed="true"` and the
        # gold seal border (the `✓` is no longer a text prefix in the token row).
        self.assertEqual(marker.first.get_attribute("aria-pressed"), "true")
        selected_count = page.evaluate(
            "() => document.querySelectorAll('.dock-menu .dock-menu__token--pressed').length"
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
            "() => document.querySelectorAll('.dock-menu .dock-menu__token--pressed').length"
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
            '[data-testid="status-panel__gauge-value--mp"]'
        ).inner_text()

        # H3 (design D11): wind_blade is the elemental_magic / wind group.
        # Skills tab -> category frame -> group frame (fire + wind) -> wind group
        # -> skill frame (wind_blade) -> 威力 scale step (wind_mastery owned);
        # 威力×2 is the fourth cell of the five-cell grid.
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # open skills -> category frame
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowRight")  # select the wind group (index 1)
        self._press(page, "Enter")  # open the wind group -> skill frame (wind_blade)
        self._press(page, "Enter")  # open wind_blade: 威力 scale step
        # H3: the scale step's rows are the pane's `.dock-menu__scale` buttons.
        scale_rows = page.locator(".dock-menu .dock-menu__scale")
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
                '[data-testid="status-panel__gauge-value--mp"]'
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
