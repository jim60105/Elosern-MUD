"""Self-arming integration guard for the real change-5 skill registry."""

import unittest
import importlib

from world.imports.validate import _check_skills

try:
    SKILL_REGISTRY = importlib.import_module(
        "world.skills.registry"
    ).SKILL_REGISTRY
except ModuleNotFoundError as error:
    if error.name not in {"world.skills", "world.skills.registry"}:
        raise
    SKILL_REGISTRY = None


class SkillRegistryLandingTests(unittest.TestCase):
    @unittest.skipUnless(
        SKILL_REGISTRY is not None,
        "world.skills.registry has not landed yet",
    )
    def test_real_skill_registry_rejects_unknown_key(self):
        unknown = "definitely_not_a_real_skill_xyz"
        self.assertNotIn(unknown, SKILL_REGISTRY)
        self.assertTrue(_check_skills({"skills": [unknown], "passives": []}))
