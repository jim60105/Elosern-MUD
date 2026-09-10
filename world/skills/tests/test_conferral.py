"""Tests for partial skill conferral."""

from tools.spec_traceability import covers_requirement

import inspect

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import RejectReason, RejectedAction
from world.rules.skill_effects import record_conferred_grant
from world.skills.handler import SkillHandler
from world.tests.synthetic_data import make_skill, synthetic_registries

# Synthetic conferral fixtures. The gate is structural (continuous-valued
# effect present, no gate-type effect), so each shape is built from invented
# rows; no shipped skill key can substitute for the shape it demonstrates.
_T_GRANT = make_skill("t_tide_march", effects=["stat_multiply:atk_phys:100"])
_T_RULE = make_skill("t_rule_step", effects=["passive_buff:t_rule_key"])
_T_GATE_DISGUISE = make_skill("t_gate_disguise", effects=["set_disguise"])
_T_GATE_SEXUAL = make_skill("t_gate_sexual", effects=["sexual_magic_mastery"])
_T_FLAVOR_ONLY = make_skill("t_ash_flavor", effects=["passive_trait:t_ash_flavor"])
_T_DAMAGE_ONLY = make_skill("t_spark_jab", effects=["damage:t_dummy:physical"])

_SCOPE = synthetic_registries(
    "skills",
    "races",
    "subraces",
    "static_tiers",
    "elements",
    "items",
    "sexual_acts",
    extra={
        "skills": {
            skill.key: skill
            for skill in (
                _T_GRANT,
                _T_RULE,
                _T_GATE_DISGUISE,
                _T_GATE_SEXUAL,
                _T_FLAVOR_ONLY,
                _T_DAMAGE_ONLY,
            )
        }
    },
)


@_SCOPE
class ConferredSkillTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="grant recipient")
        entity.race = "t_duskmari"
        entity.subrace = "t_duskmari_evensong"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_fractional_grant_scales_the_source_skill_multiplier(self):
        entity = self._entity()
        entity.traits.atk_phys.base = 60
        record_conferred_grant(entity, "t_synth_source", _T_GRANT.key, 0.1)
        # The multiplier's source of truth is the fixture itself.
        multiplier = _T_GRANT.parsed_effects[0].multiplier
        self.assertEqual(
            entity.skills.effective_value("atk_phys"), round(60 * multiplier * 0.1)
        )

    def test_grant_write_does_not_check_source_or_ownership(self):
        entity = self._entity()
        before = entity.traits.atk_phys.value
        record_conferred_grant(entity, "unknown source", "unknown skill", 0.5)
        grant = entity.skills.conferred_grants()[0]
        self.assertEqual(grant.source_key, "unknown source")
        self.assertEqual(grant.skill_key, "unknown skill")
        self.assertEqual(grant.scale, 0.5)
        self.assertEqual(entity.skills.effective_value("atk_phys"), before)

    def test_skill_handler_has_no_grant_mutator(self):
        self.assertFalse(hasattr(SkillHandler, "grant_conferred"))
        for name, method in inspect.getmembers(SkillHandler, inspect.isfunction):
            self.assertNotIn("ConferredSkillGrant(", inspect.getsource(method))

    def test_grant_survives_database_serialization_round_trip(self):
        entity = self._entity()
        record_conferred_grant(entity, "t_synth_source", _T_GRANT.key, 0.1)

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        grant = reloaded.db.skill_grants[0]
        self.assertEqual(grant.source_key, "t_synth_source")
        self.assertEqual(grant.skill_key, _T_GRANT.key)
        self.assertEqual(grant.scale, 0.1)

    def _assert_gate_type_rejected(self, skill_key: str):
        entity = self._entity()
        with self.assertRaises(RejectedAction) as raised:
            record_conferred_grant(entity, "t_synth_source", skill_key, 0.5)
        self.assertIs(raised.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(entity.skills.conferred_grants(), [])

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_disguise_gate_type_skill_is_rejected(self):
        self._assert_gate_type_rejected(_T_GATE_DISGUISE.key)

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_sexual_mastery_gate_type_skill_is_rejected(self):
        self._assert_gate_type_rejected(_T_GATE_SEXUAL.key)

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_damage_only_skill_is_rejected_as_a_silent_no_op(self):
        self._assert_gate_type_rejected(_T_DAMAGE_ONLY.key)

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_flavor_only_skill_is_rejected_as_a_silent_no_op(self):
        self._assert_gate_type_rejected(_T_FLAVOR_ONLY.key)

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_continuous_effect_skills_remain_conferrable(self):
        entity = self._entity()
        record_conferred_grant(entity, "t_synth_source", _T_GRANT.key, 0.5)
        record_conferred_grant(entity, "t_synth_source", _T_RULE.key, 0.5)
        keys = [grant.skill_key for grant in entity.skills.conferred_grants()]
        self.assertEqual(keys, [_T_GRANT.key, _T_RULE.key])
