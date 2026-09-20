"""Data-contract test: skill registry content contract
File-local category vocabularies and the pinned availability key set
for the ``test_skill_registry`` slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""

from tools.spec_traceability import covers_requirement
import ast
from dataclasses import fields
import pathlib
import unittest
from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import (
    DamageEffect,
    HealEffect,
    RevealDisguiseEffect,
    SelfHealEffect,
    SexualMasteryEffect,
)
from world.skills.registry import (
    FactionConstraint,
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    prerequisite_consumers,
    validate_prerequisite_graph,
)
from world.rules.progression import proficiency_cap
from ..test_spell_catalogs import _CATALOG_EFFECTS

_CATEGORY_ORDER = [
    SkillCategory.ELEMENTAL_MAGIC,
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.ENHANCEMENT,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.UTILITY,
    SkillCategory.SEXUAL_ACT,
]

_UNGROUPED_CATEGORIES = (
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.UTILITY,
)

_MASTERY_KEYS = frozenset(
    f"{element_key}_mastery"
    for element_key in ELEMENT_REGISTRY
)

#: The frozen ``usable_out_of_combat=False`` inventory. The policy the set
#: encodes (delta spec skill-registry::every-skill-declares-usable-out-of-
#: combat-deliberately-under-one-written-policy): an ACTIVE skill declares
#: True unless casting it with no fight in progress is meaningless (flee —
#: nothing to disengage from), and PASSIVE skills declare True because their
#: continuously-owned effects (stat multipliers, mastery, movement, body
#: enhancement, passive buffs, growth/longevity traits) apply regardless of a
#: battlefield; only a passive whose effect is combat-context-only would
#: declare False. Damage-carrying skills declare True as well: their outside-
#: combat use is exactly opening a fight, which the damaging-action gate
#: (skill-field-availability) then confines to a battlefield. A new skill
#: that omits a decision falls outside this set by the helpers' False
#: default and fails the inventory assertion.
USABLE_OUT_OF_COMBAT_FALSE_KEYS = frozenset({"flee"})
