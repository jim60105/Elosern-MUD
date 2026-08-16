"""Integration tests for skill ownership and effective trait values."""

from tools.spec_traceability import covers_requirement

import ast
import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.races import RACE_REGISTRY
from world.rules.traits import STATIC_KEYS
from world.skills import handler
from world.skills.effects import StatMultiplyEffect
from world.skills.handler import _matching_multiplier
from world.skills.registry import SKILL_REGISTRY
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY


# A fresh entity owns only the unconditionally-unlocked acts; counter-gated
# catalogue rows stay absent until their thresholds are met.
def _fresh_entity_act_keys():
    return sorted(
        key for key, act in SEXUAL_ACT_REGISTRY.items() if not act.unlock
    )


class SkillHandlerTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="skill tester")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    @covers_requirement("skill-handler::skillhandler-is-mounted-directly-as-entity-skills")
    def test_handler_reads_private_storage_and_has_no_bare_assignment(self):
        entity = self._entity()
        entity.db.skills = None
        self.assertEqual(
            entity.skills.owned_keys(),
            ["flee", "basic_attack", *_fresh_entity_act_keys()],
        )
        with self.assertRaises(AttributeError):
            entity.skills = {"active": [], "passive": []}

        entity.db.skills = {
            "active": ["fire_ball"],
            "passive": ["defense_instinct"],
        }
        self.assertEqual(
            entity.skills.owned_keys(),
            [
                "fire_ball",
                "defense_instinct",
                "flee",
                "basic_attack",
                *_fresh_entity_act_keys(),
            ],
        )

    @covers_requirement("universal-action-ownership::innate-ownership-is-unconditional-and-not-combat-gated")
    def test_flee_is_innate_for_bare_monster_and_not_combat_gated(self):
        monster = create_object(Monster, key="bare monster")
        monster.db.skills = None
        before = monster.skills.owned_keys()
        monster.db.current_battlefield = object()
        after = monster.skills.owned_keys()
        self.assertEqual(
            before, ["flee", "basic_attack", *_fresh_entity_act_keys()]
        )
        self.assertEqual(after, before)

    @covers_requirement("universal-action-ownership::world-skills-does-not-depend-on-world-rules-to-define-innate-ownership")
    def test_skill_handler_has_no_rules_dependency(self):
        source = inspect.getsource(handler)
        self.assertNotIn("world.rules", source)

    @covers_requirement("skill-handler::effective-value-is-the-sole-resolution-time-multiplier-application-point-and-never-writes-to-entity-traits")
    def test_effective_value_multiplies_without_mutating_base(self):
        entity = self._entity()
        entity.db.skills = {
            "active": ["body_enhancement_extreme"],
            "passive": [],
        }
        before = entity.traits.atk_phys.value
        self.assertEqual(entity.skills.effective_value("atk_phys"), before * 1000)
        self.assertEqual(entity.traits.atk_phys.value, before)

        entity.db.skills = {"active": ["fire_ball"], "passive": []}
        self.assertEqual(entity.skills.effective_value("atk_phys"), before)

    @covers_requirement("skill-registry::body-enhancement-family-is-passive-not-active")
    def test_passive_ownership_still_applies_the_multiplier(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [],
            "passive": ["body_enhancement_extreme"],
        }
        before = entity.traits.atk_phys.value
        self.assertEqual(entity.skills.effective_value("atk_phys"), before * 1000)

    def test_duplicate_owned_key_is_resolution_idempotent(self):
        entity = self._entity()
        entity.db.skills = {
            "active": ["body_enhancement", "body_enhancement"],
            "passive": [],
        }
        base = entity.traits.atk_phys.value
        self.assertEqual(entity.skills.effective_value("atk_phys"), base * 100)

    def test_effective_value_never_moves_static_bases_out_of_race_bands(self):
        entity = self._entity()
        entity.db.skills = {
            "active": [
                "body_enhancement",
                "body_enhancement_extreme",
                "body_enhancement_basic",
            ],
            "passive": [],
        }
        for _ in range(3):
            for key in STATIC_KEYS:
                entity.skills.effective_value(key)
        race = RACE_REGISTRY["human"]
        for key in STATIC_KEYS:
            lower, upper = getattr(race.static_baseline, key)
            self.assertLessEqual(lower, getattr(entity.traits, key).base)
            self.assertLessEqual(getattr(entity.traits, key).base, upper)

    def test_matching_multiplier_reads_typed_effects(self):
        skill = SKILL_REGISTRY["body_enhancement"]
        self.assertEqual(
            _matching_multiplier(skill.parsed_effects, "atk_phys"),
            100.0,
        )
        self.assertIsNone(_matching_multiplier(skill.parsed_effects, "magic_level"))
        self.assertIsNone(_matching_multiplier((), "atk_phys"))
        duplicate = (
            StatMultiplyEffect(trait="atk_phys", multiplier=2.0),
            StatMultiplyEffect(trait="atk_phys", multiplier=3.0),
        )
        with self.assertRaises(ValueError):
            _matching_multiplier(duplicate, "atk_phys")

    def test_handler_source_never_assigns_to_traits(self):
        tree = ast.parse(inspect.getsource(handler))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                self.assertNotIn(".traits", ast.unparse(target))
