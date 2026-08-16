"""Repository contract: fixture-free test classes use the lightest base.

Pins the fixture-optimization boundary: representative classes that were
downgraded from ``EvenniaTest`` to ``EvenniaTestCase`` (optionally with an
isolation mixin) must keep that base, so per-method setup/teardown cost is not
silently re-added to the deterministic non-browser suite. Assertions are
AST-based so the contract never imports game or Evennia code.
"""

from pathlib import Path
import ast
import unittest

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]

#: Representative downgraded classes across packages, keyed by repository path.
#: The expected base set is either exactly ``EvenniaTestCase`` or an isolation
#: mixin plus ``EvenniaTestCase`` (mixin order is not asserted here; the AST
#: base-list membership is what pins the boundary).
DOWNGRADED_SAMPLE = {
    "commands/tests/test_combat_actions.py": {
        "TokenParsingTests": {"BattlefieldIsolation", "EvenniaTestCase"},
    },
    "server/conf/tests/test_scene_flavor_service.py": {
        "SceneFlavorServiceTests": {"EvenniaTestCase"},
    },
    "typeclasses/tests/test_entities.py": {
        "LivingEntityTests": {"EvenniaTestCase"},
    },
    "web/webclient/actions/tests/test_combat_actions.py": {
        "CombatAdapterTests": {"BattlefieldIsolation", "EvenniaTestCase"},
    },
    "web/webclient/presentation/tests/test_art_push.py": {
        "ArtPushBoundaryTests": {"EvenniaTestCase"},
    },
    "world/art/tests/test_presenter.py": {
        "ArtPresenterTests": {"EvenniaTestCase"},
    },
    "world/maps/tests/test_service_interiors.py": {
        "ServiceInteriorTests": {"EvenniaTestCase"},
    },
    "world/quests/tests/test_planner.py": {
        "QuestPlannerTests": {"QuestRegistryIsolation", "EvenniaTestCase"},
    },
    "world/rules/tests/test_buffs.py": {
        "BuffIntegrationTests": {"EvenniaTestCase"},
    },
    "world/rules/tests/test_combat_modifiers.py": {
        "CombatModifierTests": {"EvenniaTestCase"},
    },
    "world/rules/tests/test_sexual_transitions.py": {
        "SexualTransitionTests": {"EvenniaTestCase"},
    },
    "world/skills/tests/test_handler.py": {
        "SkillHandlerTests": {"EvenniaTestCase"},
    },
}


class FixtureBaseContractTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::fixture-free-test-classes-use-the-lightest-base"
    )
    def test_downgraded_sample_inherits_evennia_test_case(self):
        for relative_path, classes in DOWNGRADED_SAMPLE.items():
            tree = ast.parse((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
            actual = {
                node.name: {ast.unparse(base) for base in node.bases}
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.bases
            }
            for class_name, expected_bases in classes.items():
                with self.subTest(path=relative_path, class_name=class_name):
                    self.assertEqual(actual[class_name], expected_bases)


if __name__ == "__main__":
    unittest.main()
