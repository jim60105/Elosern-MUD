"""Data-contract test: shop registry content contract
Self-consistency checks for the shop registry (authored host identity)."""

import unittest

from tools.spec_traceability import covers_requirement
from world.lore.settlements.shops import (
    SHOP_REGISTRY,
    ShopDefinition,
    validate_registry_identity_uniqueness,
    validate_shop_npc_identities,
    validate_shipped_identity_uniqueness,
)


class ShopNPCIdentityTests(unittest.TestCase):
    """Authored host identities fail closed at load (design D4)."""

    def test_invalid_host_name_is_named_by_row_and_field(self):
        row = SHOP_REGISTRY["altoria_general_store"]
        bad = {
            "s": ShopDefinition(
                "s", "",
                row.assortment_keys,
            )
        }
        with self.assertRaises(ValueError) as caught:
            validate_shop_npc_identities(bad)
        self.assertIn("shop s", str(caught.exception))
        self.assertIn("invalid host_name", str(caught.exception))

    def test_missing_identity_fields_reject_construction(self):
        # Required-without-default fields: a row built without them fails at
        # construction, before any validation runs.
        import dataclasses

        fields = {field.name: None for field in dataclasses.fields(ShopDefinition)}
        fields.pop("host_name")
        with self.assertRaises(TypeError):
            ShopDefinition(**fields)

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_shipped_rows_load_clean(self):
        validate_shop_npc_identities()

    def test_cross_registry_uniqueness_passes_on_shipped_rows(self):
        # Every shop host, branch host and persistent adventurer name is distinct.
        validate_shipped_identity_uniqueness()

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_duplicate_cross_registry_names_reject_on_substituted_rows(self):
        # The pure checker accepts explicit row sets, so collisions are proven
        # without mutating the shipped registries: shop-vs-person and
        # branch-vs-person duplicates both raise naming both holders.
        from dataclasses import replace as dc_replace

        from world.lore.guild import GUILD_BRANCH_REGISTRY
        from world.lore.guild_adventurers import ADVENTURER_REGISTRY

        shop_row = SHOP_REGISTRY["altoria_general_store"]
        person = next(iter(ADVENTURER_REGISTRY.values()))
        branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        holder = f"persistent_adventurer:{person.key}"

        shop_vs_person = dc_replace(shop_row, host_name=person.name)
        with self.assertRaises(Exception) as caught:
            validate_registry_identity_uniqueness(
                {"s": shop_vs_person},
                {"b": branch},
                {person.key: person},
            )
        self.assertIn("shop:altoria_general_store", str(caught.exception))
        self.assertIn(holder, str(caught.exception))

        branch_vs_person = dc_replace(branch, host_name=person.name)
        with self.assertRaises(Exception) as caught:
            validate_registry_identity_uniqueness(
                {"s": shop_row},
                {"b": branch_vs_person},
                {person.key: person},
            )
        self.assertIn("guild_branch:guild_branch_altoria", str(caught.exception))
        self.assertIn(holder, str(caught.exception))

    def test_shop_registry_follows_the_place_registry_order(self):
        # A shop identity is derived from a place's merchant capability, so
        # the registry is exactly the places that author one, in place order.
        # Which places those are is game data and is not pinned here.
        from world.lore.settlements.places import PLACE_REGISTRY, place_shop_identity

        expected = [
            shop_key
            for shop_key in map(place_shop_identity, PLACE_REGISTRY.values())
            if shop_key is not None
        ]
        self.assertTrue(expected)
        self.assertEqual(list(SHOP_REGISTRY), expected)
