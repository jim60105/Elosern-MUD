"""Repository contract for the quest long-test-file split.

AST-based (no test-module imports) partition check: the scene-builder and
compile classes from the pre-split inventories must each live in exactly one
``world/quests/tests`` module, and every themed split module must exist.
"""

import ast
from pathlib import Path
import unittest

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]
QUESTS_TESTS = REPO_ROOT / "world" / "quests" / "tests"

#: The six themed modules introduced by the split.
SPLIT_MODULES = (
    "test_scene_builder_offline.py",
    "test_scene_builder_flavor.py",
    "test_scene_builder_boundary.py",
    "test_compile_blueprint.py",
    "test_compile_registration.py",
    "test_compile_offline.py",
)

#: Every test class from the two pre-split inventories. Each must appear in
#: exactly one module of ``world/quests/tests``.
PRE_SPLIT_TEST_CLASSES = (
    "SceneOccupantPrototypeTests",
    "SceneBuilderMaterializationTests",
    "SceneBuilderCharacterizationTests",
    "SceneBuilderPortraitPipelineTests",
    "SceneBuilderOfflineLoopTests",
    "SceneFlavorContextAndApplyTests",
    "SceneBuilderBoundaryTests",
    "CompileQuestBlueprintTests",
    "RegisterGeneratedQuestTests",
    "SceneBoundCompileTests",
    "SceneRequirementRegistryTests",
    "CharacterizationCompileTests",
    "SharedPayloadContractTests",
    "OfflineDirectorEndToEndTests",
)

#: Shared bases/mixins that must keep a single fixed home.
SHARED_BASES = (
    "SceneBuilderTestBase",
    "SceneBuilderIsolation",
    "CompileRegistryIsolation",
)


def _module_class_occurrences(path: Path) -> dict[str, int]:
    """Count ClassDef occurrences per class name (AST only, no imports)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    occurrences: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            occurrences[node.name] = occurrences.get(node.name, 0) + 1
    return occurrences


class QuestTestsLayoutContractTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::scene-builder-and-compile-test-modules-are-split-with-shared-bases-kept-importable"
    )
    def test_split_modules_exist(self):
        for relative in SPLIT_MODULES:
            with self.subTest(module=relative):
                self.assertTrue(
                    (QUESTS_TESTS / relative).is_file(),
                    f"{relative} is missing from world/quests/tests",
                )

    @covers_requirement(
        "evennia-test-optimization::scene-builder-and-compile-test-modules-are-split-with-shared-bases-kept-importable"
    )
    def test_every_presplit_class_lives_in_exactly_one_module(self):
        modules = sorted(QUESTS_TESTS.glob("*.py"))
        self.assertTrue(modules, "world/quests/tests has no Python modules")
        per_class: dict[str, list[Path]] = {name: [] for name in PRE_SPLIT_TEST_CLASSES}
        occurrences: dict[str, int] = {name: 0 for name in PRE_SPLIT_TEST_CLASSES}
        for path in modules:
            module_occurrences = _module_class_occurrences(path)
            for name in PRE_SPLIT_TEST_CLASSES:
                count = module_occurrences.get(name, 0)
                occurrences[name] += count
                if count:
                    per_class[name].append(path)
        for name in PRE_SPLIT_TEST_CLASSES:
            with self.subTest(class_name=name):
                self.assertEqual(
                    occurrences[name],
                    1,
                    f"{name} is defined {occurrences[name]} times in "
                    "world/quests/tests (a later definition shadows earlier ones)",
                )
                self.assertEqual(
                    len(per_class[name]),
                    1,
                    f"{name} appears in {len(per_class[name])} modules: "
                    + ", ".join(path.name for path in per_class[name]),
                )

    @covers_requirement(
        "evennia-test-optimization::scene-builder-and-compile-test-modules-are-split-with-shared-bases-kept-importable"
    )
    def test_shared_bases_keep_a_single_fixed_home(self):
        modules = sorted(QUESTS_TESTS.glob("*.py"))
        per_base: dict[str, list[Path]] = {name: [] for name in SHARED_BASES}
        for path in modules:
            for name in _module_class_occurrences(path):
                if name in per_base:
                    per_base[name].append(path)
        for name, homes in per_base.items():
            with self.subTest(base=name):
                self.assertEqual(
                    len(homes),
                    1,
                    f"{name} must live in exactly one module, found: "
                    + ", ".join(path.name for path in homes),
                )
                self.assertIn(
                    homes[0].name,
                    ("test_scene_builder.py", "_compile_helpers.py"),
                    f"{name} must live in the original module or a helpers module",
                )

    @covers_requirement(
        "evennia-test-optimization::scene-builder-and-compile-test-modules-are-split-with-shared-bases-kept-importable"
    )
    def test_original_compile_module_is_deleted_once_empty(self):
        original = QUESTS_TESTS / "test_compile.py"
        self.assertFalse(
            original.exists(),
            "test_compile.py must be deleted once every class and helper moved out",
        )


if __name__ == "__main__":
    unittest.main()
