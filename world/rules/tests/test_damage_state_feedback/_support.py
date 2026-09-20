"""Synthetic skill/tier fixtures shared by the `test_damage_state_feedback` slices.

Module-level fixtures, helpers, and bases moved verbatim from the
original flat module (not a collected test module).
"""

import math
import importlib
from typing import Any
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, PendingEffect
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
    tick_buffs,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield, BattlefieldActionContext, _handle_damage
from world.rules.combat_modifiers import _RULES, evaluate_combat_modifiers
from world.rules.items import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemEffectStep,
    ItemStat,
    ItemTargetScope,
    ItemUseError,
    ItemUsePlan,
    _apply_gauge_step,
)
from world.rules.pleasure import apply_pleasure_gain
from world.rules.rulebook.schema import Rule
from world.rules.sexual_state import EXPOSURE_LEVELS
from world.rules.targeting import RoomActionContext
from world.skills.handler import ConferredSkillGrant
from world.rules.state_reactions import (
    STATE_REACTION_RULES,
    dispatch_outcome_reaction,
    validate_state_reaction_rules,
)
from world.skills.effects import RuleTableEffect
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)

_cost_mod = importlib.import_module("world.skills.cost_tiers")


_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")


_tier_names = list(_cost_tiers_table.keys())


T_APPRENTICE = _tier_names[0]


T_ADEPT = _tier_names[1]


T_MASTER = _tier_names[2]


T_SAGE = _tier_names[3]


T_SOVEREIGN = _tier_names[4]


T_GODHEAD = _tier_names[5]


_skills_mod = importlib.import_module("world.skills.registry")


_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")


_lore_mod = importlib.import_module("world.lore.elements")


_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


def _make_synth_skill(
    key: str,
    kind: SkillKind = SkillKind.ACTIVE,
    element: str | None = None,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    effects: tuple[str, ...] | list[str] = (),
    category: SkillCategory = SkillCategory.ELEMENTAL_MAGIC,
) -> SkillDef:
    elem = _ELEMENT_MAP.get(element) if element is not None else None
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=elem,
        effects=list(effects),
        category=category,
    )
