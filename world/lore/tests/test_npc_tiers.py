"""Registry self-consistency and boundary-consumer checks for NPC tiers."""

from dataclasses import FrozenInstanceError

import unittest

from world.lore.npc_tiers import NPC_TIER_REGISTRY, NPCTier
from world.lore.races import RACE_REGISTRY, STATIC_TIER_REGISTRY

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
    @covers_requirement("scene-builder::npc-role-tiers-resolve-deterministic-physical-stats-through-the-lore-registries")
    def test_every_tier_resolves_a_lore_backed_stat_mapping(self):
        self.assertTrue(RACE_REGISTRY)
        self.assertTrue(STATIC_TIER_REGISTRY)
        for key, tier in NPC_TIER_REGISTRY.items():
            with self.subTest(tier=key):
                race = RACE_REGISTRY[tier.race_key]
                static_tier = STATIC_TIER_REGISTRY[tier.static_tier_key]
                self.assertEqual(static_tier.race_key, tier.race_key)
                self.assertEqual(static_tier.race_key, race.key)

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

    @covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")
    def test_elven_tier_validates_and_resolves_to_the_elf_lifespan_band(self):
        tier = NPC_TIER_REGISTRY["elven_civilian"]
        self.assertEqual(tier.race_key, "elf")
        self.assertEqual(tier.static_tier_key, "elf_common")
        race = RACE_REGISTRY[tier.race_key]
        static_tier = STATIC_TIER_REGISTRY[tier.static_tier_key]
        self.assertEqual(static_tier.race_key, "elf")
        self.assertEqual(race.key, "elf")
        self.assertEqual(race.lifespan, (800, 1200))

    @covers_requirement("scenario-director::scene-archetype-and-npc-tier-registries-are-immutable-lore-data")
    def test_elven_tier_is_frozen(self):
        from dataclasses import FrozenInstanceError

        with self.assertRaises(FrozenInstanceError):
            NPC_TIER_REGISTRY["elven_civilian"].display_name_zh = "changed"


if __name__ == "__main__":
    unittest.main()
