"""Tests for partial skill conferral."""

from tools.spec_traceability import covers_requirement

import inspect

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import RejectReason, RejectedAction
from world.rules.skill_effects import record_conferred_grant
from world.skills.handler import SkillHandler


class ConferredSkillTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="grant recipient")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_fractional_grant_scales_the_source_skill_multiplier(self):
        entity = self._entity()
        entity.traits.atk_phys.base = 60
        record_conferred_grant(entity, "elosia", "body_enhancement", 0.1)
        self.assertEqual(entity.skills.effective_value("atk_phys"), 600)

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
        record_conferred_grant(entity, "elosia", "body_enhancement", 0.1)

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        grant = reloaded.db.skill_grants[0]
        self.assertEqual(grant.source_key, "elosia")
        self.assertEqual(grant.skill_key, "body_enhancement")
        self.assertEqual(grant.scale, 0.1)

    def _assert_gate_type_rejected(self, skill_key: str):
        entity = self._entity()
        with self.assertRaises(RejectedAction) as raised:
            record_conferred_grant(entity, "elosia", skill_key, 0.5)
        self.assertIs(raised.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(entity.skills.conferred_grants(), [])

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_element_mastery_skill_is_structurally_rejected(self):
        self._assert_gate_type_rejected("fire_mastery")

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_sexual_mastery_skill_is_structurally_rejected(self):
        self._assert_gate_type_rejected("reincarnation_boon_yuna")

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_disguise_skill_is_structurally_rejected(self):
        self._assert_gate_type_rejected("status_disguise")

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_damage_only_skill_is_rejected_as_a_silent_no_op(self):
        self._assert_gate_type_rejected("fire_ball")

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_flavor_only_skill_is_rejected_as_a_silent_no_op(self):
        self._assert_gate_type_rejected("elf_longevity")

    @covers_requirement("skill-handler::a-skill-can-confer-a-scaled-down-partial-effect-of-another-entity-s-skill-\u7d71\u5fa1\u8853")
    def test_continuous_effect_skills_remain_conferrable(self):
        entity = self._entity()
        record_conferred_grant(entity, "elosia", "defense_instinct", 0.5)
        grant = entity.skills.conferred_grants()[0]
        self.assertEqual(grant.skill_key, "defense_instinct")
