"""Integration tests for roster-driven service content sync (tasks 3.x, 4.2)."""

from tools.spec_traceability import covers_requirement

import dataclasses
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.components import (
    GuildExaminer,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
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
from world.rules.guild_config import CATALOG, ServiceHostRow, get_catalog
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.profession_assembly import assemble_profession_components
from world.rules.profession_config import get_profession
from world.rules.quest_issuance import resolve_issuer_key
from world.rules.guild_economy import (
    ServiceAnchorIntegrityError,
    sync_service_content,
)

GUILD_SERVICE_ID = "altoria_guild_master"
MERCHANT_SERVICE_ID = "altoria_merchant"


def _roster_row(service_id):
    """The live catalog's roster row anchored on ``service_id``.

    This suite is the sync interpreter's contract over the roster itself;
    every authored identity it asserts (host names/titles, branch/shop/
    dialogue keys) is READ from the loaded roster rows instead of being
    named here, so the same assertions survive a roster re-author.
    """
    for row in get_catalog().service_hosts:
        if row.service_id == service_id:
            return row
    raise AssertionError(f"roster lost the {service_id!r} row")


def _guild_row():
    return _roster_row(GUILD_SERVICE_ID)


def _merchant_row():
    return _roster_row(MERCHANT_SERVICE_ID)


def _guild_host_name():
    return _guild_row().name


def _merchant_host_name():
    return _merchant_row().name


def _guild_branch_key():
    return _guild_row().authored_kwargs["branch_key"]


def _guild_dialogue_key():
    return _guild_row().authored_kwargs["dialogue_key"]


def _merchant_shop_key():
    return _merchant_row().authored_kwargs["shop_key"]


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
        return NPC.objects.filter(db_key=_guild_host_name()).first()

    def _merchant_host(self):
        return NPC.objects.filter(db_key=_merchant_host_name()).first()

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
        # Race baseline + canonical ages are the unchanged creation guarantees.
        for host in (guild_host, merchant_host):
            self.assertEqual(host.race, "human")
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


class ServiceHostIdentityTests(ServiceContentIsolation, EvenniaTestCase):
    """Authored creation, service-anchor reuse, no runtime identity writes (D3)."""

    def _guild_host(self):
        return NPC.objects.filter(db_key=_guild_host_name()).first()

    def _merchant_host(self):
        return NPC.objects.filter(db_key=_merchant_host_name()).first()

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
        self.assertEqual(host.npc_title, _guild_row().title)
        events = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_created"
        ]
        self.assertEqual(len(events), 2)  # guild host + merchant host
        self.assertEqual(events[0].kwargs["context"]["char"], _guild_host_name())
        self.assertEqual(events[0].kwargs["context"]["service"], GUILD_SERVICE_ID)
        self.assertEqual(events[0].kwargs["context"]["shop"], _guild_branch_key())
        self.assertEqual(
            events[0].kwargs["context"]["profession"], _guild_row().profession.key
        )
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
            authored_kwargs=dict(_guild_row().authored_kwargs),
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
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 1)
        self.assertEqual(NPC.objects.filter(db_key="改名後").count(), 0)
        self.assertEqual(self._guild_host().pk, before.pk)

    def _anchored_legacy_host(self, key):
        # A pre-identity dev host anchored by service_id under a free key.
        legacy = create_object(NPC, key=key, location=self._guild_hallish())
        legacy.components.add(
            GuildStaff.create(legacy, service_id=GUILD_SERVICE_ID, branch_key=_guild_branch_key())
        )
        legacy.components.add(
            GuildExaminer.create(legacy, service_id=GUILD_SERVICE_ID, branch_key=_guild_branch_key())
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
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 0)

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
            Merchant.create(extra, service_id="retired_shop_id", shop_key=_merchant_shop_key())
        )
        # Attach a second, retired-anchor component to the SAME host so it
        # holds both a roster-matching anchor and a stale one.
        titled = host
        titled.components.add(
            Merchant.create(titled, service_id="retired_shop_id", shop_key=_merchant_shop_key())
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
                second, service_id=GUILD_SERVICE_ID, branch_key=_guild_branch_key()
            )
        )
        with self.assertRaises(ServiceAnchorIntegrityError):
            sync_service_content()
        first.refresh_from_db()
        second.refresh_from_db()  # untouched fail-closed, no arbitrary pick
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 0)

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
        self.assertEqual(events[0].kwargs["context"]["char"], _merchant_host_name())
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
        self.assertEqual(host.npc_title, _guild_row().title)
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
        host = NPC.objects.filter(db_key=_merchant_host_name()).first()
        host.key = "手工改名的商人"
        host.save()
        with patch("world.rules.guild_economy.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                sync_service_content()
        self.assertEqual(NPC.objects.filter(db_key="手工改名的商人").count(), 1)
        self.assertIsNone(NPC.objects.filter(db_key=_merchant_host_name()).first())
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
        self.assertIsNotNone(NPC.objects.filter(db_key=_guild_host_name()).first())
        self.assertEqual(NPC.objects.filter(db_key=_merchant_host_name()).count(), 0)


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
            Merchant.create(host, service_id="retired_shop_id", shop_key=_merchant_shop_key())
        )
        return host

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    def test_empty_roster_converges_every_host_even_with_no_rooms(self):
        # The most direct roster shrink: an empty roster authorises nothing,
        # so sync deletes both hosts even though no row's room can resolve.
        sync_service_content()
        guild = NPC.objects.filter(db_key=_guild_host_name()).first()
        merchant = NPC.objects.filter(db_key=_merchant_host_name()).first()
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
        guild = NPC.objects.filter(db_key=_guild_host_name()).first()
        merchant = NPC.objects.filter(db_key=_merchant_host_name()).first()
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
                    host, service_id=MERCHANT_SERVICE_ID, shop_key=_merchant_shop_key()
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
        self.assertIsNone(NPC.objects.filter(db_key=_guild_host_name()).first())
        self.assertIsNone(NPC.objects.filter(db_key=_merchant_host_name()).first())

    def _hall(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]


