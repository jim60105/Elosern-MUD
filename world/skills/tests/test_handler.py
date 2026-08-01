"""Integration tests for skill ownership and effective trait values."""

import ast
import inspect

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.races import RACE_REGISTRY
from world.rules.traits import STATIC_KEYS
from world.skills import handler
from world.skills.handler import _matching_multiplier, _parse_stat_multiply


class SkillHandlerTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="skill tester")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def test_handler_reads_private_storage_and_has_no_bare_assignment(self):
        entity = self._entity()
        entity.db.skills = None
        self.assertEqual(entity.skills.owned_keys(), ["flee", "basic_attack"])
        with self.assertRaises(AttributeError):
            entity.skills = {"active": [], "passive": []}

        entity.db.skills = {
            "active": ["fire_ball"],
            "passive": ["defense_instinct"],
        }
        self.assertEqual(
            entity.skills.owned_keys(),
            ["fire_ball", "defense_instinct", "flee", "basic_attack"],
        )

    def test_flee_is_innate_for_bare_monster_and_not_combat_gated(self):
        monster = create_object(Monster, key="bare monster")
        monster.db.skills = None
        before = monster.skills.owned_keys()
        monster.db.current_battlefield = object()
        after = monster.skills.owned_keys()
        self.assertEqual(before, ["flee", "basic_attack"])
        self.assertEqual(after, before)

    def test_skill_handler_has_no_rules_dependency(self):
        source = inspect.getsource(handler)
        self.assertNotIn("world.rules", source)

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

    def test_parser_ignores_opaque_and_malformed_effects(self):
        self.assertEqual(
            _parse_stat_multiply("stat_multiply:atk_phys:1.2"),
            ("atk_phys", 1.2),
        )
        for effect in (
            "damage:fire:magic",
            "stat_multiply:atk_phys",
            "stat_multiply::10",
            "stat_multiply:atk_phys:not-a-number",
            "stat_multiply:atk_phys:nan",
        ):
            self.assertIsNone(_parse_stat_multiply(effect))
        with self.assertRaises(ValueError):
            _matching_multiplier(
                [
                    "stat_multiply:atk_phys:2",
                    "stat_multiply:atk_phys:3",
                ],
                "atk_phys",
            )

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
