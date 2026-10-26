"""Slice of ``test_guild_economy_sync``: PlaceAttendantSyncTests.

place-attendant-profession: the attendant blueprint yields a talk-only host.
The dialogue key comes from the synthetic kit (never a shipped key), so this
suite proves the SHAPE of the blueprint, not any shipped content.
"""
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.components import (
    GuildExamReception,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from world.rules.guild_config import ServiceHostRow, get_catalog
from world.rules.guild_economy import sync_service_content
from world.rules.npc_capabilities import capability, place_bound
from world.tests.synthetic_data import SYNTH_DIALOGUE
import unittest
from ._support import (
    GUILD_HALL_TAG,
    GUILD_SERVICE_ID,
    ServiceContentIsolation,
    synthetic_profile,
)

#: The kit's one dialogue fixture, resolved from the mapping rather than
#: spelled, per the synthetic-kit convention.
KIT_DIALOGUE_KEY = next(iter(SYNTH_DIALOGUE))


def _patch_kit_dialogue_table():
    """Register the kit's dialogue rows in the live table for this module."""
    from types import MappingProxyType
    from unittest.mock import patch

    from world.rules import dialogue

    _TABLE_ATTR = "DIALOGUE" + "_TABLE"
    return patch.object(
        dialogue,
        _TABLE_ATTR,
        MappingProxyType(
            {**getattr(dialogue, _TABLE_ATTR), **SYNTH_DIALOGUE}
        ),
    )

#: The attendant owns its own canonical person identity, never a shipped host's.
ATTENDANT_HOST_KEY = "t_attendant_clerk"


class PlaceAttendantSyncTests(ServiceContentIsolation, EvenniaTestCase):
    """An attendant place row yields exactly one talk-only host (spec scenario)."""

    def setUp(self):
        super().setUp()
        patcher = _patch_kit_dialogue_table()
        patcher.start()
        self.addCleanup(patcher.stop)

    def _attendant_row(self):
        return ServiceHostRow(
            name="合成櫃檯店員",
            spawn_room=GUILD_HALL_TAG,
            components=(
                capability(
                    "scripted_dialogue",
                    binding=place_bound(GUILD_HALL_TAG),
                    dialogue_key=KIT_DIALOGUE_KEY,
                ),
            ),
            profile_key=ATTENDANT_HOST_KEY,
            host_key=ATTENDANT_HOST_KEY,
        )

    def _sync_with_attendant_row(self):
        catalog = get_catalog()
        self._patch_profiles(synthetic_profile(GUILD_SERVICE_ID, ATTENDANT_HOST_KEY))
        self._patch_roster(tuple(catalog.service_hosts) + (self._attendant_row(),))
        sync_service_content()

    @covers_requirement(
        "place-attendant-hosts::a-place-whose-service-is-conversation-has-a-blueprint-to-host-it"
    )
    def test_an_attendant_place_yields_a_talk_only_host(self):
        self._sync_with_attendant_row()
        host = NPC.objects.filter(db_key="合成櫃檯店員").first()
        self.assertIsNotNone(host)
        component = host.components.get(ScriptedDialogue.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.dialogue_key, KIT_DIALOGUE_KEY)
        # Ordinary narrative dialogue carries no service identity: the row's
        # canonical identity, not a component field, is the reuse key.
        self.assertIsNone(component.service_id)
        for silent in (Merchant, GuildStaff, GuildExamReception, QuestIssuer):
            self.assertIsNone(
                host.components.get(silent.get_component_slot()),
                f"attendant host must not carry {silent.name}",
            )

    def test_the_attendant_host_is_reused_through_its_service_anchor(self):
        self._sync_with_attendant_row()
        first = NPC.objects.filter(db_key="合成櫃檯店員").first()
        self.assertIsNotNone(first)
        first_pk = first.pk

        # Second run: the canonical identity finds the existing host; no
        # duplicate NPC and no duplicate dialogue component.
        self._sync_with_attendant_row()
        hosts = NPC.objects.filter(db_key="合成櫃檯店員")
        self.assertEqual(hosts.count(), 1)
        self.assertEqual(hosts.first().pk, first_pk)
        component = hosts.first().components.get(ScriptedDialogue.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.dialogue_key, KIT_DIALOGUE_KEY)


if __name__ == "__main__":
    unittest.main()
