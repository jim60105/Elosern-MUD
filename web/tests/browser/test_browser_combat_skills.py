"""Keyboard-only combat skill-shape and outcome journeys (webclient-combat-menu 5.2-5.5): NONE/SELF/AREA submissions, defend/flee seams, forfeit confirmation, and the terminal-outcome panel refresh.
"""

from __future__ import annotations

import time
from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import combat_journey_values
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
        instead of hardcoding it. The root tab bar is itself a listbox
        carrying ``data-item-key`` tabs; the keyboard router walks the
        committed FRAME's own grid, so the tab bar is excluded from the
        measurement."""
        cells = page.evaluate(
            """() => Array.from(
                 document.querySelectorAll(
                   '#action-dock [role="listbox"] [data-item-key]'))
               .filter((el) => !el.closest(".dock-tab-bar"))
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
        self._press(page, "ArrowRight")  # skills tab
        self._press(page, "Enter")  # -> category frame

    def _open_category(self, page, category: str) -> None:
        """Arrow to ``category`` in the category frame and Enter into it (a
        single-group category opens its skill frame directly)."""
        names = [item["category"] for item in self._combat_panel(page)["skills"]]
        self.assertIn(category, names)
        self._press_to(page, "ArrowRight", names.index(category))
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
        names = [item["category"] for item in panel["skills"]]
        self.assertIn(category, names)
        category_index = names.index(category)
        groups = panel["skills"][names.index(category)]["groups"]
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

    @covers_requirement("webclient-combat-menu::combat-target-selection-sends-one-shape-per-targetspec")
    def test_none_skill_submits_skill_key_only(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # The mode's NONE-shape active lives in a mode-dependent category
        # (enhancement shipped, utility under the kit install). H3 (design
        # D11): skills tab -> category frame; the category opens the skill
        # frame (the carrier row is focused after the intra-frame walk).
        roles = self._roles()
        self._open_skills(page)
        self._open_category(page, roles["none_category"])
        self._focus_skill(page, roles["none_category"], roles["none_key"])
        self._press(page, "Enter")  # open-skill -> 施展 item
        self._press(page, "Enter")  # confirm the single 施展 item

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], roles["none_key"])
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
        # -> select the ladder's element group -> skill frame -> 威力 scale
        # step (preselected ×1) -> all-enemies shorthand.
        ladder = self._roles()["ladder_key"]
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", ladder)
        self._press(page, "Enter")  # open the ladder skill: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # AREA grid: candidate targets, then the shorthand cells, then the
        # confirm cell. The party roster is mode-dependent (the synth preset
        # arrives with a companion), so the journey walks the router to the
        # named cells instead of assuming fixed grid positions.
        self._walk_to(page, "shorthand-all-enemies")
        self._press(page, "Enter")  # choose shorthand
        # The chosen shorthand re-homes focus onto the confirm cell.
        self._walk_to(page, "area-confirm")
        self._press(page, "Enter")  # confirm cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], ladder)
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
        self._press(page, "ArrowRight")  # 背包 (the client-local drawer row)
        self._press(page, "ArrowRight")  # defend (disabled)
        page.wait_for_timeout(120)
        self.assertEqual(
            store_state(page).get("focus", {}).get("key"),
            "defend",
            "the disabled defend tab is the focused root cell",
        )
        self._press(page, "Enter")
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), 0)

    @covers_requirement("webclient-combat-menu::production-combat-actions-are-narrow-and-server-authoritative")
    def test_flee_flow_submits_empty_payload(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._press(page, "ArrowRight")  # skills (1)
        self._press(page, "ArrowRight")  # items (2)
        self._press(page, "ArrowRight")  # 背包 (3, client-local drawer row)
        self._press(page, "ArrowRight")  # defend (4)
        self._press(page, "ArrowRight")  # flee (5)
        self.assertEqual(
            store_state(page).get("focus", {}).get("key"),
            "flee",
            "the flee tab is the focused root cell",
        )
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
        # skills, items, 背包, defend, flee, forfeit — the client-local 背包
        # row joined it with add-inventory-item-actions) — navigation is
        # horizontal. Focus reaches `forfeit` (index 6) by pressing
        # ArrowRight six times.
        self._press(page, "ArrowRight")  # skills (1)
        self._press(page, "ArrowRight")  # items (2)
        self._press(page, "ArrowRight")  # 背包 (3, client-local drawer row)
        self._press(page, "ArrowRight")  # defend (4)
        self._press(page, "ArrowRight")  # flee (5)
        self._press(page, "ArrowRight")  # forfeit (6)
        self.assertEqual(
            store_state(page).get("focus", {}).get("key"),
            "forfeit",
            "the forfeit tab is the focused root cell",
        )
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
        # During combat the exploration and character panels render
        # unavailable; only a full post-settlement snapshot restores them.
        # services v3 keeps its panel available through combat with the read
        # model forcing host/guild/shop null, so personal item actions stay
        # usable while no remote service is exposed.
        state = store_state(page)
        for name in ("exploration", "character"):
            self.assertIn(name, state["panels"])
            self.assertFalse(state["panels"][name]["available"], f"{name} must be combat-unavailable")
        services = state["panels"]["services"]
        self.assertTrue(services["available"], "services v3 keeps the personal surfaces available")
        self.assertIsNone(services["host"])
        self.assertIsNone(services["guild"])
        self.assertIsNone(services["shop"])
        self.assertIsNotNone(services["player"])
        self.assertIsNotNone(services["inventory"])
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

    @covers_requirement(
        "webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content"
    )
    def test_fixed_column_skill_pane_keeps_its_rows_inside_the_command_region(self):
        """The fixed-column skill pane stays inside the command region (1280x720).

        Relocated from the exploration keyword frame (C8c's nav pane, which
        this change leaves without a reachable producer): the combat skill
        frame carries the requirement's surviving assertions — every row
        inside the pane's right edge at the minimum supported viewport, and
        the fixed column count governing which cell a row occupies.
        """
        page = self.logged_in_page((1280, 720))
        install_outbound_recorder(page)
        self._engage(page)
        self._open_skills(page)  # skills tab -> category frame

        pane_selector = '#action-dock [data-testid="dock-menu"]'
        page.wait_for_selector(pane_selector, timeout=15000)
        rows = page.locator(pane_selector + " [data-item-key]")
        self.assertGreater(
            rows.count(), 0, "the skill pane must render at least one row"
        )
        pane_box = page.locator(pane_selector).bounding_box()
        self.assertIsNotNone(pane_box, "the skill pane must be visible at 1280x720")
        pane_right_edge = pane_box["x"] + pane_box["width"]
        for i in range(rows.count()):
            box = rows.nth(i).bounding_box()
            self.assertIsNotNone(box, "skill row %d must have a bounding box" % i)
            self.assertLessEqual(
                box["x"] + box["width"],
                pane_right_edge + 1,
                "skill row %d overflows the pane horizontally" % i,
            )
            self.assertGreaterEqual(
                box["x"],
                pane_box["x"] - 1,
                "skill row %d starts left of the pane" % i,
            )

        # The fixed column count governs the keyboard geometry: ArrowRight
        # advances a column when the frame maps more than one (and is a no-op
        # in a single-column frame), never a function of the rendered width.
        columns = page.locator(pane_selector).evaluate(
            "el => { const m = /repeat\\((\\d+)/.exec(el.style.gridTemplateColumns || '');"
            " return m ? Number(m[1]) : 1; }"
        )
        grid = self._cell_grid(page)
        start = self._focus_key(page)
        self.assertIn(start, grid, "the focused skill row must be a measured cell")
        self._press(page, "ArrowRight")
        moved = self._focus_key(page)
        self.assertIn(moved, grid, "ArrowRight must land on a measured cell")
        if columns > 1:
            self.assertEqual(
                grid[moved][1],
                grid[start][1] + 1,
                "ArrowRight must reach the second column of the fixed mapping",
            )
        else:
            self.assertEqual(
                moved, start, "ArrowRight is a no-op in a single-column frame"
            )
        self.assertEqual(
            sent_action_count(page), 0, "arrow-key navigation submits nothing"
        )
