"""Behaviour tests for the four C7b 神之秘法 acts.

Covers the delta spec's scenarios for the four hand-built acts — 感度創世
(sensitivity saturation), 恥辱剝奪 (permanent shame pinning, eager Monster
rejection), 絕對從屬 (permanent auto-comply mark keyed by the caster's unique
database id), 無垢回歸 (purity restoration) — plus the race gate, the
seven-entry ``DIVINE_ACTS`` growth with the first three pairs unchanged, and
the line-agnostic dispatch-table contract of the four new effect prefixes.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.quests.catalog import register_catalog
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    RejectReason,
    _handle_clamp_shame,
    _handle_mark_submission,
    _handle_restore_purity,
    _handle_saturate_sensitivity,
)
from world.rules.sexual_resist import ResistVerdict, resist_verdict
from world.rules.sexual_state import decay_tick
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts.divine import DIVINE_ACTS

_C7A_KEYS = ("divine_extreme_climax_command", "divine_timed_copulation", "divine_realm_drain")
_MUTATOR_KEYS = (
    "divine_sensitivity_creation",
    "divine_shame_deprivation",
    "divine_absolute_submission",
    "divine_purity_restoration",
)
_EXPECTED_EFFECTS = {
    "divine_sensitivity_creation": ["divine_saturate_sensitivity:感度創世"],
    "divine_shame_deprivation": ["divine_clamp_shame:恥辱剝奪"],
    "divine_absolute_submission": ["divine_mark_submission:絕對從屬"],
    "divine_purity_restoration": ["divine_restore_purity:無垢回歸"],
}
_C7A_EFFECTS = {
    "divine_extreme_climax_command": ["divine_pleasure_max:絕頂律令"],
    "divine_timed_copulation": ["divine_climax_extension_stage:3"],
    "divine_realm_drain": ["divine_drain:神域搾取"],
}


def _verdict(resisted: bool) -> ResistVerdict:
    """One deterministic resist verdict for the elf-vs-human fixture."""
    return ResistVerdict(
        resisted=resisted,
        auto_comply=False,
        roll=None,
        actor_score=100.0,
        resister_score=100.0,
    )


def _entity(key="divine mutator catalog owner", race="human"):
    entity = create_object(PlayerCharacter, key=key)
    entity.race = race
    entity.apply_race_baseline()
    entity.db.skills = {"active": [], "passive": []}
    return entity


def _monster(key="divine mutator monster"):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier()
    monster.db.skills = {"active": [], "passive": []}
    return monster


def _pairs_by_key(keys):
    return {
        skill.key: (skill, act)
        for skill, act in DIVINE_ACTS
        if skill.key in keys
    }


class DivineMutatorRegistrationTests(unittest.TestCase):
    """The four rows extend DIVINE_ACTS to seven without altering the first three."""

    @covers_requirement("sexual-catalog-divine-mutators::four-hand-built-acts-extend-divine-acts-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_divine_acts_grow_to_seven_with_first_three_unchanged(self):
        self.assertEqual(len(DIVINE_ACTS), 7)
        for key in _C7A_KEYS:
            skill, act = _pairs_by_key(_C7A_KEYS)[key]
            with self.subTest(key=key):
                self.assertEqual(skill.label, {"divine_extreme_climax_command": "絕頂律令", "divine_timed_copulation": "時姦", "divine_realm_drain": "神域搾取"}[key])
                self.assertEqual(skill.effects, _C7A_EFFECTS[key])
                self.assertEqual(act.sexual_events, ())
                self.assertTrue(skill.requires_divine_arts)
                self.assertEqual(act.unlock, {})
                self.assertIsNone(act.target_part)
                self.assertTrue(act.resistible)
                self.assertEqual(act.actor_counters, ())
                self.assertEqual(act.participant_counters, ())

    @covers_requirement("sexual-catalog-divine-mutators::four-hand-built-acts-extend-divine-acts-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_four_new_acts_declare_the_shared_field_values(self):
        pairs = _pairs_by_key(_MUTATOR_KEYS)
        self.assertEqual(set(pairs), set(_MUTATOR_KEYS))
        for key in _MUTATOR_KEYS:
            skill, act = pairs[key]
            with self.subTest(key=key):
                self.assertEqual(skill.key, act.key)
                self.assertIs(skill.target_spec, TargetSpec.SINGLE)
                self.assertTrue(skill.requires_divine_arts)
                self.assertEqual(act.unlock, {})
                self.assertIsNone(act.target_part)
                self.assertTrue(act.resistible)
                self.assertEqual(act.actor_counters, ())
                self.assertEqual(act.participant_counters, ())
                self.assertIs(skill.category.value, "sexual_act")
                self.assertEqual(skill.group, "神之秘法")
                self.assertEqual(skill.cost, {})
                self.assertTrue(skill.usable_out_of_combat)
                self.assertIs(skill.kind, SkillKind.ACTIVE)
                self.assertEqual(skill.effects, _EXPECTED_EFFECTS[key])
                self.assertEqual(act.sexual_events, ())

    def test_placeholder_pleasure_fields_are_documented_not_read(self):
        for key in _MUTATOR_KEYS:
            _, act = _pairs_by_key(_MUTATOR_KEYS)[key]
            with self.subTest(key=key):
                self.assertEqual(act.base_pleasure, 1)
                self.assertEqual(act.actor_pleasure_ratio, 0.0)
                self.assertIsNone(act.actor_part)


class DivineMutatorCastTests(EvenniaTest):
    """Casting the four acts through ActionResolver."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = _entity("divine mutator caster", race="elf")
        self.actor.location = self.room1
        self.target = _entity("divine mutator target")
        self.target.location = self.room1

    def _cast(self, act_key, targets, context=None):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                context or RoomActionContext(self.actor.location, {}),
            )
        )

    @covers_requirement("sexual-catalog-divine-mutators::four-hand-built-acts-extend-divine-acts-gated-exclusively-by-requires-divine-arts-with-no-counter-unlock")
    def test_non_divine_race_cannot_cast_any_of_the_four(self):
        human = _entity("non-divine mutator caster")
        human.location = self.room1
        for key in _MUTATOR_KEYS:
            with self.subTest(key=key):
                with patch("world.rules.action.roll_d100", return_value=1):
                    result = ActionResolver.resolve(
                        ActionRequest(
                            human,
                            key,
                            [self.target],
                            RoomActionContext(human.location, {}),
                        )
                    )
                self.assertIs(result.reason, RejectReason.DIVINE_ARTS_FORBIDDEN)

    @covers_requirement("sexual-catalog-divine-mutators::感度創世-saturates-the-target-s-sensitivity-excluding-the-actor-and-tolerating-a-resisted-cast")
    def test_sensitivity_creation_saturates_every_named_body_part(self):
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_sensitivity_creation", [self.target])
        self.assertEqual(result.outcome, "success")
        for part in BODY_PARTS:
            with self.subTest(part=part):
                self.assertEqual(
                    self.target.sexual.sensitivity[part].level,
                    "敏感異常",
                )
        self.assertEqual(len(self.actor.sexual.sensitivity.items()), 0)

    @covers_requirement("sexual-catalog-divine-mutators::感度創世-saturates-the-target-s-sensitivity-excluding-the-actor-and-tolerating-a-resisted-cast")
    def test_sensitivity_creation_resisted_cast_is_a_no_op(self):
        with patch("world.rules.sexual_resist.resist_verdict", return_value=_verdict(True)):
            result = self._cast("divine_sensitivity_creation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(len(self.target.sexual.sensitivity.items()), 0)
        self.assertIsNone(result.reason)

    @covers_requirement("sexual-catalog-divine-mutators::恥辱剝奪-pins-the-target-s-shame-at-成癮-eagerly-rejecting-a-monster-target-before-staging-any-mutation")
    def test_shame_deprivation_pins_shame_and_survives_decay(self):
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_shame_deprivation", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.shame.level, "成癮")
        self.target.attributes.add(
            "decay_elapsed__shame",
            1800,
            category="sexual_state",
        )
        decay_tick(self.target, 1)
        self.assertEqual(self.target.sexual.shame.level, "成癮")
        self.assertEqual(self.target.sexual.shame.value, 4)

    @covers_requirement("sexual-catalog-divine-mutators::恥辱剝奪-pins-the-target-s-shame-at-成癮-eagerly-rejecting-a-monster-target-before-staging-any-mutation")
    def test_shame_deprivation_at_monster_is_rejected_before_any_mutation(self):
        monster = _monster("shame-deprivation monster")
        monster.location = self.room1
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_shame_deprivation", [monster])
        self.assertIs(result.outcome, "rejected")
        self.assertIs(
            result.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )
        self.assertIsNot(result.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(monster.sexual.shame.level, "無")

    @covers_requirement("sexual-catalog-divine-mutators::絕對從屬-marks-the-target-as-permanently-auto-complying-toward-the-caster-keyed-by-a-guaranteed-unique-identity")
    def test_absolute_submission_makes_future_contests_auto_comply(self):
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_absolute_submission", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.target.sexual.submission_marks,
            frozenset({str(self.actor.id)}),
        )
        verdict = resist_verdict(self.actor, self.target, rng=lambda: 1)
        self.assertFalse(verdict.resisted)
        self.assertTrue(verdict.auto_comply)
        self.assertIsNone(verdict.roll)

    @covers_requirement("sexual-catalog-divine-mutators::絕對從屬-marks-the-target-as-permanently-auto-complying-toward-the-caster-keyed-by-a-guaranteed-unique-identity")
    def test_submission_mark_does_not_affect_a_different_actor(self):
        other = _entity("unrelated mutator caster", race="elf")
        other.location = self.room1
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_absolute_submission", [self.target])
        self.assertEqual(result.outcome, "success")
        verdict = resist_verdict(other, self.target, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertIsNotNone(verdict.roll)

    @covers_requirement("sexual-catalog-divine-mutators::絕對從屬-marks-the-target-as-permanently-auto-complying-toward-the-caster-keyed-by-a-guaranteed-unique-identity")
    def test_two_entities_sharing_a_key_are_not_confused_by_the_mark(self):
        # Two distinct entities with the same .key (the wilderness monster
        # spawn shape from wilderness_population.py); the mark is stored keyed
        # by str(actor.id), so the same-key impostor's distinct id never
        # matches it.
        self.actor = _entity("shared-key caster", race="elf")
        self.actor.location = self.room1
        impostor = _entity("shared-key caster", race="elf")
        impostor.location = self.room1
        self.assertEqual(self.actor.key, impostor.key)
        self.assertNotEqual(self.actor.id, impostor.id)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_absolute_submission", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.target.sexual.submission_marks,
            frozenset({str(self.actor.id)}),
        )
        verdict = resist_verdict(impostor, self.target, rng=lambda: 1)
        self.assertFalse(verdict.auto_comply)
        self.assertIsNotNone(verdict.roll)

    @covers_requirement("sexual-catalog-divine-mutators::無垢回歸-restores-the-target-s-virgin-flag-without-touching-experience-types")
    def test_purity_restoration_reverses_false_virgin(self):
        self.target.sexual.virgin = False
        self.target.sexual.add_experience_type("陰道性交")
        self.assertFalse(self.target.sexual.virgin)
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("divine_purity_restoration", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertTrue(self.target.sexual.virgin)
        self.assertEqual(
            self.target.sexual.experience_types,
            frozenset({"陰道性交"}),
        )

    @covers_requirement("sexual-catalog-divine-mutators::無垢回歸-restores-the-target-s-virgin-flag-without-touching-experience-types")
    def test_purity_restoration_resisted_cast_is_a_no_op(self):
        self.target.sexual.virgin = False
        with patch("world.rules.sexual_resist.resist_verdict", return_value=_verdict(True)):
            result = self._cast("divine_purity_restoration", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.target.sexual.virgin)

    def test_resisted_absolute_submission_plants_no_mark(self):
        with patch("world.rules.sexual_resist.resist_verdict", return_value=_verdict(True)):
            result = self._cast("divine_absolute_submission", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.submission_marks, frozenset())


class DivineMutatorHandlerDirectTests(EvenniaTest):
    """The four handlers are line-agnostic dispatch-table entries."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = _entity("direct mutator handler actor", race="elf")
        self.target = _entity("direct mutator handler target")
        self.target.location = self.actor.location

    def test_handlers_filter_the_actor_present_in_targets(self):
        for handler, effect_id, probe in (
            (
                _handle_saturate_sensitivity,
                "divine_saturate_sensitivity:感度創世",
                lambda entity: entity.sexual.sensitivity["私處"].level,
            ),
            (
                _handle_clamp_shame,
                "divine_clamp_shame:恥辱剝奪",
                lambda entity: entity.sexual.shame.level,
            ),
            (
                _handle_mark_submission,
                "divine_mark_submission:絕對從屬",
                lambda entity: entity.sexual.submission_marks,
            ),
            (
                _handle_restore_purity,
                "divine_restore_purity:無垢回歸",
                lambda entity: entity.sexual.virgin,
            ),
        ):
            with self.subTest(handler=handler.__name__):
                before = probe(self.actor)
                pending = handler(
                    self.actor,
                    [self.actor, self.target],
                    effect_id,
                    {},
                    1.0,
                )
                self.assertEqual(len(pending), 1)
                for effect in pending:
                    effect.apply()
                self.assertEqual(probe(self.actor), before)

    def test_empty_targets_is_a_no_op_for_all_four(self):
        for handler, effect_id in (
            (_handle_saturate_sensitivity, "divine_saturate_sensitivity:感度創世"),
            (_handle_clamp_shame, "divine_clamp_shame:恥辱剝奪"),
            (_handle_mark_submission, "divine_mark_submission:絕對從屬"),
            (_handle_restore_purity, "divine_restore_purity:無垢回歸"),
        ):
            with self.subTest(handler=handler.__name__):
                self.assertEqual(
                    handler(self.actor, [], effect_id, {}, 1.0),
                    [],
                )

    def test_clamp_shame_handler_rejects_monster_eagerly(self):
        monster = _monster("direct clamp monster")
        monster.location = self.actor.location
        with self.assertRaises(Exception) as caught:
            _handle_clamp_shame(
                self.actor,
                [monster],
                "divine_clamp_shame:恥辱剝奪",
                {},
                1.0,
            )
        self.assertEqual(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )
        self.assertEqual(monster.sexual.shame.level, "無")

    @covers_requirement("sexual-catalog-divine-mutators::the-four-new-effect-prefixes-are-line-agnostic-dispatch-table-entries")
    def test_handlers_do_not_branch_on_requires_divine_arts(self):
        # A hypothetical non-divine SkillDef naming the divine_mark_submission
        # prefix resolves through the same handler without rejection: the
        # handlers read only their resolved targets, never the caller's line.
        fake_skill = SkillDef(
            key="hypothetical_non_divine_mark_act",
            label="假設性行為",
            description="僅存在於測試中的非神之秘法技能，宣告神之秘法的效果前綴。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=["divine_mark_submission:test"],
            category=SKILL_REGISTRY["divine_absolute_submission"].category,
            group="關係",
        )
        self.assertFalse(fake_skill.requires_divine_arts)
        self.assertEqual(
            fake_skill.parsed_effects[0].__class__.__name__,
            "MarkSubmissionEffect",
        )
        pending = _handle_mark_submission(
            self.actor,
            [self.target],
            "divine_mark_submission:test",
            {},
            1.0,
        )
        self.assertEqual(len(pending), 1)
        for effect in pending:
            effect.apply()
        self.assertEqual(
            self.target.sexual.submission_marks,
            frozenset({str(self.actor.id)}),
        )
