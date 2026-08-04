"""Registry self-consistency and boundary-consumer checks for NPC tiers."""

from dataclasses import FrozenInstanceError

import unittest

from world.lore.npc_tiers import NPC_TIER_REGISTRY, NPCTier

from tools.spec_traceability import covers_requirement


class NPCTierRegistryTests(unittest.TestCase):
    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_registry_is_non_empty_and_keyed_by_role(self):
        self.assertTrue(NPC_TIER_REGISTRY)
        for key, tier in NPC_TIER_REGISTRY.items():
            self.assertEqual(key, tier.key)
            self.assertIsInstance(tier, NPCTier)
            self.assertTrue(tier.display_name_zh)

    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_entries_are_frozen_with_no_consumer_mutation(self):
        from types import MappingProxyType

        with self.assertRaises(FrozenInstanceError):
            NPC_TIER_REGISTRY["civilian"].display_name_zh = "changed"
        self.assertEqual(NPC_TIER_REGISTRY["civilian"].display_name_zh, "平民")
        self.assertIsInstance(NPC_TIER_REGISTRY, MappingProxyType)
        with self.assertRaises(TypeError):
            NPC_TIER_REGISTRY["new_tier"] = "not allowed"
        with self.assertRaises(TypeError):
            del NPC_TIER_REGISTRY["civilian"]

    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_design_example_key_resolves(self):
        self.assertIn("civilian", NPC_TIER_REGISTRY)
        self.assertTrue(NPC_TIER_REGISTRY["civilian"].description)


if __name__ == "__main__":
    unittest.main()
