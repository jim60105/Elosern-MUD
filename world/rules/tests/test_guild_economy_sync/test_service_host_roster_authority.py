"""Slice of ``test_guild_economy_sync``: ServiceHostRosterAuthorityTests, ServiceHostBindingConvergenceTests.
"""
from tools.spec_traceability import covers_requirement
import dataclasses
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.components import GuildStaff
from typeclasses.components import Merchant
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import ServiceHostIntegrityError
from world.rules.guild_economy import sync_service_content
from ._support import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    GUILD_SERVICE_ID,
    MERCHANT_SERVICE_ID,
    ServiceContentIsolation,
    _guild_branch_key,
    _guild_host_name,
    _guild_row,
    _merchant_row,
    _merchant_host_name,
    _merchant_shop_key,
    canonical_host,
)


class ServiceHostRosterAuthorityTests(ServiceContentIsolation, EvenniaTestCase):
    """Source ownership alone authorizes retirement; rooms never gate it."""

    def test_a_zero_capability_row_still_requires_exactly_one_room_per_tag(self):
        # The exact-one-Room rule belongs to the spawn room itself, not to a
        # capability anchor: a host that declares no capability must still fail
        # closed on an ambiguous or non-Room spawn tag.
        bare_row = dataclasses.replace(
            next(
                row
                for row in get_catalog().service_hosts
                if row.host_key == MERCHANT_SERVICE_ID
            ),
            components=(),
        )
        ambiguous_tag = "t_ambiguous_spawn_tag"
        create_object(NPC, key="ambiguous first", tags=[ambiguous_tag])
        create_object(NPC, key="ambiguous second", tags=[ambiguous_tag])
        for tag, fragment in (
            (ambiguous_tag, "resolves to"),
            ("t_absent_spawn_tag", "resolves to no room"),
        ):
            with self.subTest(tag=tag):
                row = dataclasses.replace(bare_row, spawn_room=tag)
                self._patch_roster((row,))
                with self.assertRaises(ServiceHostIntegrityError) as caught:
                    sync_service_content()
                self.assertIn(fragment, str(caught.exception))

    def test_interior_preparation_rolls_back_with_the_failed_batch(self):
        # A later failure must take the prepared interiors with it: the repair
        # pass runs inside the same transaction as the plan resolution and the
        # writes, so the recreated room is gone after the rollback.
        from evennia.objects.models import ObjectDB
        from world.rules import guild_economy

        interior_tag = _merchant_row().spawn_room
        for obj in list(search_object_by_tag(interior_tag)):
            obj.delete()
        self.assertEqual(list(search_object_by_tag(interior_tag)), [])
        with patch.object(
            guild_economy, "_initialize_merchant_stock", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()
        self.assertEqual(
            list(search_object_by_tag(interior_tag)),
            [],
            "the rolled-back interior must not persist",
        )
        self.assertFalse(
            ObjectDB.objects.filter(db_key=_merchant_host_name()).exists(),
            "no host row survives the rolled-back batch",
        )

    def _rows_with_tags(self, tag):
        catalog = get_catalog()
        return tuple(
            dataclasses.replace(row, spawn_room=tag) for row in catalog.service_hosts
        )

    def _untagged_stale_host(self):
        """A leftover host of no declared person, carrying no source ownership."""
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
        # An empty roster declares nothing: there is no spawn room or anchor
        # left to resolve, so the batch is legitimate and the source-owned
        # hosts whose whole declaration is gone are retired.
        sync_service_content()
        for host in (guild, merchant):
            with self.assertRaises(NPC.DoesNotExist):
                host.refresh_from_db()

    @covers_requirement(
        "guild-registration::roster-convergence-deletes-service-hosts-absent-from-the-roster"
    )
    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_all_rows_unresolvable_never_retire_roster_hosts(self):
        sync_service_content()
        guild = NPC.objects.filter(db_key=_guild_host_name()).first()
        merchant = NPC.objects.filter(db_key=_merchant_host_name()).first()
        stale = self._untagged_stale_host()
        expected = NPC.objects.all_family().count()  # nothing dies
        self._patch_roster(self._rows_with_tags("no_such_room_tag"))
        # Room resolution is complete and fail-closed: an unresolvable anchor
        # rejects the whole operation, so no host is skipped, moved or retired
        # and the prepared interiors roll back with the batch.
        with self.assertRaises(ServiceHostIntegrityError):
            sync_service_content()
        # The untagged leftover survives: no declaration was ever removed.
        stale.refresh_from_db()
        # ...and roster-listed hosts stay byte-identical and unmoved.
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
    def test_duplicate_identity_on_unresolvable_row_fails_closed_before_any_mutation(self):
        # A duplicate canonical claim on a row whose room cannot resolve still
        # fails closed: NOTHING is created, moved, repointed, or deleted.
        merchant_row = _merchant_row()
        first = canonical_host(
            create_object(NPC, key="分身商人一", location=self._hall()), merchant_row
        )
        second = canonical_host(
            create_object(NPC, key="分身商人二", location=self._hall()), merchant_row
        )
        stale = self._untagged_stale_host()
        catalog = get_catalog()
        self._patch_roster(
            tuple(
                dataclasses.replace(row, spawn_room="no_such_room_tag")
                if row.host_key == MERCHANT_SERVICE_ID
                else row
                for row in catalog.service_hosts
            )
        )
        with self.assertRaises(ServiceHostIntegrityError):
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
        # A host of the declared person whose components predate the anchoring
        # change carries no binding fields; the next sync writes them without
        # touching identity or moving the host.
        hall = search_object_by_tag(GUILD_HALL_TAG)[0]
        host = create_object(NPC, key=_guild_host_name(), location=hall)
        host.components.add(
            GuildStaff.create(
                host,
                service_id=GUILD_SERVICE_ID,
                branch_key=_guild_branch_key(),
            )
        )
        canonical_host(host, _guild_row())
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


if __name__ == "__main__":
    unittest.main()
