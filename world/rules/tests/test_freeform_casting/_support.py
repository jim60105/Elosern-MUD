"""Synthetic freeform-casting fixtures and helpers for the test_freeform_casting
slices.

Module-level fixtures and helpers moved verbatim from the original flat
module (not a collected test module).
"""
from tools.spec_traceability import covers_requirement


from dataclasses import replace


from unittest.mock import patch


import unittest


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from typeclasses.monsters import Monster


from world.lore.elements import Element


from world.rules.action import ActionRequest, ActionResolver, RejectReason


from world.rules.action_preview import preview_skill, revalidate_submission


from world.rules.clock import WorldClock


from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)


from world.rules.combat_session import engage, submit_player_action


from world.rules.player_messages import rejection_message


from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_LADDER,
    FREEFORM_SCALE_VALUES,
    _load_freeform_cast_scales,
    freeform_mastery_entitled,
    freeform_scale_entries_for,
    freeform_scales_for,
    scale_for_label,
    scale_label_for,
    scaled_magnitude,
    scaled_mp_cost,
)


from world.skills.cost_tiers import is_freeform_eligible


from world.skills.handler import ConferredSkillGrant


from world.skills.registry import SkillCategory, SkillKind, TargetSpec


from world.tests.synthetic_data import SYNTH_SKILLS


from .._combat_session_helpers import (
    _monster_tier_key,
    _race_key,
    _behaviour_archetype_key,
    open_synthetic_scope,
)


from ..combat_fixtures import BattlefieldIsolation, grant_lineage


_T_CAST = SYNTH_SKILLS["t_ember_burst"]  # ACTIVE elemental mp-12 damage spell


_T_ELEMENT = _T_CAST.element.key


def _mastery_key() -> str:
    """The element-mastery passive key the production entitlement derives.

    ``progression.freeform_mastery_entitled`` hardcodes ``f"{element}_mastery"``
    — a production vocabulary (the ``synth_innate_overlay`` precedent), so the
    row is built under the runtime-derived key and the test never names a
    shipped mastery identifier.
    """
    return f"{_T_ELEMENT}_mastery"


