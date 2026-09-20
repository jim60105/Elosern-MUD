"""Synthetic progression fixtures and helpers for the `test_progression` slices.

Module-level fixtures, helpers, and the synthetic skill tree moved verbatim
from the original flat module (not a collected test module).
"""
import inspect


import unittest


from dataclasses import replace


from tools.spec_traceability import covers_requirement


from unittest.mock import patch


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from typeclasses.monsters import Monster


from typeclasses.rooms import Room


from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    _EVENT_EFFECT_PLANNERS,
    _commit,
)


from world.rules.action_preview import preview_skill


from world.rules.buffs import grant_conferred_growth_rate


from world.rules.combat import Battlefield, BattlefieldActionContext, run_round


from world.rules.progression import (
    AFFINITY_ELEMENT_MULTIPLIER,
    NON_AFFINITY_ELEMENT_MULTIPLIER,
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    element_affinity_multiplier,
    grant_skill_practice_xp,
    skill_proficiency_level,
)


from world.rules.targeting import RoomActionContext


import world.rules.progression as progression


from world.tests.synthetic_data import (
    SYNTH_GLOWMIRE_ELEMENT,
    SYNTH_RACES,
    SYNTH_SKILLS,
    make_race,
    make_skill,
)


from ..combat_fixtures import grant_lineage


from .._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    SYNTH_GLOW_ELEMENT,
    live_skill_registry,
    SYNTH_SEAM_AREA_SKILL,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
    synth_lineage_tree,
    synth_lineage_tree_magic,
    _live_registry,
)


from world.skills.registry import (
    SkillCategory,
    SkillKind,
    validate_prerequisite_graph,
)


# Cross-lineage wiring: importing the rulebook module at collection time also
# forces its shipped-table load against the LIVE registry, before any
# synthetic scope clears it (the shared helpers' eager import is the same
# guarantee for sibling modules in other shard processes).
import world.rules.cross_lineage_unlock as cross_lineage


# The file's synthetic vocabulary. A martial drill skill for single-target
# practice, an area strike for multi-target accrual, an expensive spell for
# the affordability fallback, and a fast-learning race for the multiplier
# math. None of these rows exist in a shipped catalog.
_T_DRILL = synth_damage_skill("t_shadow_drill", "影刃練習")


_T_GALE = synth_damage_skill(
    "t_gale_cascade", "瀉風連斬", target_spec=_T_DRILL.target_spec.__class__.AREA
)


_T_HEAVY_SPELL = synth_damage_skill(
    "t_ember_deluge",
    "燼洪術",
    cost={"mp": 30},
    category=_live_registry("world.skills.registry", "SkillCategory").ELEMENTAL_MAGIC,
)


# Scoped growth-rate fixtures: a synthetic elemental spell of the borrowed
# shipped element (elemental magic by construction), an invented-element spell
# the scoped registry also carries, and PASSIVE growth rows scoped to the
# borrowed element. Scope strings are derived from the spell's own element key
# at import, so no shipped identifier is pinned in this file; the borrowed
# element's key IS a shipped element, so the rows parse at import time against
# the shipped registry and again inside the synthetic scope.
_T_FIRE_SPELL = synth_damage_skill(
    "t_scorch_salvo",
    "灼焰齊射",
    effects=(f"damage:{SYNTH_SKILLS['t_ember_burst'].element.key}:magic",),
)


_T_GLOW_SPELL = replace(
    _T_FIRE_SPELL,
    key="t_glowmire_surge",
    label="光沼湧流",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    element=SYNTH_GLOWMIRE_ELEMENT,
)


_T_GROWTH_FIRE = replace(
    _T_DRILL,
    key="t_growth_windfall",
    label="成長恩惠",
    kind=SkillKind.PASSIVE,
    category=SkillCategory.ENHANCEMENT,
    effects=[f"growth_rate:practice:5:{_T_FIRE_SPELL.element.key}"],
)


_T_GROWTH_FIRE2 = replace(
    _T_GROWTH_FIRE,
    key="t_growth_bounty",
    label="成長豐饒",
    effects=[f"growth_rate:practice:7:{_T_FIRE_SPELL.element.key}"],
)


_T_GROWTH_DUP = replace(
    _T_GROWTH_FIRE,
    key="t_growth_duplicate",
    label="成長重疊",
    effects=[
        f"growth_rate:practice:5:{_T_FIRE_SPELL.element.key}",
        f"growth_rate:practice:7:{_T_FIRE_SPELL.element.key}",
    ],
)


_T_PLAIN_DRILL = make_skill("t_plain_drill")


# The cross-lineage wiring grant: a synthetic PASSIVE the rulebook is allowed
# to grant. It lives only in the wiring rulebook's registry — never in the
# scoped skill registry — because the grant writer resolves kinds through the
# rulebook's own validated mapping.
_T_GRANTED = replace(
    _T_DRILL,
    key="t_sword_insight",
    label="領悟劍式",
    kind=SkillKind.PASSIVE,
    category=SkillCategory.ENHANCEMENT,
)


SWIFT_LEARNER = make_race(
    "t_swift_learner",
    learning_multiplier=10.0,
    description="學得極快的合成測試種族。",
)


_ALL_SKILLS = {
    _T_DRILL.key: _T_DRILL,
    _T_GALE.key: _T_GALE,
    _T_HEAVY_SPELL.key: _T_HEAVY_SPELL,
    _T_FIRE_SPELL.key: _T_FIRE_SPELL,
    _T_GLOW_SPELL.key: _T_GLOW_SPELL,
    _T_GROWTH_FIRE.key: _T_GROWTH_FIRE,
    _T_GROWTH_FIRE2.key: _T_GROWTH_FIRE2,
    _T_GROWTH_DUP.key: _T_GROWTH_DUP,
    _T_PLAIN_DRILL.key: _T_PLAIN_DRILL,
    SYNTH_SEAM_AREA_SKILL.key: SYNTH_SEAM_AREA_SKILL,
    **synth_lineage_tree(),
    **synth_lineage_tree_magic(),
}


# The unlock fixture crosses a spell-wording edge, so it uses the
# ELEMENTAL_MAGIC variant tree: caster + its Lv.3 prerequisite plus the
# blocked downstream node.
MAGIC_TREE = synth_lineage_tree_magic()


_MAGIC_CASTER = "magic_t_tree_sprout"


_MAGIC_CHILD = "magic_t_tree_branch"


def _tree_child_label() -> str:
    """The label unlock_line must render, read from the tree row itself."""
    return MAGIC_TREE[_MAGIC_CHILD].label


def _scoped_setup(test):
    """Kit scope covering every fixture this module builds."""
    # Re-validate the lineage caches against the RESTORED registry after
    # this scope exits (cleanup runs last; patch.dict restores in place).
    test.addCleanup(validate_prerequisite_graph, live_skill_registry())
    open_synthetic_scope(
        test,
        "skills",
        "elements",
        "races",
        "subraces",
        "static_tiers",
        extra={
            "skills": {
                **_ALL_SKILLS,
                **synth_innate_overlay()["skills"],
            },
            "races": {SWIFT_LEARNER.key: SWIFT_LEARNER, **SYNTH_RACES},
        },
    )
    # Bind the reverse-edge caches to the scoped rows for this test.
    validate_prerequisite_graph(live_skill_registry())


def _character(test, key: str, race: str | None = None) -> PlayerCharacter:
    entity = create_object(PlayerCharacter, key=key)
    entity.race = _race_key() if race is None else race
    entity.apply_race_baseline()
    return entity


def _monster(test, key: str) -> Monster:
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    return monster


