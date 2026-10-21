"""Data-contract test: shipped narration coverage contract over the skill and act registries
The shipped catalog validates against the shipped skill and act registries, the four
non-elemental ACTIVE families carry exactly their authored rows, and every active skill
outside those families still resolves through a family tier.
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
    NarrationCatalogError,
    NarrationRow,
    family_key,
)
from world.skills.narration.select import action_line
from world.skills.narration.validation import validate_catalog
from world.skills.registry import (
    SHIPPED_SKILL_REGISTRY,
    SKILL_REGISTRY,
    SkillCategory,
    SkillKind,
)

#: The ACTIVE families whose per-skill rows this change authors.
NON_ELEMENTAL_FAMILIES = (
    SkillCategory.MARTIAL_ARTS,
    SkillCategory.HOLY_RITE,
    SkillCategory.DIVINE_MYSTERY,
    SkillCategory.ENHANCEMENT,
)


def _active_keys(category: SkillCategory) -> set[str]:
    return {
        key
        for key, skill in SHIPPED_SKILL_REGISTRY.items()
        if skill.kind is SkillKind.ACTIVE and skill.category is category
    }


class NarrationCoverageContractTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_the_shipped_catalog_validates_at_import(self):
        validate_catalog(NARRATION_CATALOG)

    @covers_requirement(
        "action-narration::a-resolved-action-opens-with-its-own-skill-s-action-narration",
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries",
        "action-narration::every-non-elemental-active-skill-has-its-own-action-narration",
    )
    def test_the_four_non_elemental_families_have_exact_row_coverage(self):
        expected: set[str] = set()
        for category in NON_ELEMENTAL_FAMILIES:
            keys = _active_keys(category)
            self.assertTrue(keys, category)
            expected |= keys
        self.assertEqual(set(NARRATION_CATALOG), expected)

    @covers_requirement(
        "action-narration::a-resolved-action-opens-with-its-own-skill-s-action-narration",
        "action-narration::every-non-elemental-active-skill-has-its-own-action-narration",
    )
    def test_every_authored_row_opens_its_own_skill(self):
        for key, row in NARRATION_CATALOG.items():
            skill = SHIPPED_SKILL_REGISTRY[key]
            family = family_key(skill)
            with self.subTest(key=key):
                line = action_line(
                    key,
                    family,
                    scope="coverage",
                    target_key="t_target",
                    actor="A",
                )
                self.assertIn(line, row.action)
                self.assertNotIn(line, FAMILY_ROWS[family].action)

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries",
        "action-narration::every-non-elemental-active-skill-has-its-own-action-narration",
    )
    def test_a_missing_row_in_a_covered_family_stops_the_catalog_loading(self):
        for category in NON_ELEMENTAL_FAMILIES:
            key = sorted(_active_keys(category))[0]
            catalog = {
                other: row
                for other, row in NARRATION_CATALOG.items()
                if other != key
            }
            with self.subTest(key=key):
                with self.assertRaises(NarrationCatalogError) as caught:
                    validate_catalog(catalog)
                self.assertIn(key, str(caught.exception))

    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget",
        "action-narration::narration-prose-contains-no-numeric-magnitude",
        "action-narration::every-non-elemental-active-skill-has-its-own-action-narration",
    )
    def test_a_family_row_that_breaks_a_shared_bound_fails_the_same_error(self):
        key = sorted(_active_keys(SkillCategory.MARTIAL_ARTS))[0]
        for action in (
            ("{actor}" + "字" * 200 + "{target}",),
            ("{actor} 施展第 7 式——",),
        ):
            catalog = dict(NARRATION_CATALOG)
            catalog[key] = NarrationRow(key, action=action)
            with self.subTest(action=action):
                with self.assertRaises(NarrationCatalogError):
                    validate_catalog(catalog)

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
