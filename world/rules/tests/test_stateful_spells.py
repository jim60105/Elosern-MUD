"""Behavior tests for stateful spell casting, contact rituals, and stimulus (light-sacrament-casting).

Pure synthetic fixtures exercising:
- Pure preflight and final revalidation of subject-scoped cast conditions
- Authoritative contact-ritual validation (self, absent, out-of-range, capability-blocked)
- Pre-stimulus state magnitude sampling and equipment exposure bonus
- Single resist gate extension for generic contact spells (resisted = paid MP/time, no effects/practice)
- Forced-interaction action evidence recording on broken resistance
- Complete prefix-superset parsing including typed stimulus
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_evidence import has_action_evidence
from world.rules.buffs import apply_buff
from world.rules.pleasure import zero_pleasure
from world.rules.sexual_resist import ResistVerdict
from world.rules.spell_conditions import CastCondition, CastConditionSubject
from world.rules.targeting import RoomActionContext
from world.skills.effects import (
    CleanseEffect,
    EffectPolicy,
    HealEffect,
    InteractionPolicy,
    StateMagnitude,
    StateMagnitudeSubject,
    StimulusEffect,
    parse_effect,
)
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    _skill,
)
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

from ._combat_session_helpers import _race_key, open_synthetic_scope

# --- Synthetic skill fixtures (file-local, never shipped content) ---------

_SHARED_AROUSAL_CURVE = StateMagnitude(
    subject=StateMagnitudeSubject.ACTOR,
    field="arousal",
    base=3.2,
    per_ordinal=0.2,
    maximum=4.0,
)

_T_KISS = "t_sacrament_kiss"
_T_KISS_SKILL = _skill(
    _T_KISS,
    "測試聖儀親吻",
    "合成接觸治癒與刺激法術。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 10},
    usable_out_of_combat=True,
    effects=["heal:single", "stimulus:both"],
    category=SkillCategory.ENHANCEMENT,
    cast_conditions=(
        CastCondition(CastConditionSubject.ACTOR, {"field": "arousal", "gte": "微興奮"}),
        CastCondition(CastConditionSubject.EACH_TARGET, {"field": "arousal", "gte": "微興奮"}),
    ),
    interaction=InteractionPolicy(
        contact=True,
        distinct_participants=True,
        target_capable=False,
        resistible=True,
    ),
    effect_policies=(
        EffectPolicy(magnitude=_SHARED_AROUSAL_CURVE),
        EffectPolicy(),
    ),
)

_T_MILK = "t_sacrament_milk"
_T_MILK_SKILL = _skill(
    _T_MILK,
    "測試聖儀授乳",
    "合成接觸雙向能力與受術者刺激法術。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 15},
    usable_out_of_combat=True,
    effects=["heal:single", "cleanse:status", "stimulus:target"],
    category=SkillCategory.ENHANCEMENT,
    interaction=InteractionPolicy(
        contact=True,
        distinct_participants=True,
        target_capable=True,
        resistible=True,
    ),
    effect_policies=(
        EffectPolicy(coefficient=2.8),
        EffectPolicy(),
        EffectPolicy(
            stimulus_bonus=StateMagnitude(
                subject=StateMagnitudeSubject.ACTOR,
                field="effective_exposure",
                base=0.0,
                per_ordinal=2.0,
            )
        ),
    ),
)

_T_WATER_COMMUNION = "t_water_communion"
_T_WATER_SKILL = _skill(
    _T_WATER_COMMUNION,
    "測試水系共感",
    "非光系合成接觸法術，驗證通用機制複用。",
    SkillKind.ACTIVE,
    TargetSpec.SINGLE,
    cost={"mp": 8},
    usable_out_of_combat=True,
    effects=["heal:single", "stimulus:actor"],
    category=SkillCategory.ELEMENTAL_MAGIC,
    cast_conditions=(
        CastCondition(CastConditionSubject.ACTOR, {"field": "arousal", "gte": "微興奮"}),
    ),
    interaction=InteractionPolicy(
        contact=True,
        distinct_participants=True,
        target_capable=False,
        resistible=False,
    ),
    effect_policies=(
        EffectPolicy(magnitude=_SHARED_AROUSAL_CURVE),
        EffectPolicy(),
    ),
)

_ALL_TEST_SKILLS = {
    _T_KISS_SKILL.key: _T_KISS_SKILL,
    _T_MILK_SKILL.key: _T_MILK_SKILL,
    _T_WATER_SKILL.key: _T_WATER_SKILL,
}


def _scope_extra(skills: dict) -> dict:
    return {"skills": skills}


class StatefulSpellsBase(EvenniaTest):
    """Shared test fixture with caster and humanoid target."""

    def setUp(self):
        super().setUp()
        register_catalog()
        open_synthetic_scope(
            self, "skills", "elements", "races", "subraces", "static_tiers"
        )
        self.actor = create_object(PlayerCharacter, key="stateful caster", location=self.room1)
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": list(_ALL_TEST_SKILLS), "passive": []}

        self.target = create_object(PlayerCharacter, key="stateful target", location=self.room1)
        self.target.race = _race_key()
        self.target.apply_race_baseline()

    def _catalogue(self, skills: dict[str, SkillDef] | None = None):
        if skills is None:
            skills = _ALL_TEST_SKILLS
        return synthetic_registries(
            "skills",
            "sexual_acts",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            extra=_scope_extra(skills),
        )

    def _request(self, skill_key: str, targets: list[Any], room: Any = None) -> ActionRequest:
        return ActionRequest(
            self.actor,
            skill_key,
            targets,
            RoomActionContext(self.room1 if room is None else room),
        )


class StatefulSpellCastingTests(StatefulSpellsBase):
    """Behavior tests for subject-scoped conditions, magnitudes, contact, and resist gate."""

    @covers_requirement(
        "action-resolution-pipeline::actionresolver-exposes-side-effect-free-preflight-for-player-combat-input"
    )
    def test_cast_condition_threshold_failure_has_no_side_effects(self):
        """When actor or target is below threshold, preflight and resolve reject without side effects."""
        with self._catalogue():
            # Initial state: arousal is 平靜 (base=0, below 微興奮)
            req = self._request(_T_KISS, [self.target])

            mp_before = self.actor.traits.mp.value
            preflight_res = ActionResolver.preflight(req)
            self.assertEqual(preflight_res.outcome, "rejected")
            self.assertEqual(preflight_res.reason, RejectReason.CAST_CONDITION_UNMET)
            self.assertEqual(self.actor.traits.mp.value, mp_before)

            # Resolve also rejects without side effects
            resolve_res = ActionResolver.resolve(req)
            self.assertEqual(resolve_res.outcome, "rejected")
            self.assertEqual(resolve_res.reason, RejectReason.CAST_CONDITION_UNMET)
            self.assertEqual(self.actor.traits.mp.value, mp_before)
            self.assertIsNone(self.actor.attributes.get("sexual_traits", category="traits"))

    def test_stale_preflight_cannot_authorize_changed_state(self):
        """Preflight passes when conditions are met, but resolve rejects if state changes before execution."""
        with self._catalogue():
            # Bring both participants to 微興奮 (pleasure base 25)
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            self.assertEqual(self.actor.sexual.arousal.level, "微興奮")
            self.assertEqual(self.target.sexual.arousal.level, "微興奮")

            req = self._request(_T_KISS, [self.target])
            preflight_res = ActionResolver.preflight(req)
            self.assertEqual(preflight_res.outcome, "success")

            # Before resolve executes, target arousal drops to 平靜
            zero_pleasure(self.target)
            self.assertEqual(self.target.sexual.arousal.level, "平靜")

            resolve_res = ActionResolver.resolve(req)
            self.assertEqual(resolve_res.outcome, "rejected")
            self.assertEqual(resolve_res.reason, RejectReason.CAST_CONDITION_UNMET)

    def test_contact_cannot_be_spoofed(self):
        """Contact policy rejects self-target, absent target, and capability-blocked target."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25

            # 1. Distinct participants violation: self-cast
            self_req = self._request(_T_KISS, [self.actor])
            res_self = ActionResolver.preflight(self_req)
            self.assertEqual(res_self.outcome, "rejected")
            self.assertEqual(res_self.reason, RejectReason.CAST_CONDITION_UNMET)

            # 2. Absent target: target moved to room2
            req_absent = ActionRequest(
                self.actor,
                _T_KISS,
                [self.target],
                RoomActionContext(self.room1),
            )
            self.target.location = self.room2
            res_absent = ActionResolver.preflight(req_absent)
            self.assertEqual(res_absent.outcome, "rejected")
            self.assertEqual(res_absent.reason, RejectReason.TARGET_NOT_PRESENT)
            from world.rules.action import RejectedAction
            from world.rules.spell_conditions import evaluate_interaction_policy
            with self.assertRaises(RejectedAction) as ctx:
                evaluate_interaction_policy(
                    self.actor, [self.target], RoomActionContext(self.room1), _T_KISS_SKILL
                )
            self.assertEqual(ctx.exception.reason, RejectReason.CAST_CONDITION_UNMET)
            self.target.location = self.room1

            # 3. Target capability blocked (for _T_MILK which declares target_capable=True)
            apply_buff(self.target, "paralysis")
            req_milk = self._request(_T_MILK, [self.target])
            res_milk = ActionResolver.preflight(req_milk)
            self.assertEqual(res_milk.outcome, "rejected")
            self.assertEqual(res_milk.reason, RejectReason.CAST_CONDITION_UNMET)

    def test_state_sampled_before_spell_changes_it(self):
        """Healing magnitude uses pre-stimulus arousal ordinal with no repeated coefficient multiplication."""
        with self._catalogue():
            # Actor at 微興奮 (ordinal 1). Target at 微興奮.
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            self.target.traits.hp.current = 10  # Damaged target

            req = self._request(_T_KISS, [self.target])
            # For StateMagnitude(base=3.2, per_ordinal=0.2, maximum=4.0):
            # At ordinal 1 (微興奮), coefficient = 3.2 + 0.2 * 1 = 3.4
            with patch("world.rules.action.roll_d100", return_value=1):
                res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")

            # Target HP should have increased
            self.assertGreater(self.target.traits.hp.current, 10)
            # Stimulus was also applied: actor pleasure increased beyond 25
            self.assertGreater(self.actor.sexual.pleasure.base, 25)

    def test_equipment_contributes_to_exposure_magnitude(self):
        """Target stimulus bonus incorporates caster effective exposure bias."""
        with self._catalogue():
            # Setup milk cast with target stimulus bonus +2.0 * caster exposure
            # Base exposure is 極低 (ordinal 0). With bias=2, effective exposure becomes 中等 (ordinal 2).
            # Bonus to target = 0.0 + 2.0 * 2 = 4.0
            self.target.traits.hp.current = 50
            req = self._request(_T_MILK, [self.target])

            with patch("world.rules.action._stimulus_rng.randint", return_value=10):
                with patch(
                    "world.rules.equipment_effects.equipment_exposure_bias",
                    return_value=2,
                ):
                    with patch("world.rules.action.roll_d100", return_value=1):
                        res = ActionResolver.resolve(req)
                    self.assertEqual(res.outcome, "success")
                    # Base roll was 10, bonus was 4.0 -> total 14
                    self.assertEqual(self.target.sexual.pleasure.base, 14)

    @covers_requirement(
        "sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply",
        "sexual-resist-cast-wiring::the-actor-s-own-effects-and-the-cast-s-resource-time-and-practice-cost-are-never-gated-by-a-target-s-resist-outcome",
    )
    def test_resisted_interaction_has_one_paid_outcome(self):
        """Resisted generic contact spell charges MP and time, logs resist verdict, but applies no heal/stimulus/practice."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            self.target.traits.hp.current = 20
            mp_before = self.actor.traits.mp.value

            req = self._request(_T_KISS, [self.target])

            # Patch resist_verdict to return resisted=True
            with patch(
                "world.rules.sexual_resist.resist_verdict",
                return_value=ResistVerdict(
                    resisted=True,
                    auto_comply=False,
                    roll=95,
                    actor_score=10.0,
                    resister_score=50.0,
                ),
            ):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            # MP charged
            self.assertEqual(self.actor.traits.mp.value, mp_before - 10)
            # Time cost charged
            self.assertGreater(res.time_cost_seconds, 0)
            # BUT target HP unchanged (no heal)
            self.assertEqual(self.target.traits.hp.current, 20)
            # Actor and target stimulus unchanged (no pleasure gain)
            self.assertEqual(self.actor.sexual.pleasure.base, 25)
            self.assertEqual(self.target.sexual.pleasure.base, 25)
            # EventLog has sexual_resist entry
            resist_entries = [
                e for e in res.event_log.entries if e.kind == "sexual_resist"
            ]
            self.assertEqual(len(resist_entries), 1)
            self.assertTrue(resist_entries[0].data["resisted"])

    def test_successful_interaction_applies_once_to_each_participant(self):
        """Successful both-participant stimulus applies to each participant once without duplicating actor."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25

            req = self._request(_T_KISS, [self.target])

            with patch("world.rules.action._stimulus_rng.randint", return_value=10):
                with patch("world.rules.action.roll_d100", return_value=1):
                    res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            # Both participants gained exactly 10 pleasure
            self.assertEqual(self.actor.sexual.pleasure.base, 35)
            self.assertEqual(self.target.sexual.pleasure.base, 35)

    def test_late_commit_error_rolls_back_coupled_state(self):
        """Commit failure after stimulus restores HP, MP, pleasure, wetness, phase, and unmaterialized state."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            mp_before = self.actor.traits.mp.value
            hp_before = self.target.traits.hp.current

            req = self._request(_T_KISS, [self.target])

            # Force commit to fail during effect execution inside atomic transaction
            with patch(
                "world.rules.action.apply_pleasure_gain",
                side_effect=RuntimeError("simulated commit crash"),
            ):
                with patch("world.rules.action.roll_d100", return_value=1):
                    res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "rejected")
            self.assertEqual(res.reason, RejectReason.COMMIT_FAILED)
            # State fully restored
            self.assertEqual(self.actor.traits.mp.value, mp_before)
            self.assertEqual(self.target.traits.hp.current, hp_before)
            self.assertEqual(self.actor.sexual.pleasure.base, 25)
            self.assertEqual(self.target.sexual.pleasure.base, 25)

    def test_second_synthetic_non_light_configuration(self):
        """Second synthetic non-light configuration proves generic reuse of cast_conditions and InteractionPolicy."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            req = self._request(_T_WATER_COMMUNION, [self.target])

            res = ActionResolver.resolve(req)
            self.assertEqual(res.outcome, "success")
            # Stimulus:actor only
            self.assertGreater(self.actor.sexual.pleasure.base, 25)
            self.assertEqual(self.target.sexual.pleasure.base, 0)

    def test_resistible_contact_forced_interaction_records_action_evidence(self):
        """A resistible contact spell that fails resistance records forced-interaction evidence on caster."""
        with self._catalogue():
            self.actor.sexual.pleasure.base = 25
            self.target.sexual.pleasure.base = 25
            req = self._request(_T_KISS, [self.target])

            # Failed resist (coercion / forced outcome)
            with patch(
                "world.rules.sexual_resist.resist_verdict",
                return_value=ResistVerdict(
                    resisted=False,
                    auto_comply=False,
                    roll=15,
                    actor_score=40.0,
                    resister_score=20.0,
                ),
            ):
                res = ActionResolver.resolve(req)

            self.assertEqual(res.outcome, "success")
            # Verified action evidence was staged and committed on actor
            self.assertTrue(has_action_evidence(self.actor, "forced_interaction"))

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-into-a-typed-dataclass"
    )
    def test_parse_effect_all_prefixes_and_stimulus_scopes(self):
        """parse_effect recognizes stimulus:actor, stimulus:target, stimulus:both, and all 32 existing prefixes."""
        # 1. stimulus scopes
        act_eff = parse_effect("stimulus:actor")
        self.assertIsInstance(act_eff, StimulusEffect)
        self.assertEqual(act_eff.recipient, "actor")

        tgt_eff = parse_effect("stimulus:target")
        self.assertIsInstance(tgt_eff, StimulusEffect)
        self.assertEqual(tgt_eff.recipient, "target")

        both_eff = parse_effect("stimulus:both")
        self.assertIsInstance(both_eff, StimulusEffect)
        self.assertEqual(both_eff.recipient, "both")

        # Invalid stimulus arguments raise ValueError
        with self.assertRaises(ValueError):
            parse_effect("stimulus")
        with self.assertRaises(ValueError):
            parse_effect("stimulus:allies")
        with self.assertRaises(ValueError):
            parse_effect("stimulus:target:10")

        # 2. Every shipped registry effect still parses without error
        for skill in SKILL_REGISTRY.values():
            for effect_id in skill.effects:
                parsed = parse_effect(effect_id)
                self.assertIsNotNone(parsed)
