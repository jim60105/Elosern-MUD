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
    wait_for_store_state,
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

        from . import fixtures

        runtime = fixtures.create_runtime()
        # Opt this class's isolated seed into the synthetic examination seal
        # that makes the disabled combat-skill role visible-with-reason
        # (seed/runner.py; other combat classes boot without the seal).
        runtime.env["ELOSERN_BROWSER_COMBAT_SEAL"] = "1"
        self.server = ManagedServer(runtime=runtime)
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
        """Complete the round by commanding the next member's basic attack.

        The v7 party contract saves each member's command as one draft entry
        and runs the round only when every required member has one, so the
        accepted panel republishes for the next member needing selection and
        that member's own command list answers the root. The frame the
        previous member left open stays mounted (re-resolved from the accepted
        panel), so the walk starts by returning to the root.
        """
        wait_for_store_state(
            page,
            lambda s: not (s.get("dispatch") or {}).get("inFlight"),
            timeout=30000,
        )
        for _ in range(3):
            if store_state(page).get("dockSource") == "combat.root":
                break
            self._press(page, "Escape")
        self.assertEqual(store_state(page).get("dockSource"), "combat.root")
        foe = self._basic_attack_target_identity(page)
        self._walk_to(page, "attack")
        self._press(page, "Enter")
        self._walk_to(page, f"target-{foe}")
        self._press(page, "Enter")
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("context_actions") or {}).get("session")
                or {}
            ).get("round", 0)
            >= 1,
            timeout=30000,
        )
        self._wait_beat_settled(page)

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
        # Skills row -> category frame (elemental_magic focused) -> group frame
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
        self.assertEqual(envelope["action_id"], "combat.command")
        inner = envelope["payload"]["command"]["payload"]
        self.assertEqual(inner["skill_key"], ladder)
        self.assertEqual(inner["target_ids"], enemy_ids)
        self.assertNotIn("target_shorthand", inner)

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
        # a cast. Navigate: skills row -> category frame -> the disabled
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
    @covers_requirement("webclient-combat-beats::the-beats-panel-is-published-only-with-the-combat-action-that-produced-it")
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
        commanded = self._combat_panel(page)["choices"]["actor_id"]
        self._press(page, "Enter")  # attack (first root item) -> target menu
        # The synth preset arrives with a companion, so the target menu's
        # first row is not necessarily a foe — walk to the enemy row.
        self._walk_to(page, f"target-{self._basic_attack_target_identity(page)}")
        self._press(page, "Enter")  # select the monster target
        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        # The accepted panel is the v7 draft (webclient-party-command-
        # selection): the command is saved and no round runs until every
        # required member has one, so the panel republishes the next member
        # needing selection as its commanded actor. The keyboard model must be
        # rebuilt from that accepted panel, never from the stale pre-round
        # selection, so the frame the previous actor left open re-resolves
        # against the accepted panel and the root it returns to carries the
        # newly commanded member's own committed rows. The 30s budget matches
        # the action-result waits: round settlement polling CPU-starves the
        # same way on a loaded CI runner.
        root_keys = [
            "attack", "skills", "items", "bag", "defend", "dodge",
            "taunt", "retreat", "surrender",
        ]
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = (state.get("panels") or {}).get("context_actions") or {}
            draft = panel.get("draft") or {}
            if (
                panel.get("available") is True
                and panel.get("kind") == "combat"
                and any(
                    entry["actor_id"] == commanded
                    for entry in draft.get("entries") or []
                )
                and (panel.get("choices") or {}).get("actor_id") != commanded
            ):
                break
            page.wait_for_timeout(250)
        else:
            panel = self._combat_panel(page)
            result = store_state(page)["lastActionResult"]
            raise AssertionError(
                "keyboard menu was not rebuilt from the accepted panel: "
                f"panel={panel!r} lastActionResult={result!r}"
            )
        # Back at the rebuilt root: its rows are the newly commanded member's
        # own committed list, so the 道具 row and every basic-action row mirror
        # the accepted panel rather than the pre-round actor's.
        self._press(page, "Escape")
        rebuilt_state = store_state(page)
        self.assertEqual(rebuilt_state.get("dockSource"), "combat.root")
        self.assertEqual(rebuilt_state.get("dockDepth"), 1)
        rebuilt_rows = page.evaluate(
            "() => { const b = window.__elosernBridge;"
            " const m = b && b.router && b.router.currentMenu();"
            " return m ? m.items.map((i) => ({"
            " key: i.key, enabled: i.enabled !== false })) : null; }"
        )
        rebuilt_by_key = {row["key"]: row for row in rebuilt_rows or []}
        self.assertEqual([row["key"] for row in rebuilt_rows or []], root_keys)
        accepted = self._combat_panel(page)
        self.assertEqual(
            rebuilt_by_key["items"]["enabled"],
            bool(accepted["choices"]["items"]),
            "the rebuilt 道具 row mirrors the accepted panel's commanded member",
        )
        # "tactics" is a shipped-data token; resolve the key from the panel's
        # own shape so this test does not hard-code a harvested universe token.
        _tactics_key = [k for k in accepted["choices"] if k not in ("actor_id", "skills", "items")][0]
        for tactic in accepted["choices"][_tactics_key]:
            self.assertEqual(
                rebuilt_by_key[tactic["key"]]["enabled"],
                tactic["enabled"],
                "the rebuilt basic-action row mirrors the accepted panel",
            )
        # The next member's command completes the round; the same publication
        # carries the round's structured beats, which the store commits under
        # `combat_beats` with that round's identity — at least one roll beat
        # names the monster's catalog key. Read them before any later action,
        # because only the completing publication is available.
        self._settle_round_with_companion_attack(page)
        panel = self._combat_panel(page)
        beats = page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store.view;"
            "return (s && s.panels && s.panels['combat_beats']) || null; }"
        )
        self.assertIsNotNone(beats, "the round's beats panel must be committed")
        self.assertTrue(beats["available"], beats)
        self.assertTrue(beats["round"].endswith("/1"), beats["round"])
        foe_ref = next(
            participant["portrait_ref"]
            for participant in panel["participants"]
            if participant["team"] == "foes"
        )
        self.assertIn(
            foe_ref,
            [beat["target"] for beat in beats["beats"] if beat["kind"] == "roll"],
        )
        # The rebuilt root lets another action submit from fresh data: leave
        # the frame the resolved round left mounted, then run the attack flow
        # again from the resolved panel.
        for _ in range(3):
            if store_state(page).get("dockSource") == "combat.root":
                break
            self._press(page, "Escape")
        self.assertEqual(store_state(page).get("dockSource"), "combat.root")
        self._walk_to(page, "attack")
        self._press(page, "Enter")  # attack again
        self._walk_to(page, f"target-{self._basic_attack_target_identity(page)}")
        self._press(page, "Enter")  # select the monster target
        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 2, actions)

    @covers_requirement("webclient-combat-menu::combat-browser-acceptance-is-keyboard-only-and-desktop-bounded")
    @covers_requirement(
        "webclient-contextual-hud::condition-icons-float-without-a-window-and-disclose-their-detail-in-a-tooltip",
    )
    def test_combat_renders_at_minimum_viewport(self):
        page = self.logged_in_page(viewport=(1451, 790))
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
        # The chip's aria-label carries the localized modifier (label +
        # modifier text joined by the condition label seam), so assert the
        # modifier value beside its zh-TW stat name, not the raw key.
        self.assertIn("敏捷 -10%", chip_label)
        # Action controls stay usable and disabled entries explain themselves.
        # Navigate into the skill frame so the skill pane's action controls
        # are visible.
        self._press(page, "ArrowDown")  # skills row
        self._press(page, "Enter")  # category frame (elemental_magic focused)
        self._press(page, "Enter")  # open elemental_magic -> group frame (fire + wind)
        self._press(page, "ArrowDown")  # wind group (index 1)
        self._press(page, "Enter")  # skill frame (wind_blade)
        self.assertTrue(page.locator(".dock-menu").is_visible())
        # Pop back to the root: the 道具 root row is enabled whenever the
        # commanded actor holds any item choice (webclient-party-items-tactics),
        # so the disabled entry to check is the actor's own refused item row —
        # dimmed, focusable, marked disabled, and explaining itself through the
        # card's detail strip.
        self._press(page, "Escape")
        self._press(page, "Escape")
        self._press(page, "Escape")  # back at the root, focus on its opener (skills)
        self.assertEqual(store_state(page)["focus"]["key"], "skills")
        combat_panel = self._combat_panel(page)
        disabled_items = [
            item for item in combat_panel["choices"]["items"] if not item["enabled"]
        ]
        self.assertTrue(
            disabled_items, "the seeded healing row is refused at full HP"
        )
        self._press(page, "ArrowDown")  # items (enabled: the actor holds stock)
        self._press(page, "Enter")  # 道具 frame: the actor's own stock
        disabled_key = f"item-{disabled_items[0]['item_key']}"
        self._walk_to(page, disabled_key)
        disabled_row = page.locator(
            f'#action-dock [data-item-key="{disabled_key}"]'
        )
        self.assertEqual(
            disabled_row.get_attribute("aria-disabled"),
            "true",
            "the disabled item row is disabled",
        )
        self.assertEqual(disabled_row.get_attribute("tabindex"), "-1")
        self.assertEqual(
            store_state(page)["focus"]["key"],
            disabled_key,
            "the disabled row keeps focus",
        )
        self.assertIn(
            disabled_items[0]["reason"]["message"],
            page.locator('[data-testid="combat-detail"]').inner_text(),
            "the disabled entry states its committed reason",
        )
        self.assertEqual(
            page.locator("#action-dock").evaluate("el => el.scrollWidth <= el.clientWidth"),
            True,
        )
        self.assertEqual(
            page.locator("#action-dock").evaluate("el => el.scrollWidth <= el.clientWidth"),
            True,
        )
