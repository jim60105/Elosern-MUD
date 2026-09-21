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
    PlaceKind,
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

    # ---- the kind vocabulary (place-kind-vocabulary) -----------------------

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_kind_vocabulary_is_closed_and_covers_the_world_document(self):
        # The vocabulary is closed: pin the exact member set so an
        # approximate reuse is visible as a missing name, not a shrug. The
        # fourteen settlement-build members must be present with their
        # snake_case wire values — sync mirrors the value, and a member
        # authored without an explicit value would silently write the
        # uppercase name to the database.
        self.assertEqual(
            {kind.value for kind in PlaceKind},
            {
                # shipped before the settlement build
                "guild_hall", "general_store", "weaponsmith", "outfitter",
                "eatery", "home",
                # the settlement build's location types
                "jeweller", "alchemist", "temple", "sanctum_shop", "tavern",
                "lodging", "bathhouse", "palace", "watch_post",
                "training_ground", "academy", "merchant_hall", "market",
                "commons",
            },
        )
        for kind in PlaceKind:
            self.assertEqual(kind.value, kind.name.lower())

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_every_shipped_kind_describes_its_location(self):
        # Each shipped row's kind names what its room is in the world
        # document, not what mechanism its host carries. The four elven
        # homes trade and are still homes — the worked example for the
        # kind rule; reclassifying one to its host's capability fails here.
        expected = {
            "altoria_guild_hall": "guild_hall",
            "altoria_general_store": "general_store",
            "altoria_forge": "weaponsmith",
            "altoria_eatery": "eatery",
            "altoria_tailor": "outfitter",
            "ciaran_hailiel_home": "home",
            "ciaran_lareneth_home": "home",
            "ciaran_valwyn_home": "home",
            "ciaran_vethiel_home": "home",
        }
        self.assertEqual(set(PLACE_REGISTRY), set(expected))
        for key, kind in expected.items():
            with self.subTest(place=key):
                self.assertEqual(PLACE_REGISTRY[key].kind.value, kind)
        # The homes really do trade — otherwise the pin above proves nothing.
        for key in ("ciaran_hailiel_home", "ciaran_lareneth_home",
                    "ciaran_valwyn_home", "ciaran_vethiel_home"):
            place = PLACE_REGISTRY[key]
            self.assertEqual(place.profession, "merchant")
            self.assertTrue(place.assortment_keys)
            self.assertIn("shop_key", dict(place.authored_kwargs))

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_dwelling_that_trades_is_authored_a_home(self):
        # Regression guard for the kind rule, not a behaviour test: today no
        # validation reads kind at all, so this row loads because the rule
        # permits it. It earns its place because the day anyone adds a
        # capability-based kind check (a HOME that may not carry a shop_key,
        # say), this authored record — a dwelling whose occupant trades —
        # must stay a legal record, and this test fails first.
        dwelling = self._plant(
            self.store,
            kind=PlaceKind.HOME,
            room_name_zh="合成 dwelling",
        )
        try:
            validate_place_registry({"t_offense_place": dwelling})
        except ValueError as error:  # pragma: no cover - failure path asserts below
            self.fail(f"home kind rejected for a trading dwelling: {error}")
        # The kind names the home, never the host's merchant capability.
        self.assertEqual(dwelling.kind, PlaceKind.HOME)

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    @covers_requirement(
        "settlement-place-registry::a-settlement-declares-its-archetype-and-coordinate-space"
    )
    def test_shipped_places_transcribe_the_bootstrap_interiors(self):
        # The place row is the only source sync_service_interiors reads. The
        # capital five's addresses are the altoria-capital-replan exteriors;
        # every other field these rows transcribe is untouched by the replan
        # (the neutrality gate: test_capital_places_keep_their_identities).
        self.assertEqual(self.guild.room_name_zh, "阿爾托利亞冒險者公會大廳")
        self.assertEqual(self.guild.exterior_xy, (4, 3))  # 公會前
        self.assertEqual(self.store.room_name_zh, "阿爾托利亞雜貨店")
        self.assertEqual(self.store.exterior_xy, (2, 3))  # 市場街

    def test_shipped_hosts_author_human_race_and_default_sex(self):
        # host_race/host_subrace/host_sex are creation-time authored identity,
        # read by sync_service_content when it creates the host. The two
        # pre-existing hosts are authored the safe way (design risk note):
        # None subrace, matching the human baseline the sync applies.
        for place in (self.guild, self.store):
            self.assertEqual(place.host_race, "human")
            self.assertIsNone(place.host_subrace)
            self.assertEqual(place.host_sex, "other")

    def test_capital_places_keep_their_identities_after_the_replan(self):
        # The altoria-capital-replan neutrality gate: only exterior_xy moved.
        # Every identity field and every resolved shop offer of the shipped
        # capital five is pinned to its pre-replan value; the exteriors are
        # pinned to the new teardrop addresses. A row edited beyond its
        # address fails here.
        expected = [
            (
                "altoria_guild_hall", "阿爾托利亞冒險者公會大廳", (4, 3),
                "冒險者公會大廳", "葛里安·衛登", "阿爾托利亞分會會長",
                "altoria_guild_master", (),
            ),
            (
                "altoria_general_store", "阿爾托利亞雜貨店", (2, 3),
                "雜貨店", "瑪爾特·金秤", "阿爾托利亞雜貨商店老闆",
                "altoria_merchant", ("general_sundries",),
            ),
            (
                "altoria_forge", "聖潔王都鍛造鋪", (1, 3),
                "鍛造鋪", "維爾登·黑潭", "聖潔王都鍛造鋪鐵匠",
                "altoria_blacksmith", ("common_arms",),
            ),
            (
                "altoria_eatery", "聖潔王都餐館", (3, 1),
                "餐館", "西格瑪·庫柏", "聖潔王都餐館老闆",
                "altoria_eatery_owner", ("staple_meals",),
            ),
            (
                "altoria_tailor", "聖潔王都裁縫坊", (1, 3),
                "裁縫坊", "妮絲塔·狐溪", "聖潔王都裁縫坊坊主",
                "altoria_tailor", ("common_outfits",),
            ),
        ]
        shops = SHOP_REGISTRY
        for (
            key, room_name, exterior, doorway, host, title, service, assortments
        ) in expected:
            with self.subTest(place=key):
                place = PLACE_REGISTRY[key]
                self.assertEqual(place.room_name_zh, room_name)
                self.assertEqual(place.exterior_xy, exterior)
                self.assertEqual(place.doorway_key_zh, doorway)
                self.assertEqual(place.host_name, host)
                self.assertEqual(place.host_title, title)
                self.assertEqual(place.service_id, service)
                self.assertEqual(place.assortment_keys, assortments)
                # The resolved offer set follows the assortment rows.
                shop_key = dict(place.authored_kwargs).get("shop_key")
                if shop_key is None:
                    self.assertNotIn(key, shops)
                    continue
                self.assertEqual(shops[shop_key].assortment_keys, assortments)
                self.assertEqual(shops[shop_key].host_name, host)

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

    # ---- the optional host group (hostless-places) -------------------------

    def _hostless(self, key="t_plaza_place", **changes):
        """One synthetic place authoring no host at all (every field defaulted)."""
        base = dict(
            key=key,
            host_name=None,
            host_title=None,
            host_race=None,
            host_subrace=None,
            host_sex=None,
            profession=None,
            service_id=None,
            assortment_keys=(),
            authored_kwargs=(),
        )
        base.update(changes)
        return replace(self.guild, **base)

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_place_may_author_no_host_at_all(self):
        # A place that simply exists — plaza, forecourt, quay — loads with no
        # host fields, and the absent race is never reported as unknown race
        # ``None`` (the per-field checks belong to the authored host only).
        try:
            validate_place_registry({"t_plaza_place": self._hostless()})
        except ValueError as error:  # pragma: no cover - failure path asserts below
            self.fail(f"host-less place rejected: {error}")

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_half_authored_host_names_the_fields_that_break_the_set(self):
        # A name without a profession is an unfinished record, not an empty
        # room: the error names the place, the fields found and the fields
        # missing — that message is the point of the rule.
        name_only = replace(
            self._hostless(), host_name="測試街長", host_title="測試頭銜"
        )
        with self.assertRaises(ValueError) as caught:
            validate_place_registry({"t_plaza_place": name_only})
        message = str(caught.exception)
        self.assertIn("t_plaza_place", message)
        for field in ("host_name", "host_title"):
            self.assertIn(field, message)
        for field in ("host_race", "host_sex", "profession", "service_id"):
            self.assertIn(field, message)
        # The mirror image: a profession without a host name.
        profession_only = replace(self._hostless(), profession="merchant")
        with self.assertRaises(ValueError) as caught:
            validate_place_registry({"t_plaza_place": profession_only})
        message = str(caught.exception)
        self.assertIn("t_plaza_place", message)
        self.assertIn("profession", message)
        self.assertIn("host_name", message)

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_host_less_place_may_not_sell(self):
        # Goods require a merchant to sell them: assortments, additions and
        # exclusions are each rejected on a host-less row, naming the place.
        for field, value in (
            ("assortment_keys", ("common_arms",)),
            ("extra_item_keys", ("t_any_item",)),
            ("excluded_item_keys", ("t_any_item",)),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError) as caught:
                    validate_place_registry(
                        {"t_plaza_place": self._hostless(**{field: value})}
                    )
                message = str(caught.exception)
                self.assertIn("t_plaza_place", message)
                self.assertIn("goods", message)

    @covers_requirement(
        "settlement-place-registry::a-place-is-the-single-authored-record-of-one-service-location"
    )
    def test_a_stray_subrace_or_kwargs_break_the_absent_host(self):
        # A wholly absent group carries no optional parts either: a stray
        # subrace or component kwargs is found-but-rest-missing material.
        for changes in (
            {"host_subrace": "high_elven"},
            {"authored_kwargs": (("dialogue_key", "guild_staff"),)},
        ):
            with self.subTest(**changes):
                with self.assertRaises(ValueError) as caught:
                    validate_place_registry({"t_plaza_place": self._hostless(**changes)})
                message = str(caught.exception)
                self.assertIn("t_plaza_place", message)
                broken = next(iter(changes))
                self.assertIn(broken, message)


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