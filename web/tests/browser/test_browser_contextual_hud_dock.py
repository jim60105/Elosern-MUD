"""Contextual HUD action-dock acceptance (webclient-contextual-hud): the dock in the band's command region, tab-bar count badges, the router breadcrumb, digit-row activation, and per-kind pane vocabulary.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_overview_chip,
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    outbound_messages,
    push_exploration_frame,
    sent_action_count,
    store_state,
    valid_character_panel,
    valid_lore_codex_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_store_state,
)
from ._journey_support import (
    _interact_target,
    _move_row,
    _exploration_panel,
    _suggestions_ready,
    _exploration_context_actions_panel,
    _combat_panel,
    _inject_snapshot,
    _wait_mode,
    _press,
    _dock_depth,
)


def _selectable_target(identity: int, name: str) -> dict:
    """An interact target carrying one affordance, so the workspace can select it."""
    target = _interact_target(identity, name)
    target["affordances"] = [{
        "kind": "action",
        "action_id": "explore.talk_freeform",
        "label": "自由對話",
        "enabled": True,
        "disabled_reason": None,
    }]
    return target


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    @covers_requirement(
        "webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size"
    )
    def test_action_dock_fills_the_band_command_region_across_modes(self):
        """The dock fills the bottom band's command region at a fixed size
        (webclient-avg-stage-shell design D1/D5).

        The band (``stage-band``) is ``clamp(260px, 27.8vh, 400px)`` tall and
        paints the draft's `.dockwrap` chrome (gradient, hairline top border,
        upward shadow); its right third is the command region, which holds
        ``#action-dock`` — a content column that paints nothing itself. No
        frame (the interaction workspace with a target selected, the waiting
        frame) moves or resizes the region. Verified across the scenario's
        viewport range (1280x720 through 1920x1080).
        """
        measure = """() => {
          const band = document.querySelector('[data-testid="stage-band"]');
          const region = document.querySelector('[data-testid="anchor-band-command"]');
          const dock = document.querySelector('#action-dock');
          const b = band.getBoundingClientRect();
          const r = region.getBoundingClientRect();
          const d = dock.getBoundingClientRect();
          const bandStyle = getComputedStyle(band);
          const dockStyle = getComputedStyle(dock);
          return {
            bandTop: b.top, bandBottom: b.bottom, bandHeight: b.height,
            regionLeft: r.left, regionRight: r.right, regionTop: r.top,
            regionBottom: r.bottom, regionWidth: r.width,
            dockLeft: d.left, dockRight: d.right, dockTop: d.top, dockBottom: d.bottom,
            bandBackgroundImage: bandStyle.backgroundImage,
            bandBorderTopWidth: bandStyle.borderTopWidth,
            bandBoxShadow: bandStyle.boxShadow,
            dockBackgroundImage: dockStyle.backgroundImage,
            dockBorderTopWidth: dockStyle.borderTopWidth,
            dockBoxShadow: dockStyle.boxShadow,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
          };
        }"""
        for viewport in ((1280, 720), (1600, 900), (1920, 1080)):
            page = self.logged_in_page(viewport)
            exploration = _exploration_panel([_selectable_target(11, "小販")])
            _inject_snapshot(
                page,
                {
                    "exploration": exploration,
                    "context_actions": _exploration_context_actions_panel(
                        {"status": "unavailable"}
                    ),
                    "local_map": valid_local_map_panel(),
                },
                mode="exploration",
            )
            _wait_mode(page, "exploration")

            dock = page.locator("#action-dock")
            self.assertEqual(dock.count(), 1, "exactly one #action-dock element")
            self.assertTrue(dock.is_visible(), "the action dock is visible")

            geometry = page.evaluate(measure)
            expected_band = min(max(260.0, geometry["viewportHeight"] * 0.278), 400.0)
            self.assertAlmostEqual(
                geometry["bandHeight"], expected_band, delta=1.0,
                msg=f"the band is clamp(260px, 27.8vh, 400px) tall at {viewport}",
            )
            self.assertAlmostEqual(
                geometry["bandBottom"], geometry["viewportHeight"], delta=1.0,
                msg=f"the band sits on the stage's bottom edge at {viewport}",
            )
            self.assertAlmostEqual(
                geometry["regionLeft"], geometry["viewportWidth"] * 2 / 3, delta=1.0,
                msg=f"the command region starts at two thirds of the width at {viewport}",
            )
            self.assertAlmostEqual(
                geometry["regionRight"], geometry["viewportWidth"], delta=1.0,
                msg=f"the command region ends at the stage's right edge at {viewport}",
            )
            self.assertAlmostEqual(geometry["regionTop"], geometry["bandTop"], delta=1.0)
            self.assertAlmostEqual(geometry["regionBottom"], geometry["bandBottom"], delta=1.0)
            # The dock lies inside the command region.
            self.assertGreaterEqual(geometry["dockLeft"], geometry["regionLeft"] - 0.5)
            self.assertLessEqual(geometry["dockRight"], geometry["regionRight"] + 0.5)
            self.assertGreaterEqual(geometry["dockTop"], geometry["regionTop"] - 0.5)
            self.assertLessEqual(geometry["dockBottom"], geometry["regionBottom"] + 0.5)
            # The band paints the draft's chrome; the content column paints nothing.
            self.assertIn("gradient", geometry["bandBackgroundImage"])
            self.assertTrue(geometry["bandBorderTopWidth"].startswith("1px"))
            self.assertNotEqual(geometry["bandBoxShadow"], "none")
            self.assertEqual(geometry["dockBackgroundImage"], "none")
            self.assertEqual(geometry["dockBorderTopWidth"], "0px")
            self.assertEqual(geometry["dockBoxShadow"], "none")

            # No frame moves or resizes the region: a target's verb popover
            # over the inert overview, then the waiting frame.
            baseline = (geometry["regionLeft"], geometry["regionTop"],
                        geometry["regionRight"], geometry["regionBottom"],
                        geometry["bandHeight"])
            activate_overview_chip(page, "target-11")
            page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
            after_interact = page.evaluate(measure)
            # Escape closes the popover and returns to the overview, whose
            # 等待／休息 chip then opens the waiting frame.
            _press(page, "Escape")
            wait_for_store_state(page, lambda s: s.get("dockSource") == "exploration.root")
            activate_overview_chip(page, "wait")
            page.wait_for_selector(".waiting-screen", timeout=15000)
            after_wait = page.evaluate(measure)
            for label, state in (("popover", after_interact), ("wait", after_wait)):
                box = (state["regionLeft"], state["regionTop"], state["regionRight"],
                       state["regionBottom"], state["bandHeight"])
                for got, want in zip(box, baseline):
                    self.assertAlmostEqual(
                        got, want, delta=1.0,
                        msg=f"the {label} frame left the command region unchanged at {viewport}",
                    )

        # One #action-dock element persists across a mode change (not remounted),
        # and its data-mode switches to the committed mode.
        page = self.logged_in_page()
        exploration = _exploration_panel([_interact_target(11, "小販")])
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        page.evaluate(
            "() => { const d = document.querySelector('#action-dock'); d.__tracked = true; }"
        )
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        self.assertEqual(
            page.locator("#action-dock").count(), 1, "exactly one #action-dock persists"
        )
        self.assertEqual(
            page.locator("#action-dock").get_attribute("data-mode"),
            "combat",
            "the dock's data-mode switches to the committed mode",
        )
        tracked = page.evaluate(
            "() => { const d = document.querySelector('#action-dock'); "
            "return d && d.__tracked === true; }"
        )
        self.assertTrue(
            tracked,
            "the same #action-dock node persists across the mode change (not remounted)",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-combat-dock-s-root-frame-renders-as-an-icon-tab-bar-with-a-truthful-skills-badge"
    )
    def test_combat_dock_root_tab_bar_truthful_skills_badge(self):
        """The COMBAT root renders as an icon tab bar with a truthful 技能
        badge; exploration renders the scene overview and no tab bar at all
        (webclient-scene-overview-swap)."""
        page = self.logged_in_page()
        # The combat panel's 技能 badge equals the committed skill-descriptor
        # count (the fixture's flattened categories/groups).
        combat = _combat_panel()
        skill_count = sum(
            len(group.get("skills") or [])
            for category in combat.get("skills") or []
            for group in category.get("groups") or []
        )
        self.assertGreater(skill_count, 0, "the combat fixture must carry skills")
        _inject_snapshot(
            page,
            {
                "context_actions": combat,
                "local_map": valid_local_map_panel(),
            },
            mode="combat",
        )
        _wait_mode(page, "combat")

        # The combat root tab bar (depth 1) carries the listbox composite +
        # the dock-menu testid, a single tab stop, and the active-descendant.
        tab_bar = page.locator('[data-testid="dock-menu"]')
        self.assertEqual(tab_bar.count(), 1, "the combat root tab bar carries the dock-menu hook at depth 1")
        self.assertEqual(tab_bar.get_attribute("role"), "listbox")
        self.assertEqual(tab_bar.get_attribute("tabindex"), "0")
        self.assertIsNotNone(tab_bar.get_attribute("aria-activedescendant"))
        tabs = page.locator("#action-dock .dock-tab-bar [data-item-key]")
        self.assertGreaterEqual(tabs.count(), 5, "the combat root renders one tab per root item")

        # The 技能 tab carries the exact committed count; no other combat tab
        # carries a badge.
        skills_badge = page.locator("#dock-tab-skills .dock-tab-bar__badge")
        self.assertEqual(skills_badge.count(), 1, "the 技能 tab carries a badge")
        self.assertEqual(
            skills_badge.inner_text(),
            str(skill_count),
            "the 技能 badge equals the committed skill-descriptor count",
        )
        for key in ("attack", "items", "defend", "flee", "forfeit", "bag"):
            self.assertEqual(
                page.locator("#dock-tab-%s .dock-tab-bar__badge" % key).count(),
                0,
                "no combat tab other than 技能 carries a badge (%s)" % key,
            )

        # Each tab carries a leading glyph + its server-authored label.
        focused = page.locator("#action-dock .dock-tab-bar__tab--on").first
        self.assertEqual(
            focused.locator("svg.dock-tab-bar__icon").count(),
            1,
            "each tab carries a decorative glyph",
        )

        # Exploration renders no root tab bar: the scene overview owns the
        # dock's rows instead.
        exploration = _exploration_panel([_interact_target(11, "小販")])
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        self.assertEqual(
            page.locator("#action-dock .dock-tab-bar").count(),
            0,
            "exploration renders no root tab bar",
        )
        self.assertEqual(
            page.locator('[data-testid="scene-overview"]').count(),
            1,
            "the exploration root is the scene overview",
        )

    @covers_requirement(
        "webclient-contextual-hud::a-breadcrumb-derived-from-the-router-names-the-player-s-position-at-depth"
    )
    def test_breadcrumb_tracks_router_depth(self):
        """The breadcrumb appears only below the root and names parent + current frames."""
        page = self.logged_in_page()
        exploration = _exploration_panel(
            [_interact_target(11, "小販"), _interact_target(12, "守門人")]
        )
        context_actions = _exploration_context_actions_panel(
            _suggestions_ready(["查看四周", "查看物品", "查看角色"])
        )
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": context_actions,
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")

        crumb = page.locator('[data-testid="dock-crumb"]')
        # At the root frame (depth 1) the breadcrumb is hidden.
        self.assertTrue(
            crumb.evaluate("el => el.hidden || getComputedStyle(el).display === 'none'"),
            "no breadcrumb is rendered at the root frame",
        )

        # Open a person chip's verb popover: the breadcrumb appears naming
        # parent + current (webclient-scene-overview-swap: the popover is the
        # overview's one child frame).
        activate_overview_chip(page, "target-11")
        page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
        self.assertEqual(
            _dock_depth(page),
            2,
            "opening the popover puts the router at depth 2",
        )
        self.assertFalse(
            crumb.evaluate("el => el.hidden || getComputedStyle(el).display === 'none'"),
            "the breadcrumb is visible at depth >= 2",
        )
        crumb_text = crumb.inner_text()
        self.assertIn("場景", crumb_text, "the breadcrumb names the parent frame")
        self.assertIn("小販", crumb_text, "the breadcrumb names the current frame")

        # The back control pops exactly one level and dispatches no ui_action.
        install_outbound_recorder(page)
        crumb.locator(".dock-crumb__back").click()
        page.wait_for_timeout(150)
        self.assertEqual(
            _dock_depth(page),
            1,
            "the back control pops exactly one router level",
        )
        self.assertTrue(
            crumb.evaluate("el => el.hidden || getComputedStyle(el).display === 'none'"),
            "the breadcrumb hides again after popping one level",
        )
        self.assertEqual(sent_action_count(page), 0, "the back control dispatches no ui_action")

    @covers_requirement(
        "webclient-contextual-hud::the-dock-s-shortcut-legend-names-only-real-keyboard-behaviour-and-renders-as-one-visible-instance"
    )
    def test_digit_keys_pick_the_first_four_rows_of_the_current_frame(self):
        """`數字鍵 1–4` is real behaviour: a digit moves the dock focus onto
        the Nth row of the current frame and runs it exactly like Enter; a
        digit whose row does not exist is unclaimed (webclient-align-01)."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        exploration = _exploration_panel(
            [_interact_target(11, "小販")],
            move_rows=[
                _move_row("ex-a", "東門", "room:44"),
                _move_row("ex-b", "北門", "room:45", enabled=False),
                _move_row("ex-c", "南門", "room:46"),
            ],
        )
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")

        # Mount the retired move-outlet frame by a direct push
        # (webclient-scene-overview-swap: the dock root is the scene overview,
        # so no keyboard or pointer path reaches it any more): the outlet pane
        # renders the three exit rows (the breadcrumb back cell is navigation
        # chrome, never a rendered row), so the digit slots are exactly
        # [ex-a, ex-b, ex-c].
        push_exploration_frame(page, "exploration.move")
        self.assertEqual(_dock_depth(page), 2, "the move frame is at depth 2")

        # `2` picks the second row (a disabled row): the focus moves onto it
        # and nothing submits — a stable state with no server commit to race.
        _press(page, "2")
        self.assertEqual(
            store_state(page)["focus"]["key"],
            "exit-ex-b",
            "digit 2 moved the focus onto the second row",
        )
        self.assertEqual(
            sent_action_count(page),
            0,
            "a disabled picked row shows its explanation and submits nothing",
        )

        # `4` is beyond the rendered rows: unclaimed, the frame stays open,
        # nothing submits (the back cell takes no digit slot here — the
        # breadcrumb chevron owns the close control).
        _press(page, "4")
        self.assertEqual(
            _dock_depth(page),
            2,
            "a digit beyond the outlet's rendered rows leaves the frame open",
        )
        self.assertEqual(sent_action_count(page), 0, "the unclaimed digit submits nothing")

        # The frame stayed open: `1` picks the first rendered row and
        # submits its move exactly as Enter would — the proof is the
        # OUTBOUND envelope (the fabricated exit_ref is the server's
        # problem, not the client's; the commit's authoritative panel
        # replace is intentionally not asserted, so the assertion cannot
        # race it).
        _press(page, "1")
        moves = [
            args[0]
            for cmdname, args, _kwargs in outbound_messages(page)
            if cmdname == "ui_action" and args and args[0].get("action_id") == "explore.move"
        ]
        self.assertEqual(
            [m.get("payload", {}).get("exit_ref") for m in moves],
            ["ex-a"],
            "digit 1 submitted exactly the first row's move, once",
        )

        # A digit with no such row is unclaimed: the bridge does not prevent
        # its default (dispatchEvent returns false only when a listener
        # cancelled the event).
        unclaimed = page.evaluate(
            """() => {
          const event = new KeyboardEvent("keydown", { key: "9", bubbles: true, cancelable: true });
          document.dispatchEvent(event);
          return !event.defaultPrevented;
        }"""
        )
        self.assertTrue(unclaimed, "a digit beyond the frame's rows is not claimed")

    @covers_requirement(
        "webclient-contextual-hud::dock-panes-render-a-per-kind-vocabulary-from-backed-fields-only"
    )
    def test_dock_panes_render_per_kind_vocabulary(self):
        """Dock panes render a per-kind vocabulary from backed fields only."""
        page = self.logged_in_page()
        exploration = _exploration_panel(
            interact_targets=[],
            move_rows=[
                _move_row("1", "南", "grid:capital_altoria:2:1"),
                _move_row("2", "南門", "grid:capital_altoria:9:9"),
            ],
        )
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel(
                    {"status": "unavailable"}
                ),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")

        # Mount the retired move-outlet frame by a direct push
        # (webclient-scene-overview-swap: the dock root is the scene overview,
        # so the move submenu is reachable only through the router's push
        # entry until webclient-retire-exploration-submenus deletes it).
        push_exploration_frame(page, "exploration.move")
        self.assertEqual(_dock_depth(page), 2)

        # The move frame renders the exit outlet vocabulary.
        outlet = page.locator('[data-testid="dock-menu"]')
        tiles = outlet.locator(".dock-menu__outlet-tile")
        self.assertEqual(tiles.count(), 2, "the move frame renders one row per exit")
        # Row 1: the canonical "南" (south) direction resolves to a glyph,
        # and the destination's display name is the tile's primary bold text
        # (outlet-tile-presentation) — the raw exit label no longer renders
        # as a separate headline.
        first = tiles.nth(0)
        first_text = first.inner_text()
        self.assertIn("↓", first_text, "the canonical direction renders its glyph")
        self.assertEqual(
            first.locator("b").inner_text(),
            "南大道",
            "the destination's display name is the tile's primary bold text",
        )
        self.assertEqual(
            first.locator("small").count(),
            0,
            "no destination sub-line renders beside the headline",
        )
        # The first exit is focused when the move frame opens; its focused
        # state is a background + border + color swap (never color alone)
        # with no second, focus-only caret glyph stacked on the tile's
        # persistent direction glyph.
        self.assertTrue(
            "dock-menu__outlet-tile--focused" in (first.get_attribute("class") or ""),
            "the first exit is focused when the move frame opens",
        )
        focused_before = first.evaluate("el => getComputedStyle(el, '::before').content")
        unfocused_before = tiles.nth(1).evaluate("el => getComputedStyle(el, '::before').content")
        self.assertIn(
            focused_before,
            ("normal", "none"),
            "the focused tile renders no ::before caret content",
        )
        self.assertEqual(
            focused_before,
            unfocused_before,
            "the focused tile's ::before content is not distinct from an unfocused one",
        )
        # Row 2: a non-canonical door "南門" renders verbatim (no guessed direction),
        # and its destination node is absent from the committed lattice (no name).
        second = tiles.nth(1)
        second_text = second.inner_text()
        self.assertIn("南門", second_text, "a non-canonical exit label renders verbatim in the glyph slot")
        self.assertNotIn("grid:capital_altoria:9:9", second_text)
        # Rows render only backed fields: no statistics line or portrait slot.
        self.assertEqual(
            outlet.locator(".dock-menu__nav-sub").count(),
            0,
            "the pane renders no statistics line or portrait the payload does not carry",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size"
    )
    def test_verb_popover_card_lies_inside_the_command_region(self):
        """The verb popover is a card INSIDE the command region, and the
        region's box is unchanged from the overview (webclient-scene-overview-
        swap D3: the popover overlays the region's visible box)."""
        measure = """() => {
          const rect = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
          };
          return {
            region: rect('[data-testid="anchor-band-command"]'),
            card: rect('[data-testid="verb-popover"]'),
            pane: rect('#action-dock .action-dock__pane'),
            band: rect('[data-testid="stage-band"]'),
          };
        }"""
        page = self.logged_in_page((1440, 900))
        exploration = _exploration_panel([_interact_target(11, "小販")])
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        overview = page.evaluate(measure)

        activate_overview_chip(page, "target-11")
        page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
        popover = page.evaluate(measure)

        # The card lies inside the command region at every edge.
        card, region = popover["card"], popover["region"]
        self.assertIsNotNone(card, "the verb popover card must render")
        self.assertGreaterEqual(card["left"], region["left"] - 1.0)
        self.assertGreaterEqual(card["top"], region["top"] - 1.0)
        self.assertLessEqual(card["right"], region["right"] + 1.0)
        self.assertLessEqual(card["bottom"], region["bottom"] + 1.0)
        # The region (and the band) keep the overview's box exactly.
        for key in ("region", "band"):
            for edge in ("left", "top", "right", "bottom"):
                self.assertAlmostEqual(
                    popover[key][edge],
                    overview[key][edge],
                    delta=1.0,
                    msg="the %s box moved when the popover opened (%s)" % (key, edge),
                )
        # The card lies inside the pane's visible box: it is laid OVER the
        # region (the overlay layer), never appended below the pane.
        pane = popover["pane"]
        self.assertGreaterEqual(card["left"], pane["left"] - 1.0)
        self.assertGreaterEqual(card["top"], pane["top"] - 1.0)
        self.assertLessEqual(card["right"], pane["right"] + 1.0)
        self.assertLessEqual(card["bottom"], pane["bottom"] + 1.0)
