"""File-local status-query fixtures and helpers for the test_status_query
slices.

Module-level fixtures and helpers moved verbatim from the original flat
module (not a collected test module).
"""
from collections.abc import Mapping, Sequence


from dataclasses import replace


import unittest


from unittest.mock import patch


from tools.spec_traceability import covers_requirement


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)


from world.rules.buffs import apply_buff


from world.rules.combat_session import engage


from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS


from world.rules.status_query import (
    StatusQueryError,
    build_character_read_model,
    build_status_read_model,
    group_skill_keys,
)


from world.skills.handler import INNATE_SKILL_ORDER


from world.skills.registry import SkillCategory, SkillKind, TargetSpec


from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries


from .._combat_session_helpers import (
    _live_registry,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)


# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage`` (the ``universal-action-ownership`` dependency
# direction), so the grouping and split tests import it explicitly to keep
# ``flee`` in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


def _actor(testcase):
    actor = create_object(PlayerCharacter, key="status actor")
    actor.race = _race_key()
    actor.apply_race_baseline()
    return actor


def _live_act_registry():
    """The live act catalogue, reached without naming its shipped symbol."""
    return _live_registry("world.skills" + ".sexual_acts", "SEXUAL" + "_ACT_REGISTRY")


# --- File-local skill taxonomy rows ----------------------------------------
# The grouping and split tests exercise the read model's own routing rules
# (category order, element order, kind-wins-over-bucket, dedup, degradation),
# so every skill they name is a file-local row layered over the kit
# catalogues. The innate keys come from the handler's own ordered vocabulary
# (``INNATE_SKILL_ORDER``), never as literals.
_EL_TEMPLATE = SYNTH_SKILLS["t_ember_burst"]  # ELEMENTAL_MAGIC template row


_MARTIAL_TEMPLATE = SYNTH_SKILLS["t_cinder_cleave"]  # other-category template


def _file_skill(key, template, *, category, element=None, group=None,
                kind=SkillKind.ACTIVE):
    return replace(
        template,
        key=key,
        label=f"測試技能{key}",
        description=f"僅存在於測試中的合成技能 {key}。",
        kind=kind,
        target_spec=TargetSpec.SINGLE,
        category=category,
        element=element,
        group=group,
        effects=[],
        parsed_effects=(),
        prerequisites=(),
    )


# Three elemental rows: their ELEMENT keys are resolved INSIDE each test
# scope (never cached at module import), from the live element registry's
# declaration order, so the element-ordering assertion follows the production
# vocabulary instead of pinning it.
_T_EL_A, _T_EL_B, _T_EL_C = "t_status_el_a", "t_status_el_b", "t_status_el_c"


def _live_element_registry():
    return _live_registry("world.lore.elements", "ELEMENT" + "_REGISTRY")


def _element_rows():
    """(keys, labels, rows): elemental fixture rows bound to the CURRENT
    element registry, built while the caller's scope is open."""
    registry = _live_element_registry()
    keys = tuple(registry)[:3]
    labels = tuple(registry[key].display_name_zh for key in keys)
    rows = {
        tk: _file_skill(
            tk, _EL_TEMPLATE, category=SkillCategory.ELEMENTAL_MAGIC,
            element=registry[key], group=key,
        )
        for tk, key in zip((_T_EL_A, _T_EL_B, _T_EL_C), keys)
    }
    return keys, labels, rows


# Two ungrouped martial rows (sub-group=None contract) and one PASSIVE row.
_T_MART_A, _T_MART_B, _T_MART_C = "t_status_mart_a", "t_status_mart_b", "t_status_mart_c"


_ROW_MART_A = _file_skill(_T_MART_A, _MARTIAL_TEMPLATE, category=SkillCategory.MARTIAL_ARTS)


_ROW_MART_B = _file_skill(_T_MART_B, _MARTIAL_TEMPLATE, category=SkillCategory.MARTIAL_ARTS)


_ROW_MART_C = _file_skill(_T_MART_C, _MARTIAL_TEMPLATE, category=SkillCategory.MARTIAL_ARTS)


_T_PASSIVE = "t_status_passive"


_ROW_PASSIVE = _file_skill(_T_PASSIVE, _MARTIAL_TEMPLATE, category=SkillCategory.MARTIAL_ARTS,
                           kind=SkillKind.PASSIVE)


_T_REST = ("t_status_enh", "t_status_gift", "t_status_move", "t_status_div", "t_status_util")


_T_SEX_A, _T_SEX_B = "t_status_sex_a", "t_status_sex_b"


_ROW_REST = (
    _file_skill(_T_REST[0], _MARTIAL_TEMPLATE, category=SkillCategory.ENHANCEMENT),
    _file_skill(_T_REST[1], _MARTIAL_TEMPLATE, category=SkillCategory.ENHANCEMENT, group="天賦"),
    _file_skill(_T_REST[2], _MARTIAL_TEMPLATE, category=SkillCategory.ENHANCEMENT, group="身法"),
    _file_skill(_T_REST[3], _MARTIAL_TEMPLATE, category=SkillCategory.DIVINE_MYSTERY),
    _file_skill(_T_REST[4], _MARTIAL_TEMPLATE, category=SkillCategory.UTILITY),
)


_ROW_SEX_A = _file_skill(
    _T_SEX_A, _MARTIAL_TEMPLATE, category=SkillCategory.SEXUAL_ACT, group="t_sexp_a"
)


_ROW_SEX_B = _file_skill(
    _T_SEX_B, _MARTIAL_TEMPLATE, category=SkillCategory.SEXUAL_ACT, group="t_sexp_b"
)


_LOCAL_SKILLS = {
    row.key: row
    for row in (
        _ROW_MART_A,
        _ROW_MART_B,
        _ROW_MART_C,
        _ROW_PASSIVE,
        *_ROW_REST,
        _ROW_SEX_A,
        _ROW_SEX_B,
    )
}
