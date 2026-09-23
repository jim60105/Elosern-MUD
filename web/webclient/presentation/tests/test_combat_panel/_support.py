"""Shared module-level helpers for the ``context_actions`` test package."""

import unittest
from dataclasses import replace
from evennia.utils.create import create_object
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from web.webclient.presentation.combat_panel import SESSION_STATES
from world.rules.dialogue import DialogueDefinition, KeywordResponse
from world.rules.tests._combat_session_helpers import synth_innate_overlay
from world.tests.synthetic_data import SYNTH_ACT, SYNTH_SKILLS


# Kit identities: the synthetic cast skill and the kit sexual act (its
# SEXUAL_ACT-category row carries the invented line name "t_合成").
T_EMBER = SYNTH_SKILLS["t_ember_burst"].key


T_ACT = SYNTH_ACT.key


# Kit-authored scripted-dialogue row: the maximal-room hosts' keyword pools
# render from this row under a dialogue scope.
T_DIALOGUE_KEY = "t_combat_lodgekeeper"


# The maximal-room test counts six scripted keywords per host, so this file
# authors its own six-response dialogue row (the kit default carries two).
_T_DIALOGUE_ROW = DialogueDefinition(
    greeting="櫃檯後的人抬起眼：「有事說一聲就好。」",
    responses=tuple(
        KeywordResponse(f"合成關鍵詞{index}", f"「合成回應{index}。」")
        for index in range(6)
    ),
)


# File-local martial twin (the kit martial template under a distinct key).
_T_MARTIAL_PROBE = "t_combat_martial_probe"


# The panel's own recovery-session state constant: the recovery-form fixture
# names the wire value through the presenter's public constant rather than
# repeating a token the session-state catalog also spells.
_T_RECOVERY_STATE = next(state for state in SESSION_STATES if state != "ready")


def _t_context_skill(base_key: str, key: str, label: str, effects):
    """A file-local kit-row twin for the handler-context seam."""
    return replace(SYNTH_SKILLS[base_key], key=key, label=label, effects=list(effects))


def _presenter_scope_extra():
    """One skills overlay: innates plus this file's probe rows."""
    skills = dict(synth_innate_overlay()["skills"])
    from world.skills.registry.data_church import ROWS as CHURCH_ROWS
    for row in CHURCH_ROWS:
        skills[row.key] = row
    disguise = _t_context_skill(
        "t_moss_veil", "t_combat_disguise_probe", "偽裝試探", ["set_disguise"]
    )
    confer = _t_context_skill(
        "t_hush_mend", "t_combat_confer_probe", "授予試探", ["confer_skill_partial"]
    )
    martial = _t_context_skill(
        "t_cinder_cleave", _T_MARTIAL_PROBE, "合成斬擊", []
    )
    skills.update(
        {disguise.key: disguise, confer.key: confer, martial.key: martial}
    )
    return {"skills": skills}


def _valid_skill(**overrides):
    # Fixture identities come from the kit rows the schema mirrors: the kit
    # burst's own key/label/element, so no shipped skill token appears.
    value = {
        "key": T_EMBER,
        "label": SYNTH_SKILLS["t_ember_burst"].label,
        "description": SYNTH_SKILLS["t_ember_burst"].description,
        "cost": {"mp": 20},
        "target_spec": "single",
        "element": SYNTH_SKILLS["t_ember_burst"].element.key,
        "enabled": True,
        "disabled_reason": None,
        "targets": [2],
        "shorthands": [],
    }
    value.update(overrides)
    return value


def _valid_skill_group(**overrides):
    value = {
        "group": T_EMBER,
        "label": SYNTH_SKILLS["t_ember_burst"].label,
        "skills": [_valid_skill()],
    }
    value.update(overrides)
    return value


def _valid_category_group(**overrides):
    value = {
        "category": "elemental_magic",
        "label": "元素魔法",
        "groups": [_valid_skill_group()],
    }
    value.update(overrides)
    return value


def _valid_participant(**overrides):
    value = {
        "identity": 2,
        "token": "e1",
        "display_name": "goblin",
        "team": "foes",
        "state": "active",
        "hp_current": 100,
        "hp_maximum": 100,
        "portrait_ref": None,
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 5,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "round": 0,
            "state": "ready",
            "reason": None,
        },
        "participants": [_valid_participant()],
        "root_actions": ["attack", "skills", "items", "defend", "flee"],
        "secondary_actions": ["forfeit"],
        "skills": [_valid_category_group()],
        "suggestions": {"status": "unavailable"},
    }
    value.update(overrides)
    return value


def _recovery_panel(**overrides):
    value = {
        "schema_version": 5,
        "available": True,
        "kind": "combat",
        "session": {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "round": 2,
            "state": _T_RECOVERY_STATE,
            "reason": {"code": "missing_participant", "message": "戰鬥成員已無法確認。"},
        },
        "participants": [],
        "root_actions": [],
        "secondary_actions": ["forfeit"],
        "skills": [],
        "suggestions": {"status": "unavailable"},
    }
    value.update(overrides)
    return value


def _player(key="panel player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


def _exploration_panel(**overrides):
    value = {
        "schema_version": 5,
        "available": True,
        "kind": "exploration",
        "affordances": [
            {
                "action_id": "explore.look",
                "label": "南門",
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "action_id": "explore.talk_scripted",
                "label": "註冊",
                "params": {"npc_id": 5, "keyword_id": "註冊"},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
        ],
        "suggestions": {"status": "unavailable"},
    }
    value.update(overrides)
    return value


def _suggestion_card(**overrides):
    value = {
        "kind": "known_action",
        "action_code": "explore.look",
        "label": "查看房間",
        "params": {"room": True},
    }
    value.update(overrides)
    return value


def _ready_suggestions(count=3):
    cards = [
        _suggestion_card(),
        _suggestion_card(action_code="explore.wait", label="等待片刻", params={"daypart": "noon"}),
        _suggestion_card(label="查看木箱", params={"target_id": 9}),
        _suggestion_card(label="前往東邊", params={"target_id": 9}),
        _suggestion_card(label="查看南門", params={"target_id": 9}),
        _suggestion_card(label="查看北門", params={"target_id": 9}),
    ]
    return {"status": "ready", "cards": cards[:count]}


def _monster(key="panel goblin", hp=100):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    return monster
