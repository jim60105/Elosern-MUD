"""Self-consistency checks for the shop registry (authored host identity)."""

import unittest

from tools.spec_traceability import covers_requirement
from world.lore.shops import (
    SHOP_REGISTRY,
    ShopDefinition,
    validate_registry_identity_uniqueness,
    validate_shop_npc_identities,
    validate_shipped_identity_uniqueness,
)


class ShopNPCIdentityTests(unittest.TestCase):
    """Authored host identities fail closed at load (design D4)."""

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_invalid_host_title_is_named_by_row_and_field(self):
        row = SHOP_REGISTRY["altoria_general_store"]
        bad = {
            "s": ShopDefinition(
                "s", row.merchant_component_key, row.host_name,
                "含　全形分隔符的稱號", row.offered_item_keys,
            )
        }
        with self.assertRaises(ValueError) as caught:
            validate_shop_npc_identities(bad)
        message = str(caught.exception)
        self.assertIn("shop s", message)
        self.assertIn("host_title", message)

    def test_invalid_host_name_is_named_by_row_and_field(self):
        row = SHOP_REGISTRY["altoria_general_store"]
        bad = {
            "s": ShopDefinition(
                "s", row.merchant_component_key, "", row.host_title,
                row.offered_item_keys,
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
        fields.pop("host_title")
        with self.assertRaises(TypeError):
            ShopDefinition(**fields)

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_shipped_rows_load_clean(self):
        validate_shop_npc_identities()

    def test_cross_registry_uniqueness_passes_on_shipped_rows(self):
        # Nine authored names (1 shop + 1 branch + 7 examiners) must be distinct.
        validate_shipped_identity_uniqueness()

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_duplicate_cross_registry_names_reject_on_substituted_rows(self):
        # The pure checker accepts explicit row sets, so collisions are proven
        # without mutating the shipped registries: shop-vs-examiner and
        # branch-vs-rank duplicates both raise naming both holders.
        from dataclasses import replace as dc_replace

        from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY

        shop_row = SHOP_REGISTRY["altoria_general_store"]
        rank = GUILD_RANK_REGISTRY["F"]
        branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]

        shop_vs_examiner = dc_replace(shop_row, host_name=rank.examiner_name)
        with self.assertRaises(Exception) as caught:
            validate_registry_identity_uniqueness(
                {"s": shop_vs_examiner},
                {"b": branch},
                {"F": rank},
            )
        self.assertIn("shop:altoria_general_store", str(caught.exception))
        self.assertIn("guild_rank:F", str(caught.exception))

        branch_vs_rank = dc_replace(branch, host_name=rank.examiner_name)
        with self.assertRaises(Exception) as caught:
            validate_registry_identity_uniqueness(
                {"s": shop_row},
                {"b": branch_vs_rank},
                {"F": rank},
            )
        self.assertIn("guild_branch:guild_branch_altoria", str(caught.exception))
        self.assertIn("guild_rank:F", str(caught.exception))

    def test_shipped_registry_carries_exactly_one_store(self):
        self.assertEqual(list(SHOP_REGISTRY), ["altoria_general_store"])
