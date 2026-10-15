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
    BASIC_ATTACK_KEY,
    to_storage,
)

from ._combat_session_helpers import BattlefieldIsolation, _monster, _player
from ._combat_session_helpers import open_synthetic_scope, synth_innate_overlay


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
                "round_revision": 0,
                "draft_version": 0,
                "draft_entries": {},
                "confirmed_actors": [],
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
            "round_revision": 0,
            "draft_version": 0,
            "draft_entries": {},
            "confirmed_actors": [],
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
            "round_revision": 0,
            "draft_version": 0,
            "draft_entries": {},
            "confirmed_actors": [],
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
            {"round_revision": -1},
            {"draft_version": -1},
            {"round_revision": "zero"},
            {"draft_entries": "not a dict"},
            {"draft_entries": {1: {"kind": "unknown", "payload": {}}}},
            {"draft_entries": {1: {"kind": "skill", "payload": {"skill_key": "s", "targets_or_shorthand": "bad", "scale": 1.0}}}},
            {"draft_entries": {1: {"kind": "skill", "payload": {"skill_key": "s", "targets_or_shorthand": [1], "scale": float("inf")}}}},
            {"draft_entries": {99: {"kind": "tactical", "payload": {"tactical_key": "defend", "target_id": None}}}},
            {"confirmed_actors": [99]},
            {"confirmed_actors": "nope"},
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
        open_synthetic_scope(self, "skills", "elements", "items", "item_effect_profiles", extra=synth_innate_overlay())
        super().setUp()
        self.room = create_object(Room, key="battlefield room")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("persist goblin")
        self.monster.location = self.room

    def test_final_confirmation_commits_once_and_clears_draft(self):
        from world.rules.combat_session import confirm_actor_command
        engage(self.player, self.monster)
        record = read_session(self.player)
        command = {"kind": "skill", "payload": {
            "skill_key": BASIC_ATTACK_KEY, "targets_or_shorthand": [self.monster.pk], "scale": 1.0,
        }}
        with patch("world.rules.combat_session.rounds.run_round", return_value=[] ) as run:
            result = confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, command)
            duplicate = confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, command)
        self.assertTrue(result["ok"])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(duplicate["reason"], "stale_round_revision")
        current = read_session(self.player)
        self.assertEqual((current.round_revision, current.rounds_elapsed), (1, 1))
        self.assertEqual(current.draft_entries, {})
        self.assertEqual(result["receipt"]["round_revision"], 0)

    def test_technical_failure_preserves_accepted_final_draft(self):
        from world.rules.combat_session import confirm_actor_command
        engage(self.player, self.monster)
        record = read_session(self.player)
        command = {"kind": "skill", "payload": {
            "skill_key": BASIC_ATTACK_KEY, "targets_or_shorthand": [self.monster.pk], "scale": 1.0,
        }}
        with patch("world.rules.combat_session.rounds.run_round", side_effect=RuntimeError("fault")):
            with self.assertRaisesRegex(RuntimeError, "fault"):
                confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, command)
        current = read_session(self.player)
        self.assertEqual((current.round_revision, current.rounds_elapsed, current.draft_version), (0, 0, 1))
        self.assertEqual(current.draft_entries[self.player.pk], command)
        self.assertIsNone(self.player.db.last_combat_receipt)
        with patch("world.rules.combat_session.rounds.run_round", return_value=[]):
            result = confirm_actor_command(self.player, record.session_id, 0, 1, self.player.pk, command)
        self.assertTrue(result["ok"])
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

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

    @covers_requirement("player-combat-session::confirmed-round-selections-persist-as-one-editable-session-draft")
    def test_confirmed_round_selections_persist_and_replace_earlier_selection(self):
        from world.rules.combat_session import confirm_actor_command
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        cmd1 = {
            "kind": "skill",
            "payload": {
                "skill_key": BASIC_ATTACK_KEY,
                "targets_or_shorthand": [self.monster.pk],
                "scale": 1.0,
            },
        }
        res1 = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd1)
        self.assertTrue(res1["ok"])
        self.assertEqual(res1["draft_version"], 1)
        self.assertIn(self.player.pk, res1["draft_entries"])
        self.assertEqual(res1["draft_entries"][self.player.pk]["payload"]["skill_key"], BASIC_ATTACK_KEY)

        # Re-read from storage
        rec = read_session(self.player)
        self.assertEqual(rec.draft_version, 1)
        self.assertEqual(rec.draft_entries[self.player.pk]["payload"]["skill_key"], BASIC_ATTACK_KEY)

        # Replace with tactical defend
        cmd2 = {
            "kind": "tactical",
            "payload": {
                "tactical_key": "defend",
                "target_id": None,
            },
        }
        res2 = confirm_actor_command(self.player, session_id, 0, 1, self.player.pk, cmd2)
        self.assertTrue(res2["ok"])
        self.assertEqual(res2["draft_version"], 2)
        self.assertEqual(res2["draft_entries"][self.player.pk]["payload"]["tactical_key"], "defend")
        # No rounds or time elapsed
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement("player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership")
    def test_draft_completeness_and_membership_change_guard(self):
        from world.rules.combat_session import confirm_actor_command, preflight_draft_entries, reconstruct_battlefield
        from world.rules.party import join_party
        from typeclasses.npcs import NPC

        companion = create_object(NPC, key="戰士同伴", location=self.player.location)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.current = 100
        join_party(companion, self.player)

        engage(self.player, self.monster)
        rec = read_session(self.player)
        session_id = rec.session_id
        self.assertIn(companion.pk, rec.player_ids)

        # Player confirms attack
        cmd_player = {
            "kind": "skill",
            "payload": {
                "skill_key": BASIC_ATTACK_KEY,
                "targets_or_shorthand": [self.monster.pk],
                "scale": 1.0,
            },
        }
        res = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd_player)
        self.assertEqual(res.get("ok"), True, res)
        self.assertTrue(res["ok"])
        self.assertFalse(res["is_complete"])
        self.assertEqual(res["missing_actors"], (companion.pk,))

        # Companion becomes incapacitated / knocked out while choices are collected (roster shrink)
        companion.traits.hp.current = 0
        # Preflight shows required set changed
        bf = reconstruct_battlefield(self.player, read_session(self.player))
        pre = preflight_draft_entries(self.player, read_session(self.player), bf)
        # Even though player is already selected, membership change requires explicit confirmation!
        self.assertTrue(pre["membership_changed"])
        self.assertFalse(pre["is_complete"])

        # Fresh confirmation acknowledges new required set
        res_ack = confirm_actor_command(self.player, session_id, 0, 1, self.player.pk, cmd_player)
        self.assertTrue(res_ack["ok"])
        self.assertTrue(res_ack["is_complete"])

    @covers_requirement("player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership")
    def test_resource_or_capability_change_produces_reselection_reasons(self):
        from world.rules.combat_session import confirm_actor_command
        from world.rules.party import join_party
        from world.rules.tests.combat_fixtures import grant_lineage
        from typeclasses.npcs import NPC
        from world.tests.synthetic_data import make_skill

        companion = create_object(NPC, key="小隊法師", location=self.player.location)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.current = 100
        from world.tests.synthetic_data import SYNTH_SKILLS
        spell_key = SYNTH_SKILLS["t_ember_burst"].key

        self.player.traits.mp.current = 30
        grant_lineage(self.player, [spell_key])
        join_party(companion, self.player)

        engage(self.player, self.monster)
        rec = read_session(self.player)
        session_id = rec.session_id
        # Grant spell to player
        grant_lineage(self.player, [spell_key])

        cmd_spell = {
            "kind": "skill",
            "payload": {
                "skill_key": spell_key,
                "targets_or_shorthand": [self.monster.pk],
                "scale": 1.0,
            },
        }
        res1 = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd_spell)
        self.assertEqual(res1.get("ok"), True, res1)
        self.assertTrue(res1["ok"])
        self.assertIn(self.player.pk, res1["draft_entries"])

        # Player MP drops before second member confirms
        self.player.traits.mp.current = 5

        cmd_comp = {
            "kind": "tactical",
            "payload": {"tactical_key": "defend", "target_id": None},
        }
        res2 = confirm_actor_command(self.player, session_id, 0, 1, companion.pk, cmd_comp)
        self.assertTrue(res2["ok"])
        # Player entry became invalid due to insufficient MP
        self.assertIn(self.player.pk, res2["reselection_reasons"])
        self.assertIn(companion.pk, res2["draft_entries"])
        self.assertFalse(res2["is_complete"])

    @covers_requirement("player-combat-session::draft-editing-has-a-separate-stale-write-version")
    def test_concurrent_cas_draft_version_rejection(self):
        from world.rules.combat_session import confirm_actor_command
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id

        cmd = {
            "kind": "tactical",
            "payload": {"tactical_key": "defend", "target_id": None},
        }
        # Request 1 commits draft_version 0 -> 1
        res1 = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd)
        self.assertTrue(res1["ok"])
        self.assertEqual(res1["draft_version"], 1)

        # Request 2 also sent with stale draft_version 0
        res2 = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd)
        self.assertFalse(res2["ok"])
        self.assertEqual(res2["reason"], "stale_draft_version")
        self.assertEqual(res2["current_draft_version"], 1)

        # Stale round_revision rejection
        res3 = confirm_actor_command(self.player, session_id, 99, 1, self.player.pk, cmd)
        self.assertFalse(res3["ok"])
        self.assertEqual(res3["reason"], "stale_round_revision")

    @covers_requirement("player-combat-session::reconnect-and-restart-restore-confirmed-selection-progress-without-execution")
    def test_reconnect_and_restart_restore_draft_without_advancing_combat(self):
        from world.rules.combat_session import confirm_actor_command, restore_active_session
        from world.rules.party import join_party
        from typeclasses.npcs import NPC

        companion = create_object(NPC, key="留守同伴", location=self.player.location)
        companion.race = "human"
        companion.apply_race_baseline()
        companion.traits.hp.current = 100
        join_party(companion, self.player)

        engage(self.player, self.monster)
        rec = read_session(self.player)
        session_id = rec.session_id

        cmd = {
            "kind": "tactical",
            "payload": {"tactical_key": "defend", "target_id": None},
        }
        confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd)

        # Simulate server restart / reconnect
        from world.rules.skip_safety import _BATTLEFIELDS
        _BATTLEFIELDS.clear()
        restore_active_session(self.player)

        restored = read_session(self.player)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.session_id, session_id)
        self.assertEqual(restored.rounds_elapsed, 0)
        self.assertEqual(restored.round_revision, 0)
        self.assertEqual(restored.draft_version, 1)
        self.assertIn(self.player.pk, restored.draft_entries)
        self.assertNotIn(companion.pk, restored.draft_entries)

    @covers_requirement("player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits")
    def test_no_eligible_actors_collection_paused_and_party_exits(self):
        from world.rules.combat_session import preflight_draft_entries, reconstruct_battlefield
        engage(self.player, self.monster)
        # Mark player incapacitated / action-forbidden (actions_per_turn = 0)
        from world.rules.buffs import apply_buff
        apply_buff(self.player, "paralysis")

        rec = read_session(self.player)
        bf = reconstruct_battlefield(self.player, rec)
        pre = preflight_draft_entries(self.player, rec, bf)
        self.assertTrue(pre["empty_required"])
        self.assertEqual(pre["reason"], "no_eligible_actors")
        self.assertFalse(pre["is_complete"])

        # Confirmed forfeit / surrender remains available
        res = forfeit(self.player)
        self.assertEqual(res["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::free-inspection-and-equipment-operations-do-not-select-round-commands")
    def test_equipment_toggle_invalidates_draft_version(self):
        from world.rules.combat_session import confirm_actor_command
        from world.rules.equipment import toggle_equipment
        from world.tests.synthetic_data import SYNTH_ITEMS
        self.player.db.equipment = None
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        cmd = {
            "kind": "tactical",
            "payload": {"tactical_key": "defend", "target_id": None},
        }
        confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, cmd)
        rec = read_session(self.player)
        self.assertEqual(rec.draft_version, 1)

        # Free equipment operation
        eq_key = SYNTH_ITEMS["t_thorn_knife"].key
        self.player.db.inventory = [eq_key]
        toggle_res = toggle_equipment(self.player, eq_key)
        self.assertEqual(toggle_res.outcome, "success", toggle_res)
        # Draft version was incremented to trigger revalidation
        rec_after = read_session(self.player)
        self.assertGreater(rec_after.draft_version, 1)

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
