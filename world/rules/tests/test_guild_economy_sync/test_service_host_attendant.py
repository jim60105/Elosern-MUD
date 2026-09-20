"""Slice of ``test_guild_economy_sync``: PlaceAttendantSyncTests.

place-attendant-profession: the attendant blueprint yields a talk-only host.
The dialogue key comes from the synthetic kit (never a shipped key), so this
suite proves the SHAPE of the blueprint, not any shipped content.
"""
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.components import (
    GuildExaminer,
    GuildStaff,
    Merchant,
    QuestIssuer,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC
from world.rules.guild_config import ServiceHostRow, get_catalog
from world.rules.guild_economy import sync_service_content
from world.rules.profession_config import get_profession
from world.tests.synthetic_data import SYNTH_DIALOGUE
import unittest
from ._support import GUILD_HALL_TAG, ServiceContentIsolation

#: The kit's one dialogue fixture, resolved from the mapping rather than
#: spelled, per the synthetic-kit convention.
KIT_DIALOGUE_KEY = next(iter(SYNTH_DIALOGUE))

ATTENDANT_SERVICE_ID = "t_attendant_clerk"


class PlaceAttendantSyncTests(ServiceContentIsolation, EvenniaTestCase):
    """An attendant place row yields exactly one talk-only host (spec scenario)."""

    def _attendant_row(self):
        return ServiceHostRow(
            name="合成櫃檯店員",
            title="合成櫃檯值班店員",
            profession=get_profession("attendant"),
            anchor_room=GUILD_HALL_TAG,
            service_id=ATTENDANT_SERVICE_ID,
            authored_kwargs={"dialogue_key": KIT_DIALOGUE_KEY},
        )

    def _sync_with_attendant_row(self):
        catalog = get_catalog()
        self._patch_roster(tuple(catalog.service_hosts) + (self._attendant_row(),))
        sync_service_content()

    def test_an_attendant_place_yields_a_talk_only_host(self):
        self._sync_with_attendant_row()
        host = NPC.objects.filter(db_key="合成櫃檯店員").first()
        self.assertIsNotNone(host)
        component = host.components.get(ScriptedDialogue.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.dialogue_key, KIT_DIALOGUE_KEY)
        # The anchor identity the row carries is projected onto the class
        # that declares it — the reuse path reads exactly this field.
        self.assertEqual(component.service_id, ATTENDANT_SERVICE_ID)
        for silent in (Merchant, GuildStaff, GuildExaminer, QuestIssuer):
            self.assertIsNone(
                host.components.get(silent.get_component_slot()),
                f"attendant host must not carry {silent.name}",
            )

    def test_the_attendant_host_is_reused_through_its_service_anchor(self):
        self._sync_with_attendant_row()
        first = NPC.objects.filter(db_key="合成櫃檯店員").first()
        self.assertIsNotNone(first)
        first_pk = first.pk

        # Second run: the service_id anchor finds the existing host; no
        # duplicate NPC and no duplicate dialogue component.
        self._sync_with_attendant_row()
        hosts = NPC.objects.filter(db_key="合成櫃檯店員")
        self.assertEqual(hosts.count(), 1)
        self.assertEqual(hosts.first().pk, first_pk)
        component = hosts.first().components.get(ScriptedDialogue.get_component_slot())
        self.assertIsNotNone(component)
        self.assertEqual(component.service_id, ATTENDANT_SERVICE_ID)


if __name__ == "__main__":
    unittest.main()
