"""Slice of ``test_guild_economy_sync``: atomic batch rollback.

The whole source batch — component convergence, authored configuration,
initial stock and whole-row retirement — is one transaction. A failure on any
later row must leave the database *and* the in-process attribute, tag and
component caches exactly as they were, and must not leave a half-built object
in the idmapper for the next sync to inherit.
"""

from copy import deepcopy
from unittest.mock import patch

from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTestCase

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

from ._support import ServiceContentIsolation

#: Managed capability type keys mapped to the slot each one occupies.
PROFESSION_TYPE_SLOTS = {
    "guild_staff": GuildStaff.get_component_slot(),
    "guild_exam_reception": GuildExamReception.get_component_slot(),
    "merchant": Merchant.get_component_slot(),
    "scripted_dialogue": ScriptedDialogue.get_component_slot(),
    "church_host": ChurchHost.get_component_slot(),
}


class ServiceHostBatchRollbackTests(ServiceContentIsolation, EvenniaTestCase):
    """A fault anywhere in the batch restores rows, attributes and caches."""

    def _host_for(self, row):
        return NPC.objects.filter(db_key=row.name).first()

    def _first_processable_row(self):
        """The first roster row whose anchor room exists (registry order)."""
        from world.rules.guild_economy import _room_by_tag

        for row in get_catalog().service_hosts:
            if _room_by_tag(row.anchor_room) is not None:
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

    def test_a_fault_after_a_component_attach_restores_the_previous_slots(self):
        sync_service_content()
        row = self._first_processable_row()
        host = self._host_for(row)
        slot = PROFESSION_TYPE_SLOTS[row.profession.components[0].type_key]
        host.components.remove_by_name(slot)
        self.assertFalse(host.components.has(slot))

        before = self._snapshot()
        with patch.object(
            guild_economy,
            "assemble_profession_components",
            new=self._fault_after(
                guild_economy.assemble_profession_components, allowed_calls=1
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

    def test_a_fault_after_a_configuration_update_restores_the_previous_values(self):
        sync_service_content()
        row = self._first_processable_row()
        host = self._host_for(row)
        component = host.components.get(
            PROFESSION_TYPE_SLOTS[row.profession.components[0].type_key]
        )
        service_before = component.service_id
        edited_service_id = f"t_{row.service_id}_edited"
        self._patch_host_row(row.host_key, service_id=edited_service_id)

        before = self._snapshot()
        with patch.object(
            guild_economy,
            "assemble_profession_components",
            new=self._fault_after(
                guild_economy.assemble_profession_components, allowed_calls=1
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        self.assertEqual(component.service_id, service_before)
        self._assert_snapshot(before)
        flush_cache()
        self._assert_snapshot(before)

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
            "converge_managed_components",
            new=self._fault_after(
                guild_economy.converge_managed_components, allowed_calls=1
            ),
        ):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        restored = NPC.objects.filter(pk=host.pk).first()
        self.assertTrue(restored.components.has(Merchant.get_component_slot()))
        self._assert_snapshot(before)
        flush_cache()
        self._assert_snapshot(before)

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

    def test_a_fault_during_retirement_restores_the_rows_and_party_state(self):
        from world.rules.party import join_party, party_ids

        sync_service_content()
        rows = [self._first_processable_row()]
        rows.extend(
            row
            for row in get_catalog().service_hosts
            if row.host_key != rows[0].host_key and self._host_for(row) is not None
        )
        first_host = self._host_for(rows[0])
        second_host = self._host_for(rows[1])
        self.assertIsNotNone(second_host)
        # A committed delete clears the instance's pk, so keep the identity.
        first_pk, second_pk = first_host.pk, second_host.pk
        # The first retired host is a live companion: its deletion purges the
        # owner's party surfaces, which the rollback must put back.
        from evennia.utils.create import create_object

        player = create_object(PlayerCharacter, key="retirement owner")
        player.race = "human"
        player.apply_race_baseline()
        player.location = first_host.location
        join_party(first_host, player)
        self.assertEqual(party_ids(player), [first_host.pk])
        self._patch_roster(
            tuple(
                row
                for row in get_catalog().service_hosts
                if row.host_key not in {rows[0].host_key, rows[1].host_key}
            )
        )
        before = self._snapshot()

        real_delete = NPC.delete
        calls = {"count": 0}

        def delete_with_fault(instance, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("injected retirement fault")
            return real_delete(instance, *args, **kwargs)

        with patch.object(NPC, "delete", delete_with_fault):
            with self.assertRaises(RuntimeError):
                sync_service_content()

        # Both rows are back, and the owner's party surfaces survived the
        # already-executed first deletion.
        self.assertIsNotNone(NPC.objects.filter(pk=first_pk).first())
        self.assertIsNotNone(NPC.objects.filter(pk=second_pk).first())
        self.assertEqual(party_ids(player), [first_pk])
        self._assert_snapshot(before)
        flush_cache()
        self._assert_snapshot(before)
