"""Keyboard-only combat action-dock flows (webclient-combat-menu 5.2-5.5): engage, breadcrumb, pointer-pop, frame geometry, basic attack, and single-skill targeting journeys.
"""

from __future__ import annotations

import time
from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import actor_command_choices, combat_journey_values
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_update,
    sent_action_count,
    store_state,
    wait_for_presentation_settled,
)
from .harness import ManagedServerTearDownMixin


class CombatMenuBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
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

    def _engage(self, page):
        """Engage the boot mode's first living combat monster through the
        ordinary text transport."""
        target = self._roles()["engage_target"]
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
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

    def _foe_identities(self, page):
        panel = self._combat_panel(page)
        return [p["identity"] for p in panel["participants"] if p["team"] == "foes"]

    def _focus_key(self, page):
        return store_state(page).get("focus", {}).get("key")

    def _cell_grid(self, page) -> dict:
        """Map every listbox cell key to its (row, column) via the DOM rects.

        The framed grid's column count is client-owned presentation
        (mode/pane-dependent), so the journeys measure the mounted grid
        instead of hardcoding it. The combat root renders in the pane as
        the frame's own vertical list (webclient-combat-command-window), so
        every mounted row is a cell of the committed frame."""
        cells = page.evaluate(
            """() => Array.from(
                 document.querySelectorAll(
                   '#action-dock [role="listbox"] [data-item-key]'))
               .map((el) => {
                 const r = el.getBoundingClientRect();
                 return { key: el.getAttribute('data-item-key'),
                          top: Math.round(r.top), left: Math.round(r.left) };
               })"""
        )
        rows = sorted({c["top"] for c in cells})
        cols = sorted({c["left"] for c in cells})
        return {
            c["key"]: (rows.index(c["top"]), cols.index(c["left"]))
            for c in cells
        }

    _WALK_UNDO = {
        "ArrowRight": "ArrowLeft",
        "ArrowLeft": "ArrowRight",
        "ArrowDown": "ArrowUp",
        "ArrowUp": "ArrowDown",
    }

    def _walk_to(self, page, key: str, max_cells: int = 32) -> None:
        """Arrow-walk the committed frame's keyboard grid onto ``key``.

        Grid geometry is client-owned and mode-dependent (roster sizes and
        frame column counts differ between the shipped and synthetic boots),
        so the journey treats the four arrow keys as a small deterministic
        state machine over the mounted cells and depth-first-searches it,
        undoing each explored edge with its inverse arrow. The walk never
        assumes a press count or a measured column layout."""
        grid = self._cell_grid(page)
        self.assertIn(key, grid, f"cell {key!r} not mounted in the frame")
        start = self._focus_key(page)
        if start == key:
            return
        visited = {start}
        explored = [start]

        def step(move):
            self._press(page, move)
            return self._focus_key(page)

        def dfs(cell):
            for move in ("ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"):
                if len(explored) > max_cells:
                    continue
                nxt = step(move)
                if nxt == key:
                    return True
                if nxt in visited or nxt not in grid:
                    step(self._WALK_UNDO[move])
                    continue
                visited.add(nxt)
                explored.append(nxt)
                if dfs(nxt):
                    return True
                explored.pop()
                step(self._WALK_UNDO[move])
            return False

        self.assertTrue(dfs(start), f"keyboard walk never reached cell {key!r}")

    # -- mode seams ----------------------------------------------------------
    #
    # Every journey role (cast/prereq/ladder/NONE/disabled keys) resolves
    # through ``combat_journey_values()``; frame positions derive from the
    # committed panel instead of hardcoded press counts, so the same journeys
    # drive the shipped and the synthetic skill tables.

    def _roles(self) -> dict:
        return combat_journey_values()

    def _press(self, page, key):
        page.keyboard.press(key)
        page.wait_for_timeout(80)

    def _press_to(self, page, key, count):
        for _ in range(count):
            self._press(page, key)

    def _open_skills(self, page) -> None:
        self._press(page, "ArrowDown")  # skills row
        self._press(page, "Enter")  # -> category frame

    def _open_category(self, page, category: str) -> None:
        """Arrow to ``category`` in the category frame and Enter into it (a
        single-group category opens its skill frame directly)."""
        names = [
            item["category"]
            for item in self._combat_panel(page)["choices"]["skills"]
        ]
        self.assertIn(category, names)
        self._press_to(page, "ArrowDown", names.index(category))
        self._press(page, "Enter")

    def _focus_skill(self, page, category: str, key: str) -> None:
        """Land focus on ``key``'s row from wherever ``_open_category``
        left off, crossing the group frame first for a multi-group
        category. Row positions are verified against the live router —
        not press counts — because the mounted row order can differ from
        the payload tree (a same-category row set may reflow), and the
        single-column skill pane ignores the horizontal arrow between
        rows whose index math was trusted here before."""
        panel = self._combat_panel(page)
        names = [item["category"] for item in panel["choices"]["skills"]]
        self.assertIn(category, names)
        category_index = names.index(category)
        groups = panel["choices"]["skills"][names.index(category)]["groups"]
        carrier_index = next(
            (
                index
                for index, group in enumerate(groups)
                if any(skill["key"] == key for skill in group["skills"])
            ),
            None,
        )
        self.assertIsNotNone(carrier_index, f"{key} not in the {category} panel tree")
        if len(groups) > 1:
            # The group frame's rows are keyed positionally by the client.
            self._walk_to(page, f"skill-group-{category_index}-{carrier_index}")
            self._press(page, "Enter")  # -> skill frame
        self._walk_to(page, key)

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

        # Open the skills row to push the category frame (depth 2).
        self._press(page, "ArrowDown")  # skills row
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
    def test_pointer_root_row_click_activates_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        # Navigate to the skills category frame (depth 2).
        self._press(page, "ArrowDown")  # skills row
        self._press(page, "Enter")  # open skills -> category frame
        self.assertEqual(store_state(page)["dockDepth"], 2)

        # A deeper frame replaces the root list (webclient-combat-command-
        # window): no root row is rendered at depth 2. Escape returns to the
        # root list, and a pointer click on its 逃跑 row focuses and confirms
        # it through the ordinary confirmation path — exactly one deliberate
        # activation, no stray `ui_action`.
        flee = '#action-dock [data-testid="dock-menu"] [data-item-key="flee"]'
        self.assertEqual(page.locator(flee).count(), 0, "no root row at depth 2")
        self._press(page, "Escape")
        page.wait_for_selector(flee, timeout=30000)
        page.locator(flee).click()

        # The root frame (depth 1) holds focus on the clicked row. The click
        # focuses `flee` synchronously, but the confirmed `combat.flee` ends the
        # session, so the store reverts to exploration (focus back to `move`) and
        # the combat dock's flee row is replaced by the exploration dock. The
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
                  const t = document.querySelector('#action-dock [data-item-key="flee"]');
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
        self.assertEqual(observed["focusKey"], "flee", "the clicked row is focused")
        self.assertEqual(observed["depth"], 1, "the router returned to the root frame")
        self.assertEqual(observed["selected"], "true", "the clicked row is marked selected")
        # Exactly one `combat.flee` ui_action was dispatched (no stray actions).
        self.assertEqual(sent_action_count(page, "combat.flee"), 1)

    @covers_requirement("webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable")
    @covers_requirement(
        "webclient-contextual-hud::combat-figures-carry-glance-plates"
    )
    def test_dock_and_figure_plate_geometry_at_both_desktop_viewports(self):
        # H3 task 8.8, migrated by webclient-combat-formation: at both
        # 1451x790 and 2560x1440, the dock panel must stay inside its anchor
        # and the deepest combat frame's cast/confirm control must be
        # reachable without clipping. Migrated again by
        # webclient-combat-command-card-centred: the dock's anchor in combat
        # is the stage's `choices` anchor (the centred command card), not
        # the band's command region; "inside its anchor and inside the
        # viewport" still detects a dock pushed off its region or clipped. The participant frame these assertions
        # once placed in the `map` anchor is gone: its replacement, each
        # drawn figure's plate, sits in the `plates` layer (never a portrait
        # anchor) and intersects neither the dock, the message window, the
        # command line, the vitals dock nor the top band.
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                install_outbound_recorder(page)
                self._engage(page)

                # Navigate to the deepest combat frame (the spell's SINGLE
                # target frame): skills row -> category -> the spell's element
                # group (mode-dependent position) -> skill -> target.
                roles = self._roles()
                self._press(page, "ArrowDown")  # skills row
                self._press(page, "Enter")  # category frame
                self._press_to(page, "ArrowDown", roles["spell_group_index"])
                self._press(page, "Enter")  # the spell's element group
                self._press(page, "Enter")  # skill frame
                self._press(page, "Enter")  # target frame (deepest)

                geo = page.evaluate(
                    """() => {
                      const box = (el) => {
                        if (!el) { return null; }
                        const r = el.getBoundingClientRect();
                        return { x: r.left, y: r.top, w: r.width, h: r.height };
                      };
                      const rectOf = (sel) => box(document.querySelector(sel));
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
                      const anchor = rectOf('[data-testid="anchor-choices"]');
                      const caption = rectOf('[data-testid="message-window"]');
                      const commandLine = rectOf('[data-anchor="command-line"]');
                      const vitals = rectOf('[data-anchor="vitals"]');
                      // The top band is the stage's top strip, `--header-h`
                      // tall (read from the stage's metrics probe).
                      const stageBox = rectOf('[data-testid="elosern-stage"]');
                      const header = rectOf('.stage-metrics > [data-metric="--header-h"]');
                      const topBand = { x: stageBox.x, y: stageBox.y, w: stageBox.w, h: header.h };
                      const plateEls = [...document.querySelectorAll('[data-testid="figure-plate"]')];
                      const plates = plateEls.map(box);
                      const confirmEl = document.querySelector(
                        '.dock-menu [aria-selected="true"], ' +
                        '.dock-menu .dock-menu-item--focused');
                      const confirm = box(confirmEl);
                      return {
                        dockInsideAnchor: inside(dock, anchor),
                        dockInChoices: !!document.querySelector('[data-anchor="choices"] #action-dock'),
                        dockInViewport: withinViewport(dock),
                        confirmReachable: withinViewport(confirm),
                        plateCount: plates.length,
                        platesNoDock: plates.every((p) => noIntersect(p, dock)),
                        platesNoCaption: plates.every((p) => noIntersect(p, caption)),
                        platesNoCommandLine: plates.every((p) => noIntersect(p, commandLine)),
                        platesNoVitals: plates.every((p) => noIntersect(p, vitals)),
                        platesBelowTopBand: plates.every((p) => p.y >= topBand.y + topBand.h),
                        platesVisible: plates.every(withinViewport),
                        inPlatesLayer: plateEls.every((el) => !!el.closest('[data-anchor="plates"]')),
                        onPortraitAnchor: plateEls.some((el) => !!el.closest('[data-anchor="actor-left"], [data-anchor="actor-right"]')),
                        roster: !!document.querySelector('[data-testid="participant-frame"]'),
                        hasConfirm: !!confirm,
                        hasAnchor: !!anchor,
                      };
                    }"""
                )
                self.assertTrue(geo["hasAnchor"], f"missing dock anchor at {viewport}")
                self.assertTrue(geo["hasConfirm"], f"missing confirm control at {viewport}")
                self.assertTrue(geo["dockInChoices"], f"the dock is not the centred card at {viewport}")
                self.assertTrue(geo["dockInsideAnchor"], f"dock not inside anchor at {viewport}")
                self.assertTrue(geo["dockInViewport"], f"the card leaves the viewport at {viewport}")
                self.assertTrue(geo["confirmReachable"], f"confirm control clipped at {viewport}")
                self.assertGreater(geo["plateCount"], 0, f"no figure plate at {viewport}")
                self.assertFalse(geo["roster"], f"a participant roster renders at {viewport}")
                self.assertTrue(geo["platesNoDock"], f"a plate intersects the dock at {viewport}")
                self.assertTrue(geo["platesNoCaption"], f"a plate intersects the message window at {viewport}")
                self.assertTrue(geo["platesNoCommandLine"], f"a plate intersects the command line at {viewport}")
                self.assertTrue(geo["platesNoVitals"], f"a plate intersects the vitals dock at {viewport}")
                self.assertTrue(geo["platesBelowTopBand"], f"a plate enters the top band at {viewport}")
                self.assertTrue(geo["platesVisible"], f"a plate leaves the viewport at {viewport}")
                self.assertTrue(geo["inPlatesLayer"], f"a plate is not in the plates layer at {viewport}")
                self.assertFalse(geo["onPortraitAnchor"], f"a plate sits on a portrait anchor at {viewport}")

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_attack_flow_submits_basic_attack_once(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        target = self._basic_attack_target_identity(page)

        # Root: first item is Attack. Open it, then its single-target menu
        # lists every participant valid for the skill's scope (the synth party
        # can carry an extra member), so the journey walks the router to the
        # enemy's row instead of assuming a fixed press count past the actor.
        self._press(page, "ArrowDown")  # skills
        self._press(page, "ArrowUp")  # back to attack
        self._press(page, "Enter")  # open attack
        self._walk_to(page, f"target-{target}")  # the monster target row
        self._press(page, "Enter")  # select the monster target

        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.command")
        command = envelope["payload"]["command"]
        self.assertEqual(command["kind"], "skill")
        self.assertEqual(command["payload"]["skill_key"], self._roles()["attack_key"])
        self.assertEqual(command["payload"]["target_ids"], [target])
        self.assertIsInstance(envelope["payload"]["actor_id"], int)
        self.assertIsInstance(envelope["payload"]["draft_version"], int)

    @covers_requirement("webclient-combat-menu::combat-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    def test_single_skill_target_flow(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        target = self._fire_ball_identity(page)
        spell = self._roles()["spell_key"]

        # H3 skill master-detail (design D11): the skills row opens the
        # category frame, then the group frame (elemental_magic has two
        # sub-groups), then the skill frame. The mode's deep spell is the
        # first skill of the first element sub-group.
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", spell)
        self._press(page, "Enter")  # open the spell -> target frame
        # The single-target menu lists every valid participant; walk to the
        # enemy's row (the synth party may add a companion candidate).
        self._walk_to(page, f"target-{target}")
        self._press(page, "Enter")  # select the monster target

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.command")
        self.assertEqual(envelope["payload"]["command"]["payload"]["skill_key"], spell)
        self.assertEqual(envelope["payload"]["command"]["payload"]["target_ids"], [target])

    @covers_requirement("webclient-frame-resolution::the-resolver-table-completes-with-the-combat-and-creation-families")
    def test_skill_frame_refreshes_on_panel_update(self):
        """Declarative-frame freshness mid-fight: the open skill frame
        re-resolves its rows from the NEXT committed combat panel while the
        client-local focus key survives — no re-push, no dispatch.

        A partial ``ui_update`` replaces only ``context_actions`` with the
        same session and a renamed spell label. The frame was never
        rebuilt from a copy: its next read enumerates the new label, the
        same-key geometry keeps the spell row focused, the depth is
        unchanged, and nothing crosses the wire.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        spell = self._roles()["spell_key"]

        # skills row -> category frame -> group frame -> skill frame (the
        # same geometry as test_single_skill_target_flow; the mode's deep
        # spell is the first skill of the first element group and holds focus).
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", spell)
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentDescriptor().source"),
            "combat.group",
        )
        depth_before = page.evaluate("() => window.__elosernBridge.router.depth()")
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentItem().key"),
            spell,
        )
        sent_before = len(self._ui_actions(page))

        new_label = "改標測試標籤"
        panel = self._combat_panel(page)
        mutated = False
        for category in panel["choices"]["skills"]:
            for group in category["groups"]:
                for skill in group["skills"]:
                    if skill["key"] == spell:
                        skill["label"] = new_label
                        mutated = True
        self.assertTrue(mutated, "fixture must carry the mode's deep spell")
        inject_update(page, {"context_actions": panel}, mode="combat")

        rows = page.evaluate(
            "() => window.__elosernBridge.router.currentMenu().items.map("
            "(i) => ({ key: i.key, label: i.label }))"
        )
        fired = [row for row in rows if row["key"] == spell]
        self.assertEqual(len(fired), 1, rows)
        self.assertEqual(fired[0]["label"], new_label)
        # Focus tracked by key across the panel replacement.
        self.assertEqual(
            page.evaluate("() => window.__elosernBridge.router.currentItem().key"),
            spell,
        )
        self.assertEqual(page.evaluate("() => window.__elosernBridge.router.depth()"), depth_before)
        # Resolution is read-side only: the injection dispatched nothing.
        self.assertEqual(len(self._ui_actions(page)), sent_before)
        self.assertEqual(sent_action_count(page, "combat.command"), 0)

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_self_skill_submits_no_target_field(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # The utility SELF caster is disabled in combat: the session context
        # cannot supply its handler's event-context key, so the menu exposes
        # the disabled explanation instead of a cast. The granted SELF-shape
        # skill is the payload journey's target now — the allied flee row is
        # not a session skill any more (§6) — so the mode's own SELF role is
        # driven. H3 (design D11): skills row -> category frame -> the role's
        # group frame when the category has sub-groups -> the skill row.
        roles = self._roles()
        self._open_skills(page)
        self._open_category(page, roles["self_category"])
        self._focus_skill(page, roles["self_category"], roles["self_key"])
        self._press(page, "Enter")  # open-skill (SELF) -> self-confirm
        self._press(page, "Enter")  # confirm self-cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.command")
        inner = envelope["payload"]["command"]["payload"]
        self.assertEqual(inner["skill_key"], roles["self_key"])
        self.assertNotIn("target_ids", inner)
        self.assertNotIn("target_shorthand", inner)
        self.assertNotIn("actor", envelope["payload"])

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    @covers_requirement(
        "webclient-combat-menu::one-command-card-switches-actors-and-renders-authoritative-draft-progress"
    )
    def test_actor_selector_chrome_returns_to_root_without_a_command(self):
        """The commanded-actor card chrome (webclient-party-command-selection).

        The compact line reports the committed draft progress; its 變更成員
        control opens the actor frame inside the same centred card; selecting
        the already-commanded member is one deliberate return to the root that
        sends no command and issues no actor query. (The fixture engagement
        has a single allied actor, so the switch path's read-only query is
        proven by the synthetic multi-actor store suite.)
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)

        panel = self._combat_panel(page)
        actor_id = panel["choices"]["actor_id"]
        change = page.locator('[data-testid="combat-actor-change"]')
        change.wait_for(state="visible", timeout=15000)
        line = page.locator('[data-testid="combat-actor-line"]')
        self.assertIn(
            "已確認", line.locator('[data-testid="combat-actor-progress"]').inner_text()
        )

        commands_before = sent_action_count(page, "combat.command")
        queries_before = sent_action_count(page, "combat.actor_choices")
        change.click()
        row = page.locator(f'#action-dock [data-item-key="actor-{actor_id}"]')
        row.wait_for(state="visible", timeout=15000)
        row.click()
        # The already-commanded member: back to exactly one root, no command
        # and no actor query.
        page.wait_for_function(
            "() => { const s = window.__elosernBridge.store.view;"
            " return s.dockSource === 'combat.root' && s.dockDepth === 1; }",
            timeout=15000,
        )
        self.assertEqual(sent_action_count(page, "combat.command"), commands_before)
        self.assertEqual(
            sent_action_count(page, "combat.actor_choices"), queries_before
        )

    def _inject_actor_stock(self, page, foe_id: int) -> None:
        """Extend the committed combat panel with the commanded actor's own
        stock and the three basic actions (webclient-party-items-tactics).

        The live engagement's grant set carries no items, so the journey
        commits the fixture's schema-valid ``choices`` fragment (one SELF item,
        one item with its committed no-effect reason, and the three basic
        actions with 挑釁 over the presented enemy). The client mirror validates
        the injected panel, so the rows are the committed facts the menu reads.
        """
        panel = self._combat_panel(page)
        panel["choices"].update(actor_command_choices(foe_id))
        inject_update(page, {"context_actions": panel}, mode="combat")

    def _last_command_payload(self, page) -> dict:
        envelopes = [
            args[0]
            for cmd, args, _kwargs in self._ui_actions(page)
            if cmd == "ui_action" and args and args[0].get("action_id") == "combat.command"
        ]
        self.assertTrue(envelopes, "no combat.command was sent")
        return envelopes[-1]["payload"]["command"]

    def _wait_unlocked(self, page) -> None:
        # The single-writer lock releases on the committed result; the next
        # deliberate activation waits for it rather than racing it.
        page.wait_for_function(
            "() => !window.__elosernBridge.store.view.dispatch.inFlight",
            timeout=30000,
        )

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    @covers_requirement("webclient-combat-menu::actor-item-use-and-tactics-reuse-the-complete-existing-selection-flow")
    def test_item_and_tactic_choices_send_the_actor_command(self):
        """The commanded actor's own items and basic actions
        (webclient-party-items-tactics).

        Keyboard only: 道具 opens the actor's own stock (quantity and effect
        summary, the unusable row's committed reason), one item's SELF review
        submits exactly one guarded `combat.command` with the closed `item`
        payload and no target field, and 防禦 confirms its round choice as the
        closed `tactic` payload. The actorless `inventory.use` is never sent,
        and the declared command is the only wire traffic.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        foes = self._foe_identities(page)
        self.assertTrue(foes, "the fixture engagement lists an enemy")
        self._inject_actor_stock(page, foes[0])
        page.wait_for_selector('#action-dock [data-item-key="items"]', timeout=15000)

        # 道具: the actor's own stock, with the committed quantity/summary and
        # the unusable row's committed reason.
        self._walk_to(page, "items")
        self._press(page, "Enter")
        self._walk_to(page, "item-trial_salve")
        stock_text = page.locator(
            '#action-dock [data-item-key="item-trial_salve"]'
        ).inner_text()
        self.assertIn("×2", stock_text)
        # The unusable row stays visible, disabled, and explains itself.
        self._walk_to(page, "item-trial_vial")
        self.assertIn(
            "目前沒有可用的效果",
            page.locator('[data-testid="action-dock-description"]').inner_text(),
        )
        self._walk_to(page, "item-trial_salve")

        # One item's SELF review, then the submit: exactly one guarded item
        # command, no target field, and no actorless inventory.use.
        self._press(page, "Enter")
        self._press(page, "Enter")
        self._wait_unlocked(page)
        self.assertEqual(
            self._last_command_payload(page),
            {"kind": "item", "payload": {"item_key": "trial_salve"}},
        )
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)

        # Back to the root, re-commit the actor's stock (a resolved round
        # republishes the panel), then 防禦: the confirm row declares the
        # round choice as the closed `tactic` payload.
        self._press(page, "Escape")
        self._inject_actor_stock(page, foes[0])
        page.wait_for_selector('#action-dock [data-item-key="defend"]', timeout=15000)
        self._walk_to(page, "defend")
        self._press(page, "Enter")
        self._walk_to(page, "tactic-confirm")
        self._press(page, "Enter")
        self._wait_unlocked(page)
        self.assertEqual(
            self._last_command_payload(page),
            {"kind": "tactic", "payload": {"key": "defend"}},
        )
        self.assertEqual(sent_action_count(page, "inventory.use"), 0)
