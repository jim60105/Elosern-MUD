"""Shared page-level panel builders and drivers for the split contextual-HUD
browser journey modules.

This module is named ``_journey_support`` (not ``test_*``) so the flat
browser discovery glob never collects it. Every body is byte-identical to
its pre-split home in ``test_browser_contextual_hud.py``; the HUD split
modules plus ``test_browser_lineage`` and ``test_browser_title_codex``
import these helpers from here."""

from __future__ import annotations

import base64
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
        "schema_version": 2,
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

    The knocked-out party member's display name and the featured elemental
    skill row ride the boot mode's catalogs (kit skill row under the
    synthetic install) via the support module's resolver, so this test path
    names no shipped registry content.
    """
    from web.browser_support.browser_fixtures_data import hud_combat_fixture_values

    fixture_values = hud_combat_fixture_values()
    participants = [
        _participant(1, "a1", "勇者", "party", "active", 100, 100, "1"),
        _participant(2, "a2", fixture_values["party_name"], "party", "knocked_out", 40, 100, "2"),
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
                            fixture_values["skill_key"],
                            fixture_values["skill_label"],
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
            "face_rect": {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5},
            "context": {"name": "角色", "role": "人物"},
        }
    return {
        "schema_version": 2,
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


# ``defaults/*`` identities, so an unserved fixture URL would 404 and trip
# the backdrop's load-failure path (the <img> is removed from the DOM),
# racing the presence assertion. Fulfilling the route (the same technique
# test_browser_art uses for its load-failure journey) makes the done scene
# deterministic and keeps the spec scenario's outcome assertion intact
# (webclient-contextual-hud: "A done scene paints the stage").
_SCENE_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


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
