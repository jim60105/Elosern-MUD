"""Contract tests for the skill registry."""

from dataclasses import fields
import unittest

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


class SkillRegistryTests(unittest.TestCase):
    def test_registry_uses_the_exact_forward_declared_contract(self):
        self.assertTrue(SKILL_REGISTRY)
        self.assertEqual(
            [field.name for field in fields(SkillDef)],
            [
                "key",
                "kind",
                "target_spec",
                "cost",
                "usable_out_of_combat",
                "element",
                "effects",
            ],
        )
        for key, skill in SKILL_REGISTRY.items():
            self.assertEqual(skill.key, key)
            self.assertIsInstance(skill.kind, SkillKind)
            self.assertIsInstance(skill.target_spec, TargetSpec)
            self.assertTrue(
                all(type(value) is int and value >= 0 for value in skill.cost.values())
            )
            if skill.element is not None:
                self.assertIsInstance(skill.element, Element)
                self.assertIn(skill.element, ELEMENT_REGISTRY.values())

    def test_enums_have_only_the_forward_declared_members(self):
        self.assertEqual(set(SkillKind.__members__), {"ACTIVE", "PASSIVE"})
        self.assertEqual(
            set(TargetSpec.__members__),
            {"NONE", "SELF", "SINGLE", "AREA"},
        )
        self.assertFalse(
            {
                name
                for name, value in SkillKind.__dict__.items()
                if callable(value) and not name.startswith("_")
            }
        )
        self.assertFalse(
            {
                name
                for name, value in TargetSpec.__dict__.items()
                if callable(value) and not name.startswith("_")
            }
        )

    def test_seed_set_spans_every_required_category(self):
        for key in (
            "body_enhancement",
            "body_enhancement_extreme",
            "body_enhancement_basic",
            "fire_mastery",
            "dark_mastery",
            "wind_mastery",
            "light_mastery",
            "fire_ball",
            "wind_blade",
            "dual_wield_style",
            "status_disguise",
            "dominion_art",
            "elf_longevity",
        ):
            self.assertIn(key, SKILL_REGISTRY)

        multipliers = {
            effect.rsplit(":", 1)[-1]
            for skill in SKILL_REGISTRY.values()
            for effect in skill.effects
            if effect.startswith("stat_multiply:")
        }
        self.assertTrue({"1.2", "100", "1000"} <= multipliers)

        for element_key in ("fire", "dark", "wind", "light"):
            skill = SKILL_REGISTRY[f"{element_key}_mastery"]
            self.assertIs(skill.kind, SkillKind.PASSIVE)
            self.assertIs(skill.element, ELEMENT_REGISTRY[element_key])

        conferral = [
            skill
            for skill in SKILL_REGISTRY.values()
            if "confer_skill_partial" in skill.effects
        ]
        disguises = [
            skill
            for skill in SKILL_REGISTRY.values()
            if "set_disguise" in skill.effects
        ]
        self.assertEqual(len(conferral), 1)
        self.assertEqual(len(disguises), 1)
        self.assertTrue(all(skill.kind is SkillKind.ACTIVE for skill in conferral + disguises))

        boons = [
            skill
            for key, skill in SKILL_REGISTRY.items()
            if key.startswith("reincarnation_boon_")
        ]
        self.assertGreaterEqual(len(boons), 3)
        self.assertEqual(len({tuple(skill.effects) for skill in boons}), len(boons))

    def test_definition_collections_are_deeply_immutable(self):
        fire_ball = SKILL_REGISTRY["fire_ball"]
        with self.assertRaises(TypeError):
            fire_ball.cost["mp"] = 0
        with self.assertRaises(TypeError):
            fire_ball.effects.append("damage:unbounded")
