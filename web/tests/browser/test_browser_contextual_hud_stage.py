"""Contextual HUD stage acceptance (webclient-contextual-hud): the mode-gated stage, the truthful scene backdrop, the bounded narrative caption/full log, drawer/overlay stage recession, the island affordance, and the command-line/dock clearance.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    open_command_line,
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
    _exploration_panel,
    _exploration_context_actions_panel,
    _art_panel,
    _combat_panel,
    _SCENE_PNG_BYTES,
    _inject_snapshot,
    _wait_mode,
    _press,
)
from .harness import wait_command_field_released


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

_GALLERY_PANEL = {
    "schema_version": 1,
    "available": True,
    "kind": "gallery",
    "subjects": [
        {
            "subject_key": "portrait:character:7001",
            "kind": "portrait:character",
            "display_name": "夜行者",
            "is_puppet": True,
        }
    ],
    "selected": "portrait:character:7001",
    "filters": {"all": 0, "defaults": 0, "bound": 0, "pending": 0, "failed": 0},
    "capabilities": {
        "supports_bindings": True,
        "supports_field_selection": True,
        "supports_free_text": True,
        "max_cards": None,
    },
    "cards": [],
    "equipment_summary": {
        "weapon_main": {"value": None, "display_name": "未裝備"},
        "weapon_off": {"value": None, "display_name": "未裝備"},
        "armor": {"value": None, "display_name": "未裝備"},
        "accessories": {"value": [], "display_names": [], "equipped_count": 0},
    },
    "binding_warnings": [],
    "error_state": None,
}


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    @covers_requirement(
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode"
    )
    def test_surface_visibility_gated_by_committed_game_mode(self):
        """The stage exposes the committed mode and gates surface visibility on it."""
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        map_panel = valid_local_map_panel()
        _inject_snapshot(page, {"local_map": map_panel}, mode="exploration")
        _wait_mode(page, "exploration")

        self.assertEqual(
            stage.get_attribute("data-elosern-mode"),
            "exploration",
            "the stage root exposes the committed exploration mode",
        )
        minimap = page.locator('[data-testid="local-map"]')
        self.assertEqual(minimap.count(), 1, "the minimap island renders in exploration")
        self.assertTrue(minimap.is_visible(), "the minimap is visible in exploration")

        # webclient-collapsible-command-line: the command line starts collapsed
        # in exploration; `#inputfield` stays in the DOM but is hidden, and
        # the ⌨ toggle is visible with `aria-expanded="false"`.
        anchor = page.locator('[data-testid="anchor-command-line"]')
        toggle = page.locator('[data-testid="command-line-toggle"]')
        field = page.locator("#inputfield")
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        self.assertTrue(toggle.is_visible(), "the command-line toggle is visible in exploration")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertEqual(field.count(), 1, "the command field is present in exploration")
        self.assertFalse(field.is_visible(), "the command field starts collapsed in exploration")

        # Commit combat: the minimap is removed from the layout with
        # display:none (never merely dimmed); the command line stays collapsed.
        _inject_snapshot(page, {"local_map": map_panel}, mode="combat")
        _wait_mode(page, "combat")
        self.assertEqual(
            stage.get_attribute("data-elosern-mode"),
            "combat",
            "the stage root exposes the committed combat mode",
        )
        self.assertEqual(minimap.count(), 1, "the minimap element stays in the DOM in combat")
        hidden = page.evaluate(
            "() => { const el = document.querySelector('[data-testid=\"local-map\"]'); "
            "return el ? (el.offsetParent === null) : false; }"
        )
        self.assertTrue(hidden, "the minimap is display:none in combat, not merely dimmed")
        for selector in (
            '[data-testid="narrative-feed"]',
            '[data-testid="command-line-toggle"]',
            "#action-dock",
        ):
            self.assertTrue(
                page.locator(selector).is_visible(),
                f"{selector} must stay visible in combat",
            )
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertEqual(page.locator("#inputfield").count(), 1, "the command field is present in combat")
        self.assertFalse(
            page.locator("#inputfield").is_visible(),
            "the command field stays collapsed in combat",
        )

        # Commit dialogue: the toggle remains visible and the command line
        # stays collapsed until opened.
        _inject_snapshot(page, {"local_map": map_panel}, mode="dialogue")
        _wait_mode(page, "dialogue")
        self.assertTrue(toggle.is_visible(), "the command-line toggle is visible in dialogue")
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertFalse(field.is_visible(), "the command field stays collapsed in dialogue")

        # Expand the command line, then commit creation: focus is rescued to
        # the action dock, both the command line and its toggle are hidden in
        # creation, and returning to exploration starts collapsed.
        open_command_line(page)
        self.assertEqual(anchor.get_attribute("data-expanded"), "true")
        self.assertTrue(field.is_visible())

        _inject_snapshot(page, {"local_map": map_panel}, mode="creation")
        _wait_mode(page, "creation")
        self.assertEqual(
            stage.get_attribute("data-elosern-mode"),
            "creation",
            "the stage root exposes the committed creation mode",
        )
        field_absent = page.evaluate(
            "() => { const el = document.querySelector('#inputfield'); "
            "return el ? (el.offsetParent === null) : true; }"
        )
        self.assertTrue(field_absent, "the command field is absent (display:none) in creation mode")
        self.assertFalse(toggle.is_visible(), "the command-line toggle is hidden in creation mode")
        self.assertEqual(anchor.get_attribute("data-expanded"), "false")

        _inject_snapshot(page, {"local_map": map_panel}, mode="exploration")
        _wait_mode(page, "exploration")
        self.assertEqual(anchor.get_attribute("data-expanded"), "false", "returning from creation starts collapsed")
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertTrue(toggle.is_visible())
        self.assertFalse(field.is_visible(), "the command field is collapsed after returning from creation")

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    def test_scene_backdrop_renders_art_payload_truthfully(self):
        """The backdrop renders the committed art scene behind the stage."""
        page = self.logged_in_page()
        page.route(
            "**/art/scene.png",
            lambda route: route.fulfill(
                status=200, content_type="image/png", body=_SCENE_PNG_BYTES
            ),
        )
        art = _art_panel(["1", "2"])
        _inject_snapshot(page, {"art": art}, mode="exploration")
        _wait_mode(page, "exploration")

        # Read the committed scene URL straight from the DOM in a single
        # (existence + attribute) DOM read instead of `get_attribute`, which
        # auto-waits on the image element. The fixture URL is not a served art
        # asset, so the component's load-failure path (task 4.7) removes the
        # `<img>` from the DOM; a locator that waits for a removed element would
        # time out. A single evaluate that both checks presence and reads `src`
        # is race-free (no window in which the element can vanish mid-assertion).
        image_dom = page.evaluate(
            """() => { const el = document.querySelector('[data-testid="scene-backdrop-image"]');
              return { present: !!el, src: el ? el.getAttribute("src") : null }; }"""
        )
        self.assertTrue(
            image_dom["present"],
            "the done scene image renders behind the stage",
        )
        self.assertEqual(
            image_dom["src"],
            "/art/scene.png",
            "the backdrop renders the committed scene URL",
        )
        backdrop = page.locator('[data-testid="scene-backdrop"]')
        self.assertEqual(
            backdrop.get_attribute("data-scene-status"),
            "done",
            "the backdrop reports the committed scene status",
        )
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-label"]').inner_text(),
            "南門街道",
            "the scene label renders as text outside the bitmap",
        )
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-alt"]').inner_text(),
            "當前場景",
            "the scene alternative text renders as text outside the bitmap",
        )

        # The per-mode gradient stages are visually distinct (exploration vs
        # combat). The backdrop's inline background carries the mode token.
        explore_bg = page.evaluate(
            "() => document.querySelector('[data-testid=\"scene-backdrop\"]').style.background"
        )
        _inject_snapshot(page, {"art": art}, mode="combat")
        _wait_mode(page, "combat")
        combat_bg = page.evaluate(
            "() => document.querySelector('[data-testid=\"scene-backdrop\"]').style.background"
        )
        self.assertNotEqual(
            explore_bg,
            combat_bg,
            "the mode's gradient stage differs per mode (exploration vs combat)",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action"
    )
    def test_narrative_caption_bounded_full_log_one_action(self):
        """The narrative caption is bounded and the full log opens in one action."""
        page = self.logged_in_page()
        for line in ("南門的風很涼。", "你看到一隻哥布林。", "哥布林舉起了木棒。"):
            page.evaluate("(text) => window.__elosernBridge.store.appendText('out', text)", line)

        # The caption card is bounded: its rendered height never fills the stage.
        feed = page.locator('[data-testid="narrative-feed"]')
        self.assertTrue(feed.is_visible(), "the narrative caption card renders")
        geometry = page.evaluate(
            """() => {
              const f = document.querySelector('[data-testid="narrative-feed"]');
              const st = document.querySelector('[data-testid="elosern-stage"]');
              return {
                feedHeight: f.getBoundingClientRect().height,
                stageHeight: st.getBoundingClientRect().height,
              };
            }"""
        )
        self.assertLess(
            geometry["feedHeight"],
            geometry["stageHeight"],
            "the caption card is bounded, not filling the stage",
        )

        # webclient-avg-stage-shell (design D6): the caption fills the bottom
        # band's message region (its content box) and keeps that box however
        # many lines arrive.
        region_measure = """() => {
          // The caption card (the feed's scroll viewport sits inside it).
          const f = document.querySelector('[data-testid="narrative-feed"]')
            .closest('.elosern-narrative').getBoundingClientRect();
          const region = document.querySelector('[data-testid="anchor-band-message"]');
          const r = region.getBoundingClientRect();
          const cs = getComputedStyle(region);
          return {
            feed: [f.left, f.top, f.right, f.bottom],
            content: [
              r.left + parseFloat(cs.paddingLeft), r.top + parseFloat(cs.paddingTop),
              r.right - parseFloat(cs.paddingRight), r.bottom - parseFloat(cs.paddingBottom),
            ],
          };
        }"""
        before = page.evaluate(region_measure)
        for got, want in zip(before["feed"], before["content"]):
            self.assertAlmostEqual(got, want, delta=1.0, msg="the caption fills the message region")
        for index in range(40):
            page.evaluate(
                "(text) => window.__elosernBridge.store.appendText('out', text)",
                f"第 {index + 1} 行敘述。",
            )
        page.wait_for_timeout(120)
        after = page.evaluate(region_measure)
        for got, want in zip(after["feed"], before["feed"]):
            self.assertAlmostEqual(got, want, delta=1.0, msg="40 more lines leave the caption's box unchanged")

        # One action opens the complete log, rendered through the same renderer.
        page.locator('[data-testid="narrative-fulllog-control"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        overlay = page.locator('[data-testid="fulllog-overlay"]')
        self.assertTrue(overlay.is_visible(), "the full log opens in one action")
        log_text = overlay.inner_text()
        for line in ("南門的風很涼。", "你看到一隻哥布林。", "哥布林舉起了木棒。"):
            self.assertIn(line, log_text, "the full log shows the complete retained narrative")

        # Focus is trapped while the full log is open.
        focus_trapped = page.evaluate(
            "() => { const o = document.querySelector('[data-testid=\"fulllog-overlay\"]');"
            " const a = document.activeElement; return o && (o === a || o.contains(a)); }"
        )
        self.assertTrue(focus_trapped, "focus is trapped in the full log while open")

        # Escape closes the full log and restores focus to the control that opened it.
        _press(page, "Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"fulllog-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"]').count(),
            0,
            "the full log closes on Escape",
        )
        focus_restored = page.evaluate(
            "() => { const c = document.querySelector('[data-testid=\"narrative-fulllog-control\"]');"
            " const a = document.activeElement; return c && c === a; }"
        )
        self.assertTrue(focus_restored, "focus is restored to the control that opened the log")

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_open_drawer_or_overlay_dims_stage(self):
        """An open drawer or overlay recesses the stage; the mark clears only when all close.

        H5 (webclient-hud-05-overlays-and-command-line): the command drawer
        is replaced by the permanently-present command line (design D1), so
        the second open surface is now an H5 full-screen overlay (settings)
        opened through the store's overlay slice (design D8/D9).
        """
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "false",
            "the stage is not recessed while no surface is open",
        )

        # Open the full-log overlay: the stage behind it is recessed.
        page.locator('[data-testid="narrative-fulllog-control"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "an open overlay recesses the stage",
        )

        # Open the H5 settings overlay through the store's overlay slice: the
        # full-log overlay is an aria-modal dialog that intercepts pointer
        # events, so the overlay opens via the store's `openOverlay` (design
        # D8), not a pointer click on the command line's 設定 button.
        page.evaluate("window.__elosernBridge.store.openOverlay('settings')")
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "the stage stays recessed while two surfaces are open",
        )

        # Close the full log: the settings overlay remains open, so the stage
        # stays recessed.
        page.locator('[data-testid="fulllog-close"]').click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"fulllog-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "the stage stays recessed until the last open surface closes",
        )

        # Close the settings overlay (the shared overlay host's close button):
        # the recess mark clears.
        page.locator('[data-testid="overlay-host-close"]').click()
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "false",
            "the recess mark clears only when no drawer and no overlay remain open",
        )

    @covers_requirement(
        "webclient-contextual-hud::a-full-screen-overlay-is-one-focus-trapped-surface-and-only-one-is-open-at-a-time"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-map-settings-and-help-surfaces-are-reachable-from-the-live-client"
    )
    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_h5_overlay_triggers_exclusion_and_focus_restoration(self):
        """H5 overlay contract (task 8.7): each trigger opens exactly its own
        overlay; at most one overlay is open at a time (opening a second closes
        the first); Escape and the close control each restore focus to the
        trigger (the opener captured at open time); the stage recession mark
        is set while an overlay is open and clears when the last closes.
        """
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        _inject_snapshot(page, {"local_map": valid_local_map_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # Each of the three triggers opens exactly its own overlay.
        # settings trigger -> settings overlay.
        page.locator('[data-testid="nav-settings"]').click()
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "the settings overlay recesses the stage",
        )
        # Close it so the next trigger is reachable (the command line is behind
        # an open overlay).
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"settings-overlay\"]') === null",
            timeout=15000,
        )

        # help trigger -> help overlay.
        page.locator('[data-testid="nav-tool-help"]').click()
        page.wait_for_selector('[data-testid="help-overlay"]', timeout=15000)

        # Mutual exclusion: opening a second overlay closes the first (the store
        # keeps a single open-overlay name, design D8).
        page.evaluate("window.__elosernBridge.store.openOverlay('settings')")
        page.wait_for_selector('[data-testid="settings-overlay"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="help-overlay"]').count(),
            0,
            "opening settings closes the open help overlay (at most one overlay open)",
        )
        page.locator('[data-testid="overlay-host-close"]').click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"settings-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "false",
            "the recession mark clears when the last overlay closes",
        )

        # map trigger (the minimap island's 展開全地圖) -> map overlay; Escape
        # restores focus to that trigger (the opener captured at open time).
        page.locator('[data-testid="local-map__expand"]').click()
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "true",
            "the map overlay recesses the stage",
        )

        # webclient-full-map-fit-view D5/D3: the open map surface's only view
        # controls are the four toolbar buttons, each with its accessible
        # name; the guide row names the gestures; and no text on the surface
        # reads as a zoom-level or scale figure.
        for test_id, name in (
            ("map-overlay-zoom-out", "縮小"),
            ("map-overlay-zoom-in", "放大"),
        ):
            control = page.locator(f'[data-testid="{test_id}"]')
            self.assertEqual(control.count(), 1)
            self.assertEqual(control.get_attribute("aria-label"), name)
        recentre = page.locator('[data-testid="map-overlay-recentre"]')
        self.assertEqual(recentre.count(), 1)
        self.assertEqual(recentre.inner_text(), "置中")
        legend_toggle = page.locator('[data-testid="map-overlay-legend-toggle"]')
        self.assertEqual(legend_toggle.count(), 1)
        self.assertEqual(legend_toggle.get_attribute("aria-label"), "圖例")
        self.assertIn(
            "滾輪或 +／− 縮放 · 拖曳平移",
            page.locator('[data-testid="map-overlay"] .map-overlay__guide').inner_text(),
        )
        import re

        scale_figure = re.compile(r"\d+\s*%|×\s*\d")
        surface_text = page.locator('[data-testid="map-overlay"]').inner_text()
        self.assertIsNone(
            scale_figure.search(surface_text),
            f"the map surface shows a zoom/scale figure: {surface_text!r}",
        )

        # Two-Escape precedence (webclient-full-map-fit-view D5): with the
        # legend popover open, the FIRST Escape closes only the popover and
        # the overlay stays open; the second closes the overlay.
        page.locator('[data-testid="map-overlay-legend-toggle"]').click()
        page.wait_for_selector('[data-testid="map-overlay-legend-popover"]', timeout=15000)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"map-overlay-legend-popover\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            page.locator('[data-testid="map-overlay"]').count(), 1,
            "the first Escape closes only the legend popover, never the overlay",
        )

        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"map-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"),
            "false",
            "the recession mark clears after the map overlay closes",
        )
        self.assertEqual(
            page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
            "local-map__expand",
            "Escape restores focus to the map trigger that opened the overlay",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-minimap-island-states-only-its-own-drawing-convention"
    )
    def test_minimap_island_single_affordance_keyboard_and_movement(self):
        """Single full-map affordance contract (webclient-minimap-04-island-single-affordance):
        the island renders exactly one full-map affordance (a full-bleed button
        with 展開全地圖) and no visible button chrome in the header; pressing
        Enter on the focused affordance opens the overlay; activating an
        actionable lattice node moves without opening the overlay.
        """
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"local_map": valid_local_map_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        page.wait_for_selector('[data-testid="local-map"]', timeout=15000)

        # Axis/words coupling (Task 3.5):
        # On coordinate-bearing layer (lattice variant), orientation marks "北↑ 東→" are stated
        # and the island draws the axis cross.
        orientation = page.locator('[data-testid="local-map__orientation"]')
        self.assertEqual(orientation.count(), 1)
        self.assertIn("北↑ 東→", orientation.inner_text())
        self.assertEqual(page.locator('.local-map [data-testid="local-map__axis"]').count(), 1)

        # Exactly one affordance exists, carrying the accessible name.
        affordances = page.locator('[data-testid="local-map__expand"]')
        self.assertEqual(affordances.count(), 1)
        self.assertEqual(affordances.get_attribute("aria-label"), "展開全地圖")
        # No button in the header meta row.
        self.assertEqual(page.locator(".local-map__meta button").count(), 0)
        # Exactly one tab stop on the island in lattice variant
        self.assertEqual(
            page.evaluate("() => document.querySelectorAll('.local-map button, .local-map a, .local-map [tabindex]:not([tabindex=\"-1\"])').length"),
            1,
        )

        # Keyboard Enter on the focused affordance opens the map overlay.
        affordances.focus()
        page.keyboard.press("Enter")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        # The full-map overlay states no orientation marks and draws no axis cross
        self.assertEqual(page.locator('[data-testid="map-overlay"] [data-testid="local-map__orientation"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="map-overlay"] [data-testid="local-map__axis"]').count(), 0)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"map-overlay\"]') === null",
            timeout=15000,
        )

        # Activating an actionable lattice node moves without opening the overlay.
        actionable = page.locator('[data-testid="local-map__actionable"]')
        self.assertEqual(actionable.count(), 1)
        moves_before = sent_action_count(page, "explore.move")
        actionable.first.click()
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 0)
        self.assertEqual(
            sent_action_count(page, "explore.move"),
            moves_before + 1,
            "clicking an actionable lattice node dispatches one explore.move intent",
        )

        # Inject an interior graph payload with remembered nodes
        interior_payload = {
            "schema_version": 1,
            "available": True,
            "layer": "interior",
            "current_node": "room:201",
            "title": "公會大廳",
            "nodes": [
                {
                    "id": "room:201",
                    "label": "公會大廳",
                    "x": 0,
                    "y": 0,
                    "visibility": "current",
                    "current": True,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
                {
                    "id": "room:202",
                    "label": "訓練場",
                    "x": 1,
                    "y": 0,
                    "visibility": "visible_visited",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": {"kind": "move", "exit_ref": "e_hall_training", "destination": "room:202"},
                },
                {
                    "id": "room:203",
                    "label": "地下金庫",
                    "x": 0,
                    "y": 1,
                    "visibility": "remembered",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
            ],
            "edges": [
                {"source": "room:201", "destination": "room:202", "label": "訓練場", "known": True, "traversable": True},
            ],
            "legend": ["你目前所在的位置", "已經探索過的相鄰位置", "曾經到過、但不在附近的遠方位置"],
        }
        _inject_snapshot(page, {"local_map": interior_payload}, mode="exploration")
        page.wait_for_selector('[data-testid="local-map-remembered-mirror"]', state="attached", timeout=15000)
        self.assertEqual(page.locator('[data-testid="local-map-remembered"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="local-map-remembered-mirror"] li').count(), 1)
        # On coordinate-free layer (radial graph variant), orientation marks and axis are absent
        self.assertEqual(page.locator('[data-testid="local-map__orientation"]').count(), 0)
        self.assertEqual(page.locator('.local-map [data-testid="local-map__axis"]').count(), 0)
        # Island still offers exactly one tab stop (the affordance)
        self.assertEqual(
            page.evaluate("() => document.querySelectorAll('.local-map button, .local-map a, .local-map [tabindex]:not([tabindex=\"-1\"])').length"),
            1,
        )

    @covers_requirement(
        "webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge"
    )
    def test_command_line_never_overlaps_dock_caption_or_hud(self):
        """H5 (task 8.8): at every supported viewport and at each of the
        three prose-scale steps, the command line does not overlap the action
        dock, the narrative caption, the bottom band, or the HUD island
        anchors, and it sits on the band's top edge (webclient-avg-stage-shell
        design D3).
        """
        for viewport in ((1920, 1080), (1440, 900), (1280, 720)):
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
            open_command_line(page)
            for scale in (0.92, 1, 1.12):
                page.evaluate("(s) => window.__elosernBridge.store.setFontScale(s)", scale)
                geo = page.evaluate(
                    """() => {
                      const byId = (sel) => {
                        const el = document.querySelector(sel);
                        return el && el.getBoundingClientRect();
                      };
                      const cmd = byId('[data-testid="command-line"]');
                      if (!cmd) { return { hits: ["command-line missing"] }; }
                      const targets = {
                        dock: byId('#action-dock'),
                        caption: byId('[data-testid="narrative-feed"]'),
                        messageRegion: byId('[data-testid="anchor-band-message"]'),
                        vitals: byId('[data-testid="anchor-vitals"]'),
                        map: byId('[data-testid="anchor-map"]'),
                        band: byId('[data-testid="stage-band"]'),
                      };
                      const hits = [];
                      for (const key of Object.keys(targets)) {
                        if (key === "messageRegion") { continue; }
                        const b = targets[key];
                        if (!b) { continue; }
                        const overlap = !(
                          cmd.right <= b.left || b.right <= cmd.left ||
                          cmd.bottom <= b.top || b.bottom <= cmd.top
                        );
                        if (overlap) { hits.push(key); }
                      }
                      const band = targets.band;
                      if (band && Math.abs(cmd.bottom - band.top) > 1) {
                        hits.push("not-on-band-top");
                      }
                      // The left HUD island column's right edge (`place` is
                      // inset 16px on each side of `--left-column`).
                      const place = byId('[data-testid="anchor-place"]');
                      const leftCol = place ? place.right + 16 : null;
                      return {
                        hits,
                        height: cmd.height,
                        left: cmd.left,
                        right: cmd.right,
                        leftCol,
                        messageRight: targets.messageRegion ? targets.messageRegion.right : null,
                      };
                    }"""
                )
                self.assertEqual(
                    geo["hits"],
                    [],
                    "the command line overlaps %s at %dx%d @ scale %s" % (
                        ", ".join(geo["hits"]), viewport[0], viewport[1], scale,
                    ),
                )
                self.assertAlmostEqual(geo["height"], 44.0, delta=1.0, msg=f"expanded row is 44px at {viewport}")
                self.assertAlmostEqual(geo["left"], geo["leftCol"], delta=1.5, msg=f"row starts at --left-column at {viewport}")
                self.assertAlmostEqual(geo["right"], geo["messageRight"], delta=1.5, msg=f"row ends at message region's right edge at {viewport}")
            page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces"
    )
    def test_band_height_is_fixed_across_frames_and_modes(self):
        """webclient-avg-stage-shell (design D1/D4): the bottom band keeps one
        height and both regions keep one box through every frame and mode, and
        the player portrait stands on the band's top edge.
        """
        measure = """() => {
          const rect = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return [r.left, r.top, r.right, r.bottom];
          };
          return {
            band: rect('[data-testid="stage-band"]'),
            message: rect('[data-testid="anchor-band-message"]'),
            command: rect('[data-testid="anchor-band-command"]'),
          };
        }"""
        page = self.logged_in_page((1920, 1080))
        exploration = _exploration_panel([_selectable_target(11, "小販")])
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
        store = "window.__elosernBridge.store"
        states = {"root": page.evaluate(measure)}

        page.evaluate(f"() => {store}.tabToRootAndConfirm('interact', 'pointer')")
        page.wait_for_selector(".interaction-workspace", timeout=15000)
        page.locator(".interaction-workspace .dock-menu__nav-row").first.click()
        page.wait_for_selector(".interaction-workspace--selected", timeout=15000)
        states["interact"] = page.evaluate(measure)

        page.evaluate(f"() => {store}.tabToRootAndConfirm('wait', 'pointer')")
        page.wait_for_selector(".waiting-screen", timeout=15000)
        states["wait"] = page.evaluate(measure)

        page.evaluate(f"() => {store}.focusPress('Escape')")
        page.evaluate(f"() => {store}.focusPress('Escape')")
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        states["combat-root"] = page.evaluate(measure)
        # The deepest combat frame: descend with Enter until the depth stops growing.
        focus_action_dock(page)
        depth = page.evaluate(f"() => {store}.view.dockDepth")
        for _ in range(6):
            _press(page, "Enter", wait_ms=120)
            now = page.evaluate(f"() => {store}.view.dockDepth")
            if now <= depth:
                break
            depth = now
        states["combat-deep"] = page.evaluate(measure)

        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "dialogue": {
                    "schema_version": 1,
                    "available": True,
                    "kind": "dialogue",
                    "host": {"identity": 11, "display_name": "小販", "portrait_ref": None},
                    "bond_stage": None,
                    "line": "歡迎光臨，要看看今天的貨嗎？",
                    "choices": [
                        {"keyword_id": "goods", "label": "有什麼貨？"},
                        {"keyword_id": "price", "label": "價錢怎麼算？"},
                        {"keyword_id": "town", "label": "最近鎮上如何？"},
                        {"keyword_id": "road", "label": "路上安全嗎？"},
                    ],
                },
            },
            mode="dialogue",
        )
        _wait_mode(page, "dialogue")
        page.wait_for_selector('[data-testid="dialogue-exit"]', timeout=15000)
        states["dialogue"] = page.evaluate(measure)

        baseline = states["root"]
        self.assertAlmostEqual(baseline["band"][3] - baseline["band"][1], 300.24, delta=1.0)
        for label, state in states.items():
            for key in ("band", "message", "command"):
                for got, want in zip(state[key], baseline[key]):
                    self.assertAlmostEqual(
                        got, want, delta=1.0,
                        msg=f"the {key} box moved or resized in the {label} state",
                    )

        # The portrait stands on the band (exploration, 1920x1080).
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        portrait = page.evaluate(
            """() => {
              const a = document.querySelector('[data-testid="anchor-actor-left"]').getBoundingClientRect();
              const b = document.querySelector('[data-testid="stage-band"]').getBoundingClientRect();
              const holds = !!document.querySelector('[data-testid="anchor-actor-left"] [data-testid="reference-artwork"]');
              const focusable = document.querySelectorAll(
                '[data-testid="anchor-actor-left"] :is(button, a, input, textarea, select, [tabindex])').length;
              return { left: a.left, bottom: a.bottom, height: a.height, bandTop: b.top, holds, focusable };
            }"""
        )
        self.assertTrue(portrait["holds"], "actor-left holds the player portrait")
        self.assertEqual(portrait["focusable"], 0, "the portrait anchor holds no focusable element")
        self.assertAlmostEqual(portrait["bottom"], portrait["bandTop"], delta=1.0)
        self.assertAlmostEqual(portrait["height"], min(0.62 * 1080, 680), delta=1.0)
        self.assertAlmostEqual(portrait["left"], 0.06 * 1920, delta=1.0)

        # At 1280x720 the portrait is clamped to the stage box.
        small = self.logged_in_page((1280, 720))
        clamp = small.evaluate(
            """() => {
              const a = document.querySelector('[data-testid="anchor-actor-left"]').getBoundingClientRect();
              const header = getComputedStyle(document.documentElement).getPropertyValue('--header-h');
              return { top: a.top, header: parseFloat(header) };
            }"""
        )
        self.assertGreaterEqual(clamp["top"] + 1, clamp["header"], "the portrait never passes under the top bar")

    @covers_requirement(
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode"
    )
    @covers_requirement(
        "webclient-contextual-hud::the-objective-tracker-island-presents-the-committed-objectives-only"
    )
    def test_objective_line_shows_only_in_exploration(self):
        """webclient-avg-stage-hud-anchors (design D2): the objective line is
        one row under the minimap in the `map` anchor, shows the first tracked
        row plus `+N`, and is display:none in combat and dialogue while the
        same `objectives` panel stays committed."""
        objectives = {
            "schema_version": 1,
            "available": True,
            "rows": [
                {
                    "quest_id": "q_1042",
                    "display_name": "磨坊糧運",
                    "objective_line": "抵達霧骨渡口",
                    "stage_index": 1,
                    "stage_total": 2,
                    "stage_progress": 1,
                    "objective_quantity": 3,
                    "reward_copper": None,
                    "deadline_line": "剩餘 2 日",
                },
                {
                    "quest_id": "q_1043",
                    "display_name": "過河商議",
                    "objective_line": "與灰婆婆議價過河",
                    "stage_index": 2,
                    "stage_total": 2,
                    "stage_progress": 0,
                    "objective_quantity": 1,
                    "reward_copper": 80,
                    "deadline_line": None,
                },
            ],
        }
        exploration = _exploration_panel([_selectable_target(11, "小販")])
        explore_panels = {
            "exploration": exploration,
            "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
            "local_map": valid_local_map_panel(),
            "objectives": objectives,
        }
        line_state = """() => {
          const el = document.querySelector('[data-testid="objective-tracker"]');
          if (!el) return { mounted: false };
          const map = document.querySelector('[data-anchor="map"]');
          const minimap = document.querySelector('[data-testid="local-map"]');
          const r = el.getBoundingClientRect();
          const m = minimap && minimap.getBoundingClientRect();
          return {
            mounted: true,
            visible: el.offsetParent !== null && r.height > 0,
            inMap: !!(map && map.contains(el)),
            belowMinimap: !!(m && m.height > 0 && r.top >= m.bottom),
            height: r.height,
            text: el.textContent.replace(/\\s+/g, " ").trim(),
            more: (el.querySelector('[data-testid="objective-tracker__more"]') || {}).textContent,
          };
        }"""
        page = self.logged_in_page((1920, 1080))
        _inject_snapshot(page, explore_panels, mode="exploration")
        _wait_mode(page, "exploration")
        page.wait_for_selector('[data-testid="objective-tracker"]', timeout=15000)
        state = page.evaluate(line_state)
        self.assertTrue(state["visible"], "the objective line shows in exploration")
        self.assertTrue(state["inMap"], "the objective line lives in the map anchor")
        self.assertTrue(state["belowMinimap"], "the objective line sits under the minimap")
        self.assertLessEqual(state["height"], 34, "the objective line is one row tall")
        self.assertEqual((state["more"] or "").strip(), "+1")
        self.assertIn("抵達霧骨渡口", state["text"])
        self.assertIn("1/3", state["text"])
        self.assertNotIn("與灰婆婆議價過河", state["text"], "later rows stay in the quest drawer")
        self.assertNotIn("剩餘 2 日", state["text"], "deadlines stay in the quest drawer")

        _inject_snapshot(
            page,
            {"context_actions": _combat_panel(), "objectives": objectives},
            mode="combat",
        )
        _wait_mode(page, "combat")
        state = page.evaluate(line_state)
        self.assertTrue(state["mounted"], "the line stays mounted while its panel is committed")
        self.assertFalse(state["visible"], "the objective line is display:none in combat")

        _inject_snapshot(
            page,
            {
                **explore_panels,
                "dialogue": {
                    "schema_version": 1,
                    "available": True,
                    "kind": "dialogue",
                    "host": {"identity": 11, "display_name": "小販", "portrait_ref": None},
                    "bond_stage": None,
                    "line": "歡迎光臨，要看看今天的貨嗎？",
                    "choices": [{"keyword_id": "goods", "label": "有什麼貨？"}],
                },
            },
            mode="dialogue",
        )
        _wait_mode(page, "dialogue")
        state = page.evaluate(line_state)
        self.assertTrue(state["mounted"])
        self.assertFalse(state["visible"], "the objective line is display:none in dialogue")

        _inject_snapshot(page, explore_panels, mode="exploration")
        _wait_mode(page, "exploration")
        state = page.evaluate(line_state)
        self.assertTrue(state["visible"], "the objective line returns in exploration")

    @covers_requirement(
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
        "webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time",
    )
    def test_stage_box_is_at_least_65_percent_at_the_reference_viewport(self):
        """webclient-avg-place-card-top-bar (design D1/D6): at 1920x1080 the
        48px top band and the 300px bottom band leave a stage box of at least
        65% of the viewport; the top band states no location, no time, and no
        home entry, and the place card states both. At 1280x720 the one-row
        brand fits its column without reaching the navigation.
        """
        page = self.logged_in_page((1920, 1080))
        page.wait_for_selector('[data-testid="place-card"]', timeout=15000)
        state = page.evaluate(
            """() => {
              const box = (sel) => document.querySelector(sel).getBoundingClientRect();
              const header = parseFloat(getComputedStyle(document.querySelector('.elosern-root'), '::before').height);
              const band = box('[data-testid="stage-band"]');
              const place = box('[data-testid="anchor-place"]');
              const location = document.querySelector('[data-testid="place-card__location"]').textContent.trim();
              const time = document.querySelector('[data-testid="place-card__time"]').textContent.trim();
              const topBand = ['.topbar-brand', '.topbar-right', '.desktop-navigation']
                .map((sel) => document.querySelector(sel)?.textContent || '').join(' ');
              const navLabels = [...document.querySelectorAll('.desktop-navigation button')]
                .map((b) => b.textContent.trim());
              return { header, bandTop: band.top, bandHeight: band.height, placeTop: place.top,
                       location, time, topBand, navLabels };
            }"""
        )
        self.assertAlmostEqual(state["header"], 48, delta=1.0, msg="the top band is 48px")
        self.assertAlmostEqual(state["bandHeight"], 300, delta=1.0, msg="the bottom band is 300px")
        self.assertGreaterEqual(state["bandTop"] - state["header"], 702, "the stage box is at least 65% of 1080")
        self.assertGreaterEqual(state["placeTop"], state["header"], "the place card sits below the top band")
        self.assertTrue(state["location"] and state["location"] != "位置：--", "the place card states the location")
        self.assertNotIn(state["location"], state["topBand"], "the top band states no location")
        self.assertNotIn(state["time"], state["topBand"], "the top band states no world time")
        self.assertNotIn("探索", state["navLabels"])
        self.assertNotIn("戰鬥", state["navLabels"])

        small = self.logged_in_page((1280, 720))
        brand = small.evaluate(
            """() => {
              const brand = document.querySelector('.topbar-brand');
              const last = brand.lastElementChild.getBoundingClientRect();
              const nav = document.querySelector('.desktop-navigation').getBoundingClientRect();
              return { contentRight: last.right, brandRight: brand.getBoundingClientRect().right,
                       scroll: brand.scrollWidth, client: brand.clientWidth, navLeft: nav.left };
            }"""
        )
        self.assertLessEqual(brand["scroll"], brand["client"], "the brand row does not overflow its column")
        self.assertLessEqual(brand["contentRight"], brand["brandRight"])
        self.assertLessEqual(brand["contentRight"], brand["navLeft"], "the brand does not reach the navigation")

        # The navigation row and the right cluster stay side by side with a
        # maximum-length (128-character) character name committed in the
        # roster: the name is bounded and truncated, so the cluster never
        # grows into the navigation.
        inject_snapshot(small, {"roster": {
            "schema_version": 2,
            "available": True,
            "characters": [{
                "identity": 1, "name": "長" * 128, "current": True, "pending": False,
                "portrait": {
                    "subject_key": None, "status": "missing", "url": None,
                    "aspect_ratio": None, "alt": "角色肖像",
                    "placeholder": {"kind": "missing", "label": "尚無肖像"},
                    "face_rect": None,
                },
            }],
            "can_create": False,
            "max_characters": 3,
            "switch_locked": False,
            "lock_reason": None,
        }})
        small.wait_for_selector('[data-testid="character-switcher-name"]', timeout=15000)
        cluster = small.evaluate(
            """() => {
              const name = document.querySelector('[data-testid="character-switcher-name"]');
              const nav = document.querySelector('.desktop-navigation').getBoundingClientRect();
              const right = document.querySelector('.topbar-right').getBoundingClientRect();
              return { hasName: !!name, navRight: nav.right, rightLeft: right.left,
                       rightRight: right.right, rightBottom: right.bottom, width: innerWidth };
            }"""
        )
        self.assertTrue(cluster["hasName"], "the switcher renders the committed name")
        self.assertLessEqual(cluster["navRight"], cluster["rightLeft"], "the navigation and the switcher do not collide")
        self.assertLessEqual(cluster["rightRight"], cluster["width"])
        self.assertLessEqual(cluster["rightBottom"], 48 + 1, "the right cluster stays inside the top band")

    @covers_requirement(
        "webclient-input-narrative::the-full-log-surface-opens-at-its-latest-line"
    )
    def test_full_log_opens_at_latest_line(self):
        page = self.logged_in_page()
        # Append 80 lines through window.__elosernBridge.store.appendText
        page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              for (let i = 1; i <= 80; i++) {
                store.appendText("out", `第 ${i} 行測試敘事內容。`);
              }
            }"""
        )
        # Open full log via narrative-fulllog-control
        page.locator('[data-testid="narrative-fulllog-control"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)

        # Assert scrollTop + clientHeight >= scrollHeight - 1
        scroll_status = page.evaluate(
            """() => {
              const el = document.querySelector('[data-testid="fulllog-overlay"]');
              const lines = el.querySelectorAll('.narrative-line');
              const lastLine = lines[lines.length - 1];
              const overlayBox = el.getBoundingClientRect();
              const lastBox = lastLine ? lastLine.getBoundingClientRect() : null;
              const lastInside = lastBox && lastBox.top >= overlayBox.top && lastBox.bottom <= overlayBox.bottom + 5;
              return {
                atBottom: el.scrollTop + el.clientHeight >= el.scrollHeight - 1,
                lastInside,
                scrollTop: el.scrollTop,
              };
            }"""
        )
        self.assertTrue(scroll_status["atBottom"], "full log must open scrolled to the bottom")
        self.assertTrue(scroll_status["lastInside"], "last line must be inside visible overlay box")

        # Scroll to top
        page.evaluate(
            """() => {
              const el = document.querySelector('[data-testid="fulllog-overlay"]');
              el.scrollTop = 0;
            }"""
        )
        # Append a line while open
        page.evaluate(
            """() => {
              window.__elosernBridge.store.appendText("out", "第 81 行即時到達的敘事內容。");
            }"""
        )
        # Assert scrollTop is unchanged
        st = page.evaluate("() => document.querySelector('[data-testid=\"fulllog-overlay\"]').scrollTop")
        self.assertEqual(st, 0, "appending a line while open must leave scroll position unchanged")

        # Close log
        page.locator('[data-testid="fulllog-close"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', state="detached", timeout=15000)

        # Reopen log and assert it is back at the bottom
        page.locator('[data-testid="narrative-fulllog-control"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        at_bottom_again = page.evaluate(
            """() => {
              const el = document.querySelector('[data-testid="fulllog-overlay"]');
              return el.scrollTop + el.clientHeight >= el.scrollHeight - 1;
            }"""
        )
        self.assertTrue(at_bottom_again, "reopening full log must open at the latest line again")
        page.close()

    @covers_requirement(
        "webclient-desktop-shell::the-top-navigation-bar-carries-the-tool-group",
        "webclient-pointer-activation::keyboard-input-is-dispatched-through-the-webclient-plugin-contract",
    )
    def test_top_bar_tool_group_fits_and_opens_with_line_collapsed(self):
        """webclient-collapsible-command-line (design D6): at 1280x720 with a
        maximum-length character name and an available gallery panel, every
        `nav-tools` button lies inside the 48px bar without intersecting
        `.topbar-right`; Tab reaches each tool in order, Enter opens its
        surface and Escape returns focus to it while the command line stays
        collapsed; and ArrowUp on the dock with the line collapsed is claimed
        by the router, while `/` then ArrowUp in the field walks history."""
        page = self.logged_in_page((1280, 720))
        exploration = _exploration_panel([_selectable_target(11, "小販")])
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel({"status": "unavailable"}),
                "local_map": valid_local_map_panel(),
                "lore_codex": valid_lore_codex_panel(),
                "gallery": _GALLERY_PANEL,
                "roster": {
                    "schema_version": 2,
                    "available": True,
                    "characters": [{
                        "identity": 1,
                        "name": "長" * 128,
                        "current": True,
                        "pending": False,
                        "portrait": {
                            "subject_key": None,
                            "status": "missing",
                            "url": None,
                            "aspect_ratio": None,
                            "alt": "角色肖像",
                            "placeholder": {"kind": "missing", "label": "尚無肖像"},
                            "face_rect": None,
                        },
                    }],
                    "can_create": False,
                    "max_characters": 3,
                    "switch_locked": False,
                    "lock_reason": None,
                },
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        page.wait_for_selector('[data-testid="gallery-opener"]', timeout=15000)
        page.wait_for_selector('[data-testid="character-switcher-name"]', timeout=15000)

        self.assertEqual(
            page.locator('[data-testid="anchor-command-line"]').get_attribute("data-expanded"),
            "false",
        )
        fit = page.evaluate(
            """() => {
              const right = document.querySelector('.topbar-right').getBoundingClientRect();
              const navButtons = [...document.querySelectorAll('.desktop-navigation button')].map((b) => {
                const r = b.getBoundingClientRect();
                return { testid: b.getAttribute('data-testid'), left: r.left, right: r.right, top: r.top, bottom: r.bottom };
              });
              const tools = [...document.querySelectorAll('[data-testid="nav-tools"] button')].map((b) => {
                const r = b.getBoundingClientRect();
                return {
                  testid: b.getAttribute('data-testid'),
                  aria: b.getAttribute('aria-label'),
                  title: b.getAttribute('title'),
                  top: r.top,
                  bottom: r.bottom,
                  left: r.left,
                  right: r.right,
                };
              });
              return { rightLeft: right.left, navButtons, tools };
            }"""
        )
        self.assertEqual(
            [t["testid"] for t in fit["tools"]],
            ["nav-tool-lineage", "nav-tool-lore", "nav-tool-codex", "gallery-opener", "nav-tool-help"],
        )
        for tool in fit["tools"]:
            self.assertEqual(tool["aria"], tool["title"])
            self.assertGreaterEqual(tool["top"], -1)
            self.assertLessEqual(tool["bottom"], 48 + 1, f"{tool['testid']} extends below the 48px bar")
        for btn in fit["navButtons"]:
            self.assertLessEqual(btn["right"], fit["rightLeft"], f"nav button {btn['testid']} intersects .topbar-right")

        # Sequential Tab from nav-settings reaches each tool in order; Enter
        # opens its surface and Escape returns focus to that tool.
        page.locator('[data-testid="nav-settings"]').focus()
        expected_tools = (
            ("nav-tool-lineage", '[data-testid="overlay-host"][data-elosern-overlay="lineage"]'),
            ("nav-tool-lore", '[data-testid="lore-codex-drawer"]'),
            ("nav-tool-codex", '[data-testid="overlay-host"][data-elosern-overlay="codex"]'),
            ("gallery-opener", '[data-testid="gallery-panel"]'),
            ("nav-tool-help", '[data-testid="help-overlay"]'),
        )
        for testid, surface_sel in expected_tools:
            page.keyboard.press("Tab")
            self.assertEqual(
                page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
                testid,
                f"Tab did not reach {testid}",
            )
            page.keyboard.press("Enter")
            page.wait_for_selector(surface_sel, timeout=15000)
            page.keyboard.press("Escape")
            page.wait_for_function(
                "(sel) => document.querySelector(sel) === null",
                arg=surface_sel,
                timeout=15000,
            )
            self.assertEqual(
                page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')"),
                testid,
                f"Escape did not restore focus to {testid}",
            )

        # Pointer-activation scenario: with the line collapsed, ArrowUp on the
        # dock is claimed by the router and does not walk history; `/` then
        # ArrowUp in the focused field walks the command history.
        open_command_line(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        wait_command_field_released(page)
        claimed = page.evaluate(
            """() => {
              const ev = new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true, cancelable: true });
              document.getElementById('action-dock').dispatchEvent(ev);
              return {
                prevented: ev.defaultPrevented,
                value: document.getElementById('inputfield').value,
              };
            }"""
        )
        self.assertTrue(claimed["prevented"], "ArrowUp on the dock with the line collapsed is claimed by the router")
        self.assertEqual(claimed["value"], "", "collapsed command line owns no key")
        open_command_line(page)
        page.keyboard.press("ArrowUp")
        self.assertEqual(
            page.evaluate("document.getElementById('inputfield').value"),
            "look",
            "ArrowUp in the expanded, focused field walks the command history",
        )
        page.close()
