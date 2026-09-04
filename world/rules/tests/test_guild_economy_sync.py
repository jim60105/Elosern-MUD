"""Integration tests for guild-economy service content sync (tasks 3.3-3.5)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.maps.bootstrap import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    sync_grid,
    sync_service_interiors,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.guild_config import CATALOG, get_catalog
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.lore.guild import GUILD_BRANCH_REGISTRY, GuildBranch
from world.lore.shops import SHOP_REGISTRY
from world.rules.guild_economy import (
    GUILD_SERVICE_KEY,
    _cleanup_legacy_service_hosts,
    MERCHANT_SERVICE_KEY,
    sync_service_content,
)

GUILD_HOST_NAME = GUILD_BRANCH_REGISTRY["guild_branch_altoria"].host_name
GUILD_HOST_TITLE = GUILD_BRANCH_REGISTRY["guild_branch_altoria"].host_title
MERCHANT_HOST_NAME = SHOP_REGISTRY["altoria_general_store"].host_name
MERCHANT_HOST_TITLE = SHOP_REGISTRY["altoria_general_store"].host_title

MERCHANT_STOCK_COUNT = 30  # every offered item key


class ServiceContentIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_service_interiors()
        self._previous_catalog = CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        global CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class ServiceContentSyncTests(ServiceContentIsolation, EvenniaTestCase):
    def _guild_host(self):
        # Authored identity is the key now; reuse anchors on the component
        # service_id (npc-title-authored-identities D3).
        return NPC.objects.filter(db_key=GUILD_HOST_NAME).first()

    def _merchant_host(self):
        return NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()

    def _guild_hall(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]

    @covers_requirement("sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state")
    def test_fresh_sync_creates_one_guild_and_one_merchant_host(self):
        sync_service_content()
        guild_host = self._guild_host()
        merchant_host = self._merchant_host()
        self.assertIsNotNone(guild_host)
        self.assertIsNotNone(merchant_host)
        self.assertTrue(guild_host.components.has(GuildStaff.get_component_slot()))
        self.assertTrue(guild_host.components.has(GuildExaminer.get_component_slot()))
        self.assertTrue(merchant_host.components.has(Merchant.get_component_slot()))
        self.assertEqual(
            guild_host.components.get(GuildStaff.get_component_slot()).branch_key,
            "guild_branch_altoria",
        )
        self.assertEqual(merchant_host.components.get(Merchant.get_component_slot()).shop_key, "altoria_general_store")

    def test_hosts_are_in_the_right_interiors(self):
        sync_service_content()
        self.assertEqual(self._guild_host().location, self._guild_hall())
        self.assertEqual(
            self._merchant_host().location,
            search_object_by_tag(GENERAL_STORE_TAG)[0],
        )

    @covers_requirement("sample-city-altoria::guild-service-hosts-carry-adult-identity")
    def test_service_hosts_carry_adult_identity(self):
        sync_service_content()
        for host in (self._guild_host(), self._merchant_host()):
            self.assertEqual(int(host.attributes.get("age")), 18)
            self.assertEqual(int(host.attributes.get("apparent_age")), 18)

    @covers_requirement("sample-city-altoria::guild-service-hosts-carry-adult-identity")
    def test_resync_repairs_hosts_missing_adult_identity(self):
        sync_service_content()
        for host in (self._guild_host(), self._merchant_host()):
            host.attributes.remove("age")
            host.attributes.remove("apparent_age")
        sync_service_content()
        for host in (self._guild_host(), self._merchant_host()):
            self.assertEqual(int(host.attributes.get("age")), 18)
            self.assertEqual(int(host.attributes.get("apparent_age")), 18)

    def test_merchant_stock_initializes_only_when_absent(self):
        sync_service_content()
        merchant = self._merchant_host().components.get(Merchant.get_component_slot())
        stock = dict(merchant.merchant_stock)
        offers = get_catalog().shop_configs["altoria_general_store"].offers
        self.assertEqual(sorted(stock), sorted(offer.item_key for offer in offers))
        self.assertGreater(len(stock), 3)
        stock["healing_potion"] = 1
        merchant.merchant_stock = stock

        sync_service_content()

        merchant = self._merchant_host().components.get(Merchant.get_component_slot())
        self.assertEqual(merchant.merchant_stock["healing_potion"], 1)

    def test_repeated_sync_creates_no_duplicates(self):
        sync_service_content()
        counts = (
            NPC.objects.all_family().count(),
            len(search_object_by_tag(GUILD_HALL_TAG)),
            len(search_object_by_tag(GENERAL_STORE_TAG)),
        )
        sync_service_content()
        sync_service_content()
        self.assertEqual(
            (NPC.objects.all_family().count(), len(search_object_by_tag(GUILD_HALL_TAG)), len(search_object_by_tag(GENERAL_STORE_TAG))),
            counts,
        )

    def test_repeated_sync_does_not_replicate_components(self):
        sync_service_content()
        guild_host = self._guild_host()
        self.assertEqual(
            [name for name in guild_host.components.db_names if name in {"guild_staff", "guild_examiner"}],
            ["guild_staff", "guild_examiner"],
        )
        sync_service_content()
        guild_host = self._guild_host()
        self.assertEqual(
            [name for name in guild_host.components.db_names if name in {"guild_staff", "guild_examiner"}],
            ["guild_staff", "guild_examiner"],
        )


class ServiceHostIdentityTests(ServiceContentIsolation, EvenniaTestCase):
    """Authored creation, service-anchor reuse, no runtime identity writes (D3)."""

    def _guild_host(self):
        return NPC.objects.filter(db_key=GUILD_HOST_NAME).first()

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    @covers_requirement("npc-identity-titles::host-and-examiner-creation-emit-boundary-info-events")
    def test_first_sync_creates_the_authored_host_once(self):
        with patch("world.rules.guild_economy.log_info") as logged:
            sync_service_content()
        host = self._guild_host()
        self.assertIsNotNone(host)
        self.assertEqual(host.npc_title, GUILD_HOST_TITLE)
        events = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_created"
        ]
        self.assertEqual(len(events), 2)  # guild host + merchant host
        self.assertEqual(events[0].kwargs["context"]["char"], GUILD_HOST_NAME)
        self.assertEqual(events[0].kwargs["context"]["service"], GUILD_SERVICE_KEY)
        self.assertEqual(events[0].kwargs["context"]["shop"], "guild_branch_altoria")
        sync_service_content()  # reuse fires nothing
        late = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_created"
        ]
        self.assertEqual(len(late), 2)

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_resync_never_renames_or_duplicates(self):
        sync_service_content()
        before = self._guild_host()
        self.assertIsNotNone(before)
        # Simulate an author renaming the registry row: the anchor keeps the host.
        branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        renamed = GuildBranch(
            branch.key, branch.display_name_zh, "改名後", branch.host_title, branch.anchor_key
        )
        GUILD_BRANCH_REGISTRY["guild_branch_altoria"] = renamed
        try:
            sync_service_content()
        finally:
            GUILD_BRANCH_REGISTRY["guild_branch_altoria"] = branch
        self.assertEqual(NPC.objects.filter(db_key=GUILD_HOST_NAME).count(), 1)
        self.assertEqual(NPC.objects.filter(db_key="改名後").count(), 0)
        self.assertEqual(self._guild_host().pk, before.pk)

    def _anchored_legacy_host(self, key):
        # A pre-identity dev host anchored by service_id under a free key.
        legacy = create_object(NPC, key=key, location=self._guild_hallish())
        legacy.components.add(
            GuildStaff.create(legacy, service_id=GUILD_SERVICE_KEY, branch_key="guild_branch_altoria")
        )
        legacy.components.add(
            GuildExaminer.create(legacy, service_id=GUILD_SERVICE_KEY, branch_key="guild_branch_altoria")
        )
        return legacy

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_sync_never_backfills_a_title_into_an_anchored_host(self):
        legacy = self._anchored_legacy_host("舊公會管理人")
        sync_service_content()
        legacy.refresh_from_db()
        # Reused as-is: no runtime title write, no second authored host.
        self.assertEqual(legacy.npc_title, "")
        self.assertEqual(NPC.objects.filter(db_key=GUILD_HOST_NAME).count(), 0)

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_legacy_keyed_host_is_discarded_and_recreated_authored(self):
        # The one-time cleanup discards hosts still keyed by the retired ASCII
        # anchors (clean cutover); the next sync recreates the full authored
        # identity with components.
        legacy = self._anchored_legacy_host(GUILD_SERVICE_KEY)
        _cleanup_legacy_service_hosts()
        self.assertIsNone(NPC.objects.filter(db_key=GUILD_SERVICE_KEY).first())
        with self.assertRaises(NPC.DoesNotExist):
            legacy.refresh_from_db()
        sync_service_content()
        host = self._guild_host()
        self.assertIsNotNone(host)
        self.assertEqual(host.npc_title, GUILD_HOST_TITLE)
        self.assertIsNotNone(host.components.get(GuildStaff.get_component_slot()))

    def _guild_hallish(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]


class ServiceHostAnchorReuseTests(ServiceContentIsolation, EvenniaTestCase):
    """Anchor survives key drift: a renamed host stays reused (no rename path)."""

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_anchor_reuse_survives_a_manual_key_change(self):
        sync_service_content()
        host = NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()
        host.key = "手工改名的商人"
        host.save()
        with patch("world.rules.guild_economy.log_info") as logged:
            sync_service_content()
        self.assertEqual(NPC.objects.filter(db_key="手工改名的商人").count(), 1)
        self.assertIsNone(NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first())
        self.assertFalse(
            [
                call for call in logged.call_args_list
                if call.args and call.args[0] == "guild_service_host_created"
            ]
        )


class ServiceContentWithoutInteriorsTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        register_catalog()

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        super().tearDown()

    def test_sync_service_content_without_interiors_degrades_gracefully(self):
        # No sync_grid was run; interiors do not exist, so no hosts are created.
        sync_service_content()
        self.assertEqual(NPC.objects.all_family().count(), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
