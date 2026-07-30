"""Tripwires keeping skills and equipment independent of combat state."""

import ast
import inspect
from pathlib import Path
import unittest

from world.skills import equipment, handler


_FORBIDDEN_PARAMETERS = {"in_combat", "combat_state", "is_combat", "turn"}
_COMBAT_CONCEPTS = _FORBIDDEN_PARAMETERS | {"action_resolver", "turn_scheduler"}


class CombatBlindnessTests(unittest.TestCase):
    def test_public_callable_signatures_have_no_combat_state_parameter(self):
        for module in (handler, equipment):
            for _, value in inspect.getmembers(module):
                if getattr(value, "__module__", None) != module.__name__:
                    continue
                if inspect.isfunction(value) and not value.__name__.startswith("_"):
                    self._assert_signature(value)
                elif inspect.isclass(value):
                    for name, method in value.__dict__.items():
                        if callable(method) and not name.startswith("_"):
                            self._assert_signature(method)

    def _assert_signature(self, value):
        parameters = set(inspect.signature(value).parameters)
        self.assertFalse(parameters & _FORBIDDEN_PARAMETERS)

    def test_modules_have_no_combat_branch_or_resolver_dispatch(self):
        package_root = Path(handler.__file__).parent
        for module_path in package_root.glob("*.py"):
            source = module_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            class_names = {
                node.name.lower()
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            }
            self.assertNotIn("actionresolver", class_names)
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.IfExp, ast.While)):
                    condition = ast.unparse(node.test).lower()
                    self.assertFalse(
                        any(concept in condition for concept in _COMBAT_CONCEPTS)
                    )
