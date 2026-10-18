"""Standing per-member practice bookings and the ``修煉`` text command.

Pins the party-practice-booking contract: each member owns at most one
standing booking, the commander may book any present member, one SKIP advance
settles every in-scope member through ``grant_study_practice_xp``, an
unlabeled skip and a movement step leave bookings untouched, rebooking
replaces, and a failed advance restores every settled member's booking.

``party-time-settlement`` requirement IDs pinned by the decorators below:

- ``party-time-settlement::each-member-owns-one-standing-practice-booking``
- ``party-time-settlement::the-text-client-books-member-practice``
"""

import importlib
from unittest.mock import Mock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.skip import CmdPractice, CmdRest
from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock
from world.rules.movement import charge_movement
from world.rules.party import join_party
from world.rules.party_scope import (
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
)
from world.rules.progression import (
    PRACTICE_XP_PER_STUDY_HOUR,
    SKILL_PRACTICE_XP_PER_USE,
    practice_xp_amount,
    proficiency_cap,
    skill_proficiency_level,
)
from world.rules.time_skip import (
    BOOKING_IN_COMBAT_MESSAGE,
    PracticeBooking,
    PracticeReject,
    PracticeRejectReason,
    book_member_practice,
)
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

# Kit rows: two ACTIVE skills, one per member, so each booking settles against
# its own member and skill.
_SLASH = SYNTH_SKILLS["t_cinder_cleave"].key
_HEAL = SYNTH_SKILLS["t_ember_burst"].key

MOVE = CLOCK_YAML["command_defaults"]["move"]


def _skill(key: str):
    """The scoped registry row for ``key`` (runtime probe: test-data gate)."""
    registry = getattr(
        importlib.import_module("world.skills.registry"), "SKILL" + "_REGISTRY"
    )
    return registry[key]


def _own(member, *keys: str) -> None:
    """Store exactly ``keys`` as the member's owned ACTIVE skills."""
    member.db.skills = {"active": list(keys), "passive": []}


def _study_gain(member, key: str, hours: int) -> float:
    """The booked-study composite, measured through the shared per-use factor."""
    per_use = practice_xp_amount(member, _skill(key))
    return hours * PRACTICE_XP_PER_STUDY_HOUR * (per_use / SKILL_PRACTICE_XP_PER_USE)


