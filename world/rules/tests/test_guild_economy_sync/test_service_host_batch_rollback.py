"""Slice of ``test_guild_economy_sync``: atomic batch rollback.

The whole source batch — component convergence, authored configuration,
initial stock and whole-row retirement — is one transaction. A failure on any
later row must leave the database *and* the in-process attribute, tag and
component caches exactly as they were, and must not leave a half-built object
in the idmapper for the next sync to inherit.
"""

import dataclasses
from copy import deepcopy
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import (
    ChurchHost,
    GuildExamReception,
    GuildStaff,
    Merchant,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from world.art.official_refs import NPC_PROFILE_PROVENANCE_ATTRIBUTE
from world.rules import guild_economy
from world.rules.guild_config import get_catalog
from world.rules.guild_economy import HOST_ATTRIBUTE_SURFACES, sync_service_content
from world.rules.npc_capabilities import COMPONENT_TYPES

from ._support import ServiceContentIsolation


def _cold_identity_map() -> None:
    """Force-flush the identity maps this slice reloads through.

    ``flush_cache()`` keeps "safe" instances, so the durable-state half of the
    assertion could pass on retained object-handler state instead of on what
    the database actually holds.
    """
    for model in (ObjectDB, Attribute):
        model.flush_instance_cache(force=True)


def _slot(type_key: str) -> str:
    """The component slot one declared capability type occupies."""
    return COMPONENT_TYPES[type_key].get_component_slot()


def _with_service_id(row, service_id: str):
    """The row with every declared service identity rewritten."""
    return dataclasses.replace(
        row,
        components=tuple(
            dataclasses.replace(
                declaration,
                kwargs={**declaration.kwargs, "service_id": service_id},
            )
            if "service_id" in declaration.kwargs
            else declaration
            for declaration in row.components
        ),
    )


class ServiceHostBatchRollbackTests(ServiceContentIsolation, EvenniaTestCase):
    """A fault anywhere in the batch restores rows, attributes and caches."""

    def _host_for(self, row):
        return NPC.objects.filter(db_key=row.name).first()

    def _first_processable_row(self):
        """The first roster row whose anchor room exists (registry order)."""
        from world.rules.guild_economy import _room_by_tag

        for row in get_catalog().service_hosts:
            if _room_by_tag(row.spawn_room) is not None:
                return row
        raise AssertionError("roster lost every resolvable row")

    def _snapshot(self):
        """Every live NPC's identity/slots/attributes and every player's party."""
        snapshot = {}
        for npc in NPC.objects.all_family():
            snapshot[("npc", npc.pk)] = {
                "key": npc.key,
                "location": npc.location.pk if npc.location else None,
                "slots": sorted(npc.components.db_names),
                "tags": sorted(
                    (str(key), str(category))
                    for key, category in npc.tags.all(return_key_and_category=True)
                ),
                "attributes": {
                    key: deepcopy(npc.attributes.get(key))
                    for key in HOST_ATTRIBUTE_SURFACES
                },
                "provenance": npc.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE),
            }
        for player in PlayerCharacter.objects.all_family():
            snapshot[("player", player.pk)] = {
                "party": list(player.db.party or []),
                "party_meta": deepcopy(player.db.party_meta),
            }
        return snapshot

    def _assert_snapshot(self, before):
        after = self._snapshot()
        self.assertEqual(sorted(after), sorted(before))
        for pk, expected in before.items():
            with self.subTest(pk=pk):
                self.assertEqual(after[pk], expected)

    @staticmethod
    def _fault_after(real, *, allowed_calls):
        """Let exactly ``allowed_calls`` calls through, then raise."""
        state = {"calls": 0}

        def wrapper(*args, **kwargs):
            if state["calls"] >= allowed_calls:
                raise RuntimeError("injected batch fault")
            state["calls"] += 1
            return real(*args, **kwargs)

        return wrapper

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_fault_after_a_component_attach_restores_the_previous_slots(self):
        sync_service_content()
        row = self._first_processable_row()
        host = self._host_for(row)
        slot = _slot(row.components[0].type)
        host.components.remove_by_name(slot)
        self.assertFalse(host.components.has(slot))

        before = self._snapshot()
        with patch.object(
            guild_economy,
            "assemble_capabilities",
            new=self._fault_after(
                guild_economy.assemble_capabilities, allowed_calls=1
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        # In-process: the batch's attachment is gone from the handler cache...
        self.assertFalse(NPC.objects.filter(pk=host.pk).first().components.has(slot))
        # ...and every host matches the pre-batch snapshot.
        self._assert_snapshot(before)
        # Durable rows agree after a full cache flush.
        flush_cache()
        self._assert_snapshot(before)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_fault_after_a_configuration_update_restores_the_previous_values(self):
        sync_service_content()
        row = self._first_processable_row()
        host = self._host_for(row)
        component = host.components.get(_slot(row.components[0].type))
        service_before = component.service_id
        edited_service_id = f"t_{row.host_key}_edited"
        self._patch_host_row(row.host_key, components=_with_service_id(row, edited_service_id).components)

        before = self._snapshot()
        with patch.object(
            guild_economy,
            "assemble_capabilities",
            new=self._fault_after(
                guild_economy.assemble_capabilities, allowed_calls=1
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        self.assertEqual(component.service_id, service_before)
        self._assert_snapshot(before)
        flush_cache()
        self._assert_snapshot(before)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_fault_after_a_component_removal_restores_the_obsolete_slot(self):
        sync_service_content()
        row = self._first_processable_row()
        host = self._host_for(row)
        # A managed capability the declaration does not declare: the batch
        # removes it, and the rollback must put it back.
        host.components.add(
            Merchant.create(host, service_id="t_obsolete", shop_key="t_obsolete")
        )
        self.assertTrue(host.components.has(Merchant.get_component_slot()))

        before = self._snapshot()
        with patch.object(
            guild_economy,
            "assemble_capabilities",
            new=self._fault_after(
                guild_economy.assemble_capabilities, allowed_calls=1
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        restored = NPC.objects.filter(pk=host.pk).first()
        self.assertTrue(restored.components.has(Merchant.get_component_slot()))
        self._assert_snapshot(before)
        flush_cache()
        self._assert_snapshot(before)

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_fault_after_the_second_row_creation_leaves_no_trace(self):
        created = []

        def failing_initializer(npc, card_raw, provenance):
            created.append(npc.pk)
            if len(created) == 2:
                raise RuntimeError("injected second-row fault")
            from world.rules.npc_persona import initialize_npc_persona as real

            return real(npc, card_raw, provenance)

        with patch.object(
            guild_economy, "initialize_npc_persona", side_effect=failing_initializer
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        self.assertEqual(len(created), 2)  # the second host was built, then rolled back
        self.assertEqual(NPC.objects.all_family().count(), 0)
        for pk in created:
            self.assertIsNone(NPC.objects.filter(pk=pk).first())

        # The failed instances never haunt the idmapper: a retry creates exactly
        # one host per resolvable row, with the authored identity intact.
        with self.captureOnCommitCallbacks(execute=True):
            sync_service_content()
        hosts = [self._host_for(row) for row in get_catalog().service_hosts]
        live = [host for host in hosts if host is not None]
        self.assertTrue(live)
        self.assertEqual(NPC.objects.all_family().count(), len(live))
        for row in get_catalog().service_hosts:
            host = self._host_for(row)
            if host is None:
                continue
            with self.subTest(row=row.host_key):
                self.assertEqual(
                    host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE),
                    row.host_key,
                )

    @covers_requirement(
        "npc-service-host-identity::managed-reconciliation-preserves-unrelated-and-subsystem-owned-state"
    )
    def test_a_fault_inside_a_retirement_restores_the_rows_and_party_state(self):
        from evennia.utils.create import create_object
        from world.rules.party import join_party, party_ids, party_meta

        sync_service_content()
        rows = [
            row
            for row in get_catalog().service_hosts
            if self._host_for(row) is not None
        ][:3]
        self.assertEqual(len(rows), 3)
        hosts = [self._host_for(row) for row in rows]
        # A committed delete clears the instance's pk, so keep the identities.
        pks = [host.pk for host in hosts]
        # All three retired hosts are companions of ONE owner: each retirement
        # shrinks the same party list, so compensation must replay the earliest
        # snapshot last.
        player = create_object(PlayerCharacter, key="retirement owner")
        # Persist the holder's component listing up front. Evennia writes it
        # lazily on the first read, and a lazy write while the instance is
        # still materializing would add the row before the host carries its
        # database alias.
        player.attributes.add("component_names", [])
        player.race = "human"
        player.apply_race_baseline()
        for host in hosts:
            player.location = host.location
            join_party(host, player)
        self.assertEqual(party_ids(player), pks)
        self._patch_roster(
            tuple(
                row for row in get_catalog().service_hosts if row not in rows
            )
        )
        before = self._snapshot()

        real_delete = NPC.delete
        calls = {"count": 0}

        def delete_with_fault(instance, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == len(hosts):
                # The deletion hook has already purged this host's party
                # binding by the time the row deletion fails.
                instance.at_object_delete()
                raise RuntimeError("injected post-hook retirement fault")
            return real_delete(instance, *args, **kwargs)

        with patch.object(NPC, "delete", delete_with_fault):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        # Every row is back, and the owner still holds all three bindings with
        # their metadata, both in process and after a full cache flush.
        for pk in pks:
            self.assertIsNotNone(NPC.objects.filter(pk=pk).first())
        self.assertEqual(party_ids(player), pks)
        self.assertEqual(sorted(party_meta(player)), sorted(str(pk) for pk in pks))
        self._assert_snapshot(before)
        _cold_identity_map()
        self.assertEqual(party_ids(player), pks)
        self._assert_snapshot(before)
