"""Slice of ``test_damage_state_feedback``: DamageStateFeedbackBehaviorTests."""
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

from ._support import (
    T_APPRENTICE,
    T_SAGE,
    _SKILL_MAP,
)


class DamageStateFeedbackBehaviorTests(EvenniaTest):
    """Behavior tests for damage-state-feedback mechanics using synthetic fixtures."""
    def setUp(self):
        super().setUp()
        from typeclasses.rooms import Room
        self.room = create_object(Room, key="synth_room")
        self.actor = create_object(PlayerCharacter, key="synth_actor")
        self.target = create_object(PlayerCharacter, key="synth_target")
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
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.target.traits.mp.base = 500
        self.target.traits.mp.current = 500

    def _register_synth_skill(self, skill: SkillDef) -> SkillDef:
        patcher = patch.dict(_SKILL_MAP, {skill.key: skill}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return skill

    def _register_synth_buff(self, buff: BuffDefinition) -> BuffDefinition:
        patcher = patch.dict(BUFF_DEFINITIONS, {buff.key: buff}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return buff

    def _grant_skill(self, entity: Any, skill_key: str, kind: SkillKind = SkillKind.PASSIVE) -> None:
        skills = dict(entity.db.skills or {"active": [], "passive": []})
        skills["active"] = list(skills.get("active", []))
        skills["passive"] = list(skills.get("passive", []))
        bucket = "passive" if kind == SkillKind.PASSIVE else "active"
        if skill_key not in skills[bucket]:
            skills[bucket].append(skill_key)
        entity.db.skills = skills

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_pleasure_gain_new_shapes_validate(self):
        """The loader accepts the flat integer and the two new derived shapes."""
        validate_state_reaction_rules(
            [
                Rule(
                    id="synth_ok_flat_int",
                    when={"event": "hp_loss"},
                    then={"pleasure_gain": 7},
                ),
                Rule(
                    id="synth_ok_coefficient",
                    when={"event": "hp_loss"},
                    then={"pleasure_gain": {"max_hp_coefficient": 140}},
                ),
                Rule(
                    id="synth_ok_flat_fraction",
                    when={"event": "negative_buff_added"},
                    then={
                        "pleasure_gain": {
                            "max_hp_coefficient": 140,
                            "flat_max_hp_fraction": 0.05,
                        }
                    },
                ),
            ]
        )

    @covers_requirement(
        "damage-state-feedback::damage-feedback-follows-actual-loss-and-newly-accepted-negative-instances"
    )
    def test_pleasure_gain_retired_tier_mapping_fails_load(self):
        """Scenario: A tier-keyed gain mapping fails at load.

        WHEN a rule authors pleasure_gain as a source-tier-keyed mapping
        THEN rule loading raises naming that rule id
        """
        retired = Rule(
            id="synth_retired_tier_rule",
            when={"event": "hp_loss"},
            then={"pleasure_gain": {T_APPRENTICE: 5, T_SAGE: 18}},
        )
        with self.assertRaises(ValueError) as ctx:
            validate_state_reaction_rules([retired])
        self.assertIn("synth_retired_tier_rule", str(ctx.exception))
        self.assertIn(T_APPRENTICE, str(ctx.exception))

        # Malformed new shapes also fail closed naming the rule id.
        for bad_rule in (
            Rule(
                id="synth_missing_coeff",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {"flat_max_hp_fraction": 0.05}},
            ),
            Rule(
                id="synth_bad_coeff",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {"max_hp_coefficient": 0}},
            ),
            Rule(
                id="synth_bad_fraction",
                when={"event": "negative_buff_added"},
                then={
                    "pleasure_gain": {
                        "max_hp_coefficient": 140,
                        "flat_max_hp_fraction": 1.0,
                    }
                },
            ),
            Rule(
                id="synth_empty_mapping",
                when={"event": "hp_loss"},
                then={"pleasure_gain": {}},
            ),
        ):
            with self.assertRaises(ValueError) as ctx:
                validate_state_reaction_rules([bad_rule])
            self.assertIn(bad_rule.id, str(ctx.exception))
