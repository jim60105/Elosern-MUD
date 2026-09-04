"""Self-consistency checks for the shop registry (authored host identity)."""

import unittest

from tools.spec_traceability import covers_requirement
from world.lore.shops import (
    SHOP_REGISTRY,
    ShopDefinition,
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

    @covers_requirement("npc-identity-titles::shop-and-guild-registries-author-host-and-examiner-identities-validated-at-load")
    def test_shipped_rows_load_clean(self):
        validate_shop_npc_identities()

    def test_cross_registry_uniqueness_passes_on_shipped_rows(self):
        # Nine authored names (1 shop + 1 branch + 7 examiners) must be distinct.
        validate_shipped_identity_uniqueness()

    def test_shipped_registry_carries_exactly_one_store(self):
        self.assertEqual(list(SHOP_REGISTRY), ["altoria_general_store"])
