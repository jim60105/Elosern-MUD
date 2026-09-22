"""Data-contract test: saintess vessel registry and preset grant contract

Row-shape and grant-surface contract for the 聖女容器 (``saintess_vessel``)
clergy qualifier passive (saintess-vessel D1): same qualifier-row shape as
its three siblings, practice-unearnable through the pre-existing PASSIVE
guards, non-conferrable, absent from every lineage/unlock table, and granted
only through the shipped Saintess preset activation — which banks the
passive and emits exactly one commit-bound ``saintess_vessel_granted``
event.

Shipped registry/preset keys appear literally because this module IS the
shipped-content contract for those rows (the test-data-independence gate
exempts tagged data-contract tests).
"""

import re
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.characters import PlayerCharacter

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules import cross_lineage_unlock
from world.rules.character_creation import (
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.progression import grant_skill_practice_xp, grant_study_practice_xp
from world.rules.skill_effects import validate_conferrable_skill
from world.rules.skill_ownership import owns_stored_skill
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind

VESSEL_KEY = "saintess_vessel"
PRESET_KEY = "violet_altoria"
GRANT_EVENT = "saintess_vessel_granted"
CLERGY_SIBLINGS = ("pain_to_pleasure", "rapture_renewal", "priestly_grace")

_CJK_RE = re.compile(r"[\u3400-\u9fff]")


class SaintessVesselRegistryContractTests(EvenniaTestCase):
    """The vessel row exists with the clergy qualifier shape."""

    def test_row_shape_matches_the_clergy_qualifier_contract(self):
        skill = SKILL_REGISTRY[VESSEL_KEY]
        self.assertIs(skill.kind, SkillKind.PASSIVE)
        self.assertTrue(skill.usable_out_of_combat)
        self.assertIs(skill.element, ELEMENT_REGISTRY["light"])
        self.assertIs(skill.category, SkillCategory.ENHANCEMENT)
        self.assertFalse(skill.effects, "the qualifier row carries no effects")
        self.assertFalse(skill.prerequisites, "no lineage prerequisites")
        self.assertTrue(skill.label)
        self.assertTrue(skill.description)
        self.assertTrue(_CJK_RE.search(skill.label))
        self.assertTrue(_CJK_RE.search(skill.description))

    def test_row_is_registered_immediately_after_priestly_grace(self):
        keys = list(SKILL_REGISTRY)
        self.assertEqual(
            keys.index(VESSEL_KEY), keys.index("priestly_grace") + 1
        )

    def test_vessel_is_not_a_node_in_any_genealogy_or_unlock_rule(self):
        # No shipped skill lists the vessel as a prerequisite edge...
        self.assertTrue(
            all(
                VESSEL_KEY
                not in {edge.skill_key for edge in skill.prerequisites}
                for skill in SKILL_REGISTRY.values()
            )
        )
        # ...no cross-lineage rule samples or grants it.
        rulebook = cross_lineage_unlock.RULEBOOK
        self.assertNotIn(VESSEL_KEY, rulebook.reverse_index)
        self.assertTrue(
            all(VESSEL_KEY not in rule.grants for rule in rulebook.rules)
        )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-granted-only-clergy-qualifier-passive")
    def test_practice_awards_reject_the_passive_key(self):
        entity = create_object(PlayerCharacter, key="vessel practice probe")
        entity.race = "human"
        entity.apply_race_baseline()
        self.assertFalse(
            grant_skill_practice_xp(entity, VESSEL_KEY, target=entity),
            "use-driven practice must refuse a PASSIVE skill",
        )
        self.assertFalse(
            grant_study_practice_xp(entity, VESSEL_KEY, 2),
            "booked study must refuse a PASSIVE skill",
        )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-granted-only-clergy-qualifier-passive")
    def test_cross_lineage_engine_rejects_the_passive_as_a_scope_node(self):
        # A rule scoping the vessel as a practice-proficiency node must fail
        # closed at load: only ACTIVE nodes hold practice proficiency.
        from world.rules.cross_lineage_unlock import load_rules

        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            load_rules(
                [
                    {
                        "id": "t_vessel_scope",
                        "requires": [
                            {
                                "scope": {"keys": [VESSEL_KEY]},
                                "min_level": 1,
                            }
                        ],
                        "grants": ["pain_to_pleasure"],
                    }
                ]
            )

    @covers_requirement("saintess-vessel::saintess-vessel-is-a-granted-only-clergy-qualifier-passive")
    def test_vessel_is_not_conferrable_like_its_siblings(self):
        from world.rules.action import RejectedAction

        for key in (*CLERGY_SIBLINGS, VESSEL_KEY):
            with self.subTest(key=key):
                with self.assertRaises(RejectedAction):
                    validate_conferrable_skill(key)


class SaintessVesselPresetGrantTests(EvenniaTest):
    """The shipped Saintess preset carries the vessel at activation."""

    def test_preset_activation_banks_the_passive_and_emits_one_grant_event(self):
        self.assertTrue(
            VESSEL_KEY in PLAYER_PRESET_REGISTRY[PRESET_KEY].passive_skills,
            "the Saintess card must declare the vessel passive",
        )
        holder = self.char1
        holder.race = "human"
        holder.apply_race_baseline()
        self.account.at_post_create_character(holder)
        with (
            patch("world.rules.character_creation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            activate_player_character(
                self.account,
                holder,
                CharacterCreationRequest(mode="preset", preset_key=PRESET_KEY),
            )
        self.assertIn(VESSEL_KEY, holder.db.skills["passive"])
        self.assertTrue(owns_stored_skill(holder, VESSEL_KEY))
        events = [call.args[0] for call in info.call_args_list if call.args]
        self.assertEqual(events, [GRANT_EVENT], "exactly one grant event at commit")
        (event,), kwargs = info.call_args
        self.assertEqual(kwargs["context"]["entity"], str(holder))
        self.assertEqual(kwargs["context"]["source"], "preset")
        self.assertEqual(kwargs["context"]["passive"], VESSEL_KEY)