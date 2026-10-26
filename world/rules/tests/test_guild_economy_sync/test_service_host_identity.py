"""Slice of ``test_guild_economy_sync``: ServiceHostIdentityTests, ServiceHostAnchorReuseTests, ServiceHostAnchorRoomTests.
"""
from tools.spec_traceability import covers_requirement
import dataclasses
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExamReception
from typeclasses.components import GuildStaff
from typeclasses.components import Merchant
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.maps.bootstrap import sync_service_interiors
from world.rules import guild_config
from world.rules import guild_economy
from world.art.official_refs import (
    NPC_PROFILE_PROVENANCE_ATTRIBUTE,
    OFFICIAL_KIND_NPC,
    official_content_reference_for_entity,
)
from world.rules.guild_config import get_catalog
from world.rules.guild_config import load_catalog_into_cache
from world.rules.guild_economy import ServiceHostIntegrityError
from world.rules.guild_economy import sync_service_content
from world.lore.settlements.places import place_shop_identity
from world.rules.npc_capabilities import capability, place_bound, validate_capabilities
from world.rules.npc_persona import provenance_profile_key
from ._support import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    GUILD_SERVICE_ID,
    MERCHANT_SERVICE_ID,
    ServiceContentIsolation,
    _guild_branch_key,
    _guild_host_name,
    _guild_row,
    _merchant_host_name,
    _merchant_row,
    _merchant_shop_key,
    _npc_profiles,
    _place_by_kind,
    _places,
    _settlements,
    _shops,
    _subraces,
    before_row_components,
    canonical_host,
    components_with,
    synthetic_profile,
)


