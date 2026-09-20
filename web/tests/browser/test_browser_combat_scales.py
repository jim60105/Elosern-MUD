"""Combat dock mockup-grid and skill-category journeys (webclient-combat-menu 5.2-5.5): grid/detail geometry at both viewports, area space-select, and the mastered-element scale ladder.
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

    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    @covers_requirement("webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable")
    @covers_requirement("webclient-desktop-shell::the-dock-s-row-region-and-detail-panes-are-direct-children-of-their-host")
    def test_combat_dock_renders_mockup_grid_and_detail_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            install_outbound_recorder(page)
            self._engage(page)
            # H3 (design D2/D11): the combat root is a single-row tab bar
            # (depth 1); the pane (DockMenu + SkillDetailPane) renders only at
            # depth >= 2. Navigate into the skill frame: skills tab -> category
            # -> the mastered ladder's element group (mode-dependent position)
            # -> its skill frame.
            roles = self._roles()
            self._press(page, "ArrowRight")  # skills tab
            self._press(page, "Enter")  # open category frame (elemental_magic focused)
            self._press(page, "Enter")  # open elemental_magic -> element group frame
            self._press_to(page, "ArrowRight", roles["ladder_group_index"])
            self._press(page, "Enter")  # open the ladder's group -> its skill frame
            # The dock host carries the split: item list left, detail right —
            # as direct children of `.dock-pane-host`, with no anonymous layout
            # wrapper between the host and either child
            # (remove-redundant-dock-menu-layout).
            self.assertEqual(page.locator(".dock-menu-layout").count(), 0)
            self.assertEqual(
                page.evaluate(
                    "() => { const list = document.querySelector('.dock-menu');"
                    " const detail = document.querySelector('[data-testid=\"combat-detail\"]');"
                    " const host = document.querySelector('.dock-pane-host');"
                    " return !!(host && list && detail"
                    " && list.parentElement === host && detail.parentElement === host); }"
                ),
                True,
                "the row region and the detail pane are direct children of the pane host",
            )
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
            # choice (not the legacy "Enter → 開啟" line). Assert a scale option:
            # the ladder's base cost doubled at 威力×2 (the seam's base cost is
            # the same value in both modes today; read it from the seam so the
            # pin follows the kit's skill row, not a magic number).
            self.assertIn(
                f"MP {roles['ladder_mp_cost'] * 2}",
                detail,
                "the detail pane shows the 威力 scale options",
            )
            # H3: the skill frame's focused row carries the gold border and
            # the `dock-menu__skill--on` class (not the legacy `dock-menu-item--focused`).
            # The obsidian-gold wave (acd3790) re-pointed the gold family:
            # the focused row's border is now --gold-500 (#b99a60, DockMenu
            # .dock-menu__skill--on). Assert the resolved token so the pin
            # follows the token, not a pinned rgb value.
            gold500_rgb = page.evaluate(
                """() => {
                  const raw = getComputedStyle(document.documentElement)
                    .getPropertyValue('--gold-500').trim();
                  const n = parseInt(raw.slice(1), 16);
                  return 'rgb(' + [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', ') + ')';
                }"""
            )
            focused = page.locator(".dock-menu .dock-menu__skill--on").first
            self.assertEqual(focused.count(), 1, "the focused skill row is rendered")
            self.assertEqual(
                focused.evaluate("el => getComputedStyle(el).borderColor"),
                gold500_rgb,
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

        # H3 (design D11): the ladder skill sits in the elemental_magic /
        # mastery-element group. Skills tab -> category frame -> group frame
        # -> ladder group -> skill frame -> 威力 scale step (preselected ×1)
        # -> target flow.
        ladder = self._roles()["ladder_key"]
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", ladder)
        self._press(page, "Enter")  # open the ladder skill: 威力 scale step
        self._press(page, "Enter")  # choose the preselected 威力×1
        # Walk the mounted grid to the monster candidate (the party roster is
        # mode-dependent) before toggling.
        self._walk_to(page, f"area-{enemy_ids[0]}")

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
        self._walk_to(page, "area-confirm")
        self._press(page, "Enter")
        actions = self._ui_actions(page)
        self.assertGreaterEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], ladder)
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

        # H3 (design D11): the ladder skill sits in the elemental_magic /
        # mastery-element group. Skills tab -> category frame -> group frame
        # -> ladder group -> skill frame -> 威力 scale step (mastery owned);
        # the scale cells are walked by key, not by a fixed press count.
        roles = self._roles()
        ladder = roles["ladder_key"]
        self._open_skills(page)
        self._open_category(page, "elemental_magic")
        self._focus_skill(page, "elemental_magic", ladder)
        self._press(page, "Enter")  # open the ladder skill: 威力 scale step
        # H3: the scale step's rows are the pane's `.dock-menu__scale` buttons.
        scale_rows = page.locator(".dock-menu .dock-menu__scale")
        self.assertGreaterEqual(scale_rows.count(), 5)
        self.assertIn(
            "威力×",
            scale_rows.first.inner_text(),
            "the scale step labels the power choice",
        )
        self._walk_to(page, "scale-2")  # 威力×2
        self._press(page, "Enter")  # choose 威力×2 -> target flow
        self._walk_to(page, f"area-{target}")  # the monster candidate
        self._press(page, "Space")  # toggle the explicit monster candidate
        self._walk_to(page, "area-confirm")
        self._press(page, "Enter")  # cast at scale 2

        actions = self._ui_actions(page)
        self.assertEqual(len(actions), 1, actions)
        envelope = actions[0][1][0]
        self.assertEqual(envelope["action_id"], "combat.cast")
        self.assertEqual(envelope["payload"]["skill_key"], ladder)
        self.assertEqual(envelope["payload"]["scale"], 2)
        self.assertEqual(envelope["payload"]["target_ids"], [target])
        # The scaled cast deducts the ladder's base cost doubled (the status
        # panel reflects the true resource pool after the round).
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
        self.assertEqual(mp_before_value - mp_after_value, roles["ladder_mp_cost"] * 2)

    @covers_requirement("webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices")
    def test_panel_groups_skills_by_category_in_enum_order(self):
        page = self.logged_in_page()
        self._engage(page)
        panel = self._combat_panel(page)
        roles = self._roles()
        # The seeded character owns elemental spells, martial-arts innates,
        # enhancement, utility, and the unconditionally-owned seed act; the
        # payload lists only the categories that have owned active skills,
        # in SkillCategory declaration order (both modes own exactly this
        # category set; movement is retired and flee is under martial_arts).
        self.assertEqual(
            [category["category"] for category in panel["skills"]],
            [
                "elemental_magic",
                "martial_arts",
                "enhancement",
                "utility",
                "sexual_act",
            ],
        )
        elemental = panel["skills"][0]
        # Element sub-groups follow the live ELEMENT_REGISTRY declaration
        # order, not ownership order. The kit install registers its own
        # element before the borrowed shipped row, so the seam names the
        # mode's registry order (reversed under the synthetic install).
        self.assertEqual(
            [group["group"] for group in elemental["groups"]],
            list(roles["element_group_order"]),
        )
        spell_group = elemental["groups"][roles["spell_group_index"]]
        self.assertEqual(spell_group["label"], roles["spell_element_label"])
        # The lineage closure adds the spell's prereq behind the requested
        # spell, so the group lists both in ownership order.
        self.assertEqual(
            [skill["key"] for skill in spell_group["skills"]],
            [roles["spell_key"], roles["prereq_key"]],
        )
        # A category without a group carries exactly one null-keyed sub-group.
        enhancement = panel["skills"][2]
        self.assertEqual(enhancement["category"], "enhancement")
        self.assertEqual(len(enhancement["groups"]), 1)
        self.assertIsNone(enhancement["groups"][0]["group"])
        self.assertIsNone(enhancement["groups"][0]["label"])
        self.assertEqual(
            [skill["key"] for skill in enhancement["groups"][0]["skills"]],
            [roles["enhancement_key"]],
        )

    @covers_requirement("webclient-combat-menu::the-combat-panel-hides-freeform-casting-from-non-masters")
    def test_panel_advertises_scales_only_for_the_mastered_element(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        panel = self._combat_panel(page)
        roles = self._roles()
        by_key = {
            skill["key"]: skill
            for category in panel["skills"]
            for group in category["groups"]
            for skill in group["skills"]
        }
        # The seeded mastery entitles only the ladder skill; every other
        # skill omits the field entirely, so a non-master's panel would
        # reveal nothing at all.
        ladder = by_key[roles["ladder_key"]]
        self.assertIn("freeform_scales", ladder)
        self.assertEqual(
            [entry["scale"] for entry in ladder["freeform_scales"]],
            [0.25, 0.5, 1, 2, 4],
        )
        for key in (
            roles["spell_key"],
            roles["prereq_key"],
            roles["none_key"],
            "flee",
            roles["attack_key"],
        ):
            self.assertNotIn("freeform_scales", by_key[key])
