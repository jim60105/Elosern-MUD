"""Registry self-consistency and boundary-consumer checks for scene archetypes."""

from dataclasses import FrozenInstanceError

import unittest

from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY, SceneArchetype

from tools.spec_traceability import covers_requirement


class SceneArchetypeRegistryTests(unittest.TestCase):
    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_registry_is_non_empty_and_keyed_by_scene_kind(self):
        self.assertTrue(SCENE_ARCHETYPE_REGISTRY)
        for key, archetype in SCENE_ARCHETYPE_REGISTRY.items():
            self.assertEqual(key, archetype.key)
            self.assertIsInstance(archetype, SceneArchetype)
            self.assertTrue(archetype.scene_sentence)

    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_entries_are_frozen_with_no_consumer_mutation(self):
        from types import MappingProxyType

        with self.assertRaises(FrozenInstanceError):
            SCENE_ARCHETYPE_REGISTRY["forest_path"].scene_sentence = "changed"
        self.assertTrue(SCENE_ARCHETYPE_REGISTRY["forest_path"].scene_sentence)
        self.assertIsInstance(SCENE_ARCHETYPE_REGISTRY, MappingProxyType)
        with self.assertRaises(TypeError):
            SCENE_ARCHETYPE_REGISTRY["new_scene"] = "not allowed"
        with self.assertRaises(TypeError):
            del SCENE_ARCHETYPE_REGISTRY["forest_path"]

    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_design_example_key_resolves(self):
        self.assertIn("forest_path", SCENE_ARCHETYPE_REGISTRY)
        self.assertTrue(SCENE_ARCHETYPE_REGISTRY["forest_path"].display_name_zh)


if __name__ == "__main__":
    unittest.main()