def _mastery_row():
    return replace(
        SYNTH_SKILLS["t_steady_stride"],
        key=_mastery_key(),
        label="合成元素精通",
        description="對該元素達到最高造詣的合成被動。",
        effects=["passive_trait:element_mastery"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_T_ELEMENT,
    )


# Expensive sibling on the same element: the high-deduction fixture.
_T_STORM = replace(
    _T_CAST,
    key="t_ember_cascade",
    label="燼焰傾瀑",
    description="連貫的燼焰一波接一波地淹沒目標。",
    cost={"mp": 30},
)


# Beyond-affordable fixture: its ×4 rung exceeds the unaffordable-cast budget.
_T_TYRANT = replace(
    _T_CAST,
    key="t_ember_tyrant",
    label="燼界暴君",
    description="牽動整個燼界的超重合成的法術。",
    cost={"mp": 60},
)


# Pure AREA heal spell: the healing-ceiling / dead-target fixture.
_T_TIDE = replace(
    _T_CAST,
    key="t_tide_mercy",
    label="潮恩",
    description="以暖流覆蓋所有仍可救治的傷者。",
    target_spec=TargetSpec.AREA,
    effects=["heal:area"],
)


# Damage + self-heal mix on a heavy mp cost: the multi-quantity scaling mix.
_T_PHOENIX = replace(
    _T_CAST,
    key="t_ember_phoenix",
    label="燼生鳳翔",
    description="焚燬對手並從餘燼中重塑自身。",
    cost={"mp": 150},
    effects=[f"damage:{_T_ELEMENT}:magic", "self_heal"],
)


# Shape-ineligible spell (damage + buff mix): the gate's ineligible-active case.
_T_MIXED = replace(
    _T_CAST,
    key="t_ember_flurry",
    label="燼屑亂舞",
    description="灼熱燼屑纏身而舞。",
    effects=[f"damage:{_T_ELEMENT}:magic", "buff_apply:t_moss_veil"],
)


# Non-elemental mp-cost skill: the gate's crash-safety case.
_T_FOCUS_MP = replace(
    SYNTH_SKILLS["t_cinder_cleave"],
    key="t_still_mind",
    label="靜心",
    description="凝聚意識的無屬性修練。",
    cost={"mp": 5},
    effects=["self_buff_apply:t_moss_veil"],
)


# SP-only elemental: the no-mp-cost rejection case.
_T_SP_SPELL = replace(
    _T_CAST,
    key="t_ash_fang",
    label="燼牙",
    description="以體力驱动的銳利燼牙。",
    cost={"sp": 12},
)


# Buff-only movement-style self skill: the out-of-combat ineligible case.
_T_VEIL = replace(
    SYNTH_SKILLS["t_moss_veil"],
    key="t_glow_veil",
    label="光燼幕",
    description="召出覆蓋燼屑的防護霧幕。",
    usable_out_of_combat=True,
)


# Out-of-combat-usable shapes for the text-command seam: the room context
# refuses damaging casts (out-of-combat-damage-gate), so the command tests
# cast scalable NON-damage shapes; the scale-token mechanics under test
# (cost scaling, clock advance) are shape-independent.
_T_OOC_HEAL = replace(
    _T_TIDE,
    key="t_ember_soothe",
    label="燼慰",
    description="以微燼暖流安撫傷口。",
    usable_out_of_combat=True,
)


_T_OOC_CAST = replace(
    _T_CAST,
    key="t_ember_gale",
    label="燼風",
    description="吹拂灼熱燼風。",
    usable_out_of_combat=True,
)


# A second-element spell (the kit's own element row): the cross-element gate
# case. The Element instance bypasses pre-patch string resolution while the
# patched registry knows the key.
_T_GLOW = replace(
    _T_CAST,
    key="t_glow_spire",
    label="光沼尖刺",
    description="自光沼抽出一根尖刺貫穿目標。",
    element=Element("t_glowmire", "光沼", "Synthetic element."),
    group="t_glowmire",
    effects=["damage:t_glowmire:magic"],
)


_EXTRA_SKILLS = {
    _T_STORM.key: _T_STORM,
    _T_TYRANT.key: _T_TYRANT,
    _T_TIDE.key: _T_TIDE,
    _T_PHOENIX.key: _T_PHOENIX,
    _T_MIXED.key: _T_MIXED,
    _T_FOCUS_MP.key: _T_FOCUS_MP,
    _T_SP_SPELL.key: _T_SP_SPELL,
    _T_VEIL.key: _T_VEIL,
    _T_OOC_HEAL.key: _T_OOC_HEAL,
    _T_OOC_CAST.key: _T_OOC_CAST,
    _T_GLOW.key: _T_GLOW,
    _mastery_row().key: _mastery_row(),
}


def _open_scope(test):
    open_synthetic_scope(
        test,
        "skills",
        "elements",
        "buffs",
        "sexual_acts",
        "races",
        "subraces",
        "static_tiers",
        extra={"skills": dict(_EXTRA_SKILLS)},
    )


def _player(key="freeform caster"):
    player = create_object(PlayerCharacter, key=key)
    player.race = _race_key()
    player.apply_race_baseline()
    player.traits.magic_power.base = 30
    return player


def _monster(key="freeform wolf"):
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    return monster


def _granted_mastery_only(player: PlayerCharacter) -> None:
    player.db.skill_grants = [ConferredSkillGrant("source", _mastery_key(), 1.0)]


def _owned(*rows) -> dict[str, list[str]]:
    """A ``db.skills`` payload carrying the given rows in active/passive order."""
    return {
        "active": [row.key for row in rows if row.kind is SkillKind.ACTIVE],
        "passive": [row.key for row in rows if row.kind is SkillKind.PASSIVE],
    }


