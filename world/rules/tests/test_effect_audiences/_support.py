"""Shared fixtures and the MockContext harness for the test_effect_audiences
slices.

Module-level fixtures moved verbatim from the original flat module (not a
collected test module).
"""
from copy import deepcopy


from dataclasses import replace


import importlib


import unittest


from unittest.mock import patch


from tools.spec_traceability import covers_requirement


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTestCase


from typeclasses.characters import PlayerCharacter


from typeclasses.rooms import Room


from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    RejectedAction,
    _stored_trait_value,
    plan_effect_audiences,
)


from world.rules.action_preview import (
    _applicable_shorthands,
    preview_skill,
    revalidate_submission,
)


from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
)


from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)


from world.rules.targeting import (
    ActionContext,
    Relation,
    RoomActionContext,
    TargetRequirement,
)


from world.rules.tests.combat_fixtures import FakeEntity


from world.skills.effects import (
    ActorSexualEventEffect,
    ClampShameEffect,
    ClimaxExtensionStageEffect,
    DamageEffect,
    DivinePleasureMaxEffect,
    EffectAudience,
    EffectPolicy,
    HealEffect,
    MarkSubmissionEffect,
    RestorePurityEffect,
    SaturateSensitivityEffect,
    SelfBuffApplyEffect,
    SelfHealEffect,
    SexualDrainEffect,
    TargetSexualEventEffect,
)


from world.skills.registry import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    _skill,
    _spell,
)


from world.tests.synthetic_data import REGISTRY_TARGETS


class MockContext:
    """Lightweight ActionContext implementation for pure planning unit tests."""

    def __init__(
        self,
        relations: dict[tuple[str, str], Relation] | None = None,
        present: set[tuple[str, str]] | None = None,
        in_range: set[tuple[str, str]] | None = None,
        battlefield: Battlefield | None = None,
    ):
        self.relations = relations or {}
        self.present = present
        self.in_range = in_range
        self.battlefield = battlefield
        self.event_context: dict = {}

    def is_present(self, actor: FakeEntity, target: FakeEntity) -> bool:
        if self.present is None:
            return True
        return (actor.key, target.key) in self.present

    def relation_to(self, actor: FakeEntity, target: FakeEntity) -> Relation:
        if actor is target or actor.key == target.key:
            return Relation.SELF
        return self.relations.get((actor.key, target.key), Relation.ENEMY)

    def is_in_range(self, actor: FakeEntity, target: FakeEntity) -> bool:
        if self.in_range is None:
            return True
        return (actor.key, target.key) in self.in_range


