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

    def _waiting_companion(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="draft companion", location=self.room)
        companion.race = self.player.race
        companion.apply_race_baseline()
        join_party(companion, self.player)
        return companion

    def test_round_start_declaration_is_projected_and_skips_the_ordinary_request(self):
        from dataclasses import replace

        from world.rules.combat_session import confirm_actor_command, reconstruct_battlefield
        from world.rules.combat_session.rounds import (
            _draft_requests,
            _draft_tactical_declarations,
        )

        self._waiting_companion()
        engage(self.player, self.monster)
        session_id = read_session(self.player).session_id
        mp_before = self.player.traits.mp.current
        command = {
            "kind": "tactical",
            "payload": {"tactical_key": "defend", "target_id": None},
        }
        result = confirm_actor_command(self.player, session_id, 0, 0, self.player.pk, command)
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["is_complete"])
        # The declaration costs no resource and advances no time.
        self.assertEqual(self.player.traits.mp.current, mp_before)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        # The declaring actor consumes its selected action: it receives no
        # ordinary round request, and its declaration is projected for
        # activation by run_round.
        self.assertNotIn(self.player.pk, _draft_requests(record, battlefield))
        self.assertEqual(
            _draft_tactical_declarations(record, battlefield),
            {str(self.player.key): "defend"},
        )

        # A taunt entry (owned by the later taunt change) still fails loudly
        # rather than silently consuming the actor's action.
        taunt_record = replace(
            record,
            draft_entries={
                self.player.pk: {
                    "kind": "tactical",
                    "payload": {"tactical_key": "taunt", "target_id": int(self.monster.pk)},
                }
            },
        )
        with self.assertRaises(ValueError):
            _draft_requests(taunt_record, battlefield)

    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
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

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
    def test_receipt_failure_after_terminal_clock_and_clear_restores_round(self):
        from world.rules.combat_session import confirm_actor_command
        from world.rules.combat_session.records import read_session_uncached, write_last_combat_receipt
        from world.rules.clock import get_world_clock

        engage(self.player, self.monster)
        record = read_session(self.player)
        clock = get_world_clock()
        tick = clock.tick
        hp = self.monster.traits.hp.current
        command = {"kind": "skill", "payload": {
            "skill_key": BASIC_ATTACK_KEY, "targets_or_shorthand": [self.monster.pk], "scale": 1.0,
        }}

        def defeat(*args, **kwargs):
            self.monster.traits.hp.current = 0
            return []

        def fail_receipt(actor, receipt):
            write_last_combat_receipt(actor, receipt)
            raise RuntimeError("receipt fault")

        with (
            patch("world.rules.combat_session.rounds.run_round", side_effect=defeat),
            patch("world.rules.combat_session.rounds.write_last_combat_receipt", side_effect=fail_receipt),
            patch("world.rules.combat_session.rounds.log_info") as info,
        ):
            with self.assertRaisesRegex(RuntimeError, "receipt fault"):
                confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, command)
        current = read_session_uncached(self.player)
        self.assertEqual(current.rounds_elapsed, 0)
        self.assertEqual(current.draft_entries[self.player.pk], command)
        self.assertEqual(self.monster.traits.hp.current, hp)
        self.assertEqual(get_world_clock().tick, tick)
        self.assertIsNone(self.player.db.last_combat_receipt)
        self.assertFalse(any(call.args[0] == "combat_round_settled" for call in info.call_args_list))
        with patch("world.rules.combat_session.rounds.run_round", side_effect=defeat):
            result = confirm_actor_command(self.player, record.session_id, 0, current.draft_version, self.player.pk, command)
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(read_session_uncached(self.player))
        self.assertEqual(get_world_clock().tick, tick + 6)
        duplicate = confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, command)
        self.assertEqual(duplicate["reason"], "already_committed")
        self.assertEqual(get_world_clock().tick, tick + 6)

    @covers_requirement("player-combat-session::execution-time-invalidation-loses-only-the-selected-action-opportunity")
    def test_earlier_defeat_invalidates_selected_spell_without_retarget_or_cost(self):
        from world.rules.combat_session import engage_group, submit_player_action
        from world.rules.tests.combat_fixtures import grant_lineage
        from world.tests.synthetic_data import SYNTH_SKILLS
        from world.rules.combat.rounds import _end_of_round_upkeep

        companion = self._waiting_companion()
        spell = SYNTH_SKILLS["t_ember_burst"].key
        grant_lineage(companion, [spell])
        companion.traits.mp.current = 50
        self.monster.traits.hp.current = 1
        survivor = _monster("untouched foe", hp=1000)
        survivor.location = self.room
        engage_group(self.player, [self.monster, survivor])
        partial = submit_player_action(self.player, spell, [self.monster], commanded_actor=companion)
        self.assertEqual(partial["outcome"], "draft")
        mp = companion.traits.mp.current
        survivor_hp = survivor.traits.hp.current
        with (
            patch("world.rules.combat.rounds.roll_initiative", return_value=[
                self.player.key, companion.key, self.monster.key, survivor.key,
            ]),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.action.gates.roll_d100", return_value=100),
            patch("world.rules.combat_session.policies._enemy_policy", return_value=None),
            patch("world.rules.combat.rounds._end_of_round_upkeep", wraps=_end_of_round_upkeep) as upkeep,
        ):
            result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(self.monster.traits.hp.current, 0)
        self.assertEqual(survivor.traits.hp.current, survivor_hp)
        self.assertEqual(companion.traits.mp.current, mp)
        self.assertEqual(upkeep.call_count, 1)
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    @covers_requirement("player-combat-session::execution-time-invalidation-loses-only-the-selected-action-opportunity")
    def test_valid_spell_miss_pays_cost_and_consumes_one_round(self):
        from world.rules.combat_session import submit_player_action
        from world.rules.tests.combat_fixtures import grant_lineage
        from world.tests.synthetic_data import SYNTH_SKILLS

        spell = SYNTH_SKILLS["t_ember_burst"].key
        grant_lineage(self.player, [spell])
        self.player.traits.mp.current = 50
        engage(self.player, self.monster)
        hp = self.monster.traits.hp.current
        mp = self.player.traits.mp.current
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.combat_session.policies._enemy_policy", return_value=None),
        ):
            result = submit_player_action(self.player, spell, [self.monster])
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(self.monster.traits.hp.current, hp)
        self.assertLess(self.player.traits.mp.current, mp)
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    def test_nested_caller_transaction_rejects_before_admission(self):
        from django.db import transaction
        from world.rules.combat_session import confirm_actor_command

        engage(self.player, self.monster)
        record = read_session(self.player)
        with transaction.atomic():
            with self.assertRaisesRegex(RuntimeError, "durable"):
                confirm_actor_command(self.player, record.session_id, 0, 0, self.player.pk, {})
        self.assertEqual(read_session(self.player).draft_version, 0)

    @covers_requirement("player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership")
    def test_companion_out_of_reach_is_dropped_from_required_membership(self):
        """A companion the commander can no longer command is not required.

        Its retained selection must not execute and must not block the round:
        the earlier submission is only an admitted draft, and the confirming
        submission re-derives membership, drops the unreachable companion and
        resolves exactly one round.
        """
        from world.rules.combat_session import submit_player_action

        companion = self._waiting_companion()
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        companion.location = create_object(Room, key="departed companion room")
        with patch("world.rules.combat_session.rounds.run_round", return_value=[]) as run:
            result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result["outcome"], "round")
        current = read_session(self.player)
        self.assertEqual(current.rounds_elapsed, 1)
        self.assertEqual(current.draft_entries, {})
        # The one committed round is the commander's own selection only: the
        # unreachable companion contributed no log and no request.
        self.assertEqual(
            [str(log.actor) for log in result["logs"]],
            [str(self.player.key) for _ in result["logs"]],
        )

    @covers_requirement("player-combat-session::draft-completeness-is-derived-again-from-authoritative-membership")
    def test_retained_entry_that_became_invalid_returns_a_reselection_reason(self):
        """A still-required actor's invalidated entry blocks the round."""
        from world.rules.combat_session import submit_player_action
        from world.rules.tests.combat_fixtures import grant_lineage
        from world.tests.synthetic_data import SYNTH_SKILLS

        spell = SYNTH_SKILLS["t_ember_burst"].key
        companion = self._waiting_companion()
        grant_lineage(companion, [spell])
        companion.traits.mp.current = 50
        engage(self.player, self.monster)
        submit_player_action(self.player, spell, [self.monster], commanded_actor=companion)
        # The companion is still authorized and still required, but its retained
        # spell is no longer affordable, so membership alone cannot complete.
        companion.traits.mp.current = 0
        with patch("world.rules.combat_session.rounds.run_round") as run:
            result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        run.assert_not_called()
        self.assertEqual(result["outcome"], "draft")
        self.assertIn("reason", result["reselection_reasons"][companion.pk])
        self.assertIn(int(companion.pk), result["missing_actors"])
        current = read_session(self.player)
        self.assertEqual(current.rounds_elapsed, 0)
        self.assertIn(self.player.pk, current.draft_entries)

    @covers_requirement("player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits")
    def test_action_locked_commander_alone_leaves_collection_paused(self):
        """An action-forbidden commander is no required actor, so no round runs."""
        from world.rules.combat_session import submit_player_action

        engage(self.player, self.monster)
        with (
            patch(
                "world.rules.combat_session.battlefield.evaluate_combat_modifiers_no_create",
                return_value={"actions_per_turn": 0},
            ),
            patch("world.rules.combat_session.rounds.run_round") as run,
        ):
            result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        run.assert_not_called()
        self.assertEqual(result["outcome"], "draft")
        self.assertTrue(result["empty_required"])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_commit_failed_after_prior_actor_aborts_entire_selected_round(self):
        from types import SimpleNamespace
        from world.rules.action import RejectReason
        from world.rules.combat_session import submit_player_action

        companion = self._waiting_companion()
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        before = self.monster.traits.hp.current

        def resolve(request):
            if request.actor.pk == self.player.pk:
                self.monster.traits.hp.current = before - 1
                return SimpleNamespace(outcome="success", event_log=None, notifications=())
            return SimpleNamespace(
                outcome="rejected", reason=RejectReason.COMMIT_FAILED, detail="injected commit failure"
            )

        with (
            patch("world.rules.combat.rounds.roll_initiative", return_value=[
                self.player.key, companion.key, self.monster.key,
            ]),
            patch("world.rules.combat.rounds.ActionResolver.resolve", side_effect=resolve),
            patch("world.rules.combat.rounds._end_of_round_upkeep") as upkeep,
        ):
            with self.assertRaisesRegex(RuntimeError, "commit_failed"):
                submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        upkeep.assert_not_called()
        self.assertEqual(self.monster.traits.hp.current, before)
        current = read_session(self.player)
        self.assertEqual((current.round_revision, current.rounds_elapsed), (0, 0))
        self.assertEqual(set(current.draft_entries), {self.player.pk, companion.pk})
        self.assertIsNone(self.player.db.last_combat_receipt)

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
        self._waiting_companion()
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
        self.assertEqual(res_ack["receipt"]["round_revision"], 0)

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
        self._waiting_companion()
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
        self._waiting_companion()
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


