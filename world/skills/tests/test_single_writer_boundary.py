"""Architecture tripwires keeping ``world.skills`` read-only."""

import ast
from pathlib import Path
import unittest

import world.skills


class SingleWriterBoundaryTests(unittest.TestCase):
    def test_production_skill_modules_do_not_write_persistent_state(self):
        package_root = Path(world.skills.__file__).parent
        for module_path in package_root.glob("*.py"):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                targets = []
                if isinstance(node, ast.Assign):
                    targets = node.targets
                elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                    targets = [node.target]
                for target in targets:
                    rendered = ast.unparse(target)
                    self.assertNotIn(".db.", rendered, module_path.name)
                    self.assertNotIn(".traits.", rendered, module_path.name)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "setattr", module_path.name)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    owner = ast.unparse(node.func.value)
                    if ".attributes" in owner:
                        self.fail(
                            f"{module_path.name} calls persistent attribute handler "
                            f"{node.func.attr}"
                        )

    def test_skill_modules_do_not_import_rule_mutators(self):
        package_root = Path(world.skills.__file__).parent
        for module_path in package_root.glob("*.py"):
            tree = ast.parse(module_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertFalse(
                        node.module.startswith("world.rules"),
                        module_path.name,
                    )
