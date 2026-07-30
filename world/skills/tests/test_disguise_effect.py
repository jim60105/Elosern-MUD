"""Regression tests for the display-only disguise boundary."""

import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.skill_effects import apply_disguise_effect


class DisguiseEffectTests(EvenniaTest):
    def test_effect_changes_only_disguise_storage(self):
        entity = create_object(PlayerCharacter, key="disguised")
        entity.race = "elf"
        entity.apply_race_baseline()
        entity.db.skills = {"active": ["status_disguise"], "passive": []}
        entity.db.equipment = {"weapon_main": "light_sword"}
        entity.db.inventory = ["healing_potion"]
        entity.db.skill_grants = []
        before = {
            key: getattr(entity.traits, key).value
            for key in entity.traits.all()
        }
        before_other_state = {
            "skills": entity.db.skills,
            "equipment": entity.db.equipment,
            "inventory": entity.db.inventory,
            "skill_grants": entity.db.skill_grants,
        }

        apply_disguise_effect(entity, {"atk_phys": 60})

        self.assertEqual(entity.db.disguised_stats, {"atk_phys": 60})
        self.assertEqual(
            {
                key: getattr(entity.traits, key).value
                for key in entity.traits.all()
            },
            before,
        )
        self.assertEqual(
            {
                "skills": entity.db.skills,
                "equipment": entity.db.equipment,
                "inventory": entity.db.inventory,
                "skill_grants": entity.db.skill_grants,
            },
            before_other_state,
        )

    def test_effect_source_has_no_trait_or_display_accessor(self):
        source = inspect.getsource(apply_disguise_effect)
        self.assertNotIn("entity.traits", source)
        self.assertNotIn("get_display_value", source)
