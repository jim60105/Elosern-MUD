"""Canonical party identity persistence and source isolation tests."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.quests.definitions import EscortCompletion, QuestStage, QuestType
from world.quests.tests._fixtures import QuestRegistryIsolation, escort, quest, register
from world.rules.party import (
    PARTY_MAX_COMPANIONS, PartyJoinError, PartyWriteError, add_temporary_source,
    bound_owner_of, general_member_ids, has_general_membership, is_companion,
    join_party, leave_party, live_companions, party_ids, party_meta, party_size,
    reasons_for, release_record_reasons,
)


class PartyIdentityTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="identity room")
        self.player = create_object(PlayerCharacter, key="identity owner", location=self.room)
        register(quest(
            "identity_escort", quest_type=QuestType.ESCORT,
            stages=(QuestStage(0, escort(
                completion=EscortCompletion.RENDEZVOUS,
                meeting_role_refs=("meeting",),
            )),),
        ))

    def _npc(self):
        return create_object(NPC, key="identity member", location=self.room)

    def _source(self, npc, number=1):
        record = QuestRecord(
            quest_id=f"identity_escort:{number}", definition_key="identity_escort",
            issuer_key=f"npc:#{npc.pk}", state=QuestState.IN_PROGRESS,
            stage_index=0, stage_progress=0, deadline_tick=None, accepted_tick=0,
            stage_room_id=None, objective_target_ids=(),
            protected_entity_ids=(npc.pk,), failure_reason=None,
            protected_roles=(("escortee", npc.pk),),
        )
        self.player.db.quest_log = [
            *list(self.player.db.quest_log or []), to_storage(record)
        ]
        add_temporary_source(npc, self.player, record.quest_id, "escortee")
        return record

    def test_metadata_attribute_roundtrip(self):
        player = create_object(PlayerCharacter, key="identity owner")
        player.db.party_meta = {"1": {"general": False, "reasons": [["r", "role"]]}}
        for reload in (False, True):
            with self.subTest(reload=reload):
                if reload:
                    player.attributes.reset_cache()
                stored = player.db.party_meta
                self.assertIsInstance(stored, Mapping)
                self.assertIsInstance(stored["1"], Mapping)
                self.assertIsInstance(stored["1"]["reasons"], Sequence)
                self.assertFalse(stored["1"]["general"])
                self.assertEqual(list(stored["1"]["reasons"][0]), ["r", "role"])
                self.assertEqual(
                    party_meta(player),
                    {"1": {"general": False, "reasons": [["r", "role"]]}},
                )

    def test_full_general_quota_admits_exact_escort_after_reload(self):
        generals = [self._npc() for _ in range(PARTY_MAX_COMPANIONS)]
        for npc in generals:
            join_party(npc, self.player)
        escorted = self._npc()
        record = self._source(escorted)
        self.player.attributes.reset_cache()
        escorted.attributes.reset_cache()
        self.assertEqual(party_size(self.player), 4)
        self.assertEqual(party_ids(self.player), [npc.pk for npc in [*generals, escorted]])
        self.assertEqual(bound_owner_of(escorted), self.player)
        self.assertEqual(reasons_for(escorted, self.player), ((record.quest_id, "escortee"),))
        self.assertFalse(has_general_membership(escorted, self.player))

    def test_dual_multiple_sources_and_general_dismissal_share_one_row(self):
        npc = self._npc()
        join_party(npc, self.player)
        first = self._source(npc)
        second = self._source(npc, 2)
        add_temporary_source(npc, self.player, first.quest_id, "escortee")
        self.assertEqual(party_ids(self.player), [npc.pk])
        self.assertEqual(len(reasons_for(npc, self.player)), 2)
        release_record_reasons(self.player, first.quest_id)
        release_record_reasons(self.player, first.quest_id)
        self.assertTrue(has_general_membership(npc, self.player))
        self.assertEqual(reasons_for(npc, self.player), ((second.quest_id, "escortee"),))
        leave_party(npc, self.player, "dismissed")
        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(general_member_ids(self.player), [])
        release_record_reasons(self.player, second.quest_id)
        self.assertFalse(is_companion(npc, self.player))
        self.assertIsNone(npc.db.party_member)

    def test_general_promotion_of_temporary_member_remains_quota_bounded(self):
        escorted = self._npc()
        source = self._source(escorted)
        for _ in range(3):
            join_party(self._npc(), self.player)
        join_party(escorted, self.player)
        self.assertEqual(party_size(self.player), 4)
        self.assertEqual(reasons_for(escorted, self.player), ((source.quest_id, "escortee"),))
        another = self._npc()
        self._source(another, 2)
        with self.assertRaises(PartyJoinError) as refused:
            join_party(another, self.player)
        self.assertEqual(refused.exception.reason, "party_full")
        self.assertTrue(is_companion(another, self.player))
        self.assertFalse(has_general_membership(another, self.player))

    def test_leave_refuses_to_silently_detach_a_temporary_only_member(self):
        from commands.leave import CmdLeave
        from world.rules.party import ESCORT_BOUND_MESSAGE

        npc = create_object(NPC, key="護衛對象", location=self.room)
        source = self._source(npc)
        command = CmdLeave()
        command.caller = self.player
        command.args = npc.key
        with patch.object(self.player, "msg") as msg:
            command.func()
        msg.assert_called_once_with(
            ESCORT_BOUND_MESSAGE.format(quests=source.quest_id)
        )
        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(
            reasons_for(npc, self.player), ((source.quest_id, "escortee"),)
        )

    def test_the_webclient_leave_adapter_refuses_a_temporary_only_member(self):
        from web.webclient.actions.exploration_actions import _party_leave_adapter
        from world.rules.party import ESCORT_BOUND_MESSAGE, REASON_ESCORT_BOUND

        npc = create_object(NPC, key="護衛對象", location=self.room)
        source = self._source(npc)
        result = _party_leave_adapter(self.player, {"npc_id": int(npc.pk)})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], REASON_ESCORT_BOUND)
        self.assertEqual(
            result["message"],
            ESCORT_BOUND_MESSAGE.format(quests=source.quest_id),
        )
        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(
            reasons_for(npc, self.player), ((source.quest_id, "escortee"),)
        )

    def test_leave_removes_only_the_general_identity_of_a_dual_member(self):
        from commands.leave import CmdLeave
        from world.rules.party import LEAVE_DISMISSED_MESSAGE

        npc = create_object(NPC, key="護衛對象", location=self.room)
        join_party(npc, self.player)
        source = self._source(npc)
        command = CmdLeave()
        command.caller = self.player
        command.args = npc.key
        with patch.object(self.player, "msg") as msg:
            command.func()
        msg.assert_called_once_with(LEAVE_DISMISSED_MESSAGE)
        self.assertFalse(has_general_membership(npc, self.player))
        self.assertTrue(is_companion(npc, self.player))
        self.assertEqual(
            reasons_for(npc, self.player), ((source.quest_id, "escortee"),)
        )

    def test_terminal_foreign_and_differently_bound_reasons_grant_nothing(self):
        npc = self._npc()
        record = self._source(npc)
        for changed in (
            replace(record, state=QuestState.FAILED, failure_reason="abandoned",
                    protected_entity_ids=()),
            replace(record, protected_roles=(("escortee", self.player.pk),)),
        ):
            self.player.db.quest_log = [to_storage(changed)]
            self.assertFalse(is_companion(npc, self.player))
            self.assertIsNone(bound_owner_of(npc))
        self.player.db.quest_log = [to_storage(record)]
        stranger = create_object(PlayerCharacter, key="other owner", location=self.room)
        stranger.db.quest_log = [to_storage(record)]
        with self.assertRaises(PartyJoinError):
            add_temporary_source(npc, stranger, record.quest_id, "escortee")
        self.assertIsNone(stranger.db.party)

    def test_corrupt_missing_and_deleted_surfaces_grant_no_identity(self):
        npc = self._npc()
        join_party(npc, self.player)
        self.player.db.party = ["invalid", npc.pk, npc.pk, 999999999]
        self.assertEqual(live_companions(self.player), [npc])
        self.player.db.party_meta = {str(npc.pk): {"general": "true", "reasons": []}}
        self.assertEqual(live_companions(self.player), [])
        self.player.db.party_meta = {}
        self.assertEqual(live_companions(self.player), [])
        join_party(npc, self.player)
        npc.delete()
        self.assertEqual(live_companions(self.player), [])
        self.assertEqual(party_meta(self.player), {})

    def test_metadata_write_failure_restores_paired_surfaces_and_reload(self):
        npc = self._npc()
        before = (list(self.player.db.party or []), self.player.db.party_meta)
        original_add = self.player.attributes.add
        armed = True

        def fail_once(key, *args, **kwargs):
            nonlocal armed
            if key == "party_meta" and armed:
                armed = False
                raise RuntimeError("metadata write fault")
            return original_add(key, *args, **kwargs)

        with patch.object(self.player.attributes, "add", side_effect=fail_once):
            with self.assertRaises(PartyWriteError):
                join_party(npc, self.player)
        for reload in (False, True):
            if reload:
                self.player.attributes.reset_cache()
                npc.attributes.reset_cache()
            self.assertEqual((list(self.player.db.party or []), self.player.db.party_meta), before)
            self.assertIsNone(npc.db.party_member)

    def test_valid_escort_retains_low_affinity_without_handback(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change, seed_affinity

        npc = self._npc()
        self._source(npc)
        seed_affinity(npc, self.player, 70)
        with patch("world.rules.possession.release_for_party_change") as handback:
            result = apply_affinity_change(npc, self.player, AffinitySource.FRIENDLY_FIRE, -10)
        self.assertEqual(npc.relations.affinity_for(self.player), 60)
        self.assertIsNone(result.auto_leave_notification)
        handback.assert_not_called()
        self.assertTrue(is_companion(npc, self.player))

    def test_dual_member_retains_low_affinity_with_a_valid_reason(self):
        from world.rules.affinity import AffinitySource, apply_affinity_change, seed_affinity

        npc = self._npc()
        join_party(npc, self.player)
        source = self._source(npc)
        seed_affinity(npc, self.player, 70)
        result = apply_affinity_change(npc, self.player, AffinitySource.FRIENDLY_FIRE, -10)
        self.assertEqual(npc.relations.affinity_for(self.player), 60)
        self.assertIsNone(result.auto_leave_notification)
        self.assertTrue(is_companion(npc, self.player))
        self.assertTrue(has_general_membership(npc, self.player))
        self.assertEqual(
            reasons_for(npc, self.player), ((source.quest_id, "escortee"),)
        )

    def test_escort_schedule_silence_ends_with_last_temporary_reason(self):
        from world.rules.service_gate import schedule_silenced

        npc = self._npc()
        source = self._source(npc)
        self.assertTrue(schedule_silenced(npc))
        release_record_reasons(self.player, source.quest_id)
        self.assertFalse(schedule_silenced(npc))
        self.assertIs(npc.location, self.room)

    def test_last_source_hands_back_but_surviving_sources_preserve_control(self):
        from world.rules.possession import current_possession, enter_possession

        npc = self._npc()
        first = self._source(npc)
        second = self._source(npc, 2)
        enter_possession(self.player, npc)
        release_record_reasons(self.player, first.quest_id)
        self.assertEqual(current_possession(self.player)["npc_dbid"], npc.pk)
        join_party(npc, self.player)
        release_record_reasons(self.player, second.quest_id)
        self.assertEqual(current_possession(self.player)["npc_dbid"], npc.pk)
        # General-only dismissal retains the established handback-first gate.
        with self.assertRaises(PartyJoinError):
            leave_party(npc, self.player, "dismissed")

    def test_temporary_last_source_release_clears_control_after_reload(self):
        from world.rules.possession import current_possession, enter_possession

        npc = self._npc()
        source = self._source(npc)
        enter_possession(self.player, npc)
        release_record_reasons(self.player, source.quest_id)
        for reload in (False, True):
            if reload:
                self.player.attributes.reset_cache()
                npc.attributes.reset_cache()
            self.assertIsNone(current_possession(self.player))
            self.assertIsNone(npc.db.possessed_by)
            self.assertFalse(is_companion(npc, self.player))

    def test_write_after_successful_handback_restores_control_and_membership(self):
        from world.rules.possession import current_possession, enter_possession

        npc = self._npc()
        source = self._source(npc)
        enter_possession(self.player, npc)
        before = party_meta(self.player)
        with patch("world.rules.party._write_binding", side_effect=RuntimeError("after handback")):
            with self.assertRaisesRegex(RuntimeError, "after handback"):
                release_record_reasons(self.player, source.quest_id)
        for reload in (False, True):
            if reload:
                self.player.attributes.reset_cache()
                npc.attributes.reset_cache()
            self.assertEqual(current_possession(self.player)["npc_dbid"], npc.pk)
            self.assertEqual(npc.db.possessed_by, self.player.pk)
            self.assertEqual(party_meta(self.player), before)
            self.assertTrue(is_companion(npc, self.player))

    def test_technical_handback_refusal_keeps_last_source(self):
        from world.rules.possession import enter_possession

        npc = self._npc()
        source = self._source(npc)
        enter_possession(self.player, npc)
        with patch("world.rules.possession.release_for_party_change", side_effect=RuntimeError("refused")):
            with self.assertRaisesRegex(RuntimeError, "refused"):
                release_record_reasons(self.player, source.quest_id)
        self.assertEqual(reasons_for(npc, self.player), ((source.quest_id, "escortee"),))
        self.assertEqual(npc.db.possessed_by, self.player.pk)

    def test_real_session_last_source_rollback_uses_fresh_sequence(self):
        from commands.default_cmdsets import PossessedCharacterCmdSet
        from world.rules.possession import enter_possession

        self.player = self.char1
        self.player.location = self.room
        npc = self._npc()
        source = self._source(npc)
        enter_possession(self.player, npc)
        self.assertIs(self.session.puppet, npc)
        before_lock = npc.locks.get("puppet")
        with patch("world.rules.party._write_binding", side_effect=RuntimeError("after handback")):
            with self.assertRaisesRegex(RuntimeError, "after handback"):
                release_record_reasons(self.player, source.quest_id)
        self.assertIs(self.account.get_puppet(self.session), npc)
        self.assertEqual(npc.locks.get("puppet"), before_lock)
        self.assertTrue(npc.cmdset.has(PossessedCharacterCmdSet))
        self.assertEqual(npc.db.possessed_by, self.player.pk)
        self.assertTrue(is_companion(npc, self.player))
        release_record_reasons(self.player, source.quest_id)
        self.assertIs(self.account.get_puppet(self.session), self.player)
        self.assertFalse(npc.cmdset.has(PossessedCharacterCmdSet))
