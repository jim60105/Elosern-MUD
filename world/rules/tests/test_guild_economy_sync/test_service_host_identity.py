"""Slice of ``test_guild_economy_sync``: ServiceHostIdentityTests, ServiceHostAnchorReuseTests, ServiceHostAnchorRoomTests.
"""
from tools.spec_traceability import covers_requirement
import dataclasses
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer
from typeclasses.components import GuildStaff
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.maps.bootstrap import sync_service_interiors
from world.rules import guild_config
from world.rules import guild_economy
from world.rules.guild_config import get_catalog
from world.rules.guild_config import load_catalog_into_cache
from world.rules.guild_economy import ServiceAnchorIntegrityError
from world.rules.guild_economy import sync_service_content
from ._support import (
    GUILD_HALL_TAG,
    GUILD_SERVICE_ID,
    MERCHANT_SERVICE_ID,
    ServiceContentIsolation,
    _guild_branch_key,
    _guild_host_name,
    _guild_row,
    _merchant_host_name,
    _merchant_shop_key,
    _place_by_kind,
    _places,
    _settlements,
    _shops,
    _subraces,
    before_row_profession,
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
        # guild host + six capital merchants + eight village hosts + the lane's
        # three attendants (altoria-hospitality) + the watch's two captains and
        # the yard's instructor (altoria-crown-and-watch) + the academy's dean
        # and the merchant hall's guild master (altoria-learning-and-exchange;
        # the host-less palace and the host-less market stalls contribute no
        # row, hence 25 and not 27)
        self.assertEqual(len(events), 25)
        # The guild host's event is located by service id, not position: the
        # terrace split (altoria-place-slices) made the lower terrace's eatery
        # the first roster row, so no shipped row keeps a fixed index.
        guild_events = [
            event for event in events
            if event.kwargs["context"]["service"] == GUILD_SERVICE_ID
        ]
        self.assertEqual(len(guild_events), 1)
        guild_event = guild_events[0]
        self.assertEqual(guild_event.kwargs["context"]["char"], _guild_host_name())
        self.assertEqual(guild_event.kwargs["context"]["shop"], _guild_branch_key())
        self.assertEqual(
            guild_event.kwargs["context"]["profession"], _guild_row().profession.key
        )
        # The merchant hosts follow the roster order (PLACE_REGISTRY terrace-
        # slice order); every merchant reports its authored shop identity.
        merchant_service_ids = [
            row.service_id
            for row in get_catalog().service_hosts
            if row.service_id != GUILD_SERVICE_ID
        ]
        merchant_events = [
            event for event in events
            if event.kwargs["context"]["service"] != GUILD_SERVICE_ID
        ]
        self.assertEqual(
            [event.kwargs["context"]["service"] for event in merchant_events],
            merchant_service_ids,
        )
        # Merchants report their authored shop; every attendant-profession
        # host — the village's two (ciaran-village-commons), the upper
        # terrace's 主祭 (altoria-sanctum) and the lane's three
        # (altoria-hospitality) — carries no shop identity at all. The
        # split is derived from the roster's profession key, not a literal
        # set: the temple's 主祭 was silently leaning on the merchant branch
        # (an attendant event passes no truthy-shop assertion).
        attendants = {
            row.service_id
            for row in get_catalog().service_hosts
            if row.profession.key == "attendant"
        }
        self.assertTrue(attendants)
        # ...and the merchant branch it contrasts against is non-empty too,
        # so neither predicate can pass by quantifying over nothing.
        self.assertTrue(set(merchant_service_ids) - attendants)
        self.assertTrue(
            all(
                event.kwargs["context"]["shop"]
                for event in merchant_events
                if event.kwargs["context"]["service"] not in attendants
            )
        )
        self.assertTrue(
            all(
                event.kwargs["context"]["shop"] is None
                for event in merchant_events
                if event.kwargs["context"]["service"] in attendants
            )
        )
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()  # reuse fires nothing
        late = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_created"
        ]
        self.assertEqual(len(late), 25)

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
            anchor_room=_guild_row().anchor_room,
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

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    @covers_requirement(
        "place-driven-service-sync::a-place-authors-its-host-s-race-subrace-and-sex"
    )
    def test_resync_never_rewrites_authored_identity(self):
        # Race/subrace/sex are creation-time authored identity: an edited
        # authored value must leave the live host untouched on re-sync, exact-
        # ly like an edited name or title (never-backfill contract). Taking
        # effect requires roster convergence, never a runtime rewrite.
        sync_service_content()
        guild_host = self._guild_host()
        identity_before = (guild_host.race, guild_host.subrace, guild_host.sex)
        host_pk = guild_host.pk
        place = _place_by_kind("guild_hall")
        # Any authored value DIFFERENT from the live one proves the
        # never-rewrite contract; pick domain values live-registry-derived
        # rather than naming shipped rows.
        edited_subrace = next(
            key for key in _subraces() if key != place.host_subrace
        )
        edited = dataclasses.replace(
            place,
            host_race="elf",
            host_subrace=edited_subrace,
            host_sex="female",
        )
        with patch.dict(_places(), {edited.key: edited}):
            sync_service_content()
        guild_host = self._guild_host()
        self.assertEqual(
            (guild_host.race, guild_host.subrace, guild_host.sex),
            identity_before,
        )
        self.assertEqual(guild_host.pk, host_pk)

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    @covers_requirement(
        "place-driven-service-sync::one-place-record-yields-a-complete-working-location"
    )
    @covers_requirement(
        "place-driven-service-sync::interiors-are-created-by-iterating-the-place-registry"
    )
    def test_one_added_place_row_yields_a_complete_working_location(self):
        # Adding a place row must produce the whole location with no module
        # constant for it: interior, both doorways, host and purchasable goods
        # (place-driven-service-sync task 4.2). The synthetic row rides the
        # production seams end to end — PLACE_REGISTRY drives interior creation
        # and host identity, the derived shop registry and catalog resolution
        # feed merchant stock — and only registry rows were added.
        from world.lore.settlements.shops import ShopDefinition

        # merchant-dialogue: the merchant blueprint's scripted_dialogue
        # component demands a dialogue table from every merchant place, so
        # the stand-in row authors one beside its shop_key. The key is the
        # live general store's own (registry-derived at runtime, never a
        # shipped literal): two places may share a table — the anchor is the
        # row's service_id, not the dialogue key.
        store_kwargs = dict(_place_by_kind("general_store").authored_kwargs)
        new_place = dataclasses.replace(
            _place_by_kind("general_store"),
            key="t_trading_post",
            service_id="t_altoria_trading_post",
            room_name_zh="測試交易站",
            room_desc_zh="A synthetic trading post with no module constant.",
            exterior_xy=(4, 1),
            doorway_key_zh="測試交易站往來通道",
            doorway_aliases=("test trading post",),
            host_name="測試商人",
            host_title="測試交易站店主",
            host_race="human",
            host_subrace=None,
            host_sex="other",
            authored_kwargs=(
                ("shop_key", "t_trading_post"),
                ("dialogue_key", store_kwargs["dialogue_key"]),
            ),
        )
        # The stand-in shop sells exactly what the live merchant's shop sells:
        # the stock-identity assertion below then holds for any authored
        # assortment, with no shipped assortment key named.
        general_store_shop = _shops()[_merchant_shop_key()]
        new_shop = ShopDefinition(
            key="t_trading_post",
            host_name="測試商人",
            host_title="測試交易站店主",
            assortment_keys=general_store_shop.assortment_keys,
        )
        commerce = guild_config.load_commerce_config()
        patched_commerce = {
            **commerce,
            "shops": [
                *commerce["shops"],
                {
                    "shop_key": "t_trading_post",
                    "open_hour": 8,
                    "close_hour": 20,
                    "restock_hour": 6,
                },
            ],
        }
        with (
            patch.dict(_places(), {"t_trading_post": new_place}),
            patch.dict(_shops(), {"t_trading_post": new_shop}),
            patch.object(
                guild_config, "load_commerce_config", return_value=patched_commerce
            ),
        ):
            load_catalog_into_cache()
            sync_service_interiors()
            sync_service_content()

        interior = search_object_by_tag("t_trading_post")[0]
        self.assertIsNotNone(interior)
        zcoord = _settlements()[_place_by_kind("guild_hall").settlement_key].zcoord
        exterior = GridRoom.objects.filter_xyz(
            xyz=(*new_place.exterior_xy, zcoord)
        ).first()
        self.assertIsNotNone(exterior)
        self.assertIn(interior, {exit_obj.destination for exit_obj in exterior.exits})
        self.assertIn(
            exterior, {exit_obj.destination for exit_obj in interior.exits}
        )
        host = NPC.objects.filter(db_key="測試商人").first()
        self.assertIsNotNone(host)
        merchant = host.components.get(Merchant.get_component_slot())
        self.assertIsNotNone(merchant)
        self.assertEqual(merchant.service_id, "t_altoria_trading_post")
        offers = get_catalog().shop_configs["t_trading_post"].offers
        self.assertEqual(
            {offer.item_key for offer in offers},
            set(merchant.merchant_stock),
        )

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

    @covers_requirement(
        "place-driven-service-sync::one-place-record-yields-a-complete-working-location"
    )
    def test_a_host_less_place_row_yields_a_room_and_no_npc(self):
        # hostless-places task 3.3: a place authoring no host still yields its
        # whole location — tagged, described interior with both doorways — and
        # NO NPC, while the freshly reloaded roster carries no row for it. The
        # row rides the production seams exactly like the complete-location
        # probe above: it clones a live, resolvable capital row so its exterior
        # exists on a spawned grid map, and the catalog is reloaded INSIDE the
        # patch scope so the roster derivation itself is exercised.
        from typeclasses.rooms import Room

        hostless = dataclasses.replace(
            _place_by_kind("general_store"),
            key="t_forecourt",
            room_name_zh="測試宮前庭",
            room_desc_zh="A host-less landmark: a room that simply exists.",
            exterior_xy=(4, 1),
            doorway_key_zh="測試宮前庭入口",
            doorway_aliases=("test forecourt",),
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
        with patch.dict(_places(), {"t_forecourt": hostless}):
            load_catalog_into_cache()
            # The roster derivation skipped the row: no anchor, no service id.
            self.assertNotIn("t_forecourt", {row.anchor_room for row in get_catalog().service_hosts})
            sync_service_interiors()
            sync_service_content()

            interior = search_object_by_tag("t_forecourt")[0]
            self.assertIsInstance(interior, Room)
            self.assertEqual(interior.key, hostless.room_name_zh)
            self.assertEqual(interior.db.desc, hostless.room_desc_zh)
            zcoord = _settlements()[hostless.settlement_key].zcoord
            exterior = GridRoom.objects.filter_xyz(
                xyz=(*hostless.exterior_xy, zcoord)
            ).first()
            self.assertIsNotNone(exterior)
            self.assertIn(
                interior, {exit_obj.destination for exit_obj in exterior.exits}
            )
            self.assertIn(
                exterior, {exit_obj.destination for exit_obj in interior.exits}
            )
            self.assertEqual(NPC.objects.all_family().filter(db_location=interior).count(), 0)

            # A second run creates nothing new: same single tagged room, same
            # exits, no NPC appears on either run.
            room_count = Room.objects.all_family().count()
            npc_count = NPC.objects.all_family().count()
            interior_pks = [room.pk for room in search_object_by_tag("t_forecourt")]
            sync_service_interiors()
            sync_service_content()
            self.assertEqual(Room.objects.all_family().count(), room_count)
            self.assertEqual(NPC.objects.all_family().count(), npc_count)
            self.assertEqual(
                [room.pk for room in search_object_by_tag("t_forecourt")], interior_pks
            )
            self.assertEqual(NPC.objects.all_family().filter(db_location=interior).count(), 0)

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


if __name__ == "__main__":
    unittest.main()