from django.test import TransactionTestCase


class DurableRoundAdmissionTests(BattlefieldIsolation, TransactionTestCase):
    """Exercise real outer commits and competing connections, without TestCase savepoints."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "skills", "elements", "items", "item_effect_profiles", extra=synth_innate_overlay())
        self.room = create_object(Room, key="durable arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("durable foe")
        self.monster.location = self.room
        engage(self.player, self.monster)
        self.record = read_session(self.player)
        self.command = {"kind": "skill", "payload": {
            "skill_key": BASIC_ATTACK_KEY, "targets_or_shorthand": [self.monster.pk], "scale": 1.0,
        }}

    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
    def test_concurrent_final_confirmations_consume_one_revision(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from world.rules.combat_session import confirm_actor_command
        from world.rules.combat_session.records import read_session_uncached

        barrier = Barrier(2)

        def confirm():
            barrier.wait(timeout=10)
            try:
                return confirm_actor_command(
                    self.player, self.record.session_id, 0, 0, self.player.pk, self.command
                )
            finally:
                connections.close_all()

        with patch("world.rules.combat_session.rounds.run_round", return_value=[]) as run:
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: confirm(), range(2)))
        self.assertEqual(run.call_count, 1)
        self.assertEqual(sum(result["ok"] for result in results), 1)
        self.assertEqual(read_session_uncached(self.player).rounds_elapsed, 1)
        self.assertEqual(read_session_uncached(self.player).round_revision, 1)

    def test_outer_commit_failure_keeps_admission_and_restores_caches(self):
        from django.db import connection
        from world.rules.combat_session import confirm_actor_command
        from world.rules.combat_session.records import read_session_uncached

        commit = connection.commit
        commits = 0
        hp = self.player.traits.hp.current

        def fail_second_commit():
            nonlocal commits
            commits += 1
            if commits == 2:
                raise RuntimeError("outer commit fault")
            return commit()

        def effects(*args, **kwargs):
            self.player.traits.hp.current = hp - 1
            return []

        with (
            patch.object(connection, "commit", side_effect=fail_second_commit),
            patch("world.rules.combat_session.rounds.run_round", side_effect=effects),
        ):
            with self.assertRaisesRegex(RuntimeError, "outer commit fault"):
                confirm_actor_command(self.player, self.record.session_id, 0, 0, self.player.pk, self.command)
        current = read_session_uncached(self.player)
        self.assertEqual(current.draft_entries[self.player.pk], self.command)
        self.assertEqual((current.draft_version, current.rounds_elapsed), (1, 0))
        self.assertEqual(self.player.traits.hp.current, hp)
        self.assertIsNone(self.player.db.last_combat_receipt)

    def test_terminal_receipt_is_readable_by_fresh_process_and_retry_is_safe(self):
        import json
        import subprocess
        from django.db import connection
        from world.rules.combat_session import confirm_actor_command
        from world.rules.clock import get_world_clock

        tick = get_world_clock().tick

        def defeat(*args, **kwargs):
            self.monster.traits.hp.current = 0
            return []

        with patch("world.rules.combat_session.rounds.run_round", side_effect=defeat):
            result = confirm_actor_command(
                self.player, self.record.session_id, 0, 0, self.player.pk, self.command
            )
        self.assertEqual(result["outcome"], "victory")
        # A separate interpreter has no Evennia/idmapper or provider used-set.
        code = (
            "import base64,json,pickle,sqlite3,sys;"
            "db=sqlite3.connect(sys.argv[1]);"
            "row=db.execute("
            "\"SELECT a.db_value FROM objects_objectdb_db_attributes oa "
            "JOIN typeclasses_attribute a ON a.id=oa.attribute_id "
            "WHERE oa.objectdb_id=? AND a.db_key='last_combat_receipt' "
            "AND a.db_category IS NULL\",(int(sys.argv[2]),)).fetchone();"
            "print(json.dumps(pickle.loads(base64.b64decode(row[0]))))"
        )
        child = subprocess.run(
            ["uv", "run", "--locked", "python", "-c", code,
             str(connection.settings_dict["NAME"]), str(self.player.pk)],
            check=True, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(json.loads(child.stdout), result["receipt"])
        self.player.attributes.reset_cache()
        with patch("world.rules.combat_session.rounds.run_round") as run:
            retry = confirm_actor_command(
                self.player, self.record.session_id, 0, 0, self.player.pk, self.command
            )
        run.assert_not_called()
        self.assertEqual(retry["reason"], "already_committed")
        self.assertEqual(get_world_clock().tick, tick + 6)
