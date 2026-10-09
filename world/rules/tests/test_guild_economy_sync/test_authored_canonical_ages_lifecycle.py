"""Lifecycle and smoke verification for authored canonical ages."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import Character
from typeclasses.npcs import NPC
from world.rules.guild_economy import sync_service_content
from typeclasses.components import GuildStaff
from world.rules.npc_persona import update_npc_persona, read_npc_persona, current_persona_version
from tools.spec_traceability import covers_requirement
from world.rules.tests.test_guild_economy_sync._support import ServiceContentIsolation
from world.rules.tests.test_guild_economy_sync._support import _guild_host_name, _merchant_host_name


class NpcAuthoredCanonicalAgesLifecycleTests(ServiceContentIsolation, EvenniaTestCase):
    """End-to-end lifecycle verification for proposal #21."""

    @covers_requirement(
        "place-driven-service-sync::host-synchronization-uses-authored-canonical-ages-without-rewriting-reused-state"
    )
    def test_fresh_host_and_reused_host_preservation(self):
        sync_service_content()

        # 1. Fresh host agrees with authored profile (guild master: 50/50, merchant: 44/44)
        guild_host = NPC.objects.filter(db_key=_guild_host_name()).first()
        self.assertIsNotNone(guild_host)
        self.assertEqual(int(guild_host.attributes.get("age")), 50)
        self.assertEqual(int(guild_host.attributes.get("apparent_age")), 50)

        # 2. Modify host: age=61, remove apparent_age, edit card appearance
        guild_host.attributes.add("age", 61)
        guild_host.attributes.remove("apparent_age")
        snapshot = read_npc_persona(guild_host)
        edited_card = snapshot.card.to_record()
        edited_card["appearance"] = "編輯過的外觀描述，留著整齊的鬍鬚。"
        current_ver = current_persona_version(guild_host)
        update_npc_persona(guild_host, edited_card, current_ver)
        meta_before_ver = current_persona_version(guild_host)

        # 3. Resync
        sync_service_content()

        guild_host = NPC.objects.filter(db_key=_guild_host_name()).first()
        # Existing age 61 preserved, missing apparent_age filled from profile (50)
        self.assertEqual(int(guild_host.attributes.get("age")), 61)
        self.assertEqual(int(guild_host.attributes.get("apparent_age")), 50)
        # Card and version preserved
        snapshot_after = read_npc_persona(guild_host)
        self.assertEqual(
            snapshot_after.card.appearance,
            "編輯過的外觀描述，留著整齊的鬍鬚。",
        )
        self.assertEqual(
            current_persona_version(guild_host),
            meta_before_ver,
        )

