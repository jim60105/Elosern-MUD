"""Contract tests for the skill registry."""

from tools.spec_traceability import covers_requirement

from dataclasses import fields
import unittest

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.registry import (
    FactionConstraint,
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
                "label",
                "description",
                "kind",
                "target_spec",
                "cost",
                "usable_out_of_combat",
                "element",
                "effects",
                "faction_constraint",
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
            self.assertIsInstance(skill.faction_constraint, FactionConstraint)

    @covers_requirement(
        "skill-registry::skilldef-carries-the-action-resolver-s-skill-owned-faction-constraint"
    )
    def test_every_definition_has_bounded_player_facing_metadata(self):
        for skill in SKILL_REGISTRY.values():
            self.assertTrue(skill.label.strip())
            self.assertTrue(skill.description.strip())
            self.assertLessEqual(
                sum(1 for _ in skill.label),
                128,
                f"skill {skill.key!r} label exceeds 128 code points",
            )
            self.assertLessEqual(
                sum(1 for _ in skill.description),
                512,
                f"skill {skill.key!r} description exceeds 512 code points",
            )
            self.assertFalse("\n" in skill.label or "\n" in skill.description)

    def test_constructing_without_metadata_fails_closed(self):
        with self.assertRaises(TypeError):
            SkillDef(
                key="no_metadata",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )

    def test_metadata_bounds_reject_empty_and_oversized_values(self):
        from world.skills.registry import _validate_metadata

        for bad_label, bad_description in (
            ("", "說明"),
            ("   ", "說明"),
            ("標籤", ""),
            ("標籤", "   "),
            ("標" * 129, "說明"),
            ("標籤", "說" * 513),
        ):
            with self.subTest(label=bad_label, description=bad_description):
                with self.assertRaises(ValueError):
                    _validate_metadata(bad_label, bad_description)


    @covers_requirement("skill-registry::skillkind-and-targetspec-are-forward-declared-for-change-8-to-import")
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

    @covers_requirement("skill-registry::the-seed-registry-spans-every-skill-category-inventoried-from-the-sample-cards")
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

    @covers_requirement("skill-registry::skilldef-carries-the-action-resolver-s-skill-owned-faction-constraint")
    def test_definition_collections_are_deeply_immutable(self):
        fire_ball = SKILL_REGISTRY["fire_ball"]
        with self.assertRaises(TypeError):
            fire_ball.cost["mp"] = 0
        with self.assertRaises(TypeError):
            fire_ball.effects.append("damage:unbounded")

    def test_direct_construction_observes_immutability_and_metadata_bounds(self):
        skill = SkillDef(
            key="direct",
            label="直接定義",
            description="直接建構的定義也受同一不變條件保護。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={"mp": 5},
            usable_out_of_combat=False,
            element=None,
            effects=["direct:effect"],
        )
        with self.assertRaises(TypeError):
            skill.cost["mp"] = 0
        with self.assertRaises(TypeError):
            skill.effects.append("unbounded")
        with self.assertRaises(ValueError):
            SkillDef(
                key="direct_bad",
                label="   ",
                description="說明",
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )
        with self.assertRaises(ValueError):
            SkillDef(
                key="direct_long",
                label="標籤",
                description="說" * 513,
                kind=SkillKind.ACTIVE,
                target_spec=TargetSpec.SELF,
                cost={},
                usable_out_of_combat=False,
                element=None,
                effects=[],
            )
        # Every registered definition, including the dynamically registered
        # production `flee`, stays immutable at runtime.
        for registered in SKILL_REGISTRY.values():
            with self.assertRaises(TypeError):
                registered.effects.append("unbounded")
            with self.assertRaises(TypeError):
                registered.cost["mp"] = 0
