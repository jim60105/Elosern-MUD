"""Integration tests for roster-driven service content sync (tasks 3.x, 4.2)."""

from tools.spec_traceability import covers_requirement

import dataclasses
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import GuildExaminer, GuildStaff, Merchant, ScriptedDialogue
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
from world.rules import guild_config
from world.rules import guild_economy
from world.rules.guild_config import CATALOG, get_catalog
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.guild_economy import (
    ServiceAnchorIntegrityError,
    sync_service_content,
)

GUILD_SERVICE_ID = "altoria_guild_master"
MERCHANT_SERVICE_ID = "altoria_merchant"

GUILD_HOST_NAME = "葛里安·衛登"
GUILD_HOST_TITLE = "阿爾托利亞分會會長"
MERCHANT_HOST_NAME = "瑪爾特·金秤"
MERCHANT_HOST_TITLE = "阿爾托利亞雜貨商店老闆"

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
        self._patchers: list = []

    def tearDown(self):
        global CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()

    def _roster_minus(self, service_id):
        """Patch the cached catalog with one roster row removed."""
        catalog = get_catalog()
        self._patch_roster(
            tuple(row for row in catalog.service_hosts if row.service_id != service_id)
        )

    def _patch_roster(self, rows):
        """Patch the cached catalog to carry exactly ``rows`` as its roster."""
        catalog = get_catalog()
        patched = guild_config.GuildCatalog(
            merit_thresholds=catalog.merit_thresholds,
            exam_profiles=catalog.exam_profiles,
            shop_configs=catalog.shop_configs,
            quest_offers=catalog.quest_offers,
            service_hosts=rows,
        )
        patcher = patch.object(guild_economy, "get_catalog", return_value=patched)
        patcher.start()
        self._patchers.append(patcher)
        self.addCleanup(patcher.stop)


