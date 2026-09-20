"""Data-contract test: settlement and place registry content contract
Self-consistency checks for the settlement and place records (one authored
record per service location, settlement-shops design §3.2/§3.3)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import replace
from unittest import mock

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.settlements.places import (
    PLACE_REGISTRY,
    validate_place_registry,
)
from world.lore.settlements.settlements import (
    SETTLEMENT_REGISTRY,
    SettlementArchetype,
    validate_settlement_registry,
)
from world.lore.settlements.shops import SHOP_REGISTRY


class SettlementRegistryTests(unittest.TestCase):
    """Settlement records: closed archetype vocabulary and anchor-key parity."""

    @covers_requirement(
        "settlement-place-registry::a-settlement-declares-its-archetype-and-coordinate-space"
    )
    def test_archetype_vocabulary_has_the_six_lore_archetypes(self):
        self.assertEqual(
            [archetype.value for archetype in SettlementArchetype],
            ["capital", "town", "port", "beast_city", "elven_village", "frontier"],
        )

    def test_every_settlement_key_resolves_in_the_anchor_registry(self):
        for key, settlement in SETTLEMENT_REGISTRY.items():
            with self.subTest(settlement=key):
                self.assertEqual(key, settlement.key)
                self.assertIn(settlement.key, ANCHOR_REGISTRY)

    def test_shipped_settlement_registry_passes_validation(self):
        validate_settlement_registry(SETTLEMENT_REGISTRY)


class PlaceRegistryTests(unittest.TestCase):
    """Place records: transcription of the shipped pair and record validity."""

    @classmethod
    def setUpClass(cls):
        cls.guild = PLACE_REGISTRY["altoria_guild_hall"]
        cls.store = PLACE_REGISTRY["altoria_general_store"]

    def test_place_iteration_order_is_the_load_bearing_slice_order(self):
        # The derived roster and shop registry iterate this dict, and the
        # roster must keep the pre-change [guild master, merchant] order first,
        # with the specialist hosts appended after (sync_service_content
        # processes rows in dict order).
        self.assertEqual(
            list(PLACE_REGISTRY),
            [
                "altoria_guild_hall", "altoria_general_store", "altoria_forge",
                "altoria_eatery", "altoria_tailor",
                "ciaran_hailiel_home", "ciaran_lareneth_home",
                "ciaran_valwyn_home", "ciaran_vethiel_home",
            ],
        )

    def test_shipped_place_registry_passes_validation(self):
        validate_place_registry(PLACE_REGISTRY)

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    @covers_requirement(
        "settlement-place-registry::a-settlement-declares-its-archetype-and-coordinate-space"
    )
    def test_shipped_places_transcribe_the_bootstrap_interiors(self):
        # Transcribed from the bootstrap module constants these rows replaced:
        # the place row is now the only source sync_service_interiors reads.
        self.assertEqual(self.guild.room_name_zh, "阿爾托利亞冒險者公會大廳")
        self.assertEqual(self.guild.exterior_xy, (3, 1))  # GUILD_HALL_EXTERIOR_XYZ
        self.assertEqual(self.store.room_name_zh, "阿爾托利亞雜貨店")
        self.assertEqual(self.store.exterior_xy, (1, 2))  # GENERAL_STORE_EXTERIOR_XYZ

    def test_shipped_hosts_author_human_race_and_default_sex(self):
        # host_race/host_subrace/host_sex are creation-time authored identity,
        # read by sync_service_content when it creates the host. The two
        # pre-existing hosts are authored the safe way (design risk note):
        # None subrace, matching the human baseline the sync applies.
        for place in (self.guild, self.store):
            self.assertEqual(place.host_race, "human")
            self.assertIsNone(place.host_subrace)
            self.assertEqual(place.host_sex, "other")

    def _plant(self, place, **changes):
        return replace(place, key="t_offense_place", service_id="t_offense", **changes)

    def _assert_rejected(self, place, fragment=None):
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_offense_place": place}, clear=True
        ):
            with self.assertRaises(ValueError) as caught:
                validate_place_registry(PLACE_REGISTRY)
        message = str(caught.exception)
        self.assertIn("t_offense_place", message)
        if fragment is not None:
            self.assertIn(fragment, message)

    def test_unknown_settlement_is_rejected(self):
        self._assert_rejected(self._plant(self.guild, settlement_key="nowhere"))

    def test_unknown_host_race_is_rejected(self):
        self._assert_rejected(self._plant(self.store, host_race="dragonborn"))

    def test_unknown_host_sex_is_rejected(self):
        self._assert_rejected(self._plant(self.store, host_sex="unknown"))

    def test_subrace_belonging_to_another_race_is_rejected(self):
        self._assert_rejected(
            self._plant(self.store, host_race="elf", host_subrace="human_plains"),
            "human_plains",
        )

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_assortments_without_a_shop_identity_are_rejected(self):
        self._assert_rejected(
            self._plant(self.guild, assortment_keys=("common_arms",)),
            "assortments",
        )

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_shop_identity_without_assortments_is_rejected(self):
        self._assert_rejected(self._plant(self.store, assortment_keys=()), "shop_key")

    def test_duplicate_authored_kwarg_is_rejected(self):
        place = self._plant(
            self.store,
            authored_kwargs=(
                ("shop_key", "altoria_general_store"),
                ("shop_key", "t_other"),
            ),
        )
        self._assert_rejected(place)

    def test_duplicate_shop_identity_across_places_is_rejected(self):
        # Two places authoring one shop_key would silently overwrite each
        # other in a plain dict; the derivation fails closed instead, naming
        # both holders.
        from world.lore.settlements.shops import _derive_shop_registry

        duplicate = replace(
            self.store,
            key="t_second_shop_place",
            service_id="t_second_shop_place",
            authored_kwargs=(("shop_key", "altoria_general_store"),),
        )
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_second_shop_place": duplicate}, clear=False
        ):
            with self.assertRaises(ValueError) as caught:
                _derive_shop_registry()
        message = str(caught.exception)
        self.assertIn("altoria_general_store", message)
        self.assertIn("t_second_shop_place", message)


class DerivedShopRegistryTests(unittest.TestCase):
    """Shop identities are a view over the places that author a shop_key."""

    @covers_requirement(
        "settlement-place-registry::shop-identities-and-the-service-host-roster-are-derived-from-places"
    )
    def test_shops_are_derived_from_the_places_that_author_a_shop_identity(self):
        self.assertEqual(
            set(SHOP_REGISTRY),
            {
                "altoria_general_store", "altoria_forge",
                "altoria_eatery", "altoria_tailor",
                "ciaran_hailiel_home", "ciaran_lareneth_home",
                "ciaran_valwyn_home", "ciaran_vethiel_home",
            },
        )
        shop = SHOP_REGISTRY["altoria_general_store"]
        store = PLACE_REGISTRY["altoria_general_store"]
        self.assertEqual(shop.key, dict(store.authored_kwargs)["shop_key"])
        self.assertEqual(shop.host_name, store.host_name)
        self.assertEqual(shop.host_title, store.host_title)
        self.assertEqual(shop.assortment_keys, store.assortment_keys)
        # The non-trading guild hall contributes no shop identity.
        self.assertNotIn(PLACE_REGISTRY["altoria_guild_hall"].key, SHOP_REGISTRY)


if __name__ == "__main__":
    unittest.main()