"""Lifecycle and smoke verification for authored canonical ages."""

from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import Character
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.guild_economy import sync_service_content
from world.rules.guild_exams import start_guild_exam
from world.rules.guild import register_adventurer
from world.rules.surfaces import write_counter_trait, read_counter_trait
from typeclasses.components import GuildStaff
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
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

    @covers_requirement(
        "guild-rank-exams::guild-exam-opponents-carry-canonical-age"
    )
    def test_exam_opponent_age_and_rollback_on_invalid_identity(self):
        sync_service_content()
        examiner = NPC.objects.filter(db_key=_guild_host_name()).first()
        self.assertIsNotNone(examiner)

        # 1. Successful exam opponent carries authored age pair
        player = create_object(PlayerCharacter, key="t_exam_tester", location=examiner.location)
        player.race = "human"
        player.apply_race_baseline()
        register_adventurer(player, examiner)
        write_counter_trait(player, "guild_merit", 100)
        # E rank examiner: guild_examiner_e (26/26)
        record = start_guild_exam(player, examiner, "E")
        opponent = ObjectDB.objects.filter(id=record.opponent_id).first()
        self.assertIsNotNone(opponent)
        self.assertEqual(int(opponent.attributes.get("age")), 26)
        self.assertEqual(int(opponent.attributes.get("apparent_age")), 26)

        # 2. Invalid age rollback: fresh eligible player, no active combat
        from unittest.mock import patch
        from dataclasses import replace
        from world.lore.guild import GUILD_RANK_REGISTRY
        rank_e = GUILD_RANK_REGISTRY["E"]
        self.assertEqual(opponent.key, rank_e.examiner_name)
        player2 = create_object(PlayerCharacter, key="t_exam_tester2", location=examiner.location)
        player2.race = "human"
        player2.apply_race_baseline()
        register_adventurer(player2, examiner)
        write_counter_trait(player2, "guild_merit", 100)
        initial_merit = 100
        initial_affinity = examiner.relations.affinity_for(player2)

        fake_registry = dict(NPC_PROFILE_REGISTRY)
        bad_profile = replace(NPC_PROFILE_REGISTRY["guild_examiner_e"])
        object.__setattr__(bad_profile, "age", 10001)
        fake_registry["guild_examiner_e"] = bad_profile
        with patch("world.rules.guild_exams.NPC_PROFILE_REGISTRY", fake_registry):
            with self.assertRaises(ValueError) as caught:
                start_guild_exam(player2, examiner, "E")
            self.assertIn("10001", str(caught.exception))
            self.assertIn("guild_examiner_e", str(caught.exception))

        # Assert rollback of opponent, merit, affinity, and no session created for player2
        from world.rules.combat_session import read_session
        self.assertEqual(read_session(player2), None)
        self.assertEqual(read_counter_trait(player2, "guild_merit"), initial_merit)
        self.assertEqual(examiner.relations.affinity_for(player2), initial_affinity)
        # The only examiner opponent in the DB is opponent 1 from step 1
        self.assertEqual(ObjectDB.objects.filter(db_key=rank_e.examiner_name).count(), 1)
        self.assertEqual(ObjectDB.objects.filter(db_key=rank_e.examiner_name).first().pk, opponent.pk)
