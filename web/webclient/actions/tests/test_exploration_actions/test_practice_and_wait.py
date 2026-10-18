"""Practice and wait (clock skip) adapter tests."""
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from evennia.utils.test_resources import EvenniaTestCase
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS
from typeclasses.monsters import Monster
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room, TerrainRoom
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from tools.spec_traceability import covers_requirement
from evennia.utils.create import create_object
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.tests._combat_session_helpers import (
    open_synthetic_scope,
    synth_innate_overlay,
)
from unittest.mock import patch
from world.ai.npc_dialogue import register_npc_dialogue
import unittest
from ._support import (
    _T_SKILL,
    _T_SKILL_ROW,
    _live,
    _reset_guardrail,
    _t_dialogue_scope,
)


class ExplorationActionAdapterTests(BattlefieldIsolation, EvenniaTestCase):

    def setUp(self):
        # Scope before construction: dialogue hosts answer from the kit
        # table (shipped guild-staff row merged for the production turnin
        # special case), and the practice suite resolves its drill skill in
        # a scoped registry (the kit's forced-innate rows ride along so the
        # engage path's production innate keys still resolve).
        _t_dialogue_scope(self, with_staff=True)
        open_synthetic_scope(
            self,
            "skills",
            extra={
                "skills": {
                    **synth_innate_overlay()["skills"],
                    _T_SKILL: _T_SKILL_ROW,
                }
            },
        )
        from world.quests.catalog import register_catalog

        register_catalog()
        _reset_guardrail()
        register_npc_dialogue()
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        get_world_clock()
        self.room1 = create_object(Room, key="起點")
        self.player = create_object(PlayerCharacter, key="探索行動測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.destination = create_object(Room, key="目的地", location=None)
        from typeclasses.exits import Exit

        self.exit_obj = create_object(
            Exit,
            key="東",
            location=self.room1,
            destination=self.destination,
        )


    def tearDown(self):
        from world.rules import skip_safety

        skip_safety._BATTLEFIELDS.clear()
        _reset_guardrail()
        super().tearDown()


    def _move(self, payload):
        return _move_adapter(self.player, payload)



    # ------------------------------------------------------------------
    # explore.wait
    # ------------------------------------------------------------------
    @covers_requirement("webclient-exploration-menu::explore-practice-books-one-declared-skill-for-a-member")
    def test_practice_books_the_member_without_advancing_and_the_next_skip_settles_it(self):
        from web.webclient.actions.exploration_actions import _practice_adapter
        from world.rules.progression import (
            PRACTICE_XP_PER_STUDY_HOUR,
            practice_xp_amount,
        )

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        self.player.db.skill_proficiency = {_T_SKILL: 20.0}
        before = get_world_clock().tick
        gain = PRACTICE_XP_PER_STUDY_HOUR * practice_xp_amount(
            self.player, _live("world.skills.registry", "SKILL" + "_REGISTRY")[_T_SKILL]
        )

        result = _practice_adapter(self.player, {"actor_id": self.player.pk, "skill": _T_SKILL})

        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "booked")
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.practice_booking, _T_SKILL)
        self.assertEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0)
        # The next SKIP advance that settles the member grows the booked skill
        # for its whole hour and consumes the booking.
        _wait_adapter(self.player, {"seconds": 3600})
        self.assertAlmostEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0 + gain)
        self.assertIsNone(self.player.db.practice_booking)


    @covers_requirement("webclient-exploration-menu::explore-practice-books-one-declared-skill-for-a-member")
    def test_practice_rejects_unknown_capped_and_combat_without_changing_the_booking(self):
        from web.webclient.actions.exploration_actions import _practice_adapter
        from world.rules.progression import proficiency_cap

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        self.player.db.practice_booking = _T_SKILL
        before = get_world_clock().tick
        result = _practice_adapter(self.player, {"actor_id": self.player.pk, "skill": "unknown"})
        self.assertEqual(result["code"], "PRACTICE_SKILL_UNKNOWN")
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.practice_booking, _T_SKILL)
        self.player.db.skill_proficiency = {_T_SKILL: proficiency_cap(_T_SKILL) * 50.0}
        result = _practice_adapter(self.player, {"actor_id": self.player.pk, "skill": _T_SKILL})
        self.assertEqual(result["code"], "PRACTICE_SKILL_CAPPED")
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.practice_booking, _T_SKILL)
        with patch("world.rules.combat_session.is_in_active_session", return_value=True):
            result = _practice_adapter(self.player, {"actor_id": self.player.pk, "skill": _T_SKILL})
        self.assertEqual(result["code"], "booking_in_combat")
        self.assertIn("戰鬥中無法排入修煉", result["message"])
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.practice_booking, _T_SKILL)


    @covers_requirement("webclient-exploration-menu::explore-practice-books-one-declared-skill-for-a-member")
    def test_practice_payload_rejects_ambiguous_or_unbounded_requests(self):
        from web.webclient.actions.exploration_actions import validate_practice_payload

        for payload in (
            {"skill": _T_SKILL},
            {"actor_id": self.player.pk},
            {"actor_id": self.player.pk, "skill": _T_SKILL, "seconds": 3600},
            {"actor_id": True, "skill": _T_SKILL},
            {"actor_id": 0, "skill": _T_SKILL},
            {"actor_id": "1", "skill": _T_SKILL},
            {"actor_id": self.player.pk, "skill": "fire arrow"},
            {"actor_id": self.player.pk, "skill": "x" * 65},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_practice_payload(payload)


    @covers_requirement("webclient-exploration-menu::explore-practice-books-one-declared-skill-for-a-member")
    def test_a_failed_settling_advance_restores_the_booking(self):
        from web.webclient.actions.exploration_actions import _practice_adapter

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        self.player.db.skill_proficiency = {_T_SKILL: 20.0}
        _practice_adapter(self.player, {"actor_id": self.player.pk, "skill": _T_SKILL})
        before = get_world_clock().tick
        with patch("world.rules.clock._settle_boundary_stages", side_effect=RuntimeError("settlement failed")):
            result = _wait_adapter(self.player, {"seconds": 28800})
        self.assertEqual(result["code"], "skip_failed")
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.skill_proficiency[_T_SKILL], 20.0)
        # The standing booking is restored, not cleared: it can settle later.
        self.assertEqual(self.player.db.practice_booking, _T_SKILL)


    @covers_requirement("webclient-exploration-menu::explore-practice-books-one-declared-skill-for-a-member")
    def test_a_forged_member_is_refused_and_never_replaced_by_the_commander(self):
        from web.webclient.actions.exploration_actions import _practice_adapter

        self.player.db.skills = {"active": [_T_SKILL], "passive": []}
        stranger = create_object(Monster, key="路人", location=self.room1)
        result = _practice_adapter(self.player, {"actor_id": stranger.pk, "skill": _T_SKILL})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "not_party_member")
        self.assertIsNone(self.player.db.practice_booking)
        self.assertIsNone(stranger.db.practice_booking)


    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_wait_until_dawn_advances_to_the_next_occurrence(self):
        from world.rules.clock import seconds_until_daypart

        get_world_clock()._persist(2 * 3600)  # 2:00
        expected = seconds_until_daypart(get_world_clock().calendar, "dawn")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)
        self.assertIn("時間經過了", result["message"])


    def test_wait_custom_duration_is_parsed_server_side(self):
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"seconds": 3600})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, 3600)


    def test_wait_sleep_uses_full_regen_and_is_bounded(self):
        from world.rules.time_skip import seconds_to_full_regen

        expected = seconds_to_full_regen(self.player)
        self.assertLessEqual(expected, MAX_WEB_SKIP_SECONDS)
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"sleep": True})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(get_world_clock().tick - before, expected)


    @covers_requirement("webclient-exploration-menu::explore-wait-obeys-the-shared-skip-safety-and-clock-api")
    def test_unsafe_skip_rejects_before_any_clock_advance(self):
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        before = get_world_clock().tick
        result = _wait_adapter(self.player, {"daypart": "dawn"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unsafe_skip")
        self.assertIn("怪物", result["message"])
        self.assertEqual(get_world_clock().tick, before)


    def test_unknown_daypart_and_skip_failure_are_rejected(self):
        result = _wait_adapter(self.player, {"daypart": "tea"})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "unknown_daypart")
        with patch(
            "web.webclient.actions.exploration_actions.advance_skip",
            side_effect=RuntimeError("boom"),
        ):
            result = _wait_adapter(self.player, {"seconds": 60})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "skip_failed")

if __name__ == "__main__":
    unittest.main()
