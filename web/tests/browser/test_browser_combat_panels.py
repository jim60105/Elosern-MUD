"""Combat dock panel journeys (webclient-combat-menu 5.2-5.5): explicit area multi-selection, disabled-row reasons, keyboard-menu rebuild after a round, and minimum-viewport rendering.
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
    narrative_log_text,
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
    def test_area_explicit_multi_selection(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        enemy_ids = [
            p["identity"] for p in panel["participants"] if p["team"] == "foes"
        ]
        self.assertEqual(len(enemy_ids), 1, "engage opens a single-enemy battle")

        # H3 (design D11): the ladder skill is the mastery element's group.
        # Skills tab -> category frame (elemental_magic focused) -> group frame
        # -> ladder group -> skill frame -> 威力 scale
        # step (preselected ×1) -> target flow.
        ladder = self._roles()["ladder_key"]
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", ladder)
        self._press(page, "Enter")  # open the ladder skill: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # AREA grid: candidate targets, then shorthand cells, then confirm.
        # Walk the mounted grid to the enemy candidate (party/roster sizes
        # are mode-dependent) and toggle it explicitly.
        self._walk_to(page, f"area-{enemy_ids[0]}")
        self._press(page, "Space")  # toggle the explicit monster candidate
        self._walk_to(page, "area-confirm")
        self._press(page, "Enter")  # confirm cast

        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], ladder)
        self.assertEqual(envelope["payload"]["target_ids"], enemy_ids)
        self.assertNotIn("target_shorthand", envelope["payload"])

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_disabled_reason_is_visible_without_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        roles = self._roles()
        # H3 (design D2/D11): a disabled entry explains itself through the
        # detail pane (`SkillDetailPane`, `combat-detail`) in the skill frame.
        # The mode's race-gated SELF caster is disabled in combat (the
        # fixture character's race lacks the divine affinity its row
        # requires), so the pane exposes its disabled explanation instead of
        # a cast. Navigate: skills tab -> category frame -> the disabled
        # row's category (utility under the kit install; divine-mystery in
        # shipped mode) -> skill frame (the disabled row is the utility
        # group's first focus under the kit install).
        self._open_skills(page)
        disabled_category = roles["self_disabled_category"]
        self._open_category(page, disabled_category)
        self._focus_skill(page, disabled_category, roles["self_disabled_key"])
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
        # The synth preset arrives with a companion, so the target menu's
        # first row is not necessarily a foe — walk to the enemy row.
        self._walk_to(page, f"target-{self._basic_attack_target_identity(page)}")
        self._press(page, "Enter")  # select the monster target
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
        self._walk_to(page, f"target-{self._basic_attack_target_identity(page)}")
        self._press(page, "Enter")  # select the monster target
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
        narrative = narrative_log_text(page)
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
        # is its own condition row (the mode's modifier-rule seam), which
        # carries the ``modifiers`` field — the debuff code alone only carries
        # the label and remaining seconds.
        from web.browser_support.browser_fixtures_data import (
            combat_modifier_condition_rule_id,
        )

        chip_label = page.locator(
            '[data-testid="status-panel__condition--'
            + combat_modifier_condition_rule_id()
            + '"]'
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
