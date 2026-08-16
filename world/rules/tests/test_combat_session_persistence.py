"""Combat-session persistence tests: records, ids, and reconnect/restore."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    engage,
    forfeit,
    from_storage,
    is_in_active_session,
    read_session,
    restore_active_session,
    session_id_for,
    to_storage,
)

from ._combat_session_helpers import BattlefieldIsolation, _monster, _player


class CombatSessionRecordTests(unittest.TestCase):
    def test_record_round_trips_through_json(self):
        record = from_storage(
            {
                "session_id": "hostile:1:0",
                "mode": "hostile",
                "room_id": 5,
                "player_ids": [1],
                "enemy_ids": [2],
                "fled_ids": [],
                "knocked_out_ids": [],
                "rounds_elapsed": 0,
                "exam_id": None,
            }
        )
        self.assertEqual(record.session_id, "hostile:1:0")
        self.assertEqual(to_storage(record)["room_id"], 5)

    def test_settled_tick_is_optional_and_round_trips(self):
        base = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 5,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        # Older durable records without the marker stay valid (default None).
        self.assertIsNone(from_storage(base).settled_tick)
        marked = from_storage({**base, "settled_tick": 42})
        self.assertEqual(marked.settled_tick, 42)
        self.assertEqual(to_storage(marked)["settled_tick"], 42)

    def test_malformed_records_fail_closed(self):
        base = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 5,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        bad_cases = [
            {"session_id": ""},
            {"mode": "unknown"},
            {"player_ids": "nope"},
            {"player_ids": [1, 1]},
            {"player_ids": [1, 2]},
            {"rounds_elapsed": -1},
            {"fled_ids": [99]},
            {"exam_id": None, "mode": "guild_exam"},
            {"settled_tick": "six"},
            {"settled_tick": -1},
        ]
        for mutation in bad_cases:
            data = {**base, **mutation}
            with self.subTest(data=data):
                with self.assertRaises(CombatSessionError):
                    from_storage(data)

class CombatSessionIdTests(EvenniaTest):
    def test_deterministic_session_ids(self):
        player = _player()
        with patch("world.rules.clock.get_world_clock", return_value=WorldClock(42)):
            self.assertEqual(session_id_for(player, "hostile"), f"hostile:{player.pk}:42")

class SessionPersistenceTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="battlefield room")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("persist goblin")
        self.monster.location = self.room

    def test_disconnect_reconnect_resumes_same_session(self):
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        # Simulate reconnect by clearing transient skip-safety and re-reading.
        from world.rules.skip_safety import _BATTLEFIELDS

        _BATTLEFIELDS.clear()
        restore_active_session(self.player)
        restored = read_session(self.player)
        self.assertEqual(restored.session_id, session_id)
        self.assertEqual(restored.rounds_elapsed, 0)

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_deleted_enemy_does_not_strand_player(self):
        engage(self.player, self.monster)
        self.monster.delete()
        restore_active_session(self.player)
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_exit_traversal_is_blocked_during_combat(self):
        engage(self.player, self.monster)
        other = create_object(Room, key="elsewhere")
        self.assertFalse(self.player.move_to(other))
        self.assertIs(self.player.location, self.room)
        self.assertTrue(is_in_active_session(self.player))

    def test_forfeit_cleans_session(self):
        engage(self.player, self.monster)
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))
