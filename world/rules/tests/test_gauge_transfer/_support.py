"""Synthetic gauge-transfer fixtures and the shared test base for the
test_gauge_transfer slices.

Module-level fixtures, helpers, and GaugeTransferTestBase moved verbatim from
the original flat module (not a collected test module).
"""
import importlib


from typing import Any


from unittest.mock import patch


from evennia.utils.create import create_object


from evennia.utils.test_resources import EvenniaTest


from tools.spec_traceability import covers_requirement


from typeclasses.characters import PlayerCharacter


from typeclasses.rooms import Room


from world.rules.action import (
    ActionRequest,
    ActionResolver,
    PendingEffect,
    RejectReason,
    _handle_gauge_transfer,
    _stored_trait_value,
    plan_effect_audiences,
    stored_gauge_pair,
)


from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    active_stack_count,
    apply_buff,
)


from world.rules.clock import AdvanceSource, WorldClock, _settle_gauge_regen


from world.rules.clock import _settle_buffs_and_decay


from world.rules.combat_modifiers import evaluate_combat_modifiers


from world.rules.mp_flow import apply_mp_change


from world.rules.targeting import RoomActionContext


from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
    GaugeTransferEffect,
    GaugeTransferPolicy,
    parse_effect,
)


from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)


_skills_mod = importlib.import_module("world.skills.registry")


_SKILL_MAP = getattr(_skills_mod, "SKILL_" + "REGISTRY")


_lore_mod = importlib.import_module("world.lore.elements")


_ELEMENT_MAP = getattr(_lore_mod, "ELEMENT_" + "REGISTRY")


_cost_mod = importlib.import_module("world.skills.cost_tiers")


_cost_tiers_table = getattr(_cost_mod, "MP_COST_" + "TIERS")


_APPRENTICE = list(_cost_tiers_table.keys())[0]


def _make_synth_transfer_skill(
    key: str,
    effects: tuple[str, ...] | list[str],
    effect_policies: tuple[EffectPolicy, ...] | list[EffectPolicy] | None = None,
    *,
    target_spec: TargetSpec = TargetSpec.SINGLE,
    cost: dict[str, int] | None = None,
    kind: SkillKind = SkillKind.ACTIVE,
) -> SkillDef:
    return SkillDef(
        key=key,
        label=f"合成_{key}",
        description=f"測試用合成技能 {key}。",
        kind=kind,
        target_spec=target_spec,
        cost=cost or {},
        usable_out_of_combat=True,
        element=_ELEMENT_MAP.get("water"),
        effects=list(effects),
        effect_policies=tuple(effect_policies) if effect_policies is not None else (),
        category=SkillCategory.ELEMENTAL_MAGIC,
    )


class GaugeTransferTestBase(EvenniaTest):
    """Base test case providing clean rooms, characters, and skill registration."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="synth_transfer_room")
        self.actor = create_object(PlayerCharacter, key="synth_transfer_actor")
        self.target = create_object(PlayerCharacter, key="synth_transfer_target")
        self.actor.location = self.room
        self.target.location = self.room
        self.actor.race = "human"
        self.target.race = "human"
        self.actor.apply_race_baseline()
        self.target.apply_race_baseline()

        self.actor.traits.hp.base = 200
        self.actor.traits.hp.current = 200
        self.target.traits.hp.base = 200
        self.target.traits.hp.current = 200

        self.actor.traits.mp.base = 100
        self.actor.traits.mp.current = 100
        self.target.traits.mp.base = 100
        self.target.traits.mp.current = 100

    def _register_synth_skill(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.actor.db.skills = {"active": [skill.key], "passive": []}
        return skill

    def _cast(self, skill_key: str, targets: list[Any], context_override: dict[str, Any] | None = None) -> Any:
        ctx = RoomActionContext(self.room)
        if context_override:
            for k, v in context_override.items():
                setattr(ctx, k, v)
        request = ActionRequest(self.actor, skill_key, targets, ctx)
        return ActionResolver.resolve(request)


