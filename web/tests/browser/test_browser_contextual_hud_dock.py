"""Contextual HUD action-dock acceptance (webclient-contextual-hud): the floating dock panel, tab-bar count badges, the router breadcrumb, digit-row activation, and per-kind pane vocabulary.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    outbound_messages,
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


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    @covers_requirement(
        "webclient-contextual-hud::the-action-dock-renders-as-a-floating-panel-in-the-stage-s-dock-anchor"
    )
    def test_action_dock_floating_panel_persists_across_modes(self):
        """The dock band paints the full stage width; the content column is
        centred inside it (webclient-align-01-dock-chrome).

        The painted chrome (the draft's `.dockwrap` gradient, hairline top
        border, upward shadow, and padding) belongs to the full-width dock
        ANCHOR; `#action-dock` is the centred max-width-1180 content column
        (the draft's `.dock`) and paints nothing itself. Verified across the
        scenario's viewport range (1280x720 through 1920x1080).
        """
        for viewport in ((1280, 720), (1600, 900), (1920, 1080)):
            page = self.logged_in_page(viewport)
            exploration = _exploration_panel([_interact_target(11, "小販")])
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
            self.assertTrue(dock.is_visible(), "the floating dock panel is visible")
            page.evaluate(
                "() => { const d = document.querySelector('#action-dock'); d.__tracked = true; }"
            )

            geometry = page.evaluate(
                """() => {
                  const dock = document.querySelector('#action-dock');
                  const anchor = document.querySelector('[data-testid="anchor-dock"]');
                  const d = dock.getBoundingClientRect();
                  const a = anchor.getBoundingClientRect();
                  const style = getComputedStyle(dock);
                  const anchorStyle = getComputedStyle(anchor);
                  return {
                    dockLeft: d.left, dockWidth: d.width, dockHeight: d.height,
                    anchorLeft: a.left, anchorWidth: a.width, anchorHeight: a.height,
                    maxWidth: style.maxWidth,
                    dockBackgroundImage: style.backgroundImage,
                    dockBorderTopWidth: style.borderTopWidth,
                    dockBoxShadow: style.boxShadow,
                    borderTopWidth: anchorStyle.borderTopWidth,
                    backgroundImage: anchorStyle.backgroundImage,
                    boxShadow: anchorStyle.boxShadow,
                    padTop: parseFloat(anchorStyle.paddingTop),
                    padBottom: parseFloat(anchorStyle.paddingBottom),
                    viewportWidth: window.innerWidth,
                  };
                }"""
            )
            # The desktop redesign re-tenanted the dock anchor from the
            # full-width draft band to the spec's floating panel
            # (webclient-desktop-shell: "a floating panel bounded to a
            # maximum width and centred in the stage's dock anchor";
            # app-shell.css .elosern-root [data-anchor="dock"] left: 35%).
            self.assertAlmostEqual(
                geometry["anchorLeft"],
                float(geometry["viewportWidth"]) * 0.35,
                delta=1.0,
                msg=f"the dock anchor is the workspace's left-anchored panel at {viewport}",
            )
            self.assertLess(
                geometry["anchorWidth"],
                float(geometry["viewportWidth"]),
                f"the dock anchor is a bounded panel, not the full-width band, at {viewport}",
            )
            self.assertIn(
                "gradient",
                geometry["backgroundImage"],
                f"the band paints the draft's gradient at {viewport}",
            )
            self.assertTrue(
                geometry["borderTopWidth"].startswith("1px"),
                "the panel carries the --line hairline border",
            )
            self.assertIn(
                "inset",
                geometry["boxShadow"],
                "the panel carries the redesign's inset highlight",
            )
            # The panel is horizontally centred within the anchor.
            self.assertLess(
                abs((geometry["dockLeft"] + geometry["dockWidth"] / 2)
                    - (geometry["anchorLeft"] + geometry["anchorWidth"] / 2)),
                4.0,
                f"the dock must be centred within the dock anchor at {viewport}",
            )
            self.assertLessEqual(
                geometry["dockWidth"],
                min(1180.0, geometry["anchorWidth"]),
                f"the content column stays inside max-width 1180 at {viewport}",
            )
            self.assertEqual(geometry["maxWidth"], "1180px")
            # The content column paints nothing: the band owns the chrome.
            self.assertEqual(geometry["dockBackgroundImage"], "none")
            self.assertEqual(geometry["dockBorderTopWidth"], "0px")
            self.assertEqual(geometry["dockBoxShadow"], "none")
            # The band's border-box height is the --dock-h token (the anchor
            # is border-box: height = token); the content column fills the
            # band's padded content box (vertical padding + border subtract).
            self.assertAlmostEqual(
                geometry["dockHeight"],
                geometry["anchorHeight"]
                - geometry["padTop"]
                - geometry["padBottom"]
                - 2.0,
                places=1,
                msg=f"the content column fills the band's padded box at {viewport}",
            )
            # The panel stays inside the anchor's box.
            self.assertGreaterEqual(geometry["dockLeft"], geometry["anchorLeft"])
            self.assertLessEqual(
                geometry["dockLeft"] + geometry["dockWidth"],
                geometry["anchorLeft"] + geometry["anchorWidth"],
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
        "webclient-contextual-hud::the-dock-s-root-frame-renders-as-an-icon-tab-bar-with-truthful-count-badges"
    )
    def test_dock_root_tab_bar_truthful_count_badges(self):
        """The root frame renders as an icon tab bar with truthful count badges."""
        page = self.logged_in_page()
        exploration = _exploration_panel(
            [_interact_target(11, "小販"), _interact_target(12, "守門人")]
        )
        context_actions = _exploration_context_actions_panel(
            _suggestions_ready(["查看四周", "查看物品", "查看角色", "查看任務"])
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

        # The root tab bar (depth 1) carries the listbox composite + the
        # dock-menu testid, a single tab stop, and the active-descendant.
        tab_bar = page.locator('[data-testid="dock-menu"]')
        self.assertEqual(tab_bar.count(), 1, "the root tab bar carries the dock-menu hook at depth 1")
        self.assertEqual(tab_bar.get_attribute("role"), "listbox")
        self.assertEqual(tab_bar.get_attribute("tabindex"), "0")
        self.assertIsNotNone(tab_bar.get_attribute("aria-activedescendant"))
        tabs = page.locator("#action-dock [data-item-key]")
        self.assertGreaterEqual(tabs.count(), 5, "the root frame renders one tab per root item")

        # Truthful count badges: interact tab = 2 (interact target count),
        # suggestions tab = 4 (ready-card count); move and look carry no badge.
        interact_badge = page.locator("#dock-tab-interact .dock-tab-bar__badge")
        self.assertEqual(interact_badge.count(), 1, "the interact tab carries a badge")
        self.assertEqual(interact_badge.inner_text(), "2", "the interact badge equals the target count")
        sugg_badge = page.locator("#dock-tab-suggestions .dock-tab-bar__badge")
        self.assertEqual(sugg_badge.count(), 1, "the suggestions tab carries a badge")
        self.assertEqual(sugg_badge.inner_text(), "4", "the suggestions badge equals the ready-card count")
        self.assertEqual(
            page.locator("#dock-tab-move .dock-tab-bar__badge").count(),
            0,
            "the move tab carries no badge",
        )
        self.assertEqual(
            page.locator("#dock-tab-look .dock-tab-bar__badge").count(),
            0,
            "the look tab carries no badge",
        )

        # Each tab carries a leading glyph + its server-authored label.
        focused = page.locator("#action-dock .dock-tab-bar__tab--on").first
        self.assertEqual(
            focused.locator("svg.dock-tab-bar__icon").count(),
            1,
            "each tab carries a decorative glyph",
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

        # Open the interact submenu: the breadcrumb appears naming parent + current.
        focus_action_dock(page)
        page.locator("#dock-tab-interact").click()
        page.wait_for_timeout(150)
        self.assertEqual(
            _dock_depth(page),
            2,
            "opening a submenu puts the router at depth 2",
        )
        self.assertFalse(
            crumb.evaluate("el => el.hidden || getComputedStyle(el).display === 'none'"),
            "the breadcrumb is visible at depth >= 2",
        )
        crumb_text = crumb.inner_text()
        self.assertIn("探索", crumb_text, "the breadcrumb names the parent frame")
        self.assertIn("互動", crumb_text, "the breadcrumb names the current frame")

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

        # Open the move frame: the outlet pane renders the three exit rows
        # (the breadcrumb back cell is navigation chrome, never a rendered
        # row), so the digit slots are exactly [ex-a, ex-b, ex-c].
        focus_action_dock(page)
        page.locator("#dock-tab-move").click()
        page.wait_for_timeout(150)
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

        # Open the move frame: the first root item is "move".
        focus_action_dock(page)
        _press(page, "Enter")
        page.wait_for_timeout(150)
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
