"""Data-contract test: shipped narration coverage contract over the skill and act registries
The shipped catalog validates against the shipped skill and act registries,
and every active skill resolves through a family tier in this change.
"""

from __future__ import annotations

import unittest

import world.skills.sexual_acts  # noqa: F401  (registers the act rows)
from world.skills.narration import (
    FAMILY_ROWS,
    NARRATION_CATALOG,
    PENDING_FAMILIES,
    family_key,
)
from world.skills.narration.validation import validate_catalog
from world.skills.registry import SKILL_REGISTRY, SkillCategory, SkillKind


class NarrationCoverageContractTests(unittest.TestCase):
    def test_the_shipped_catalog_validates_at_import(self):
        validate_catalog(NARRATION_CATALOG)
        self.assertEqual(
            set(NARRATION_CATALOG),
            set(),
            "this change lands the engine, not per-skill rows",
        )

    def test_every_active_skill_resolves_through_a_family_tier(self):
        active = [
            (key, skill)
            for key, skill in SKILL_REGISTRY.items()
            if skill.kind is SkillKind.ACTIVE
        ]
        self.assertGreaterEqual(len(active), 200)
        for key, skill in active:
            with self.subTest(key=key):
                self.assertIn(family_key(skill), FAMILY_ROWS)
                if key not in NARRATION_CATALOG:
                    self.assertTrue(
                        skill.category is SkillCategory.SEXUAL_ACT
                        or skill.category.value in PENDING_FAMILIES
                    )

    def test_a_sexual_act_family_carries_its_line(self):
        acts = [
            skill
            for skill in SKILL_REGISTRY.values()
            if skill.category is SkillCategory.SEXUAL_ACT
            and skill.kind is SkillKind.ACTIVE
        ]
        self.assertGreaterEqual(len(acts), 60)
        for skill in acts:
            with self.subTest(key=skill.key):
                self.assertTrue(FAMILY_ROWS[family_key(skill)].action)


if __name__ == "__main__":
    unittest.main()
