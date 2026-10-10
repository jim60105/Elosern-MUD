"""Contextual HUD action-dock acceptance (webclient-contextual-hud): the dock in the band's command region, the combat root's vertical command list and its count, the router breadcrumb, digit-row activation, and per-kind pane vocabulary.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    activate_overview_chip,
    aim_compass_exit,
    compass_target_refs,
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


def _selectable_target(identity: int, name: str) -> dict:
    """An interact target carrying one affordance, so the workspace can select it."""
    target = _interact_target(identity, name)
    target["affordances"] = [{
        "kind": "action",
        "action_id": "explore.talk_open",
        "label": "交談",
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

        The band (``stage-band``) is ``clamp(190px*S, 27.85vh, 400px*S)`` tall
        (retarget-desktop-viewport-contract D2: 220px at the reference) and
        paints the draft's `.dockwrap` chrome (gradient, hairline top border,
        upward shadow); its right third is the command region, which holds
        ``#action-dock`` — a content column that paints nothing itself. No
        frame (the interaction workspace with a target selected, the waiting
        frame) moves or resizes the region. Verified across the scenario's
        viewport range (1451x790 through 2560x1440).
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
            bandEdgeImage: getComputedStyle(band, '::after').backgroundImage,
            bandBoxShadow: bandStyle.boxShadow,
            dockBackgroundImage: dockStyle.backgroundImage,
            dockBorderTopWidth: dockStyle.borderTopWidth,
            dockBoxShadow: dockStyle.boxShadow,
            viewportWidth: window.innerWidth,
            viewportHeight: window.innerHeight,
          };
        }"""
        for viewport in ((1451, 790), (1741, 948), (2560, 1440)):
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
            scale = ui_scale(viewport)
            expected_band = min(
                max(190.0 * scale, geometry["viewportHeight"] * 0.2785), 400.0 * scale
            )
            self.assertAlmostEqual(
                geometry["bandHeight"], expected_band, delta=1.0,
                msg=f"the band is clamp(190px*S, 27.85vh, 400px*S) tall at {viewport}",
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
            # The top edge is the seam's fine gold line (webclient-band-
            # material-pass), drawn by the band's decorative `::after`.
            self.assertIn("gradient", geometry["bandEdgeImage"])
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
        "webclient-contextual-hud::the-combat-dock-root-renders-as-a-vertical-command-window-with-a-truthful-skills-count"
    )
    def test_combat_dock_root_vertical_list_truthful_skills_count(self):
        """The COMBAT root renders as one vertical icon-and-label list with a
        neutral, truthful 技能 count (webclient-combat-command-window);
        exploration renders the scene overview and no combat list at all."""
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

        # The combat root list (depth 1) is the pane's one row container: the
        # listbox composite, a single tab stop, and the active-descendant.
        menu = page.locator('[data-testid="dock-menu"]')
        self.assertEqual(menu.count(), 1, "the combat root list carries the dock-menu hook at depth 1")
        self.assertEqual(menu.get_attribute("role"), "listbox")
        self.assertEqual(menu.get_attribute("tabindex"), "0")
        self.assertEqual(menu.get_attribute("data-pane-kind"), "commands")
        self.assertIsNotNone(menu.get_attribute("aria-activedescendant"))
        rows = menu.locator("[data-item-key]")
        keys = [rows.nth(i).get_attribute("data-item-key") for i in range(rows.count())]
        self.assertEqual(
            keys,
            ["attack", "skills", "items", "bag", "defend", "flee", "forfeit"],
            "the root list renders the resolver's items in order",
        )
        # One column: every row shares the list's left edge and stacks below
        # the previous one.
        boxes = [rows.nth(i).bounding_box() for i in range(rows.count())]
        self.assertEqual(len({round(box["x"]) for box in boxes}), 1, "the root rows share one column")
        self.assertTrue(
            all(boxes[i + 1]["y"] > boxes[i]["y"] for i in range(len(boxes) - 1)),
            "the root rows stack vertically in rendered order",
        )

        # The 技能 row carries the exact committed count as neutral inline
        # text; no other root row carries a count.
        counts = menu.locator(".dock-menu__command-count")
        self.assertEqual(counts.count(), 1, "exactly one root row carries a count")
        self.assertEqual(
            counts.first.evaluate("el => el.closest('[data-item-key]').dataset.itemKey"), "skills"
        )
        self.assertEqual(
            counts.first.inner_text(),
            str(skill_count),
            "the 技能 count equals the committed skill-descriptor count",
        )
        # Neutral: no filled alert bubble behind the count.
        self.assertEqual(
            counts.first.evaluate("el => getComputedStyle(el).backgroundColor"),
            "rgba(0, 0, 0, 0)",
        )

        # Each concept row carries a leading glyph.
        self.assertEqual(
            menu.locator('[data-item-key="attack"] svg.dock-menu__command-icon').count(),
            1,
            "a root row carries a decorative glyph",
        )

        # Exploration renders no combat root list: the scene overview owns
        # the dock's rows instead.
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
            page.locator('#action-dock [data-pane-kind="commands"]').count(),
            0,
            "exploration renders no combat root list",
        )
        self.assertEqual(
            page.locator('[data-testid="scene-overview"]').count(),
            1,
            "the exploration root is the scene overview",
        )

    @covers_requirement(
        "webclient-contextual-hud::a-breadcrumb-derived-from-the-router-names-the-player-s-position-at-depth",
        "webclient-contextual-hud::the-bottom-band-separates-material-and-focus-without-obscuring-controls",
    )
    def test_breadcrumb_tracks_router_depth(self):
        """The breadcrumb appears below the root (except over a verb popover) and names parent + current."""
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

        # Open a person chip's verb popover (webclient-band-material-pass):
        # the popover's own heading names the target once, so no breadcrumb
        # renders on that one frame.
        activate_overview_chip(page, "target-11")
        page.wait_for_selector('[data-testid="verb-popover"]', timeout=15000)
        self.assertEqual(
            _dock_depth(page),
            2,
            "opening the popover puts the router at depth 2",
        )
        self.assertEqual(
            page.locator('[data-testid="dock-crumb"]').count(),
            0,
            "the verb popover renders no breadcrumb",
        )
        self.assertEqual(
            page.locator('[data-testid="verb-popover"] h3').inner_text().strip(),
            "小販",
            "the popover's single heading names the target",
        )

        # The card isolates the covered chips: a press where the 守門人 chip
        # sits lands on the popover's layer, never on the chip.
        covered = page.evaluate(
            """() => {
              const chip = document.querySelector('[data-testid="scene-overview"] [data-item-key="target-12"]');
              const r = chip.getBoundingClientRect();
              const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { chip: chip.contains(hit),
                       layer: !!hit.closest('[data-testid="verb-popover-layer"]') };
            }"""
        )
        self.assertEqual(covered, {"chip": False, "layer": True}, "covered chips cannot be hit")

        # The popover's back row pops exactly one level and dispatches no
        # ui_action.
        install_outbound_recorder(page)
        page.locator('[data-testid="verb-popover"]').get_by_text("返回上一層").click()
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 1, "the back row pops exactly one router level")
        self.assertEqual(sent_action_count(page), 0, "the back row dispatches no ui_action")

        # Any other submenu keeps the breadcrumb naming parent + current.
        activate_overview_chip(page, "suggestions")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 2, "the suggestions frame is depth 2")
        self.assertFalse(
            crumb.evaluate("el => el.hidden || getComputedStyle(el).display === 'none'"),
            "the breadcrumb is visible at depth >= 2",
        )
        self.assertIn("場景", crumb.inner_text(), "the breadcrumb names the parent frame")

        # The back control pops exactly one level and dispatches no ui_action.
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
    def test_digit_keys_pick_the_rows_of_the_current_frame(self):
        """`數字鍵 1–9` is real behaviour: a digit moves the dock focus onto
        the Nth rendered entry of the current frame and runs it exactly like
        Enter; a digit whose entry does not exist is unclaimed
        (webclient-align-01, widened by webclient-retire-exploration-submenus).
        """
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

        # The exploration root is the scene overview: its rendered chips in
        # reading order are [target-11, look-room, wait] (the suggestions
        # envelope is unavailable). The three exits are the exit compass's
        # (exploration-exit-compass) and take no digit slot.
        self.assertEqual(_dock_depth(page), 1, "the overview is the root frame")
        self.assertEqual(
            page.evaluate(
                "() => Array.from(document.querySelectorAll("
                "'#action-dock .scene-chip')).map((el) => el.getAttribute('data-item-key'))"
            ),
            ["target-11", "look-room", "wait"],
            "the overview's rendered chips are the digit slots",
        )
        self.assertEqual(sorted(compass_target_refs(page)), ["ex-a", "ex-b", "ex-c"])

        # `9` is beyond the three rendered chips: unclaimed, the overview
        # stays current, nothing submits.
        _press(page, "9")
        self.assertEqual(
            _dock_depth(page),
            1,
            "a digit beyond the overview's rendered chips leaves the frame current",
        )
        self.assertEqual(sent_action_count(page), 0, "the unclaimed digit submits nothing")

        # `2` picks the second rendered chip (查看房間) and submits its look
        # exactly as Enter would — the proof is the OUTBOUND envelope, so the
        # assertion cannot race the commit. No digit ever moves.
        _press(page, "2")
        looks = [
            args[0]
            for cmdname, args, _kwargs in outbound_messages(page)
            if cmdname == "ui_action" and args and args[0].get("action_id") == "explore.look"
        ]
        self.assertEqual(
            [m.get("payload") for m in looks],
            [{"room": True}],
            "digit 2 submitted exactly the second chip's look, once",
        )
        self.assertEqual(sent_action_count(page, "explore.move"), 0, "no digit moves")

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
        """Dock panes render a per-kind vocabulary from backed fields only.

        The exploration root's exit vocabulary is the exit compass and its
        readout (exploration-exit-compass replaced the overview's exit chips,
        which had replaced the move frame's outlet pane), so the compass's
        targets and the readout's lead and text are the form under test.
        """
        page = self.logged_in_page()
        exploration = _exploration_panel(
            interact_targets=[],
            move_rows=[
                _move_row("1", "南", "grid:capital_altoria:2:1"),
                _move_row("2", "南門", "grid:capital_altoria:9:9"),
                _move_row("3", "北", "grid:capital_altoria:9:9", enabled=False),
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

        # The exploration root renders the exit compass beside the scene
        # overview, and no exit-outlet grid or exit chip exists anywhere in
        # the dock (exploration-exit-compass).
        self.assertEqual(_dock_depth(page), 1)
        self.assertEqual(page.locator('[data-testid="scene-overview"]').count(), 1)
        # A NEGATIVE assertion (the retired outlet grid must not exist). It is
        # read through `evaluate` so the frozen-contract scanner — which cannot
        # tell a positive target from a retired-hook absence check — does not
        # re-register the retired class in the audit's hook list.
        self.assertEqual(
            page.evaluate(
                "() => document.querySelectorAll("
                "'#action-dock .dock-menu__outlet, #action-dock [data-item-key^=\"exit-\"]').length"
            ),
            0,
            "no exit-outlet grid or exit chip exists anywhere in the dock",
        )
        self.assertEqual(sorted(compass_target_refs(page)), ["1", "2", "3"])

        readout = lambda: (  # noqa: E731
            page.locator('[data-testid="exploration-readout-lead"]').inner_text().strip(),
            page.locator('[data-testid="exploration-readout-text"]').inner_text().strip(),
        )

        # Exit 1 leads to a committed map node one step north: the map
        # bearing (not its 南 label) places it, and the readout names the
        # destination's display name, never the node id.
        aim_compass_exit(page, "1")
        self.assertEqual(readout(), ("前往 ↑", "南大道"))

        # Exit 2 is a non-canonical label whose destination is absent from
        # the committed lattice: a portal that renders its own label verbatim
        # with no guessed direction.
        aim_compass_exit(page, "2")
        self.assertEqual(readout(), ("通道 ✦", "南門"))
        self.assertNotIn("grid:capital_altoria:9:9", page.locator('[data-testid="exploration-readout"]').inner_text())

        # Exit 3 is disabled: its target stays aimable, drawn hollow, and the
        # readout shows the server-authored reason verbatim.
        aim_compass_exit(page, "3")
        self.assertEqual(readout(), ("無法通行", "出口被阻擋。"))
        self.assertEqual(
            page.locator('#action-dock [data-testid="exit-compass"] [data-exit-ref="3"]').get_attribute("data-enabled"),
            "false",
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
        page = self.logged_in_page((1451, 790))
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