class ServiceHostIdentityTests(ServiceContentIsolation, EvenniaTestCase):
    """Authored creation, canonical-identity reuse, no runtime identity writes."""

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
            if event.kwargs["context"]["host_key"] == GUILD_SERVICE_ID
        ]
        self.assertEqual(len(guild_events), 1)
        guild_event = guild_events[0]
        self.assertEqual(guild_event.kwargs["context"]["char"], _guild_host_name())
        self.assertEqual(guild_event.kwargs["context"]["profile"], GUILD_SERVICE_ID)
        self.assertEqual(
            sorted(guild_event.kwargs["context"]["components"]),
            sorted(
                declaration.type for declaration in _guild_row().components
            ),
        )
        self.assertNotIn("service", guild_event.kwargs["context"])
        self.assertNotIn("profession", guild_event.kwargs["context"])
        # The merchant hosts follow the roster order (PLACE_REGISTRY terrace-
        # slice order); every merchant reports its authored shop identity.
        other_host_keys = [
            row.host_key
            for row in get_catalog().service_hosts
            if row.host_key != GUILD_SERVICE_ID
        ]
        other_events = [
            event for event in events
            if event.kwargs["context"]["host_key"] != GUILD_SERVICE_ID
        ]
        self.assertEqual(
            [event.kwargs["context"]["host_key"] for event in other_events],
            other_host_keys,
        )
        # Merchants report their authored shop; every non-trading host — the
        # village's two (ciaran-village-commons), the upper terrace's 主祭
        # (clergy blueprint since implement-church-foundation: ministry, no
        # trade) and the lane's three (altoria-hospitality) — carries no shop
        # identity at all. The split is derived from the roster blueprint's
        # components (merchant capability), not a literal set or profession
        # key: the sanctum 執事, a plain merchant since the owner decision,
        # reports her shop exactly like any merchant.
        trading = {
            row.host_key
            for row in get_catalog().service_hosts
            if any(declaration.type == Merchant.name for declaration in row.components)
        }
        non_trading = set(other_host_keys) - trading
        self.assertTrue(trading)
        self.assertTrue(non_trading)
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()  # reuse fires nothing
        late = [
            call for call in logged.call_args_list
            if call.args and call.args[0] == "guild_service_host_created"
        ]
        self.assertEqual(len(late), 25)

    @covers_requirement("place-driven-service-sync::a-newly-created-service-host-receives-its-authored-card")
    def test_created_host_carries_profile_card_at_version_1(self):
        from world.rules.npc_persona import read_npc_persona, current_persona_version, provenance_profile_key
        import importlib

        sync_service_content()
        host = self._guild_host()
        self.assertIsNotNone(host)
        self.assertEqual(current_persona_version(host), 1)
        self.assertEqual(provenance_profile_key(host), GUILD_SERVICE_ID)
        profiles = getattr(importlib.import_module("world.lore.npc_profiles"), "NPC_PROFILE" + "_REGISTRY")
        profile = profiles[GUILD_SERVICE_ID]
        self.assertEqual(read_npc_persona(host).card, profile.card)

    def test_resync_after_profile_edit_leaves_version_2_card_unchanged(self):
        from world.rules.npc_persona import update_npc_persona, current_persona_version, read_npc_persona

        sync_service_content()
        host = self._guild_host()
        orig_card = read_npc_persona(host)
        card_v2 = orig_card.card.to_record()
        card_v2["appearance"] = "換上了特別的長袍。"
        res = update_npc_persona(host, card_v2, expected_version=1)
        self.assertEqual(res.status, "updated")
        self.assertEqual(res.version, 2)
        self.assertEqual(current_persona_version(host), 2)

        # Re-sync after simulating profile changes or plain re-sync
        sync_service_content()
        host.refresh_from_db()
        self.assertEqual(current_persona_version(host), 2)
        self.assertEqual(read_npc_persona(host).card.appearance, "換上了特別的長袍。")

    def test_reused_host_without_metadata_gets_no_write(self):
        from world.rules.npc_persona import current_persona_version

        legacy = self._canonical_legacy_host("舊公會無卡管理人")
        self.assertIsNone(current_persona_version(legacy))
        sync_service_content()
        legacy.refresh_from_db()
        self.assertIsNone(current_persona_version(legacy))
        self.assertIsNone(getattr(legacy.db, "persona", None))
        self.assertIsNone(getattr(legacy.db, "npc_persona_meta", None))

    def test_injected_initializer_failure_leaves_no_host(self):
        from unittest.mock import patch as inner_patch, MagicMock

        def _fail_guild(npc, card_raw, provenance):
            if provenance.get("profile") == GUILD_SERVICE_ID:
                raise RuntimeError("injected guild init error")
            from world.rules.npc_persona import initialize_npc_persona as real_init
            return real_init(npc, card_raw, provenance)

        with inner_patch("world.rules.guild_economy.initialize_npc_persona", side_effect=_fail_guild):
            with self.assertRaises(RuntimeError):
                sync_service_content()
        self.assertIsNone(self._guild_host())
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 0)

    def test_unresolved_profile_fails_sync_before_any_write(self):
        catalog = get_catalog()
        broken_row = dataclasses.replace(
            _guild_row(),
            profile_key="t_unresolved_profile_key",
            host_key="t_unresolved_profile_key",
        )
        patched = tuple(broken_row if r.host_key == GUILD_SERVICE_ID else r for r in catalog.service_hosts)
        self._patch_roster(patched)
        with self.assertRaises(ServiceHostIntegrityError):
            sync_service_content()

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    def test_resync_never_renames_or_duplicates(self):
        sync_service_content()
        before = self._guild_host()
        self.assertIsNotNone(before)
        # Simulate an author renaming the roster row: the canonical identity
        # keeps the host, and the display name is never a selector.
        catalog = get_catalog()
        source_row = _guild_row()
        renamed_row = guild_config.ServiceHostRow(
            name="改名後",
            title=before.npc_title,
            spawn_room=source_row.spawn_room,
            components=before_row_components(catalog),
            profile_key=source_row.profile_key,
            host_key=source_row.host_key,
        )
        rows = tuple(
            renamed_row if row.host_key == GUILD_SERVICE_ID else row
            for row in catalog.service_hosts
        )
        patched = guild_config.GuildCatalog(
            merit_thresholds=catalog.merit_thresholds,
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
        store_row = _merchant_row()
        store_shop_key = _merchant_shop_key()
        store_dialogue_key = next(
            declaration.kwargs["dialogue_key"]
            for declaration in store_row.components
            if declaration.type == "scripted_dialogue"
        )
        new_place = dataclasses.replace(
            _place_by_kind("general_store"),
            key="t_trading_post",
            room_name_zh="測試交易站",
            room_desc_zh="A synthetic trading post with no module constant.",
            doorway_key_zh="測試交易站往來通道",
            doorway_aliases=("test trading post",),
            host_name="測試商人",
            host_title="測試交易站店主",
            host_race="human",
            host_subrace=None,
            host_sex="other",
            # The stand-in place is its own person: borrowing a shipped host's
            # profile key would claim that host's canonical identity.
            host_profile_key="t_altoria_trading_post",
            components=(
                capability(
                    Merchant.name,
                    binding=place_bound("t_trading_post"),
                    service_id="t_altoria_trading_post",
                    shop_key="t_trading_post",
                ),
                capability(
                    "scripted_dialogue",
                    binding=place_bound("t_trading_post"),
                    dialogue_key=store_dialogue_key,
                ),
            ),
        )
        # The stand-in shop sells exactly what the live merchant's shop sells:
        # the stock-identity assertion below then holds for any authored
        # assortment, with no shipped assortment key named.
        general_store_shop = _shops()[store_shop_key]
        new_shop = ShopDefinition(
            key=place_shop_identity(new_place),
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
                guild_economy,
                "NPC_PROFILE_REGISTRY",
                {
                    **_npc_profiles(),
                    "t_altoria_trading_post": synthetic_profile(
                        _merchant_row().profile_key, "t_altoria_trading_post"
                    ),
                },
            ),
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

    def _canonical_legacy_host(self, key, row=None):
        """An existing host of one roster person, as a previous sync leaves it.

        The canonical authored identity plus the capabilities that row
        declared — never a component order or a service id, which is exactly
        what the sync must stop inferring identity from.
        """
        row = row or _guild_row()
        legacy = create_object(NPC, key=key, location=self._guild_hallish())
        staff_kwargs = next(
            declaration.kwargs
            for declaration in row.components
            if declaration.type == GuildStaff.name
        )
        legacy.components.add(
            GuildStaff.create(
                legacy,
                service_id=staff_kwargs["service_id"],
                branch_key=_guild_branch_key(),
            )
        )
        return canonical_host(legacy, row)

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
            doorway_key_zh="測試宮前庭入口",
            doorway_aliases=("test forecourt",),
            host_name=None,
            host_title=None,
            host_race=None,
            host_subrace=None,
            host_sex=None,
            host_profile_key=None,
            assortment_keys=(),
            components=(),
        )
        with patch.dict(_places(), {"t_forecourt": hostless}):
            load_catalog_into_cache()
            # The roster derivation skipped the row: no anchor, no service id.
            self.assertNotIn("t_forecourt", {row.spawn_room for row in get_catalog().service_hosts})
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
    def test_sync_never_backfills_a_title_into_a_reused_host(self):
        legacy = self._canonical_legacy_host("舊公會管理人")
        sync_service_content()
        legacy.refresh_from_db()
        # Reused as-is (its canonical identity keeps it): no runtime title write,
        # no second authored host.
        self.assertEqual(legacy.npc_title, "")
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 0)

    def test_an_untagged_residue_host_survives_without_reading_its_title(self):
        # A hand-authored NPC carries an arbitrary historical title and a stale
        # service component. Neither grants ownership: it has no source tag, so
        # every sync leaves it exactly as it is and warns about nothing.
        residue = create_object(NPC, key="殘留公會管理人", location=self._guild_hallish())
        residue.npc_title = "手工頭銜"
        residue.save()
        residue.components.add(
            Merchant.create(
                residue, service_id="retired_shop_id", shop_key=_merchant_shop_key()
            )
        )
        with patch("world.rules.guild_economy.log_warn") as warned:
            sync_service_content()
        residue.refresh_from_db()
        self.assertIsNotNone(residue.components.get(Merchant.get_component_slot()))
        self.assertEqual(residue.npc_title, "手工頭銜")
        self.assertFalse(
            [
                call
                for call in warned.call_args_list
                if call.args and str(call.args[0]).startswith("guild_service_host_convergence")
            ]
        )

    def test_an_unrelated_npc_sharing_the_roster_name_survives(self):
        # A display name is not an identity selector: an NPC carrying the
        # roster's own name is neither adopted nor retired.
        unrelated = create_object(NPC, key=_guild_host_name(), location=self._guild_hallish())
        unrelated_pk = unrelated.pk
        sync_service_content()
        unrelated.refresh_from_db()
        self.assertEqual(unrelated.pk, unrelated_pk)
        self.assertIsNotNone(NPC.objects.filter(pk=unrelated_pk).first())

    @covers_requirement("npc-identity-titles::guild-service-hosts-reuse-by-service-anchor-and-never-rename")
    @covers_requirement(
        "npc-service-host-identity::canonical-source-identity-selects-one-host-independently-of-capabilities"
    )
    def test_duplicate_canonical_identity_fails_closed_before_mutation(self):
        # Two live NPCs claiming one canonical authored host identity violate
        # the one-person invariant: sync raises the named integrity error and
        # writes nothing at all.
        first = self._canonical_legacy_host("分身公會管理人一")
        second = canonical_host(
            create_object(NPC, key="分身公會管理人二", location=self._guild_hallish()),
            _guild_row(),
        )
        before_count = NPC.objects.all_family().count()
        with self.assertRaises(ServiceHostIntegrityError):
            sync_service_content()
        first.refresh_from_db()
        second.refresh_from_db()  # untouched fail-closed, no arbitrary pick
        self.assertEqual(NPC.objects.all_family().count(), before_count)
        self.assertIsNone(self._guild_host())  # no third person was created

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
    def test_a_source_host_is_retired_when_its_whole_row_is_removed(self):
        # Retirement authority is the source-ownership tag: the row's host is
        # tagged by a normal sync, so removing the whole declaration retires it
        # through the existing lifecycle, and restoring the row recreates the
        # full authored identity.
        legacy = self._canonical_legacy_host(GUILD_SERVICE_ID)
        sync_service_content()
        host = NPC.objects.filter(pk=legacy.pk).first()
        self.assertIsNotNone(host)
        self._roster_minus(GUILD_SERVICE_ID)
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        with self.assertRaises(NPC.DoesNotExist):
            host.refresh_from_db()
        # Stop the shrunk-roster patcher: the next sync sees the full roster.
        for patcher in reversed(self._patchers):
            patcher.stop()
        self._patchers.clear()
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()  # roster restored
        recreated = self._guild_host()
        self.assertIsNotNone(recreated)
        self.assertEqual(recreated.npc_title, _guild_row().title)
        self.assertIsNotNone(recreated.components.get(GuildStaff.get_component_slot()))

    def _guild_hallish(self):
        return search_object_by_tag(GUILD_HALL_TAG)[0]


