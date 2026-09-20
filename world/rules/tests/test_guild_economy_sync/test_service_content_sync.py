"""Slice of ``test_guild_economy_sync``: ServiceContentSyncTests, ServiceContentWithoutInteriorsTests.
"""
from tools.spec_traceability import covers_requirement
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.components import GuildExaminer
from typeclasses.components import GuildStaff
from typeclasses.components import Merchant
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.guild_config import get_catalog
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.guild_economy import sync_service_content
import unittest
from ._support import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    GUILD_SERVICE_ID,
    MERCHANT_SERVICE_ID,
    ServiceContentIsolation,
    _guild_branch_key,
    _guild_dialogue_key,
    _guild_host_name,
    _guild_row,
    _merchant_host_name,
    _merchant_row,
    _merchant_shop_key,
    _place_by_kind,
)


class ServiceContentSyncTests(ServiceContentIsolation, EvenniaTestCase):
    def _guild_host(self):
        # Authored identity is the key now; reuse anchors on the component
        # service_id (npc-title-authored-identities D3).
        return NPC.objects.filter(db_key=_guild_host_name()).first()

    def _merchant_host(self):
        return NPC.objects.filter(db_key=_merchant_host_name()).first()

    def _guild_hall(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    @covers_requirement("sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state")
    @covers_requirement(
        "place-driven-service-sync::a-place-authors-its-host-s-race-subrace-and-sex"
    )
    def test_fresh_sync_creates_one_guild_and_one_merchant_host(self):
        sync_service_content()
        guild_host = self._guild_host()
        merchant_host = self._merchant_host()
        self.assertIsNotNone(guild_host)
        self.assertIsNotNone(merchant_host)
        self.assertTrue(guild_host.components.has(GuildStaff.get_component_slot()))
        self.assertTrue(guild_host.components.has(GuildExaminer.get_component_slot()))
        self.assertTrue(guild_host.components.has(ScriptedDialogue.get_component_slot()))
        self.assertTrue(merchant_host.components.has(Merchant.get_component_slot()))
        self.assertEqual(
            guild_host.components.get(GuildStaff.get_component_slot()).branch_key,
            _guild_branch_key(),
        )
        self.assertEqual(
            guild_host.components.get(GuildStaff.get_component_slot()).service_id,
            GUILD_SERVICE_ID,
        )
        self.assertEqual(
            guild_host.components.get(GuildExaminer.get_component_slot()).service_id,
            GUILD_SERVICE_ID,
        )
        self.assertEqual(
            guild_host.components.get(ScriptedDialogue.get_component_slot()).dialogue_key,
            _guild_dialogue_key(),
        )
        self.assertEqual(merchant_host.components.get(Merchant.get_component_slot()).shop_key, _merchant_shop_key())
        self.assertEqual(merchant_host.components.get(Merchant.get_component_slot()).service_id, MERCHANT_SERVICE_ID)
        # Bit-for-bit room placement matches the pre-change interpreter.
        self.assertEqual(guild_host.location, self._guild_hall())
        self.assertEqual(
            merchant_host.location, search_object_by_tag(GENERAL_STORE_TAG)[0]
        )
        # Authored identity + race baseline + canonical ages are the unchanged
        # creation guarantees. place-driven-service-sync applies each place
        # row's authored race/subrace/sex instead of a hard-coded human; the
        # subrace-None assertion pins the task 4.1 neutrality precondition
        # (if a subrace is ever authored, the comparison must widen to stats).
        for host, place in (
            (guild_host, _place_by_kind("guild_hall")),
            (merchant_host, _place_by_kind("general_store")),
        ):
            self.assertEqual(host.race, place.host_race)
            self.assertIsNone(place.host_subrace)
            self.assertEqual(host.subrace, place.host_subrace)
            self.assertEqual(host.sex, place.host_sex)
            self.assertEqual(int(host.attributes.get("age")), 18)
            self.assertEqual(int(host.attributes.get("apparent_age")), 18)
        self.assertEqual(guild_host.npc_title, _guild_row().title)
        self.assertEqual(merchant_host.npc_title, _merchant_row().title)

    def test_hosts_are_in_the_right_interiors(self):
        sync_service_content()
        self.assertEqual(self._guild_host().location, self._guild_hall())
        self.assertEqual(
            self._merchant_host().location,
            search_object_by_tag(GENERAL_STORE_TAG)[0],
        )

    @covers_requirement("sample-city-altoria::guild-service-hosts-carry-canonical-age")
    def test_service_hosts_carry_canonical_ages(self):
        sync_service_content()
        for host in (self._guild_host(), self._merchant_host()):
            self.assertEqual(int(host.attributes.get("age")), 18)
            self.assertEqual(int(host.attributes.get("apparent_age")), 18)

    @covers_requirement("sample-city-altoria::guild-service-hosts-carry-canonical-age")
    def test_resync_repairs_hosts_missing_canonical_ages(self):
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
        offers = get_catalog().shop_configs[_merchant_shop_key()].offers
        self.assertEqual(sorted(stock), sorted(offer.item_key for offer in offers))
        self.assertGreater(len(stock), 3)
        # Probe on the lowest offered item key: any offered key survives the
        # resync identically; none is named.
        probe_key = min(offer.item_key for offer in offers)
        stock[probe_key] = 1
        merchant.merchant_stock = stock

        sync_service_content()

        merchant = self._merchant_host().components.get(Merchant.get_component_slot())
        self.assertEqual(merchant.merchant_stock[probe_key], 1)

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
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
            [name for name in guild_host.components.db_names if name in {GuildStaff.get_component_slot(), GuildExaminer.get_component_slot()}],
            [GuildStaff.get_component_slot(), GuildExaminer.get_component_slot()],
        )
        sync_service_content()
        guild_host = self._guild_host()
        self.assertEqual(
            [name for name in guild_host.components.db_names if name in {GuildStaff.get_component_slot(), GuildExaminer.get_component_slot()}],
            [GuildStaff.get_component_slot(), GuildExaminer.get_component_slot()],
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
    unittest.main()
