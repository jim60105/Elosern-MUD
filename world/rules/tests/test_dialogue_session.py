"""Dialogue-session state (webclient-align-07): the deterministic-core seam.

These EvenniaTest cases pin the ONLY writers of ``db.dialogue_session``: the
session helpers (open/refresh/truncate, conditional + unconditional clears,
corrupt-value degradation, stale-dbid not-live reporting), the ``talk``
text-command scripted-success writer, and the clear seams (a settled
movement, an ``engage``, the NPC leave-room/despawn/leave-party cleanup).
The offline scenario proves the scripted table path drives the whole session
with every AI profile disabled.
"""

from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.ai.profiles import default_profiles
from world.rules.clock import get_world_clock
from world.rules.combat_session import engage
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    MAX_DIALOGUE_SESSION_LINE_CODE_POINTS,
    clear_dialogue_session,
    greeting_for,
    live_dialogue_session,
    open_or_refresh_dialogue,
    table_response,
)
from world.rules.movement_settlement import settle_movement
from world.rules.party import follow_companions, join_party, leave_party
from world.rules.tests.combat_fixtures import BattlefieldIsolation


def _all_profiles_off() -> dict:
    raw = default_profiles()
    for layer in raw:
        raw[layer]["enabled"] = False
    return raw


class DialogueSessionHelperTests(EvenniaTest):
    """The helper trio as the only writers of the stored value."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="session player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.host = create_object(NPC, key="公會職員", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        self.other = create_object(NPC, key="路人", location=self.room1)
        self.away = create_object(Room, key="別處", location=None)

    def test_open_records_host_line_and_clock_tick(self):
        tick = get_world_clock().tick
        session = open_or_refresh_dialogue(self.player, self.host, "公會欢迎你。")
        stored = self.player.db.dialogue_session
        self.assertEqual(session.npc_id, int(self.host.pk))
        self.assertEqual(stored["npc_id"], int(self.host.pk))
        self.assertEqual(stored["line"], "公會欢迎你。")
        self.assertEqual(stored["updated_tick"], tick)
        live = live_dialogue_session(self.player)
        self.assertIsNotNone(live)
        self.assertEqual(live.line, "公會欢迎你。")

    def test_refresh_replaces_the_one_session_in_place(self):
        open_or_refresh_dialogue(self.player, self.host, "第一句")
        open_or_refresh_dialogue(self.player, self.other, "第二句")
        stored = self.player.db.dialogue_session
        self.assertEqual(stored["npc_id"], int(self.other.pk))
        self.assertEqual(stored["line"], "第二句")
        self.assertEqual(live_dialogue_session(self.player).npc_id, int(self.other.pk))

    def test_overlong_line_is_truncated_at_write(self):
        long_line = "言" * (MAX_DIALOGUE_SESSION_LINE_CODE_POINTS + 500)
        session = open_or_refresh_dialogue(self.player, self.host, long_line)
        self.assertEqual(len(session.line), MAX_DIALOGUE_SESSION_LINE_CODE_POINTS)
        self.assertEqual(
            len(self.player.db.dialogue_session["line"]),
            MAX_DIALOGUE_SESSION_LINE_CODE_POINTS,
        )

    def test_corrupt_value_reads_no_session(self):
        for corrupt in ("garbage", {"npc_id": "x", "line": "y"}, {"npc_id": True, "line": "y"}):
            with self.subTest(corrupt=repr(corrupt)):
                self.player.db.dialogue_session = corrupt
                self.assertIsNone(live_dialogue_session(self.player))

    def test_unconditional_clear_retires_a_corrupt_value(self):
        self.player.db.dialogue_session = "garbage"
        self.assertFalse(clear_dialogue_session(self.player, npc=self.host))
        self.assertEqual(self.player.db.dialogue_session, "garbage")
        self.assertTrue(clear_dialogue_session(self.player))
        self.assertIsNone(self.player.db.dialogue_session)

    def test_named_clear_touches_only_its_own_npc(self):
        open_or_refresh_dialogue(self.player, self.host, "第一句")
        self.assertFalse(clear_dialogue_session(self.player, npc=self.other))
        self.assertIsNotNone(live_dialogue_session(self.player))
        self.assertTrue(clear_dialogue_session(self.player, npc=self.host))
        self.assertIsNone(self.player.db.dialogue_session)

    def test_clear_without_a_session_is_a_noop(self):
        self.assertFalse(clear_dialogue_session(self.player))
        self.assertFalse(clear_dialogue_session(self.player, npc=self.host))

    def test_stale_dbid_is_never_live(self):
        # A dbid that never resolves (a deleted object): not live, and the
        # helper reports without repairing — the value stays for the next
        # clear seam or talk to retire. The host is parked elsewhere so its
        # despawn hook never sees this player's session.
        ghost = create_object(NPC, key="已消失的宿主", location=self.away)
        self.player.db.dialogue_session = {
            "npc_id": int(ghost.pk),
            "line": "公會欢迎你。",
            "updated_tick": None,
        }
        ghost.delete()
        self.assertIsNone(live_dialogue_session(self.player))
        self.assertIsNotNone(self.player.db.dialogue_session)
        # A present host outside the character's location: the co-location
        # gate reports the session not live without touching the value.
        self.player.db.dialogue_session = {
            "npc_id": int(self.host.pk),
            "line": "公會欢迎你。",
            "updated_tick": None,
        }
        self.player.location = self.away
        self.assertIsNone(live_dialogue_session(self.player))
        self.assertIsNotNone(self.player.db.dialogue_session)


class DialogueSessionClearSeamTests(BattlefieldIsolation, EvenniaTest):
    """The movement/engage/departure seams retire the session.

    ``BattlefieldIsolation`` keeps the ``engage`` case's skip-safety
    registration out of the shared registry for later tests.
    """

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="clear seam player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.host = create_object(NPC, key="公會職員", location=self.room1)
        self.other = create_object(NPC, key="路人", location=self.room1)
        self.away = create_object(Room, key="別處", location=None)

    def _open(self):
        open_or_refresh_dialogue(self.player, self.host, "公會欢迎你。")

    def test_settled_movement_clears_the_session(self):
        self._open()
        settle_movement(
            self.player,
            self.room1,
            traverse=lambda: self.player.move_to(self.away) or True,
            destination=self.away,
        )
        self.assertIs(self.player.location, self.away)
        self.assertIsNone(self.player.db.dialogue_session)

    def test_unsuccessful_movement_keeps_the_session(self):
        self._open()
        with self.assertRaises(RuntimeError):
            settle_movement(
                self.player,
                self.room1,
                traverse=lambda: (_ for _ in ()).throw(RuntimeError("move failed")),
            )
        self.assertIs(self.player.location, self.room1)
        self.assertIsNotNone(self.player.db.dialogue_session)

    def test_engage_clears_the_session(self):
        monster = create_object(Monster, key="哥布林")
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.location = self.room1
        self._open()
        engage(self.player, monster)
        self.assertIsNone(self.player.db.dialogue_session)

    def test_npc_leave_room_clears_sessions_naming_it(self):
        self._open()
        other_player = create_object(PlayerCharacter, key="鄰居")
        other_player.race = "human"
        other_player.apply_race_baseline()
        other_player.location = self.room1
        open_or_refresh_dialogue(other_player, self.other, "另一段對話")
        # The departure fan-out rides transaction.on_commit (settlement-
        # rollback safety); the capture seam executes it as a committed
        # transaction would.
        with self.captureOnCommitCallbacks(execute=True):
            self.host.move_to(self.away)
        self.assertIsNone(self.player.db.dialogue_session)
        # Another host's session in the same room is untouched.
        self.assertIsNotNone(other_player.db.dialogue_session)

    def test_rolled_back_companion_departure_never_clears(self):
        """The on_commit deferral is what settlement rollback-safety demands.

        A companion's follow-move runs INSIDE the player's movement
        settlement transaction. When the settlement fails and compensates,
        the NPC relocation rolls back at the DB layer but the session
        attribute cache does not roll back with it — so the clear may only
        run after the departure commits.
        """
        from django.db import transaction

        join_party(self.host, self.player)
        self._open()
        with transaction.atomic():
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                follow_companions(self.player, self.room1, destination=self.away)
            self.assertNotEqual(
                callbacks, [], "a companion departure registers the clear"
            )
            transaction.set_rollback(True)
        self.assertIsNotNone(self.player.db.dialogue_session)

    def test_npc_despawn_clears_the_session(self):
        self._open()
        with self.captureOnCommitCallbacks(execute=True):
            self.host.delete()
        self.assertIsNone(self.player.db.dialogue_session)

    def test_leave_party_clears_the_session(self):
        join_party(self.host, self.player)
        self._open()
        leave_party(self.host, self.player, "dismissed")
        self.assertIsNone(self.player.db.dialogue_session)


class TalkCommandSessionWriterTests(EvenniaCommandTestMixin, EvenniaTest):
    """The ``talk`` command's scripted branch is a session writer."""

    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.hall = create_object(Room, key="guild hall")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="公會職員", location=self.hall)
        self.staff.components.add(
            ScriptedDialogue.create(self.staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )

    def test_scripted_keyword_records_the_delivered_authored_line(self):
        from commands.talk import CmdsTalk

        output = self.call(CmdsTalk(), "公會職員 公會")
        stored = self.char1.db.dialogue_session
        self.assertIsNotNone(stored)
        self.assertEqual(stored["npc_id"], int(self.staff.pk))
        self.assertEqual(
            stored["line"], table_response(GUILD_STAFF_DIALOGUE_KEY, "公會")
        )
        self.assertIn(stored["line"], output)

    def test_greeting_path_never_touches_the_session(self):
        from commands.talk import CmdsTalk

        output = self.call(CmdsTalk(), "公會職員")
        self.assertIn(greeting_for(self.staff), output)
        self.assertIsNone(self.char1.db.dialogue_session)

    def test_offline_scripted_dialogue_drives_the_whole_session(self):
        from commands.talk import CmdsTalk

        with override_settings(LLM_PROFILES=_all_profiles_off()):
            self.call(CmdsTalk(), "公會職員 公會")
            first = self.char1.db.dialogue_session
            self.assertIsNotNone(first)
            self.call(CmdsTalk(), "公會職員 任務")
            refreshed = self.char1.db.dialogue_session
            self.assertEqual(refreshed["npc_id"], int(self.staff.pk))
            self.assertNotEqual(refreshed["line"], first["line"])
            settle_movement(
                self.char1,
                self.hall,
                traverse=lambda: self.char1.move_to(self.room1) or True,
                destination=self.room1,
            )
            self.assertIsNone(self.char1.db.dialogue_session)
