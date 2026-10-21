"""Data-contract test: shipped narration coverage contract over the skill and act registries
The shipped catalog validates against the shipped skill and act registries,
and every active skill resolves through a family tier in this change.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

import world.skills.sexual_acts  # noqa: F401  (registers the act rows)
from world.skills.narration import (
    FAMILY_ROWS,
    NARRATION_CATALOG,
    PENDING_FAMILIES,
    family_key,
)
from world.skills.narration.validation import validate_catalog
from world.skills.registry import (
    SHIPPED_SKILL_REGISTRY,
    SKILL_REGISTRY,
    SkillCategory,
    SkillKind,
)


class NarrationCoverageContractTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
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

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_a_synthetic_registry_scope_never_trips_validation(self):
        # The catalog validates against the shipped snapshot, never the live
        # binding a synthetic kit scope substitutes for the duration of a test.
        with patch.dict(
            SKILL_REGISTRY,
            {"t_scope_only": SKILL_REGISTRY["basic_attack"]},
            clear=True,
        ):
            validate_catalog(NARRATION_CATALOG, shipped=SHIPPED_SKILL_REGISTRY)


if __name__ == "__main__":
    unittest.main()
