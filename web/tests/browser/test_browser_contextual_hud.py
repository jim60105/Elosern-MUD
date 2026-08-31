"""Contextual HUD action-dock browser acceptance (webclient-contextual-hud).

One browser test per currently-uncovered ``webclient-contextual-hud``
requirement. Each journey drives the shared managed server's committed
presentation state (injected through ``ui_snapshot``) and asserts the Vue
surfaces: the mode-gated stage, the truthful scene backdrop, the bounded
narrative caption + full log, the drawer/overlay stage recession, the
floating action-dock panel, the tab bar with truthful count badges, the
router-derived breadcrumb, the per-kind dock panes, the combat participant
frame, the bounded skill master-detail, and the two-step forfeit
confirmation.

Every test is deterministic: fixed panel payloads, no live LLM, Stable
Diffusion, or other network service.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    sent_action_count,
    valid_character_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_store_state,
)

# ---------------------------------------------------------------------------
# Schema-valid panel builders (mirrors of the committed presentation schemas).
# ---------------------------------------------------------------------------


def _interact_target(identity: int, name: str) -> dict:
    """One schema-valid exploration interact target."""
    return {
        "identity": identity,
        "display_name": name,
        "portrait_ref": None,
        "affordances": [],
    }


def _move_row(exit_ref: str, label: str, destination: str, enabled: bool = True) -> dict:
    """One schema-valid exploration move row (a canonical direction or a named exit)."""
    return {
        "exit_ref": exit_ref,
        "label": label,
        "destination": destination,
        "enabled": enabled,
        "disabled_reason": None if enabled else {"code": "blocked", "message": "出口被阻擋。"},
    }


def _exploration_panel(interact_targets: list, move_rows: list | None = None) -> dict:
    """A schema-valid available exploration panel."""
    return {
        "schema_version": 1,
        "available": True,
        "kind": "exploration",
        "move": move_rows or [],
        "look": {
            "room": {"identity": 43, "display_name": "南門", "room": True},
            "entities": [],
            "objects": [],
        },
        "interact": interact_targets,
        "character": {"available": False},
        "quests": {"available": False},
        "inventory": {"available": False},
    }


def _suggestions_ready(card_labels: list) -> dict:
    """A schema-valid ``ready`` suggestions envelope (status + cards)."""
    cards = [
        {
            "kind": "known_action",
            "action_code": "explore.look",
            "label": label,
            "params": {"room": True},
        }
        for label in card_labels
    ]
    return {"status": "ready", "cards": cards}


def _exploration_context_actions_panel(suggestions: dict) -> dict:
    """A schema-valid ``context_actions`` exploration form with a suggestions envelope."""
    return {
        "schema_version": 5,
        "available": True,
        "kind": "exploration",
        "affordances": [],
        "suggestions": suggestions,
    }


def _participant(identity, token, name, team, state, hp_current, hp_maximum, portrait_ref) -> dict:
    """One schema-valid combat participant descriptor."""
    return {
        "identity": identity,
        "token": token,
        "display_name": name,
        "team": team,
        "state": state,
        "hp_current": hp_current,
        "hp_maximum": hp_maximum,
        "portrait_ref": portrait_ref,
    }


def _skill(key, label, description, cost, target_spec, element=None, enabled=True, targets=None, shorthands=None) -> dict:
    """One schema-valid combat skill descriptor."""
    return {
        "key": key,
        "label": label,
        "description": description,
        "cost": cost,
        "target_spec": target_spec,
        "element": element,
        "enabled": enabled,
        "disabled_reason": None if enabled else {"code": "unavailable", "message": "技能尚未解鎖。"},
        "targets": targets or [],
        "shorthands": shorthands or [],
    }


def _skill_group(group, label, skills: list) -> dict:
    """One schema-valid combat skill sub-group."""
    return {"group": group, "label": label, "skills": skills}


def _skill_category(category: str, label: str, groups: list) -> dict:
    """One schema-valid combat skill category."""
    return {"category": category, "label": label, "groups": groups}


def _combat_panel() -> dict:
    """A schema-valid combat ``context_actions`` panel.

    Carries two party / two foes (one knocked out) and two skill categories:
    a multi-group ``elemental_magic`` (two sub-groups) and a single-group
    ``enhancement`` (one sub-group) — the two shapes the spec's single-vs-multi
    group scenario requires.
    """
    participants = [
        _participant(1, "a1", "勇者", "party", "active", 100, 100, "1"),
        _participant(2, "a2", "法師", "party", "knocked_out", 40, 100, "2"),
        _participant(3, "e1", "哥布林", "foes", "active", 60, 60, None),
        _participant(4, "e2", "史萊姆", "foes", "active", 30, 30, None),
    ]
    skills = [
        _skill_category(
            "elemental_magic",
            "元素魔法",
            [
                _skill_group(
                    "火焰",
                    "火焰技",
                    [
                        _skill(
                            "fire_ball",
                            "火球術",
                            "凝聚火焰的攻擊技。",
                            {"mp": 20},
                            "single",
                            "fire",
                            True,
                            [3, 4],
                            [],
                        ),
                    ],
                ),
                _skill_group(
                    "寒冰",
                    "寒冰技",
                    [
                        _skill(
                            "ice_arrow",
                            "冰箭術",
                            "冷凍的射擊技。",
                            {"mp": 12},
                            "single",
                            "ice",
                            True,
                            [3, 4],
                            [],
                        ),
                    ],
                ),
            ],
        ),
        _skill_category(
            "enhancement",
            "強化術",
            [
                _skill_group(
                    None,
                    None,
                    [
                        _skill(
                            "shield",
                            "護盾術",
                            "暫時提升防禦。",
                            {"mp": 8},
                            "self",
                            "light",
                            True,
                            [],
                            [],
                        ),
                    ],
                ),
            ],
        ),
    ]
    return {
        "schema_version": 5,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": "browser-combat-0001",
            "mode": "hostile",
            "round": 1,
            "state": "ready",
            "reason": None,
        },
        "participants": participants,
        "root_actions": ["attack", "skills", "items", "defend", "flee"],
        "secondary_actions": ["forfeit"],
        "skills": skills,
        "suggestions": {"status": "unavailable"},
    }


def _art_panel(portrait_refs: list) -> dict:
    """A schema-valid available art panel with a done scene + portrait catalog."""
    catalog = {}
    for ref in portrait_refs:
        catalog[ref] = {
            "subject_key": "subject_" + ref,
            "status": "done",
            "url": "/art/portrait_" + ref + ".png",
            "aspect_ratio": "3:4",
            "alt": "角色肖像",
            "placeholder": None,
            "context": {"name": "角色", "role": "人物"},
        }
    return {
        "schema_version": 1,
        "available": True,
        "kind": "scene",
        "scene": {
            "archetype": None,
            "label": "南門街道",
            "subject_key": None,
            "status": "done",
            "url": "/art/scene.png",
            "aspect_ratio": "16:9",
            "alt": "當前場景",
            "placeholder": None,
        },
        "portrait_catalog": catalog,
    }


def _local_map_unavailable_panel() -> dict:
    """A schema-valid registry-owned unavailable ``local_map`` panel.

    Mirrors the registry's ``build_unavailable("local_map")`` form: exactly
    ``schema_version``, ``available: False``, and a bounded registry-owned
    ``reason`` (the ``map_unavailable`` code + the 區域地圖目前無法顯示 message).
    """
    return {
        "schema_version": 1,
        "available": False,
        "reason": {"code": "map_unavailable", "message": "區域地圖目前無法顯示"},
    }


# ---------------------------------------------------------------------------
# Page-level helpers.
# ---------------------------------------------------------------------------


def _inject_snapshot(page, panels: dict, mode: str = "exploration") -> None:
    """Inject one schema-valid ``ui_snapshot`` through the store's ``receive``."""
    inject_snapshot(page, panels, mode=mode)


