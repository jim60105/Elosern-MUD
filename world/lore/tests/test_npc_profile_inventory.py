"""Data-contract test: shipped NPC source inventory data contract
Derives the actual NPC source set from the live registries and example files
and asserts it matches ``NPC_SOURCE_INVENTORY`` -- a source without an owner,
or an inventory row naming a source that no longer exists, fails this check.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from types import MappingProxyType
from tools.spec_traceability import covers_requirement

from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.rules.npc_roster_validation import derive_shipped_sources

# The nine owning content-change slice labels bound in design.md D1.
OWNER_LABELS = frozenset(
    {
        "altoria_lower",
        "altoria_trade",
        "altoria_guild",
        "altoria_upper",
        "ciaran_homes_a",
        "ciaran_homes_b",
        "companions",
        "generated_quest_cards",
        "import_cards",
    }
)

# The closed source vocabulary, including persistent normal people.
SOURCE_KINDS = frozenset(
    {
        "place_host",
        "dialogue_table",
        "persistent_adventurer",
        "starting_companion",
        "quest_template_occupant",
        "import_example",
    }
)


class NpcSourceInventoryContractTests(unittest.TestCase):
    """The inventory and the live registries name exactly the same sources."""

    @classmethod
    def setUpClass(cls):
        cls.actual = derive_shipped_sources(quest_templates=QUEST_TEMPLATE_POOL)
        cls.inventory_pairs = {(row.kind, row.key) for row in NPC_SOURCE_INVENTORY}

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-source-inventory-enumerates-every-source-with-an-owner"
    )
    def test_inventory_matches_the_live_registries(self):
        missing = sorted(self.actual - self.inventory_pairs)
        extra = sorted(self.inventory_pairs - self.actual)
        self.assertEqual(
            (missing, extra),
            ([], []),
            f"missing from inventory: {missing}; extra in inventory (no longer exists): {extra}",
        )

    def test_every_row_names_one_of_the_nine_owners(self):
        for row in NPC_SOURCE_INVENTORY:
            with self.subTest(kind=row.kind, key=row.key):
                self.assertIn(row.owner, OWNER_LABELS)

    def test_every_row_names_a_registered_source_kind(self):
        for row in NPC_SOURCE_INVENTORY:
            with self.subTest(kind=row.kind, key=row.key):
                self.assertIn(row.kind, SOURCE_KINDS)


class ShippedProfileRegistryImmutabilityTests(unittest.TestCase):
    """The shipped, assembled profile registry is a read-only mapping.

    Moved here from the behavior suite once content slices populated the
    registry: a test that reads the shipped catalog is a data-contract test.
    """

    @covers_requirement(
        "npc-profile-registry::one-module-assembles-the-profile-registry-from-owned-slices"
    )
    def test_registry_is_a_read_only_mapping_proxy(self):
        self.assertIsInstance(NPC_PROFILE_REGISTRY, MappingProxyType)
        before = dict(NPC_PROFILE_REGISTRY)
        with self.assertRaises(TypeError):
            NPC_PROFILE_REGISTRY["t_injected"] = None
        self.assertEqual(dict(NPC_PROFILE_REGISTRY), before)

    @covers_requirement(
        "npc-profile-registry::every-shipped-host-and-examiner-profile-authors-a-bounded-age-pair"
    )
    def test_every_shipped_host_and_examiner_has_bounded_age_pair(self):
        from world.lore.settlements.places import PLACE_REGISTRY
        # All 25 place hosts
        host_keys = {
            place.service_id
            for place in PLACE_REGISTRY.values()
            if place.service_id is not None
        }
        self.assertEqual(len(host_keys), 25)
        for host_key in host_keys:
            with self.subTest(host_key=host_key):
                self.assertIn(host_key, NPC_PROFILE_REGISTRY)
                prof = NPC_PROFILE_REGISTRY[host_key]
                self.assertIsInstance(prof.age, int)
                self.assertNotIsInstance(prof.age, bool)
                self.assertIsInstance(prof.apparent_age, int)
                self.assertNotIsInstance(prof.apparent_age, bool)
                self.assertTrue(0 <= prof.age <= 10000)
                self.assertTrue(0 <= prof.apparent_age <= 10000)

        from world.lore.guild_adventurers import ADVENTURER_REGISTRY

        person_profiles = {row.profile_key for row in ADVENTURER_REGISTRY.values()}
        self.assertEqual(len(person_profiles), 3)
        self.assertFalse(person_profiles & host_keys)
        for key in person_profiles:
            profile = NPC_PROFILE_REGISTRY[key]
            self.assertIs(type(profile.age), int)
            self.assertIs(type(profile.apparent_age), int)
            self.assertTrue(0 <= profile.age <= 10000)
            self.assertTrue(0 <= profile.apparent_age <= 10000)
        self.assertEqual(len(host_keys | person_profiles), 28)