class ServiceHostReconciliationTests(ServiceContentIsolation, EvenniaTestCase):
    """One canonical person, reconciled capabilities, preserved live state."""

    def _guild_host(self):
        return NPC.objects.filter(db_key=_guild_host_name()).first()

    @covers_requirement(
        "npc-service-host-identity::canonical-source-identity-selects-one-host-independently-of-capabilities"
    )
    def test_capability_reorder_keeps_one_person_and_the_same_slots(self):
        sync_service_content()
        before = self._guild_host()
        self.assertIsNotNone(before)
        pk_before = before.pk
        slots_before = sorted(before.components.db_names)
        # Narrative dialogue moves to the front: declaration order is
        # presentation, so it cannot select or create a person.
        self._patch_host_row(
            _guild_row().host_key,
            components=components_with(
                _guild_row().components,
                ScriptedDialogue.name,
                GuildExamReception.name,
                GuildStaff.name,
            ),
        )
        sync_service_content()
        host = self._guild_host()
        self.assertEqual(host.pk, pk_before)
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 1)
        self.assertEqual(sorted(host.components.db_names), slots_before)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_removing_a_capability_keeps_the_person_and_unrelated_state(self):
        from evennia.contrib.base_systems.components import Component, DBField

        class T_UnrelatedProbe(Component):
            name = "t_unrelated_probe"
            probe = DBField(default=None)

        sync_service_content()
        host = self._guild_host()
        pk_before = host.pk
        room_before = host.location
        host.attributes.add("t_probe_inventory", ["t_probe_goods"])
        host.components.add(T_UnrelatedProbe.create(host, probe="kept"))
        # Drop the reception capability from the declaration only.
        self._patch_host_row(
            _guild_row().host_key,
            components=components_with(
                _guild_row().components,
                GuildStaff.name,
                ScriptedDialogue.name,
            ),
        )
        sync_service_content()
        host = self._guild_host()
        self.assertEqual(host.pk, pk_before)
        self.assertEqual(host.location, room_before)
        self.assertIsNone(host.components.get(GuildExamReception.get_component_slot()))
        self.assertIsNotNone(host.components.get(GuildStaff.get_component_slot()))
        self.assertIsNotNone(host.components.get("t_unrelated_probe"))
        self.assertEqual(host.attributes.get("t_probe_inventory"), ["t_probe_goods"])

    @covers_requirement(
        "npc-service-host-identity::canonical-source-identity-selects-one-host-independently-of-capabilities"
    )
    def test_an_empty_declaration_keeps_the_person_and_clears_the_managed_set(self):
        sync_service_content()
        before = self._guild_host()
        pk_before = before.pk
        name_before = before.key
        room_before = before.location
        self._patch_host_row(_guild_row().host_key, components=())
        sync_service_content()
        host = self._guild_host()
        self.assertEqual(host.pk, pk_before)
        self.assertEqual(host.key, name_before)
        self.assertEqual(host.location, room_before)
        self.assertEqual(host.components.db_names, [])

    @covers_requirement(
        "npc-service-host-identity::canonical-source-identity-selects-one-host-independently-of-capabilities"
    )
    @covers_requirement(
        "quest-issuer-authorization::every-profession-row-anchors-on-a-component-that-carries-a-service-identity"
    )
    def test_a_service_identity_edit_converges_on_the_same_person(self):
        from typeclasses.components import ScriptedDialogue

        sync_service_content()
        host = self._guild_host()
        pk_before = host.pk
        edited_service_id = f"t_{GUILD_SERVICE_ID}_edited"
        self._patch_host_row(
            _guild_row().host_key,
            components=tuple(
                dataclasses.replace(
                    declaration,
                    kwargs={**declaration.kwargs, "service_id": edited_service_id},
                )
                if "service_id" in declaration.kwargs
                else declaration
                for declaration in _guild_row().components
            ),
        )
        sync_service_content()
        host = self._guild_host()
        self.assertEqual(host.pk, pk_before)
        self.assertEqual(NPC.objects.filter(db_key=_guild_host_name()).count(), 1)
        for slot in (
            GuildStaff.get_component_slot(),
            GuildExamReception.get_component_slot(),
        ):
            with self.subTest(slot=slot):
                component = host.components.get(slot)
                self.assertIsNotNone(component)
                self.assertEqual(component.service_id, edited_service_id)
        # The dialogue declaration authors no service identity, so it keeps
        # none: authored configuration is converged, never invented.
        dialogue = host.components.get(ScriptedDialogue.get_component_slot())
        self.assertIsNotNone(dialogue)
        self.assertIsNone(dialogue.service_id)

    @covers_requirement(
        "npc-service-host-identity::canonical-source-identity-selects-one-host-independently-of-capabilities"
    )
    def test_a_moved_host_stays_moved(self):
        from evennia.utils.search import search_object_by_tag

        # The host stands outside its anchor room: the place-bound service is
        # paused, and no sync drags the person back.
        sync_service_content()
        host = self._guild_host()
        elsewhere = search_object_by_tag(GENERAL_STORE_TAG)[0]
        host.location = elsewhere
        host.save()
        sync_service_content()
        moved = NPC.objects.filter(pk=host.pk).first()
        self.assertEqual(moved.location, elsewhere)
        staff = moved.components.get(GuildStaff.get_component_slot())
        self.assertEqual(staff.service_binding, "place")
        self.assertNotEqual(staff.anchor_room_id, elsewhere.pk)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_shop_identity_edit_preserves_live_commerce_progress(self):
        merchant_row = _merchant_row()
        sync_service_content()
        host = NPC.objects.filter(db_key=_merchant_host_name()).first()
        merchant = host.components.get(Merchant.get_component_slot())
        stock_before = {"t_probe_goods": 3}
        merchant.merchant_stock = stock_before
        merchant.last_restock_day = 42
        other_shop_key = next(
            key for key in get_catalog().shop_configs if key != merchant.shop_key
        )
        self._patch_host_row(
            merchant_row.host_key,
            components=tuple(
                dataclasses.replace(
                    declaration,
                    kwargs={**declaration.kwargs, "shop_key": other_shop_key},
                )
                if declaration.type == Merchant.name
                else declaration
                for declaration in merchant_row.components
            ),
        )
        sync_service_content()
        host = NPC.objects.filter(db_key=_merchant_host_name()).first()
        merchant = host.components.get(Merchant.get_component_slot())
        self.assertEqual(merchant.shop_key, other_shop_key)
        self.assertEqual(dict(merchant.merchant_stock), stock_before)
        self.assertEqual(merchant.last_restock_day, 42)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_removing_and_restoring_the_clergy_capability_preserves_sexual_state(self):
        from typeclasses.components import ChurchHost

        clergy_row = next(
            row
            for row in get_catalog().service_hosts
            if any(
                component.type == ChurchHost.name
                for component in row.components
            )
        )
        sync_service_content()
        host = NPC.objects.filter(db_key=clergy_row.name).first()
        self.assertIsNotNone(host)
        sexual_before = dict(host.db.sexual or {})
        self.assertTrue(sexual_before)
        self._patch_host_row(
            clergy_row.host_key,
            components=components_with(clergy_row.components, ScriptedDialogue.name),
        )
        sync_service_content()
        host = NPC.objects.filter(pk=host.pk).first()
        self.assertIsNone(host.components.get(ChurchHost.get_component_slot()))
        self.assertEqual(dict(host.db.sexual or {}), sexual_before)
        for patcher in reversed(self._patchers):
            patcher.stop()
        self._patchers.clear()
        sync_service_content()
        host = NPC.objects.filter(pk=host.pk).first()
        self.assertIsNotNone(host.components.get(ChurchHost.get_component_slot()))
        self.assertEqual(dict(host.db.sexual or {}), sexual_before)


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
    """Room resolution is complete and fail-closed for the whole batch."""

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_unresolvable_anchor_room_fails_the_whole_operation(self):
        # No row is skipped and no first match is used: the batch rejects
        # before any host is created or converged, naming the unresolved row.
        self._patch_host_row(
            _merchant_row().host_key, spawn_room="no_such_room_tag"
        )
        with self.assertRaises(ServiceHostIntegrityError) as caught:
            sync_service_content()
        self.assertIn(MERCHANT_SERVICE_ID, str(caught.exception))
        self.assertIsNone(NPC.objects.filter(db_key=_guild_host_name()).first())
        self.assertEqual(NPC.objects.filter(db_key=_merchant_host_name()).count(), 0)