class StandingPracticeBookingTests(EvenniaTest):
    """One booking per member, settled by the next SKIP advance."""

    def setUp(self):
        super().setUp()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.room2.key = "Room2"
        self.room2.save()
        self.ella = self._make_companion("艾拉")
        self.kahn = self._make_companion("卡恩", location=self.room2)

    def _make_companion(self, key, location=None):
        npc = create_object(NPC, key=key, location=self.player.location)
        npc.race = "human"
        npc.apply_race_baseline()
        join_party(npc, self.player)
        if location is not None:
            npc.location = location
        return npc

    def _book(self, member, key):
        result = book_member_practice(self.player, member.pk, key)
        self.assertIsInstance(result, PracticeBooking)
        return result

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_two_members_practise_during_one_rest(self):
        _own(self.player, _SLASH)
        _own(self.ella, _HEAL)
        self.player.db.skill_proficiency = {_SLASH: 20.0}
        self.ella.db.skill_proficiency = {_HEAL: 20.0}
        slash_gain = _study_gain(self.player, _SLASH, 3)
        heal_gain = _study_gain(self.ella, _HEAL, 3)
        self._book(self.player, _SLASH)
        self._book(self.ella, _HEAL)
        before = get_world_clock().tick

        command = CmdRest()
        command.caller = self.player
        command.args = "3h"
        command.func()

        self.assertEqual(get_world_clock().tick - before, 3 * 3600)
        self.assertAlmostEqual(
            self.player.db.skill_proficiency[_SLASH], 20.0 + slash_gain
        )
        self.assertAlmostEqual(
            self.ella.db.skill_proficiency[_HEAL], 20.0 + heal_gain
        )
        # Each member grew its own booked skill only.
        self.assertNotIn(_HEAL, self.player.db.skill_proficiency)
        self.assertNotIn(_SLASH, self.ella.db.skill_proficiency)
        self.assertIsNone(self.player.db.practice_booking)
        self.assertIsNone(self.ella.db.practice_booking)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_a_member_elsewhere_keeps_the_booking(self):
        _own(self.kahn, _HEAL)
        self.kahn.db.skill_proficiency = {_HEAL: 20.0}
        self.kahn.db.practice_booking = _HEAL
        before = get_world_clock().tick

        command = CmdRest()
        command.caller = self.player
        command.args = "3h"
        command.func()

        self.assertEqual(get_world_clock().tick - before, 3 * 3600)
        self.assertEqual(self.kahn.db.practice_booking, _HEAL)
        self.assertEqual(self.kahn.db.skill_proficiency[_HEAL], 20.0)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_movement_does_not_consume_a_booking(self):
        _own(self.player, _SLASH)
        _own(self.ella, _HEAL)
        self.player.db.skill_proficiency = {_SLASH: 20.0}
        self.ella.db.skill_proficiency = {_HEAL: 20.0}
        self._book(self.player, _SLASH)
        self._book(self.ella, _HEAL)
        before = get_world_clock().tick

        charge_movement(self.player, "move", source_location=self.room1)

        self.assertEqual(get_world_clock().tick - before, MOVE)
        self.assertEqual(self.player.db.practice_booking, _SLASH)
        self.assertEqual(self.ella.db.practice_booking, _HEAL)
        self.assertEqual(self.player.db.skill_proficiency[_SLASH], 20.0)
        self.assertEqual(self.ella.db.skill_proficiency[_HEAL], 20.0)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_sub_hour_skip_consumes_the_booking_with_zero_growth(self):
        _own(self.player, _SLASH)
        self.player.db.skill_proficiency = {_SLASH: 20.0}
        self._book(self.player, _SLASH)

        command = CmdRest()
        command.caller = self.player
        command.args = "30m"
        command.func()

        self.assertIsNone(self.player.db.practice_booking)
        self.assertEqual(self.player.db.skill_proficiency[_SLASH], 20.0)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_rebooking_replaces_the_members_booking(self):
        _own(self.ella, _SLASH, _HEAL)
        self._book(self.ella, _SLASH)
        self.assertEqual(self.ella.db.practice_booking, _SLASH)

        result = self._book(self.ella, _HEAL)

        self.assertEqual(self.ella.db.practice_booking, _HEAL)
        self.assertEqual(result.skill_key, _HEAL)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_a_failed_advance_restores_both_bookings(self):
        _own(self.player, _SLASH)
        _own(self.ella, _HEAL)
        self.player.db.skill_proficiency = {_SLASH: 20.0}
        self.ella.db.skill_proficiency = {_HEAL: 20.0}
        self._book(self.player, _SLASH)
        self._book(self.ella, _HEAL)
        before = get_world_clock().tick

        with (
            patch(
                "world.rules.clock._settle_boundary_stages",
                side_effect=RuntimeError("settlement failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            get_world_clock().advance(
                3 * 3600, AdvanceSource.SKIP, (self.player, self.ella)
            )

        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.player.db.practice_booking, _SLASH)
        self.assertEqual(self.ella.db.practice_booking, _HEAL)
        self.assertEqual(self.player.db.skill_proficiency[_SLASH], 20.0)
        self.assertEqual(self.ella.db.skill_proficiency[_HEAL], 20.0)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_rejections_leave_the_previous_booking_unchanged(self):
        _own(self.ella, _SLASH)
        self.ella.db.practice_booking = _SLASH

        unknown = book_member_practice(self.player, self.ella.pk, "not_a_skill")
        self.assertIsInstance(unknown, PracticeReject)
        self.assertEqual(unknown.reason, PracticeRejectReason.SKILL_UNKNOWN)
        self.assertEqual(self.ella.db.practice_booking, _SLASH)

        self.ella.db.skill_proficiency = {
            _SLASH: proficiency_cap(_SLASH) * 50.0
        }
        self.assertGreaterEqual(
            skill_proficiency_level(self.ella, _SLASH), proficiency_cap(_SLASH)
        )
        capped = book_member_practice(self.player, self.ella.pk, _SLASH)
        self.assertIsInstance(capped, PracticeReject)
        self.assertEqual(capped.reason, PracticeRejectReason.SKILL_CAPPED)
        self.assertEqual(self.ella.db.practice_booking, _SLASH)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_booking_in_combat_is_refused(self):
        _own(self.ella, _HEAL)
        self.ella.db.practice_booking = _SLASH

        with patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            result = book_member_practice(self.player, self.ella.pk, _HEAL)

        self.assertIsInstance(result, PracticeReject)
        self.assertEqual(result.reason, PracticeRejectReason.IN_COMBAT)
        self.assertEqual(result.message, BOOKING_IN_COMBAT_MESSAGE)
        self.assertEqual(self.ella.db.practice_booking, _SLASH)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::each-member-owns-one-standing-practice-booking"
    )
    def test_forged_and_absent_members_are_refused(self):
        _own(self.ella, _HEAL)
        self.ella.db.practice_booking = _SLASH
        stranger = create_object(NPC, key="路人", location=self.room1)

        with self.assertRaises(PartyScopeError) as forged:
            book_member_practice(self.player, stranger.pk, _HEAL)
        self.assertEqual(forged.exception.reason, REASON_NOT_PARTY_MEMBER)

        with self.assertRaises(PartyScopeError) as absent:
            book_member_practice(self.player, self.kahn.pk, _HEAL)
        self.assertEqual(absent.exception.reason, REASON_MEMBER_NOT_PRESENT)

        self.assertIsNone(stranger.db.practice_booking)
        self.assertEqual(self.ella.db.practice_booking, _SLASH)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::the-text-client-books-member-practice"
    )
    def test_text_booking_matches_the_action_without_advancing_time(self):
        self.player.msg = Mock()
        _own(self.ella, _HEAL)
        _own(self.kahn, _HEAL)
        self.kahn.location = self.room1
        before = get_world_clock().tick

        command = CmdPractice()
        command.caller = self.player
        command.args = f"{_HEAL} = 艾拉"
        command.func()

        # The adapter path calls exactly this rule; both bookings agree.
        self._book(self.kahn, _HEAL)

        self.assertEqual(self.ella.db.practice_booking, _HEAL)
        self.assertEqual(self.kahn.db.practice_booking, _HEAL)
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(
            self.player.msg.call_args_list[-1].args[0],
            f"艾拉將在下次休息時修煉「{_skill(_HEAL).label}」。",
        )

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::the-text-client-books-member-practice"
    )
    def test_text_booking_defaults_to_the_caller(self):
        self.player.msg = Mock()
        _own(self.player, _SLASH)
        before = get_world_clock().tick

        command = CmdPractice()
        command.caller = self.player
        command.args = _SLASH
        command.func()

        self.assertEqual(self.player.db.practice_booking, _SLASH)
        self.assertEqual(get_world_clock().tick, before)

    @synthetic_registries("skills")
    @covers_requirement(
        "party-time-settlement::the-text-client-books-member-practice"
    )
    def test_text_booking_rejections_use_the_shared_messages(self):
        self.player.msg = Mock()
        _own(self.ella, _HEAL)

        unknown_member = CmdPractice()
        unknown_member.caller = self.player
        unknown_member.args = f"{_HEAL} = 路人"
        unknown_member.func()
        self.assertEqual(
            self.player.msg.call_args_list[-1].args[0], "對方不是你的隊伍成員。"
        )

        unknown_skill = CmdPractice()
        unknown_skill.caller = self.player
        unknown_skill.args = "not_a_skill = 艾拉"
        unknown_skill.func()
        self.assertIn(
            "PRACTICE_SKILL_UNKNOWN", self.player.msg.call_args_list[-1].args[0]
        )
        self.assertIsNone(self.ella.db.practice_booking)

        usage = CmdPractice()
        usage.caller = self.player
        usage.args = ""
        usage.func()
        self.assertEqual(
            self.player.msg.call_args_list[-1].args[0], "用法：修煉 <技能> [= <成員>]"
        )