def _wait_mode(page, mode: str, timeout: int = 30000) -> None:
    """Gate on the committed store mode matching ``mode``."""
    wait_for_store_state(
        page,
        lambda s: s.get("mode") == mode,
        timeout=timeout,
    )


def _press(page, key: str, wait_ms: int = 80) -> None:
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def _dock_depth(page) -> int:
    return page.evaluate("window.__elosernBridge.store.view.dockDepth")


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

        # H5 (task 8.6): the command line's `#inputfield` is present and
        # visible in exploration with no opening action (the field is always
        # in the DOM, design D1).
        field = page.locator("#inputfield")
        self.assertEqual(field.count(), 1, "the command field is present in exploration")
        self.assertTrue(field.is_visible(), "the command field is visible in exploration")

        # Commit combat: the minimap is removed from the layout with
        # display:none (never merely dimmed); the other mode-visible surfaces
        # (narrative feed, command line, action dock) stay up (H5: the command
        # line is permanently present, webclient-hud-05-overlays-and-command-line).
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
            # H5 (webclient-hud-05-overlays-and-command-line): the command
            # line is permanently present (design D1) — it stays visible in
            # combat mode.
            '[data-testid="command-line"]',
            "#action-dock",
        ):
            self.assertTrue(
                page.locator(selector).is_visible(),
                f"{selector} must stay visible in combat",
            )
        # H5 (task 8.6): the command field stays present and visible in
        # combat (the command line is never closed).
        self.assertEqual(page.locator("#inputfield").count(), 1, "the command field is present in combat")
        self.assertTrue(
            page.locator("#inputfield").is_visible(),
            "the command field is visible in combat",
        )

        # Commit creation: per H1's mode matrix, the command-line anchor is
        # display:none, so the command field is absent from the layout.
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

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    def test_scene_backdrop_renders_art_payload_truthfully(self):
        """The backdrop renders the committed art scene behind the stage."""
        page = self.logged_in_page()
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
        page.locator('[data-testid="command-line-settings"]').click()
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
        page.locator('[data-testid="command-line-help"]').click()
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
        "webclient-contextual-hud::the-action-dock-renders-as-a-floating-panel-in-the-stage-s-dock-anchor"
    )
    def test_command_line_never_overlaps_dock_caption_or_hud(self):
        """H5 (task 8.8): at both supported viewports and at each of the
        three prose-scale steps, the command line does not overlap the action
        dock, the narrative caption, or the HUD island anchors.
        """
        for viewport in ((1440, 900), (1280, 720)):
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
            for scale in (0.92, 1, 1.12):
                page.evaluate("(s) => window.__elosernBridge.store.setFontScale(s)", scale)
                overlaps = page.evaluate(
                    """() => {
                      const byId = (sel) => {
                        const el = document.querySelector(sel);
                        return el && el.getBoundingClientRect();
                      };
                      const cmd = byId('[data-testid="command-line"]');
                      if (!cmd) { return ["command-line missing"]; }
                      const targets = {
                        dock: byId('#action-dock'),
                        caption: byId('[data-testid="narrative-feed"]'),
                        hudLeft: byId('[data-testid="anchor-hud-left"]'),
                        hudRight: byId('[data-testid="anchor-hud-right"]'),
                      };
                      const hits = [];
                      for (const key of Object.keys(targets)) {
                        const b = targets[key];
                        if (!b) { continue; }
                        const overlap = !(
                          cmd.right <= b.left || b.right <= cmd.left ||
                          cmd.bottom <= b.top || b.bottom <= cmd.top
                        );
                        if (overlap) { hits.push(key); }
                      }
                      return hits;
                    }"""
                )
                self.assertEqual(
                    overlaps,
                    [],
                    "the command line overlaps %s at %dx%d @ scale %s" % (
                        ", ".join(overlaps), viewport[0], viewport[1], scale,
                    ),
                )

    @covers_requirement(
        "webclient-contextual-hud::the-action-dock-renders-as-a-floating-panel-in-the-stage-s-dock-anchor"
    )
    def test_action_dock_floating_panel_persists_across_modes(self):
        """The action dock is one centred floating panel in the dock anchor."""
        for viewport in ((1440, 900), (1280, 720)):
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
                    borderTop: style.borderTopWidth,
                    boxShadow: style.boxShadow,
                    anchorHeightComputed: anchorStyle.height,
                    viewportWidth: window.innerWidth,
                  };
                }"""
            )
            # The panel is horizontally centred within the anchor.
            self.assertLess(
                abs((geometry["dockLeft"] + geometry["dockWidth"] / 2)
                    - (geometry["anchorLeft"] + geometry["anchorWidth"] / 2)),
                4.0,
                f"the dock must be centred within the dock anchor at {viewport}",
            )
            self.assertTrue(
                geometry["borderTop"].startswith("1px"),
                "the floating panel carries the --line top border",
            )
            self.assertIn("rgba", geometry["boxShadow"], "the panel carries an upward shadow")
            # The panel's height equals the anchor's height (both driven by --dock-h).
            self.assertAlmostEqual(
                geometry["dockHeight"],
                float(geometry["anchorHeightComputed"].replace("px", "")),
                places=1,
                msg=f"the dock height must equal the anchor height (the --dock-h token) at {viewport}",
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

    @covers_requirement(
        "webclient-contextual-hud::the-combat-participant-frame-presents-the-session-s-participants-and-their-portraits"
    )
    def test_combat_participant_frame_presents_participants_and_portraits(self):
        """The combat participant frame presents the session's participants and portraits."""
        page = self.logged_in_page()
        _inject_snapshot(
            page,
            {
                "context_actions": _combat_panel(),
                "art": _art_panel(["1", "2"]),
            },
            mode="combat",
        )
        _wait_mode(page, "combat")

        frame = page.locator('[data-testid="participant-frame"]')
        self.assertEqual(frame.count(), 1, "the participant frame mounts in the HUD area")
        self.assertTrue(frame.is_visible())

        # Both sides render from the committed participants, in presenter order.
        frame_text = frame.inner_text()
        self.assertIn("我方", frame_text, "the player's side renders")
        self.assertIn("敵方", frame_text, "the opposing side renders")
        self.assertIn("a1", frame_text, "the participant token renders")
        self.assertIn("勇者", frame_text, "the participant display name renders")
        self.assertIn("100/100", frame_text, "the current/maximum HP render as numerals")
        # A non-active participant carries an explicit text state marker.
        self.assertIn("倒地", frame_text, "a knocked-out participant is marked in text, not colour alone")

        # Portraits resolve only through the committed art portrait catalog.
        imgs = frame.locator("img.participant-frame__portrait")
        placeholders = frame.locator('[data-testid="participant-portrait-placeholder"]')
        self.assertEqual(imgs.count(), 2, "resolvable portrait references render the catalog image")
        self.assertEqual(placeholders.count(), 0, "a null portrait_ref renders no placeholder card")
        # While the participant frame is mounted, no separate portrait strip renders.
        self.assertEqual(
            page.locator('[data-testid="art-panel"]').count(),
            0,
            "while the participant frame is mounted, no separate portrait strip renders",
        )

    @covers_requirement(
        "webclient-contextual-hud::combat-skills-are-chosen-through-a-bounded-master-detail"
    )
    def test_combat_skills_bounded_master_detail(self):
        """Combat skills are chosen through a bounded category/group/skill master-detail."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        # Open the Skills tab (second root item) -> the category frame.
        _press(page, "ArrowRight")
        _press(page, "Enter")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 2, "the skills tab opens the category frame")

        # The category frame lists the committed categories in panel order, each
        # carrying its own skill-descriptor count.
        pane = page.locator('[data-testid="dock-menu"]')
        pane_text = pane.inner_text()
        self.assertIn("元素魔法", pane_text, "the category frame lists the committed category labels")
        self.assertIn("強化術", pane_text)

        # Navigate to the single-group category (強化術) and open it: the skill
        # frame opens directly (no pointless single-choice group level).
        _press(page, "ArrowRight")
        _press(page, "Enter")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 3, "the single-group category opens the skill frame directly")

        # The skill frame lists the group's descriptors beside the detail pane,
        # which names the focused skill, its cost, description and target spec.
        detail = page.locator('[data-testid="combat-detail"]')
        self.assertEqual(detail.count(), 1, "the single-group category opens the skill frame with the detail pane")
        detail_text = detail.inner_text()
        self.assertIn("護盾術", detail_text, "the detail pane names the focused skill")
        self.assertIn("MP 8", detail_text, "the detail pane shows the skill's cost")
        self.assertIn("防禦", detail_text, "the detail pane shows the skill's description")
        self.assertIn("self", detail_text, "the detail pane shows the skill's target requirement")

    @covers_requirement(
        "webclient-contextual-hud::destructive-combat-confirmation-renders-as-an-explicit-two-step-panel"
    )
    def test_destructive_combat_confirmation_two_step_panel(self):
        """Opening Forfeit renders an explicit two-step confirmation panel."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        # The combat root is a single-row tab bar; Forfeit is the last tab.
        tab_count = page.evaluate("document.querySelectorAll('#action-dock [data-item-key]').length")
        for _ in range(tab_count - 1):
            _press(page, "ArrowRight")
        _press(page, "Enter")  # open the Forfeit confirmation frame
        page.wait_for_timeout(150)

        # The confirmation frame renders as an explicit warning panel with a
        # cancel row and a confirm row; opening it submits nothing.
        pane = page.locator('[data-testid="dock-menu"]')
        pane_text = pane.inner_text()
        self.assertIn("確認投降", pane_text, "the confirmation frame renders the confirm row")
        self.assertIn("取消", pane_text, "the confirmation frame renders the cancel row")
        self.assertEqual(sent_action_count(page), 0, "opening Forfeit submits no mutation")

        # Escape closes exactly one level without submitting.
        _press(page, "Escape")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 1, "Escape pops exactly one level")
        self.assertEqual(sent_action_count(page), 0, "leaving the confirmation submits nothing")

        # Re-open Forfeit and activate the confirm row: exactly one
        # combat.forfeit action is emitted carrying the current session id.
        # After the first Escape the root frame's focus is already on the
        # Forfeit tab (the parent focus is restored by the router), so a single
        # Enter re-opens the confirmation frame.
        _press(page, "Enter")
        page.wait_for_timeout(150)
        page.locator('[data-testid="dock-menu"] button[data-item-key="confirm-forfeit"]').click()
        page.wait_for_timeout(200)
        self.assertEqual(
            sent_action_count(page, "combat.forfeit"),
            1,
            "activating the confirm row emits exactly one combat.forfeit",
        )
        sent = page.evaluate("window.__elosernSent || []")
        forfeit = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args and args[0].get("action_id") == "combat.forfeit"
        ]
        self.assertEqual(
            forfeit[0]["payload"]["session_id"],
            "browser-combat-0001",
            "the forfeit action carries the current session identifier",
        )


    # ------------------------------------------------------------------
    # H4 (tasks 9.5-9.7): reference-drawer browser acceptance.
    # ------------------------------------------------------------------

    REFERENCE_SURFACE_TESTIDS = [
        "skill-book",
        "inventory-panel",
        "shop-panel",
        "quest-board",
        "lore-drawer",
        "character-status-drawer",
    ]

    def _open_status_drawer(self, page):
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('status'); }"
        )
        page.wait_for_selector('[data-testid="hud-drawer"]', timeout=15000)

    def _stage_anchor_rects(self, page):
        return page.evaluate(
            """() => {
              const ids = ["anchor-hud-left", "anchor-hud-right", "anchor-feed", "anchor-dock"];
              return ids.map((id) => {
                const el = document.getElementById(id);
                if (!el) return { id, rect: null };
                return { id, rect: el.getBoundingClientRect() };
              });
            }"""
        )

    def _anchors_overlap(self, page):
        rects = self._stage_anchor_rects(page)
        present = [r for r in rects if r["rect"]]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = present[i]["rect"], present[j]["rect"]
                overlap = not (
                    a.right <= b.left or b.right <= a.left
                    or a.bottom <= b.top or b.bottom <= a.top
                )
                if overlap:
                    return True
        return False

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_reference_drawer_close_focus_and_absent_surfaces(self):
        """H4 (task 9.5): at both viewports an open drawer closes in one
        action, Escape restores focus, and no reference surface is in the DOM
        while every drawer is closed."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                # The focus-restoration contract: the drawer is opened while the
                # preserved #action-dock holds focus, so Escape returns focus
                # there (the opener is the dock, not <body>).
                focus_action_dock(page)
                self._open_status_drawer(page)
                stage = page.locator('[data-testid="elosern-stage"]')

                # The open drawer recesses the stage (task 9.6 assertion inline).
                self.assertEqual(
                    stage.get_attribute("data-menu-open"),
                    "true",
                    f"the stage is recessed while the reference drawer is open at {viewport}",
                )

                # One action (Escape) closes the drawer; focus returns to the
                # preserved action-dock target.
                _press(page, "Escape")
                page.wait_for_function(
                    "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
                    timeout=15000,
                )
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer"]').count(),
                    0,
                    f"the drawer closes in one action (Escape) at {viewport}",
                )
                self.assertEqual(
                    stage.get_attribute("data-menu-open"),
                    "false",
                    f"the recession mark clears when the last surface closes at {viewport}",
                )
                # Escape closes the drawer and restores focus to the preserved
                # action-dock focus target (the focus-restoration contract).
                focus_id = page.evaluate(
                    "() => { const a = document.activeElement; "
                    "return a ? (a.id || (a.getAttribute && a.getAttribute('data-testid')) || a.tagName) : null; }"
                )
                self.assertEqual(
                    focus_id,
                    "action-dock",
                    f"Escape restores focus to the preserved #action-dock target at {viewport}",
                )
                dock = page.locator("#action-dock")
                self.assertTrue(dock.count() >= 1, "the preserved action dock is present")

                # No reference surface is in the DOM while every drawer is closed.
                for testid in self.REFERENCE_SURFACE_TESTIDS:
                    self.assertEqual(
                        page.locator(f'[data-testid="{testid}"]').count(),
                        0,
                        f"reference surface {testid} is absent while all drawers are closed at {viewport}",
                    )
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer"]').count(), 0,
                    "no drawer chrome in the DOM while closed")
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer-scrim"]').count(), 0,
                    "no drawer scrim in the DOM while closed")
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::an-open-drawer-or-overlay-dims-the-stage-behind-it"
    )
    def test_reference_drawer_recession_mark_lifecycle(self):
        """H4 (task 9.6): the stage recession mark is present while a
        reference drawer is open and cleared when the last surface closes."""
        page = self.logged_in_page()
        stage = page.locator('[data-testid="elosern-stage"]')
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "false",
            "no surface open: no recession mark",
        )
        # Open the drawer while #action-dock holds focus so the opener (the
        # element focused when the drawer opened) is the preserved dock.
        focus_action_dock(page)
        self._open_status_drawer(page)
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "true",
            "the open reference drawer recesses the stage",
        )
        _press(page, "Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            stage.get_attribute("data-menu-open"), "false",
            "the recession mark clears when the last surface closes",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action"
    )
    def test_caption_wider_and_no_anchor_overlap(self):
        """H4 (task 9.7): with `#panel-right` emptied into drawers, the
        narrative caption is wider at both viewports and no stage anchor
        overlaps another."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                feed_width = page.evaluate(
                    "() => { const f = document.querySelector('[data-testid=\"narrative-feed\"]');"
                    "return f ? f.getBoundingClientRect().width : 0; }"
                )
                self.assertGreater(
                    feed_width, 400,
                    f"the narrative caption is wider than before the hud-right removal at {viewport}",
                )
                self.assertFalse(
                    self._anchors_overlap(page),
                    f"no stage anchor overlaps another at {viewport}",
                )
                page.close()

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_local_map_unavailable_renders_registry_reason_in_map_overlay(self):
        """8.9 offline-degradation regression: with the `local_map` panel in its
        registry-owned unavailable form, the minimap island renders only the
        registry-owned reason, and the map overlay's opening path still works —
        the map overlay renders only the reason, never a stale lattice."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"local_map": _local_map_unavailable_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # The minimap island renders the registry-owned reason (not the lattice).
        island_reason = page.locator('[data-testid="local-map__unavailable"]')
        self.assertTrue(island_reason.is_visible(), "the minimap island shows the registry-owned reason")
        self.assertEqual(
            island_reason.inner_text(),
            "區域地圖目前無法顯示",
            "the island shows the exact registry-owned reason message",
        )
        self.assertEqual(
            page.locator('[data-testid="local-map__lattice"]').count(),
            0,
            "no lattice renders while the local_map panel is unavailable",
        )

        # The map overlay's opening path (the island's 展開全地圖 trigger routes
        # through the store's overlay slice) still opens the surface.
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)

        # The map overlay renders ONLY the registry-owned reason (no lattice).
        overlay_reason = page.locator('[data-testid="map-overlay-unavailable"]')
        self.assertTrue(
            overlay_reason.is_visible(),
            "the map overlay shows the registry-owned reason",
        )
        self.assertEqual(
            overlay_reason.inner_text(),
            "區域地圖目前無法顯示",
            "the map overlay shows the exact registry-owned reason message",
        )
        self.assertEqual(
            page.locator('[data-testid="map-overlay-content"]').count(),
            0,
            "the map overlay renders only the reason, never a stale lattice",
        )
        page.close()

    def test_status_drawer_tiles_and_pills_fit_with_no_overlap(self):
        """The re-chromed 角色狀態 drawer: the stat tiles and condition pills
        wrap without overlap, clipping, or horizontal overflow at both
        viewports (the design's card-tile / pill-badge presentation).

        Exercises a low-HP resource (the 危險 marker case) and a 9-condition
        roster spanning all five severities (more than the H2 island's 6-item
        cap), including a multi-modifier condition and several durations.
        """
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                focus_action_dock(page)
                status = valid_status_panel("艾倫·灰誓", "char-42")
                status["resources"]["hp"] = {"current": 12, "maximum": 405}
                # The signed modifier values mirror the deterministic
                # combat_modifiers.yaml (defense -15, agility -10, hp -3):
                # the global JSON-safety bound now spans the full
                # JavaScript-safe range, so the roster reaches the drawer.
                status["conditions"] = [
                    {"code": "regen", "label": "再生", "severity": "beneficial", "remaining_seconds": 30},
                    {"code": "fog_veil", "label": "霧隱", "severity": "informational"},
                    {
                        "code": "focus",
                        "label": "專注",
                        "severity": "warning",
                        "remaining_seconds": 10,
                        "modifiers": {"atk_phys": 5},
                    },
                    {
                        "code": "exposure",
                        "label": "高露出",
                        "severity": "harmful",
                        "modifiers": {"defense": -15, "agility": -10},
                    },
                    {
                        "code": "bleed",
                        "label": "出血",
                        "severity": "harmful",
                        "remaining_seconds": 20,
                        "modifiers": {"hp": -3},
                    },
                    {"code": "paralyze", "label": "癱瘓", "severity": "critical"},
                    {"code": "shield", "label": "護盾", "severity": "beneficial", "remaining_seconds": 15},
                    {"code": "chill", "label": "失溫", "severity": "harmful", "remaining_seconds": 8},
                    {"code": "lucky", "label": "幸運", "severity": "informational", "remaining_seconds": 60},
                ]
                character = valid_character_panel()
                _inject_snapshot(page, {"status": status, "character": character}, mode="exploration")
                _wait_mode(page, "exploration")
                self._open_status_drawer(page)
                page.wait_for_selector('[data-testid="character-status-drawer__condition--regen"]', timeout=15000)

                fit = page.evaluate(
                    """() => {
                      const body = document.querySelector('.hud-drawer__body');
                      if (!body) return { ok: false, reason: 'drawer body missing' };
                      const bodyRect = body.getBoundingClientRect();
                      const tiles = Array.from(document.querySelectorAll(
                        '[data-testid^="character-status-drawer__vital--"], ' +
                        '[data-testid^="character-status-drawer__trait--"], ' +
                        '[data-testid="character-status-drawer__guild-rank"], ' +
                        '[data-testid="character-status-drawer__guild-merit"]'));
                      const pills = Array.from(document.querySelectorAll('.character-status-drawer__pill'));
                      const els = [...tiles, ...pills];
                      // Per-element overflow: a tile or pill whose text content
                      // is wider than its own box would scroll internally.
                      for (const el of els) {
                        if (el.scrollWidth > el.clientWidth + 1) {
                          return { ok: false, reason: 'element content overflows its box' };
                        }
                      }
                      const boxes = els.map((el) => el.getBoundingClientRect());
                      // Non-intersection pattern (fix-webclient-local-map-node-crowding):
                      // no two tiles/pills may overlap.
                      for (let i = 0; i < boxes.length; i++) {
                        for (let j = i + 1; j < boxes.length; j++) {
                          const a = boxes[i], b = boxes[j];
                          const overlap = !(
                            a.right <= b.left || b.right <= a.left ||
                            a.bottom <= b.top || b.bottom <= a.top
                          );
                          if (overlap) return { ok: false, reason: 'tile/pill pair overlaps' };
                        }
                      }
                      // Boundary: no tile/pill spills past the drawer's horizontal
                      // content box; any box intersecting the body's visible area
                      // must not be clipped at the body's top or bottom edge.
                      for (const box of boxes) {
                        if (box.left < bodyRect.left || box.right > bodyRect.right) {
                          return { ok: false, reason: 'box outside drawer horizontal bounds' };
                        }
                      }
                      for (const box of boxes) {
                        const intersects = box.top < bodyRect.bottom + 1 && box.bottom > bodyRect.top - 1;
                        if (intersects && (box.top < bodyRect.top - 1 || box.bottom > bodyRect.bottom + 1)) {
                          return { ok: false, reason: 'box clipped at the drawer body edge' };
                        }
                      }
                      // No unexpected horizontal overflow in the drawer body.
                      if (body.scrollWidth > body.clientWidth + 1) {
                        return { ok: false, reason: 'drawer body has horizontal overflow' };
                      }
                      return { ok: true, tileCount: tiles.length, pillCount: pills.length };
                    }"""
                )
                self.assertTrue(fit["ok"], f"status drawer tiles and pills fit at {viewport}: {fit}")
                self.assertEqual(fit["pillCount"], 9, "all 9 conditions render as pills")
                self.assertEqual(fit["tileCount"], 6, "3 vitals + 1 trait + 2 guild tiles render")
                # Visual evidence for the design-alignment check (task 6.5).
                if viewport == (1440, 900):
                    page.screenshot(path=f"tmp/status_drawer_{viewport[0]}x{viewport[1]}.png")
                page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
