"""Regression tests for the display-only disguise boundary."""

from tools.spec_traceability import covers_requirement

import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.skill_effects import apply_disguise_effect
from world.tests.synthetic_data import make_skill, synthetic_registries

# A synthetic disguise-shaped skill row owns the storage slot the boundary
# must never reach past; invented keys throughout keep the assertion about
# the boundary, not about shipped content.
_T_CLOAK = make_skill("t_status_cloak", effects=["set_disguise"])


@synthetic_registries(
    "skills",
    "races",
    "subraces",
    "static_tiers",
    "elements",
    "items",
    "sexual_acts",
    extra={"skills": {_T_CLOAK.key: _T_CLOAK}},
)
class DisguiseEffectTests(EvenniaTestCase):
    def test_effect_changes_only_disguise_storage(self):
        entity = create_object(PlayerCharacter, key="disguised")
        entity.race = "t_duskmari"
        entity.subrace = "t_duskmari_evensong"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [_T_CLOAK.key], "passive": []}
        entity.db.equipment = {"weapon_main": "t_iron_fang"}
        entity.db.inventory = ["t_ember_spray"]
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

    @covers_requirement("skill-handler::the-\u72c0\u614b\u507d\u88dd-skill-s-effect-resolution-can-only-ever-touch-disguised-stats-never-entity-traits")
    def test_effect_source_has_no_trait_or_display_accessor(self):
        source = inspect.getsource(apply_disguise_effect)
        self.assertNotIn("entity.traits", source)
        self.assertNotIn("get_display_value", source)