class ServiceHostBindingConvergenceTests(ServiceContentIsolation, EvenniaTestCase):
    """Every sync converges binding fields on reused hosts without identity churn."""

    @covers_requirement(
        "service-anchoring::service-components-carry-an-authored-person-or-place-binding"
    )
    def test_repeated_sync_converges_bindings_and_never_recreates_components(self):
        sync_service_content()
        guild = NPC.objects.filter(db_key=_guild_host_name()).first()
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
        host = create_object(NPC, key=_guild_host_name(), location=hall)
        host.components.add(
            GuildStaff.create(
                host,
                service_id=GUILD_SERVICE_ID,
                branch_key=_guild_branch_key(),
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
        self.assertEqual(backfilled.branch_key, _guild_branch_key())
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


COMMISSIONER_NAME = "灰婆婆"
COMMISSIONER_SERVICE_ID = "altoria_commissioner"
IMPORTED_COMMISSIONER_SERVICE_ID = "grey_granny"


class ServiceHostQuestIssuerSyncTests(ServiceContentIsolation, EvenniaTestCase):
    """quest-issuer-authorization: roster anchors reuse; imported carriers survive.

    The commissioner row used here is an internal robustness fixture: config
    validation rejects person-bound roster rows, so no shipped roster can
    carry one — the row exercises the sync interpreter's anchor-reuse path
    directly, exactly the path the row-anchor contract protects.
    """

    def _commissioner_row(self):
        return ServiceHostRow(
            name=COMMISSIONER_NAME,
            title="委託人灰婆婆",
            profession=get_profession("quest_issuer"),
            anchor_room=GUILD_HALL_TAG,
            service_id=COMMISSIONER_SERVICE_ID,
            authored_kwargs={},
        )

    def _sync_with_commissioner_row(self):
        catalog = get_catalog()
        self._patch_roster(tuple(catalog.service_hosts) + (self._commissioner_row(),))
        sync_service_content()

    @covers_requirement(
        "quest-issuer-authorization::the-questissuer-component-mirrors-the-existing-service-host-component-shape",
    )
    def test_commissioner_blueprint_survives_repeated_roster_synchronization(self):
        self._sync_with_commissioner_row()
        host = NPC.objects.filter(db_key=COMMISSIONER_NAME).first()
        self.assertIsNotNone(host)
        component = host.components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, COMMISSIONER_SERVICE_ID)
        first_pk = host.pk

        # Second run: reuse through the service_id anchor, no duplicate host,
        # no duplicate component, no raise.
        self._sync_with_commissioner_row()
        hosts = NPC.objects.filter(db_key=COMMISSIONER_NAME)
        self.assertEqual(hosts.count(), 1)
        self.assertEqual(hosts.first().pk, first_pk)
        component = hosts.first().components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, COMMISSIONER_SERVICE_ID)

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_a_roster_created_commissioner_resolves_to_its_identity_form(self):
        # The roster projects only REQUIRED identity kwargs; issuer_key is
        # deliberately not one, so a roster-created commissioner is unauthored.
        self._sync_with_commissioner_row()
        host = NPC.objects.filter(db_key=COMMISSIONER_NAME).first()
        component = host.components.get(QuestIssuer.get_component_slot())
        self.assertIsNone(component.issuer_key)
        self.assertEqual(resolve_issuer_key(host), f"npc:#{host.pk}")

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_an_imported_person_bound_commissioner_survives_the_service_sync(self):
        # An imported commissioner carries a service_id the roster can never
        # claim (person-bound anchors are not roster-anchorable); convergence
        # must not treat it as shrunken-away residue and delete the host.
        sync_service_content()
        hall = search_object_by_tag(GUILD_HALL_TAG)[0]
        commissioner = create_object(NPC, key=COMMISSIONER_NAME, location=hall)
        assemble_profession_components(
            commissioner,
            get_profession("quest_issuer"),
            {
                "quest_issuer": {
                    "service_id": IMPORTED_COMMISSIONER_SERVICE_ID,
                    "issuer_key": "grey_granny",
                }
            },
            anchor_room=None,
        )

        sync_service_content()

        survivor = NPC.objects.filter(pk=commissioner.pk).first()
        self.assertIsNotNone(survivor)
        component = survivor.components.get(QuestIssuer.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(resolve_issuer_key(survivor), "npc:grey_granny")

    @covers_requirement(
        "quest-issuer-authorization::commissioner-authority-is-authorable-through-the-import-pipeline",
    )
    def test_no_existing_npc_gains_issuing_authority_without_authored_content(self):
        sync_service_content()
        carriers = [
            host
            for host in NPC.objects.all_family()
            if host.components.has(QuestIssuer.name)
        ]
        self.assertEqual(carriers, [])


if __name__ == "__main__":
    import unittest

    unittest.main()
