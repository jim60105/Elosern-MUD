"""Repository contract: the rules and skills long test files stay split.

Pins the post-split layout of the ``world/rules/tests`` combat-session family
and the ``world/skills/tests`` registry family: the seven themed modules
exist, every pre-split class lives in its pinned themed module exactly once
(no duplicates, no orphans, no misplaced classes), and the original
monolithic modules are deleted.
"""

import ast
from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_TESTS = REPO_ROOT / "world" / "rules" / "tests"
SKILLS_TESTS = REPO_ROOT / "world" / "skills" / "tests"

#: The post-split combat-session family modules (world/rules/tests).
COMBAT_SESSION_SPLIT_MODULES = {
    "test_combat_session_flow.py",
    "test_combat_session_targeting.py",
    "test_combat_session_persistence.py",
    "test_combat_session_recovery.py",
}

#: The post-split skill-registry family modules (world/skills/tests).
SKILL_REGISTRY_SPLIT_MODULES = {
    "test_skill_registry.py",
    "test_spell_catalogs.py",
    "test_skill_casts.py",
}

#: Every pre-split class and the single themed module it must live in
#: (world/rules/tests).
COMBAT_SESSION_CLASS_MODULES = {
    "InnateSkillTests": "test_combat_session_flow.py",
    "EngageTests": "test_combat_session_flow.py",
    "PlayerRoundTests": "test_combat_session_flow.py",
    "CommandedActionAttributionTests": "test_combat_session_flow.py",
    "RoundSettlementSeamTests": "test_combat_session_flow.py",
    "CommandSessionTests": "test_combat_session_flow.py",
    "ExplicitTargetContractTests": "test_combat_session_targeting.py",
    "CombatSessionRecordTests": "test_combat_session_persistence.py",
    "CombatSessionIdTests": "test_combat_session_persistence.py",
    "SessionPersistenceTests": "test_combat_session_persistence.py",
    "MalformedSessionNormalizationTests": "test_combat_session_recovery.py",
    "MalformedSessionRecoveryTests": "test_combat_session_recovery.py",
    "SettlementRecoveryTests": "test_combat_session_recovery.py",
    "UpkeepTickCreditTests": "test_combat_session_recovery.py",
    "OverwhelmDirectionTests": "test_combat_session_recovery.py",
    "PreflightSideEffectTests": "test_combat_session_recovery.py",
}

#: Every pre-split class and the single themed module it must live in
#: (world/skills/tests).
SKILL_REGISTRY_CLASS_MODULES = {
    "SkillRegistryTests": "test_skill_registry.py",
    "SkillContentCompletionTests": "test_skill_registry.py",
    "DivineMysteryRegistryTests": "test_skill_registry.py",
    "SkillCategoryClassificationTests": "test_skill_registry.py",
    "FleeCategoryDeclarationTests": "test_skill_registry.py",
    "FireSpellCatalogTests": "test_spell_catalogs.py",
    "WaterSpellCatalogTests": "test_spell_catalogs.py",
    "EarthSpellCatalogTests": "test_spell_catalogs.py",
    "WindSpellCatalogTests": "test_spell_catalogs.py",
    "LightningSpellCatalogTests": "test_spell_catalogs.py",
    "IceSpellCatalogTests": "test_spell_catalogs.py",
    "LightSpellCatalogTests": "test_spell_catalogs.py",
    "DarkSpellCatalogTests": "test_spell_catalogs.py",
    "DualBladeMasteryCastTests": "test_skill_casts.py",
    "LightSwordStyleCastTests": "test_skill_casts.py",
    "EarthHardenedSkinCastTests": "test_skill_casts.py",
}


def _module_class_occurrences(path: Path) -> dict[str, int]:
    """Count ClassDef occurrences per class name (AST only, no imports)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    occurrences: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            occurrences[node.name] = occurrences.get(node.name, 0) + 1
    return occurrences


class RulesSkillsTestLayoutContractTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules"
    )
    def test_combat_session_family_splits_into_the_four_themed_modules(self):
        discovered = {
            path.name
            for path in RULES_TESTS.glob("test_combat_session_*.py")
            if path.name in COMBAT_SESSION_SPLIT_MODULES
        }
        self.assertEqual(discovered, COMBAT_SESSION_SPLIT_MODULES)
        for relative in COMBAT_SESSION_SPLIT_MODULES:
            self.assertTrue(
                (RULES_TESTS / relative).is_file(),
                f"{relative} is missing from world/rules/tests",
            )

    @covers_requirement(
        "evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules"
    )
    def test_skill_registry_family_splits_into_the_three_themed_modules(self):
        for relative in SKILL_REGISTRY_SPLIT_MODULES:
            self.assertTrue(
                (SKILLS_TESTS / relative).is_file(),
                f"{relative} is missing from world/skills/tests",
            )
        discovered = {
            path.name
            for path in SKILLS_TESTS.glob("test_skill_*.py")
            if path.name in SKILL_REGISTRY_SPLIT_MODULES
        } | {
            path.name
            for path in SKILLS_TESTS.glob("test_spell_catalogs.py")
            if path.name in SKILL_REGISTRY_SPLIT_MODULES
        }
        self.assertEqual(discovered, SKILL_REGISTRY_SPLIT_MODULES)

    @covers_requirement(
        "evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules"
    )
    def test_every_presplit_combat_class_lives_in_its_pinned_module(self):
        self._assert_partition(RULES_TESTS, COMBAT_SESSION_CLASS_MODULES)

    @covers_requirement(
        "evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules"
    )
    def test_every_presplit_skill_class_lives_in_its_pinned_module(self):
        self._assert_partition(SKILLS_TESTS, SKILL_REGISTRY_CLASS_MODULES)

    def _assert_partition(
        self, tests_dir: Path, class_modules: dict[str, str]
    ) -> None:
        modules = sorted(tests_dir.glob("*.py"))
        self.assertTrue(modules, f"{tests_dir} has no Python modules")
        per_class: dict[str, list[Path]] = {name: [] for name in class_modules}
        occurrences: dict[str, int] = {name: 0 for name in class_modules}
        for path in modules:
            module_occurrences = _module_class_occurrences(path)
            for name in class_modules:
                count = module_occurrences.get(name, 0)
                occurrences[name] += count
                if count:
                    per_class[name].append(path)
        for name, pinned_module in class_modules.items():
            with self.subTest(class_name=name):
                self.assertEqual(
                    occurrences[name],
                    1,
                    f"{name} is defined {occurrences[name]} times across "
                    f"{tests_dir.name} (a later definition shadows earlier ones)",
                )
                self.assertEqual(
                    per_class[name],
                    [tests_dir / pinned_module],
                    f"{name} must live in {pinned_module}, found: "
                    + ", ".join(path.name for path in per_class[name]),
                )

    @covers_requirement(
        "evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules"
    )
    def test_original_modules_are_deleted_once_empty(self):
        self.assertFalse(
            (RULES_TESTS / "test_combat_session.py").exists(),
            "test_combat_session.py must be deleted once every class and helper moved out",
        )
        self.assertFalse(
            (SKILLS_TESTS / "test_registry.py").exists(),
            "test_registry.py must be deleted once every class and constant moved out",
        )


if __name__ == "__main__":
    unittest.main()