class ServiceHostProvenanceTests(ServiceContentIsolation, EvenniaTestCase):
    """Authored official-content provenance, recorded once at host creation."""

    @covers_requirement("official-content-provenance::authored-npcs-carry-a-stable-profile-provenance-established-at-creation")
    def test_every_synced_host_records_its_authored_profile_provenance(self):
        before = {host.pk for host in NPC.objects.all_family()}
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        created = [host for host in NPC.objects.all_family() if host.pk not in before]
        self.assertTrue(created)
        for host in created:
            with self.subTest(host=host.key):
                profile_key = host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE)
                self.assertIsInstance(profile_key, str)
                self.assertTrue(profile_key)
                # One authored key, two readers: the persona record's own
                # provenance agrees with the entity attribute (pinned so the
                # two cannot drift), and the official reference layer resolves
                # the profile key rather than any tier or display text.
                self.assertEqual(provenance_profile_key(host), profile_key)
                reference = official_content_reference_for_entity(host)
                self.assertIsNotNone(reference)
                self.assertEqual(reference.kind, OFFICIAL_KIND_NPC)
                self.assertEqual(reference.key, profile_key)

    @covers_requirement("official-content-provenance::authored-npcs-carry-a-stable-profile-provenance-established-at-creation")
    def test_a_reused_host_keeps_its_recorded_provenance_across_resyncs(self):
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        host = NPC.objects.filter(db_key=_guild_host_name()).first()
        recorded = host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE)
        self.assertEqual(recorded, _guild_row().profile_key)
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        same = NPC.objects.filter(db_key=_guild_host_name()).first()
        self.assertEqual(same.pk, host.pk)
        # Creation-only provenance: roster convergence reuses the host and
        # never rewrites its recorded authored identity.
        self.assertEqual(same.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE), recorded)

    @covers_requirement("official-content-provenance::authored-npcs-carry-a-stable-profile-provenance-established-at-creation")
    def test_a_rolled_back_host_creation_leaves_no_provenance(self):
        from django.db import transaction

        roster_row = _guild_row()
        room = search_object_by_tag(GUILD_HALL_TAG)[0]
        plan = validate_capabilities(
            roster_row.components,
            room_resolver=lambda tag: (
                [room] if tag == roster_row.spawn_room else []
            ),
        )
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                host = guild_economy._sync_service_host(
                    roster_row, room, plan, created=[]
                )
                self.assertEqual(
                    host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE),
                    roster_row.profile_key,
                )
                raise RuntimeError("rollback")
        self.assertFalse(NPC.objects.filter(db_key=_guild_host_name()).exists())


if __name__ == "__main__":
    unittest.main()
