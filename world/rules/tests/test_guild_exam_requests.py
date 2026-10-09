"""Presence-first guild examination request coordinator (decision table).

Synthetic counter, candidate and branch-qualified persistent host only. Every
rejection and every schedule answer is asserted against deterministic
before/after snapshots of the candidate and the host; the started branch is
the authoritative ``start_guild_exam`` path.
"""

from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.combat_session import read_session
from world.rules.exam_schedule_holds import begin_exam_schedule_hold
from world.rules.guild_exam_request import (
    OUTCOME_SCHEDULE,
    OUTCOME_STARTED,
    next_exam_rank,
    request_guild_exam,
)
from world.rules.guild_exams import ExamReason, ExamState, GuildExamError
from world.rules.npc_schedules import set_npc_schedule
from world.rules.service_windows import read_next_planned_service_interval
from world.rules.tests.test_guild_exams import EXAM_BRANCH, ExamHostFixture

_HOUR = 3600
_ARRIVE = 10 * _HOUR
_LEAVE = 14 * _HOUR


class ExamRequestCoordinatorTests(ExamHostFixture, EvenniaTestCase):
    """The shared request order: target, presence, then authoritative start."""

    def setUp(self):
        super().setUp()
        self.home = create_object(Room, key="host lodging")

    def _send_host_home_on_weekly_visits(self):
        """Absent host whose weekly schedule visits the hall [10:00, 14:00)."""
        self.host.location = self.home
        set_npc_schedule(self.host, {
            "schema_version": 1,
            "cycle_days": 7,
            "entries": [
                {"tick_offset": _ARRIVE, "kind": "move", "target": f"#{self.hall.pk}"},
                {"tick_offset": _LEAVE, "kind": "move", "target": f"#{self.home.pk}"},
            ],
        })

    def _snapshot(self):
        return {
            "actor": self._actor_state(),
            "host": self._host_state(),
            "host_schedule": (self.host.db.schedule, self.host.db.schedule_state),
            "affinity": self.host.relations.has_record(self.player),
            "objects": ObjectDB.objects.count(),
            "tick": self.clock.tick,
        }

    def _assert_rejected_unchanged(self, reason, **kwargs):
        before = self._snapshot()
        with self.assertRaises(GuildExamError) as ctx:
            request_guild_exam(self.player, kwargs.pop("target", "E"), requested_by="command", **kwargs)
        self.assertEqual(ctx.exception.args[0], reason)
        self.assertEqual(self._snapshot(), before)
        return ctx.exception

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_absent_host_below_merit_returns_planned_attendance_without_mutation(self):
        self._send_host_home_on_weekly_visits()
        before = self._snapshot()
        with patch("world.rules.guild_exam_request.start_guild_exam") as start:
            outcome = request_guild_exam(self.player, "E", requested_by="webclient")
        start.assert_not_called()
        self.assertEqual(outcome.kind, OUTCOME_SCHEDULE)
        self.assertEqual((outcome.target_rank, outcome.host_name), ("E", self.host.key))
        self.assertIsNone(outcome.record)
        expected = read_next_planned_service_interval(self.host, self.hall)
        self.assertEqual(outcome.interval, expected.interval)
        self.assertEqual(
            (outcome.interval.start_tick % (7 * 24 * _HOUR), outcome.interval.end_tick - outcome.interval.start_tick),
            (_ARRIVE, _LEAVE - _ARRIVE),
        )
        self.assertGreaterEqual(outcome.interval.start_tick, self.clock.tick)
        self.assertEqual(self._snapshot(), before)
        self.assertIsNone(read_session(self.player))

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_present_host_below_merit_reaches_the_authoritative_merit_gate(self):
        self._assert_rejected_unchanged(ExamReason.BELOW_THRESHOLD)

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination",
        "guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself",
    )
    def test_eligible_present_host_starts_the_same_persistent_simulation(self):
        self._give_merit(50)
        hosts_before = NPC.objects.count()
        outcome = request_guild_exam(self.player, "E", requested_by="command")
        self.assertEqual(outcome.kind, OUTCOME_STARTED)
        self.assertEqual(outcome.record.state, ExamState.ACTIVE)
        self.assertEqual(outcome.record.opponent_id, self.host.pk)
        self.assertEqual(outcome.record.requested_by, "command")
        self.assertEqual(read_session(self.player).enemy_ids, (self.host.pk,))
        self.assertEqual(NPC.objects.count(), hosts_before)

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_absent_host_with_unknown_attendance_rejects_before_merit(self):
        self.host.location = self.home  # no schedule at all
        error = self._assert_rejected_unchanged(ExamReason.ATTENDANCE_UNKNOWN)
        self.assertEqual(error.args[1], "missing_schedule")
        self._send_host_home_on_weekly_visits()
        self.host.db.schedule = {"schema_version": 1, "entries": "malformed"}
        error = self._assert_rejected_unchanged(ExamReason.ATTENDANCE_UNKNOWN)
        self.assertEqual(error.args[1], "indeterminate_schedule")

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_absent_host_held_by_another_exam_reports_no_planned_time(self):
        self._send_host_home_on_weekly_visits()
        begin_exam_schedule_hold(self.host, "999:E:1", self.clock.tick)
        error = self._assert_rejected_unchanged(ExamReason.ATTENDANCE_UNKNOWN)
        self.assertEqual(error.args[1], "active_exam_hold")

    @covers_requirement("guild-rank-exams::start-guild-exam-is-the-sole-trigger-and-validates-authority-itself")
    def test_busy_present_host_returns_its_service_reason_without_starting(self):
        self._give_merit(50)
        self.host.db.schedule_state = "busy"
        self._assert_rejected_unchanged(ExamReason.EXAMINER_BUSY)

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_busy_counter_takes_no_request_before_attendance(self):
        self._send_host_home_on_weekly_visits()
        self.counter.db.schedule_state = "busy"
        with patch("world.rules.guild_exam_request.read_next_planned_service_interval") as reader:
            self._assert_rejected_unchanged(ExamReason.SCHEDULE_BLOCKED)
        reader.assert_not_called()

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_target_and_registration_rejections_precede_attendance(self):
        self._send_host_home_on_weekly_visits()
        self._give_merit(500)
        stranger = self._candidate("unregistered stranger")
        with patch("world.rules.guild_exam_request.read_next_planned_service_interval") as reader:
            self._assert_rejected_unchanged(ExamReason.NOT_NEXT_RANK, target="D")
            with self.assertRaises(GuildExamError) as ctx:
                request_guild_exam(stranger, "E", requested_by="command")
            self.assertEqual(ctx.exception.args[0], ExamReason.UNREGISTERED)
            examiner = self.counter.components.get(GuildExaminer.get_component_slot())
            examiner.branch_key = "t_other_branch"
            self._assert_rejected_unchanged(ExamReason.WRONG_BRANCH)
        reader.assert_not_called()
        self.assertIsNone(stranger.db.guild_exams)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_speaker_grants_no_authority_beyond_counter_or_qualified_host(self):
        bystander = create_object(NPC, key="hall bystander", location=self.hall)
        self._assert_rejected_unchanged(ExamReason.NO_EXAMINER, speaker=bystander)
        remote = create_object(NPC, key="remote clerk", location=self.home)
        self._assert_rejected_unchanged(ExamReason.REMOTE_EXAMINER, speaker=remote)
        # The counter and the qualified host may both voice the request; the
        # same order and gates apply (below merit, host present).
        self._assert_rejected_unchanged(ExamReason.BELOW_THRESHOLD, speaker=self.counter)
        self._assert_rejected_unchanged(ExamReason.BELOW_THRESHOLD, speaker=self.host)

    @covers_requirement(
        "guild-rank-exams::rank-promotion-requires-cumulative-merit-and-exactly-the-next-examination"
    )
    def test_non_player_actor_and_next_rank_derivation(self):
        npc = create_object(NPC, key="npc actor", location=self.hall)
        with self.assertRaises(GuildExamError) as ctx:
            request_guild_exam(npc, "E", requested_by="command")
        self.assertEqual(ctx.exception.args[0], ExamReason.NOT_A_PLAYER)
        self.assertEqual(next_exam_rank(self.player), "E")
        top = create_object(PlayerCharacter, key="top ranked")
        top.guild_rank = "S"
        self.assertIsNone(next_exam_rank(top))
        self.assertEqual(EXAM_BRANCH, self.counter.components.get(
            GuildExaminer.get_component_slot()).branch_key)