class ServiceContentSyncTests(ServiceContentIsolation, EvenniaTestCase):
    def _guild_host(self):
        # Authored identity is the key now; reuse anchors on the component
        # service_id (npc-title-authored-identities D3).
        return NPC.objects.filter(db_key=GUILD_HOST_NAME).first()

    def _merchant_host(self):
        return NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()

    def _guild_hall(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    @covers_requirement("sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state")
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
            "guild_branch_altoria",
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
            "guild_staff",
        )
        self.assertEqual(merchant_host.components.get(Merchant.get_component_slot()).shop_key, "altoria_general_store")
        self.assertEqual(merchant_host.components.get(Merchant.get_component_slot()).service_id, MERCHANT_SERVICE_ID)
        # Bit-for-bit room placement matches the pre-change interpreter.
        self.assertEqual(guild_host.location, self._guild_hall())
        self.assertEqual(
            merchant_host.location, search_object_by_tag(GENERAL_STORE_TAG)[0]
        )
        # Race baseline + adult identity are the unchanged creation guarantees.
        for host in (guild_host, merchant_host):
            self.assertEqual(host.race, "human")
            self.assertEqual(int(host.attributes.get("age")), 18)
            self.assertEqual(int(host.attributes.get("apparent_age")), 18)
        self.assertEqual(guild_host.npc_title, GUILD_HOST_TITLE)
        self.assertEqual(merchant_host.npc_title, MERCHANT_HOST_TITLE)

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

    def _merchant_host(self):
        return NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    @covers_requirement("npc-identity-titles::host-and-examiner-creation-emit-boundary-info-events")
    def test_first_sync_creates_the_authored_host_once(self):
        # The creation event is commit-bound (sync runs inside startup
        # transactions); execute the callbacks to observe it.
        with patch("world.rules.guild_economy.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
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
        self.assertEqual(events[0].kwargs["context"]["service"], GUILD_SERVICE_ID)
        self.assertEqual(events[0].kwargs["context"]["shop"], "guild_branch_altoria")
        self.assertEqual(events[0].kwargs["context"]["profession"], "guild_staff")
        with self.captureOnCommitCallbacks(execute=True):
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
        # Simulate an author renaming the roster row: the anchor keeps the host.
        catalog = get_catalog()
        renamed_row = guild_config.ServiceHostRow(
            name="改名後",
            title=before.npc_title,
            profession=before_row_profession(catalog),
            anchor_room="altoria_guild_hall",
            service_id=GUILD_SERVICE_ID,
            authored_kwargs={
                "branch_key": "guild_branch_altoria",
                "dialogue_key": "guild_staff",
            },
        )
        rows = tuple(
            renamed_row if row.service_id == GUILD_SERVICE_ID else row
            for row in catalog.service_hosts
        )
        patched = guild_config.GuildCatalog(
            merit_thresholds=catalog.merit_thresholds,
            exam_profiles=catalog.exam_profiles,
            shop_configs=catalog.shop_configs,
            quest_offers=catalog.quest_offers,
            service_hosts=rows,
        )
        with patch.object(guild_economy, "get_catalog", return_value=patched):
            sync_service_content()
        self.assertEqual(NPC.objects.filter(db_key=GUILD_HOST_NAME).count(), 1)
        self.assertEqual(NPC.objects.filter(db_key="改名後").count(), 0)
        self.assertEqual(self._guild_host().pk, before.pk)

    def _anchored_legacy_host(self, key):
        # A pre-identity dev host anchored by service_id under a free key.
        legacy = create_object(NPC, key=key, location=self._guild_hallish())
        legacy.components.add(
            GuildStaff.create(legacy, service_id=GUILD_SERVICE_ID, branch_key="guild_branch_altoria")
        )
        legacy.components.add(
            GuildExaminer.create(legacy, service_id=GUILD_SERVICE_ID, branch_key="guild_branch_altoria")
        )
        return legacy

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_sync_never_backfills_a_title_into_an_anchored_host(self):
        legacy = self._anchored_legacy_host("舊公會管理人")
        sync_service_content()
        legacy.refresh_from_db()
        # Reused as-is (roster membership keeps it): no runtime title write,
        # no second authored host.
        self.assertEqual(legacy.npc_title, "")
        self.assertEqual(NPC.objects.filter(db_key=GUILD_HOST_NAME).count(), 0)

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_unrelated_npc_sharing_a_retired_key_survives_convergence(self):
        # Deletion anchors on the service-component identity shape, never the
        # key: an unrelated NPC with no service component is never destroyed.
        unrelated = create_object(NPC, key=GUILD_SERVICE_ID, location=self._guild_hallish())
        sync_service_content()
        unrelated.refresh_from_db()  # still alive

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_ambiguous_titled_same_anchor_host_is_kept_with_warning(self):
        # A titled NPC holding both a roster-matching anchor and a stale
        # foreign service_id is ambiguous residue; convergence refuses to
        # guess and names the condition instead.
        host = self._anchored_legacy_host("可疑公會管理人")
        host.npc_title = "手工頭銜"
        host.save()
        extra = create_object(NPC, key="殘留商人", location=self._guild_hallish())
        extra.components.add(
            Merchant.create(extra, service_id="retired_shop_id", shop_key="altoria_general_store")
        )
        # Attach a second, retired-anchor component to the SAME host so it
        # holds both a roster-matching anchor and a stale one.
        titled = host
        titled.components.add(
            Merchant.create(titled, service_id="retired_shop_id", shop_key="altoria_general_store")
        )
        with patch("world.rules.guild_economy.log_warn") as warned:
            sync_service_content()
        titled.refresh_from_db()  # kept for manual repair
        host.refresh_from_db()
        self.assertIsNotNone(titled.components.get(Merchant.get_component_slot()))
        events = [
            call for call in warned.call_args_list
            if call.args and call.args[0] == "guild_service_host_convergence_ambiguous"
        ]
        self.assertEqual(len(events), 1)
        # The unrelated titleless stale-merchant is deleted, not warned.
        with self.assertRaises(NPC.DoesNotExist):
            extra.refresh_from_db()

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_duplicate_service_anchors_fail_closed_before_mutation(self):
        # Two live NPCs claiming one service anchor violate the single-host
        # invariant: sync raises the named integrity error and creates nothing.
        first = self._anchored_legacy_host("分身公會管理人一")
        second = create_object(NPC, key="分身公會管理人二", location=self._guild_hallish())
        second.components.add(
            GuildStaff.create(
                second, service_id=GUILD_SERVICE_ID, branch_key="guild_branch_altoria"
            )
        )
        with self.assertRaises(ServiceAnchorIntegrityError):
            sync_service_content()
        first.refresh_from_db()
        second.refresh_from_db()  # untouched fail-closed, no arbitrary pick
        self.assertEqual(NPC.objects.filter(db_key=GUILD_HOST_NAME).count(), 0)

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    def test_roster_shrink_deletes_only_the_surplus_host(self):
        sync_service_content()
        merchant = self._merchant_host()
        # Party bindings purge through NPC.at_object_delete on the deletion.
        from typeclasses.characters import PlayerCharacter
        from world.rules.party import join_party, party_ids

        player = create_object(PlayerCharacter, key="收縮測試玩家")
        player.race = "human"
        player.apply_race_baseline()
        player.location = merchant.location
        join_party(merchant, player)
        self.assertEqual(party_ids(player), [merchant.pk])
        self._roster_minus(MERCHANT_SERVICE_ID)
        with patch("world.rules.guild_economy.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()
        with self.assertRaises(NPC.DoesNotExist):
            merchant.refresh_from_db()
        self.assertIsNotNone(self._guild_host())  # roster member survives
        events = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_convergence_removed"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["char"], MERCHANT_HOST_NAME)
        self.assertEqual(events[0].kwargs["context"]["service"], MERCHANT_SERVICE_ID)
        self.assertEqual(party_ids(player), [])

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    def test_stale_keyed_host_is_converged_away_and_recreated_authored(self):
        # A dev host still keyed by the roster service_id (the old sync shape)
        # still matches roster membership through its component service_id, so
        # it is reused as-is (never renamed); deleting the row converges it
        # away, and restoring the row recreates the full authored identity.
        legacy = self._anchored_legacy_host(GUILD_SERVICE_ID)
        self._roster_minus(GUILD_SERVICE_ID)
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        with self.assertRaises(NPC.DoesNotExist):
            legacy.refresh_from_db()
        # Stop the shrunk-roster patcher: the next sync sees the full roster.
        for patcher in reversed(self._patchers):
            patcher.stop()
        self._patchers.clear()
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()  # roster restored
        host = self._guild_host()
        self.assertIsNotNone(host)
        self.assertEqual(host.npc_title, GUILD_HOST_TITLE)
        self.assertIsNotNone(host.components.get(GuildStaff.get_component_slot()))

    def _guild_hallish(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]


def before_row_profession(catalog):
    for row in catalog.service_hosts:
        if row.service_id == GUILD_SERVICE_ID:
            return row.profession
    raise AssertionError("shipped roster lost the guild row")


class ServiceHostAnchorReuseTests(ServiceContentIsolation, EvenniaTestCase):
    """Anchor survives key drift: a renamed host stays reused (no rename path)."""

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_anchor_reuse_survives_a_manual_key_change(self):
        sync_service_content()
        host = NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()
        host.key = "手工改名的商人"
        host.save()
        with patch("world.rules.guild_economy.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()
        self.assertEqual(NPC.objects.filter(db_key="手工改名的商人").count(), 1)
        self.assertIsNone(NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first())
        self.assertFalse(
            [
                call for call in logged.call_args_list
                if call.args and call.args[0] == "guild_service_host_created"
            ]
        )


class ServiceHostAnchorRoomTests(ServiceContentIsolation, EvenniaTestCase):
    """Per-row anchor resolution: an unresolvable tag skips exactly one row."""

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_unresolvable_anchor_room_skips_only_its_row(self):
        catalog = get_catalog()
        rows = tuple(
            guild_config.ServiceHostRow(
                row.name,
                row.title,
                row.profession,
                "no_such_room_tag",
                row.service_id,
                row.authored_kwargs,
            )
            if row.service_id == MERCHANT_SERVICE_ID
            else row
            for row in catalog.service_hosts
        )
        patched = guild_config.GuildCatalog(
            merit_thresholds=catalog.merit_thresholds,
            exam_profiles=catalog.exam_profiles,
            shop_configs=catalog.shop_configs,
            quest_offers=catalog.quest_offers,
            service_hosts=rows,
        )
        with patch.object(guild_economy, "get_catalog", return_value=patched):
            with patch("world.rules.guild_economy.log_warn") as warned:
                sync_service_content()
        events = [
            call for call in warned.call_args_list
            if call.args and call.args[0] == "guild_service_host_anchor_room_missing"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["service"], MERCHANT_SERVICE_ID)
        self.assertEqual(events[0].kwargs["context"]["anchor_room"], "no_such_room_tag")
        # The resolvable row processed exactly as before; nothing was created
        # for the skipped row, and the skipped merchant's stock stayed absent.
        self.assertIsNotNone(NPC.objects.filter(db_key=GUILD_HOST_NAME).first())
        self.assertEqual(NPC.objects.filter(db_key=MERCHANT_HOST_NAME).count(), 0)


class ServiceHostRosterAuthorityTests(ServiceContentIsolation, EvenniaTestCase):
    """Roster authority never depends on anchor-room resolution (design D9)."""

    def _rows_with_tags(self, tag):
        catalog = get_catalog()
        return tuple(
            dataclasses.replace(row, anchor_room=tag) for row in catalog.service_hosts
        )

    def _stale_host(self):
        host = create_object(NPC, key="殘留服務人", location=None)
        host.components.add(
            Merchant.create(host, service_id="retired_shop_id", shop_key="altoria_general_store")
        )
        return host

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    def test_empty_roster_converges_every_host_even_with_no_rooms(self):
        # The most direct roster shrink: an empty roster authorises nothing,
        # so sync deletes both hosts even though no row's room can resolve.
        sync_service_content()
        guild = NPC.objects.filter(db_key=GUILD_HOST_NAME).first()
        merchant = NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()
        self._patch_roster(())
        with patch("world.rules.guild_economy.log_warn") as warned:
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()
        for host in (guild, merchant):
            with self.assertRaises(NPC.DoesNotExist):
                host.refresh_from_db()
        still_missing = [
            call for call in warned.call_args_list
            if call.args and call.args[0] == "guild_economy_service_interiors_still_missing"
        ]
        self.assertEqual(len(still_missing), 1)  # creation skipped; deletion was not

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_all_rows_unresolvable_still_converge_and_never_touch_roster_hosts(self):
        sync_service_content()
        guild = NPC.objects.filter(db_key=GUILD_HOST_NAME).first()
        merchant = NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first()
        stale = self._stale_host()
        expected = NPC.objects.all_family().count() - 1  # only the stale host dies
        self._patch_roster(self._rows_with_tags("no_such_room_tag"))
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        # The stale host is converged away...
        with self.assertRaises(NPC.DoesNotExist):
            stale.refresh_from_db()
        # ...while roster-listed hosts stay byte-identical and unmoved.
        guild.refresh_from_db()
        merchant.refresh_from_db()
        self.assertEqual(
            guild.location, search_object_by_tag(GUILD_HALL_TAG)[0]
        )
        self.assertEqual(
            merchant.location, search_object_by_tag(GENERAL_STORE_TAG)[0]
        )
        self.assertEqual(NPC.objects.all_family().count(), expected)

    @covers_requirement(
        "npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename"
    )
    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    def test_duplicate_anchor_on_unresolvable_row_fails_closed_before_any_mutation(self):
        # A duplicate claim on a row whose room cannot resolve still fails
        # closed: NOTHING is created, moved, or deleted — convergence included.
        first = create_object(NPC, key="分身商人一", location=self._hall())
        second = create_object(NPC, key="分身商人二", location=self._hall())
        for host in (first, second):
            host.components.add(
                Merchant.create(
                    host, service_id=MERCHANT_SERVICE_ID, shop_key="altoria_general_store"
                )
            )
        stale = self._stale_host()
        catalog = get_catalog()
        self._patch_roster(
            tuple(
                dataclasses.replace(row, anchor_room="no_such_room_tag")
                if row.service_id == MERCHANT_SERVICE_ID
                else row
                for row in catalog.service_hosts
            )
        )
        with self.assertRaises(ServiceAnchorIntegrityError):
            sync_service_content()
        first.refresh_from_db()
        second.refresh_from_db()
        stale.refresh_from_db()  # convergence never ran
        self.assertIsNone(NPC.objects.filter(db_key=GUILD_HOST_NAME).first())
        self.assertIsNone(NPC.objects.filter(db_key=MERCHANT_HOST_NAME).first())

    def _hall(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]


class ServiceHostBindingConvergenceTests(ServiceContentIsolation, EvenniaTestCase):
    """Every sync converges binding fields on reused hosts without identity churn."""

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_repeated_sync_converges_bindings_and_never_recreates_components(self):
        sync_service_content()
        guild = NPC.objects.filter(db_key=GUILD_HOST_NAME).first()
        staff = guild.components.get(GuildStaff.get_component_slot())
        self.assertEqual(staff.service_binding, "place")
        self.assertEqual(
            staff.anchor_room_id, search_object_by_tag(GUILD_HALL_TAG)[0].pk
        )
        dialogue = guild.components.get(ScriptedDialogue.get_component_slot())
        self.assertEqual(dialogue.service_binding, "place")
        staff_before = (staff.service_id, staff.branch_key)
        slots_before = sorted(guild.components.db_names)
        # A second sync on the reused host: bindings stay, identity intact,
        # the slot is never duplicated.
        sync_service_content()
        guild.refresh_from_db()
        staff2 = guild.components.get(GuildStaff.get_component_slot())
        self.assertEqual((staff2.service_id, staff2.branch_key), staff_before)
        self.assertEqual(staff2.service_binding, "place")
        self.assertEqual(sorted(guild.components.db_names), slots_before)

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_reuse_backfills_missing_binding_fields_on_legacy_hosts(self):
        # A host whose components predate the anchoring change carries no
        # binding fields; the next sync writes them without touching identity
        # or moving the host.
        hall = search_object_by_tag(GUILD_HALL_TAG)[0]
        host = create_object(NPC, key=GUILD_HOST_NAME, location=hall)
        host.components.add(
            GuildStaff.create(
                host,
                service_id="altoria_guild_master",
                branch_key="guild_branch_altoria",
            )
        )
        legacy = host.components.get(GuildStaff.get_component_slot())
        self.assertIsNone(legacy.service_binding)
        sync_service_content()
        host.refresh_from_db()
        backfilled = host.components.get(GuildStaff.get_component_slot())
        self.assertEqual(backfilled.service_binding, "place")
        self.assertEqual(
            backfilled.anchor_room_id, search_object_by_tag(GUILD_HALL_TAG)[0].pk
        )
        self.assertEqual(backfilled.branch_key, "guild_branch_altoria")
        self.assertEqual(host.location, hall)


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
