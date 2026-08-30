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
from world.rules.clock import WorldClock, get_world_clock

class LogoutTriggerTests(EvenniaTest):
    """``at_post_unpuppet`` schedules one logout nomination for the player."""

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


class TypedRestTriggerTests(EvenniaCommandTestMixin, EvenniaTest):
    """rest hands its advance events to the boundary gate."""

    def setUp(self):
        super().setUp()
        self.actor = self.char1
        self.patcher = patch(
            "server.title_nomination_service.schedule_rest_boundary_nomination"
        )
        self.schedule = self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _run(self, cmd, args):
        return self.call(cmd, args, caller=self.actor, receiver=self.actor)

    def test_rest_passes_events_across_the_gate(self):
        self._run(CmdRest(), "1h")
        self.assertEqual(self.schedule.call_count, 1)
        caller, events = self.schedule.call_args.args
        self.assertIs(caller, self.actor)
        kinds = [getattr(event, "kind", None) for event in events]
        # 1h from tick 0 crosses no day boundary; the gate sees no daily_reset.
        self.assertNotIn("daily_reset", kinds)
    def test_rest_crossing_the_boundary_reports_daily_reset(self):
        # commands/skip.py resolves the clock through its own module-level
        # name; a fresh instance two seconds before the day boundary makes
        # 23h cross exactly one boundary, which is the trigger's gate.
        fresh = WorldClock(86400 - 2)
        with patch("commands.skip.get_world_clock", return_value=fresh):
            self._run(CmdRest(), "23h")
        self.assertEqual(self.schedule.call_count, 1)
        events = self.schedule.call_args.args[1]
        self.assertIn("daily_reset", [getattr(e, "kind", None) for e in events])

    def test_scheduling_failure_never_breaks_rest(self):
        self.schedule.side_effect = RuntimeError("boom")
        # commands/skip.py swallows inside its own helper; the service helper
        # swallows too — either way, rest still advances the clock.
        before = get_world_clock().tick
        self._run(CmdRest(), "1h")
        self.assertGreater(get_world_clock().tick, before)


class WebWaitAdapterTriggerTests(EvenniaTest):
    """The ``explore.wait`` adapter routes through the same boundary gate."""

    def test_wait_adapter_calls_the_gate(self):
        from web.webclient.actions.exploration_actions import _wait_adapter

        with patch(
            "server.title_nomination_service.schedule_rest_boundary_nomination"
        ) as schedule:
            result = _wait_adapter(self.char1, {"seconds": 60})
        self.assertEqual(result["code"], "skipped")
        self.assertEqual(schedule.call_count, 1)
        self.assertIs(schedule.call_args.args[0], self.char1)

    def test_failed_wait_schedules_nothing(self):
        from web.webclient.actions.exploration_actions import _wait_adapter

        with (
            patch("world.rules.time_skip.get_world_clock") as clock,
            patch(
                "server.title_nomination_service.schedule_rest_boundary_nomination"
            ) as schedule,
        ):
            clock.return_value.advance.side_effect = RuntimeError("no advance")
            result = _wait_adapter(self.char1, {"seconds": 60})
        self.assertEqual(result["code"], "skip_failed")
        schedule.assert_not_called()


class CombatNeverTriggersTests(unittest.TestCase):
    """Nomination stays out of the combat round machinery by structure."""

    def test_combat_modules_never_reference_nomination(self):
        from world.rules import combat, combat_session

        for module in (combat, combat_session):
            with self.subTest(module=module.__name__):
                self.assertNotIn("title_nomination", inspect.getsource(module))
