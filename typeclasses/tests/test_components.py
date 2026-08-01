"""Source tests proving service components delegate all state writes (task 3.6)."""

from tools.spec_traceability import covers_requirement

import ast
import inspect
import unittest
from pathlib import Path

from typeclasses import components as components_module
from typeclasses.components import GuildExaminer, GuildStaff, Merchant


class ComponentModuleSourceTests(unittest.TestCase):
    FORBIDDEN_ASSIGNMENTS = (
        "guild_rank",
        "merit",
        "wallet",
        "inventory",
        "quest_log",
        "guild_reward_claims",
        "active_combat",
        "guild_exam",
        "guild_registration",
        "disguised_stats",
    )

    @covers_requirement("guild-registration::guild-service-components-are-capability-adapters-not-state-writers")
    def test_components_define_only_capability_markers_and_service_data(self):
        source = inspect.getsource(components_module)
        tree = ast.parse(source)
        forbidden_hits = []
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            for target in targets:
                unparsed = ast.unparse(target)
                for keyword in self.FORBIDDEN_ASSIGNMENTS:
                    if keyword in unparsed:
                        forbidden_hits.append(unparsed)
        self.assertEqual(
            forbidden_hits,
            [],
            f"components module assigns forbidden player-state: {forbidden_hits}",
        )

    def test_components_import_no_deterministic_write_api(self):
        source = inspect.getsource(components_module)
        self.assertNotIn("world.rules", source)
        self.assertNotIn("world.quests", source)

    def test_each_component_has_unique_stable_name(self):
        names = {component.name for component in (GuildStaff, GuildExaminer, Merchant)}
        self.assertEqual(
            names, {"guild_staff", "guild_examiner", "merchant"}
        )

    def test_component_slots_match_names(self):
        for component in (GuildStaff, GuildExaminer, Merchant):
            self.assertEqual(component.get_component_slot(), component.name)

    def test_module_has_no_function_bodies_writing_state(self):
        tree = ast.parse(inspect.getsource(components_module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Attribute) and child.attr in self.FORBIDDEN_ASSIGNMENTS:
                    self.fail(
                        f"function {node.name} references forbidden state {child.attr}"
                    )


if __name__ == "__main__":
    unittest.main()
