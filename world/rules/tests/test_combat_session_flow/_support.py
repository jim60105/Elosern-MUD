"""Synthetic combat-session-flow fixtures and helpers for the
test_combat_session_flow slices.

Module-level fixtures and helpers moved verbatim from the original flat
module (not a collected test module).
"""
from tools.spec_traceability import covers_requirement


import inspect


from pathlib import Path


import unittest


from unittest.mock import patch


from dataclasses import replace


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase


from typeclasses.monsters import Monster


from typeclasses.npcs import NPC


from typeclasses.rooms import Room


from commands.action import CmdCast


from world.quests.catalog import register_catalog


from world.quests.tests._fixtures import QuestRegistryIsolation


from world.rules.action import ActionRequest, ActionResolver, RejectReason


from world.rules.clock import WorldClock


from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)


from world.rules.overwhelm import classify_overwhelm


from world.rules.event_log import render_plain_text


from world.rules.party import join_party


from world.rules.combat_session import BASIC_ATTACK_KEY


from world.skills.registry import SkillKind, TargetSpec


from world.tests.synthetic_data import SYNTH_SKILLS, make_skill


from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)


from ..combat_fixtures import grant_lineage


SEAM_AREA_KEY = SYNTH_SEAM_AREA_SKILL.key


_T_CAST = SYNTH_SKILLS["t_ember_burst"].key


_T_PASSIVE = SYNTH_SKILLS["t_steady_stride"].key


# Non-damaging zero-cost active with no targets: the round-path opener and
# the first-strike carrier (the shipped concentrate analogue).
_T_FOCUS = make_skill(
    "t_still_breath", label="靜息", effects=[], target_spec=TargetSpec.NONE
)


# The same AREA template at zero MP cost for the 2-MP seam casters.
_T_SEAM_CASCADE = replace(SYNTH_SEAM_AREA_SKILL, cost={})


def _innate_keys():
    """The innate roster from the (patched) live surfaces, never a literal."""
    attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    flee_key = _live_registry("world.rules.disengage", "FLEE_SKILL_KEY")
    innate = _live_registry("world.skills.handler", "INNATE_SKILL_KEYS")
    act_registry = _live_registry("world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY")
    unlock_free = sorted(key for key, act in act_registry.items() if not act.unlock)
    return attack_key, flee_key, innate, unlock_free


def _live_registry(dotted: str, attribute: str):
    import importlib

    return getattr(importlib.import_module(dotted), attribute)


def _open_scope(test, *, monster_tiers=True, **extra_skills):
    skills = dict(synth_innate_overlay()["skills"])
    skills[SYNTH_SEAM_AREA_SKILL.key] = SYNTH_SEAM_AREA_SKILL
    skills[_T_SEAM_CASCADE.key] = _T_SEAM_CASCADE
    skills[_T_FOCUS.key] = _T_FOCUS
    skills.update(extra_skills)
    logicals = ["skills", "elements", "sexual_acts", "races", "subraces", "static_tiers"]
    if monster_tiers:
        logicals.append("monster_tiers")
    open_synthetic_scope(
        test,
        *logicals,
        extra={"skills": skills},
    )


def _basic_attack_row():
    """The innate attack row as the patched registry serves it."""
    attack_key = _live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")
    registry = _live_registry("world.skills.registry", "SKILL_REGISTRY")
    return registry[attack_key]


