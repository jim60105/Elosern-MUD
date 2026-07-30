"""Tests for partial skill conferral."""

import inspect

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.skill_effects import record_conferred_grant
from world.skills.handler import SkillHandler


class ConferredSkillTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="grant recipient")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        return entity

    def test_fractional_grant_scales_the_source_skill_multiplier(self):
        entity = self._entity()
        entity.traits.atk_phys.base = 60
        record_conferred_grant(
            entity,
            "elosia",
            "body_enhancement",
            ("atk_phys", "agility", "defense"),
            0.1,
        )
        self.assertEqual(entity.skills.effective_value("atk_phys"), 600)

    def test_grant_write_does_not_check_source_or_ownership(self):
        entity = self._entity()
        before = entity.traits.atk_phys.value
        record_conferred_grant(
            entity,
            "unknown source",
            "unknown skill",
            ("atk_phys",),
            0.5,
        )
        grant = entity.skills.conferred_grants()[0]
        self.assertEqual(grant.source_key, "unknown source")
        self.assertEqual(grant.skill_key, "unknown skill")
        self.assertEqual(grant.trait_keys, ("atk_phys",))
        self.assertEqual(grant.scale, 0.5)
        self.assertEqual(entity.skills.effective_value("atk_phys"), before)

    def test_skill_handler_has_no_grant_mutator(self):
        self.assertFalse(hasattr(SkillHandler, "grant_conferred"))
        for name, method in inspect.getmembers(SkillHandler, inspect.isfunction):
            self.assertNotIn("ConferredSkillGrant(", inspect.getsource(method))

    def test_grant_survives_database_serialization_round_trip(self):
        entity = self._entity()
        record_conferred_grant(
            entity,
            "elosia",
            "body_enhancement",
            ("atk_phys",),
            0.1,
        )

        reloaded = ObjectDB.objects.get(pk=entity.pk)

        grant = reloaded.db.skill_grants[0]
        self.assertEqual(grant.source_key, "elosia")
        self.assertEqual(grant.skill_key, "body_enhancement")
        self.assertEqual(grant.trait_keys, ("atk_phys",))
        self.assertEqual(grant.scale, 0.1)
