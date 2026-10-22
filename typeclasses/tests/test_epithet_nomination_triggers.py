"""Rest-point trigger wiring for epithet nomination (title-system D4, change G).

Pins that each owning surface calls the composition-root service with the
right entity and the advance events, that the combat settlement code never
references nomination, and that the logout hook fires through the typeclass.
The scheduling itself (suppression, cooldown, transport) is the service's own
contract, tested in ``server.conf.tests.test_title_nomination_service``; the
event-boundary gating is tested here at the seam with the service patched.
"""

import inspect
import unittest
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.skip import CmdRest
from tools.spec_traceability import covers_requirement
from world.rules.clock import WorldClock, get_world_clock

class LogoutTriggerTests(EvenniaTest):
    """``at_post_unpuppet`` schedules one logout nomination for the player."""

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_logout_hook_schedules_for_the_puppeted_player(self):
        with patch(
            "server.title_nomination_service.schedule_epithet_nomination"
        ) as schedule:
            self.char1.at_post_unpuppet(self.account)
        self.assertEqual(schedule.call_count, 1)
        self.assertIs(schedule.call_args.args[0], self.char1)

    def test_hook_never_raises_into_the_disconnect_path(self):
        with patch(
            "server.title_nomination_service.schedule_epithet_nomination",
            side_effect=RuntimeError("boom"),
        ):
            self.char1.at_post_unpuppet(self.account)  # must not raise


class WakeTriggerTests(EvenniaCommandTestMixin, EvenniaTest):
    """Voluntary and forced awakening schedule nomination after outer commit."""

    def setUp(self):
        super().setUp()
        from server import title_nomination_service
        title_nomination_service.reset_nomination_triggers_for_tests()
        title_nomination_service.register_nomination_triggers()
        self.addCleanup(title_nomination_service.reset_nomination_triggers_for_tests)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_voluntary_sleep_awakening_schedules_nomination(self):
        from world.rules.time_skip import begin_sleep
        from world.rules.fatigue import write_fatigue_state, SleepPosture

        write_fatigue_state(self.char1, 359000, SleepPosture.AWAKE)
        with patch("server.title_nomination_service.schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                outcome = begin_sleep(self.char1)
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.char1)
            self.assertEqual(schedule.call_args.kwargs.get("trigger"), "wake")

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_forced_sleep_awakening_schedules_nomination(self):
        from world.rules.fatigue import (
            FatigueInterval,
            FatigueActivity,
            SleepPosture,
            settle_fatigue_intervals,
            write_fatigue_state,
            read_fatigue_state,
        )

        write_fatigue_state(self.char1, 71988, SleepPosture.FORCED)
        sleeper = read_fatigue_state(self.char1)
        with patch("server.title_nomination_service.schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                settlement = settle_fatigue_intervals(
                    (FatigueInterval(self.char1, FatigueActivity.SLEEP, 1, sleeper),)
                )
            self.assertEqual(read_fatigue_state(self.char1).posture, SleepPosture.AWAKE)
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.char1)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_still_sleeping_or_awake_produces_no_wake_nomination(self):
        from world.rules.fatigue import (
            FatigueInterval,
            FatigueActivity,
            SleepPosture,
            settle_fatigue_intervals,
            write_fatigue_state,
            read_fatigue_state,
        )

        # Still asleep (not crossing wake boundary)
        write_fatigue_state(self.char1, 10000, SleepPosture.FORCED)
        sleeper = read_fatigue_state(self.char1)
        with patch("server.title_nomination_service.schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                settle_fatigue_intervals(
                    (FatigueInterval(self.char1, FatigueActivity.SLEEP, 1, sleeper),)
                )
            schedule.assert_not_called()

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_teammate_or_npc_waking_does_not_nominate_player(self):
        from typeclasses.npcs import NPC
        from evennia.utils.create import create_object
        from world.rules.fatigue import (
            FatigueInterval,
            FatigueActivity,
            SleepPosture,
            settle_fatigue_intervals,
            write_fatigue_state,
            read_fatigue_state,
        )

        npc = create_object(NPC, key="sleeping-npc", location=self.room1)
        write_fatigue_state(npc, 71988, SleepPosture.FORCED)
        sleeper = read_fatigue_state(npc)
        with patch("server.title_nomination_service.schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                settle_fatigue_intervals(
                    (FatigueInterval(npc, FatigueActivity.SLEEP, 1, sleeper),)
                )
            schedule.assert_not_called()

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_midnight_alone_does_not_nominate(self):
        from commands.skip import CmdRest
        from world.rules.clock import WorldClock
        # Run rest crossing midnight
        fresh = WorldClock(86400 - 2)
        with patch("world.rules.time_skip.get_world_clock", return_value=fresh):
            with patch("server.title_nomination_service.schedule_epithet_nomination") as schedule:
                self.call(CmdRest(), "23h", caller=self.char1, receiver=self.char1)
                schedule.assert_not_called()


class CombatNeverTriggersTests(unittest.TestCase):
    """Nomination stays out of the combat round machinery by structure."""

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_combat_modules_never_reference_nomination(self):
        from world.rules import combat, combat_session

        for module in (combat, combat_session):
            with self.subTest(module=module.__name__):
                self.assertNotIn("title_nomination", inspect.getsource(module))
