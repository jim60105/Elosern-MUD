"""Data-contract test: shipped NPC source inventory equality contract
Derives the actual NPC source set from the live registries and example files
and asserts ``NPC_SOURCE_INVENTORY`` agrees in both directions -- a source
without a row, or a row naming a source that no longer exists, fails this
check. The owning content slice of every profile-backed source is resolved from
the live profile-slice declaration instead of a fixed owner list, so a new
hosted place, table or person is owned without editing this test, and no host,
person or profile count is pinned here.
"""

from __future__ import annotations

import unittest
from types import MappingProxyType
from tools.spec_traceability import covers_requirement

from world.lore.npc_profiles import (
    NPC_PROFILE_REGISTRY,
    PROFILE_KEY_SLICES,
    PROFILE_SLICE_LABELS,
)
from world.lore.npc_profiles.inventory import NPC_SOURCE_INVENTORY
from world.ai.director_templates import QUEST_TEMPLATE_POOL
from world.rules.npc_roster_validation import (
    derive_shipped_source_owners,
    derive_shipped_sources,
)

# The closed source vocabulary, including persistent normal people. This is the
# authored kind vocabulary the inventory rows may name, not an owner or count
# list: the kinds it declares are the six relationships the roster validator
# knows how to check.
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
        cls.resolved_owners = derive_shipped_source_owners(
            quest_templates=QUEST_TEMPLATE_POOL
        )

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

    @covers_requirement(
        "npc-profile-registry::the-shipped-npc-source-inventory-enumerates-every-source-with-an-owner"
    )
    def test_every_row_owner_is_the_slice_resolved_from_the_live_declaration(self):
        # The owner relationship is checked in both directions against the live
        # slice declaration: a row naming the wrong slice fails, and a source
        # whose profile a registered slice declares must be owned by that slice.
        by_source = {(row.kind, row.key): row for row in NPC_SOURCE_INVENTORY}
        self.assertEqual(
            set(self.resolved_owners) - set(by_source),
            set(),
            "a profile-backed source resolves to an owner but has no inventory row",
        )
        for source, resolved in sorted(self.resolved_owners.items()):
            with self.subTest(source=source):
                self.assertEqual(by_source[source].owner, resolved)
                self.assertIn(resolved, PROFILE_SLICE_LABELS)
        for row in NPC_SOURCE_INVENTORY:
            with self.subTest(kind=row.kind, key=row.key):
                self.assertTrue(row.owner and row.owner.strip())

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
    def test_every_shipped_host_and_person_profile_authors_a_bounded_age_pair(self):
        from world.lore.guild_adventurers import ADVENTURER_REGISTRY
        from world.lore.settlements.places import PLACE_REGISTRY

        # The compared sets are derived from the live place and person records,
        # so a new host or person joins the check with no count to update.
        host_keys = {
            place.host_profile_key
            for place in PLACE_REGISTRY.values()
            if place.service_id is not None
        }
        person_profiles = {row.profile_key for row in ADVENTURER_REGISTRY.values()}
        for profile_key in sorted(host_keys | person_profiles):
            with self.subTest(profile_key=profile_key):
                self.assertIn(profile_key, NPC_PROFILE_REGISTRY)
                profile = NPC_PROFILE_REGISTRY[profile_key]
                self.assertIs(type(profile.age), int)
                self.assertIs(type(profile.apparent_age), int)
                self.assertTrue(0 <= profile.age <= 10000)
                self.assertTrue(0 <= profile.apparent_age <= 10000)
        # A normal person owns a profile of their own; a place host keeps its
        # own identity. Neither may reuse the other's profile.
        self.assertFalse(person_profiles & host_keys)
        self.assertEqual(
            {PROFILE_KEY_SLICES[key] for key in host_keys | person_profiles},
            set(PROFILE_SLICE_LABELS),
        )


if __name__ == "__main__":
    unittest.main()
