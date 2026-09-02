"""Startup-step observability: one timed event per catalog step, order preserved.

Every ``at_server_start`` operation is stubbed and the monotonic clock is
fixed, so the assertions cover the emitted ``startup_step`` sequence itself:
exactly one event per catalog entry, in catalog order. The fail-loud and
boot-tolerant branches are asserted separately: a fail-loud failure logs and
still propagates; a tolerated failure degrades with structured context and
startup continues.

The facade bindings and the clock seam are patched with ``patch.object`` on
the imported module object: the Evennia test runner imports ``server.conf``
modules through its own conf loader, so dotted-string targets on this module
can resolve to a stale duplicate instance and patch it invisibly.
"""

import importlib
from contextlib import ExitStack
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase

import server.conf.at_server_startstop as startup
from server.conf.at_server_startstop import STARTUP_STEP_ORDER

from tools.spec_traceability import covers_requirement

# Names imported inside at_server_start's body: patch the source modules.
_BODY_TARGETS = (
    "world.rules.clock.get_world_clock",
    "world.lore.sync.sync_all",
    "world.maps.bootstrap.sync_limbo",
    "world.maps.bootstrap.sync_grid",
    "world.maps.bootstrap.sync_service_interiors",
    "world.maps.bootstrap.sync_wilderness",
    "world.quests.bootstrap.sync_quest_runtime",
    "world.rules.guild_economy.restore_persisted_sessions",
    "world.rules.guild_economy.sync_guild_economy",
    "world.rules.npc_schedules.sync_npc_schedules",
    "world.rules.onboarding.sync_guard_npc",
    "world.rules.titles.register_title_planner",
    "world.prompts.loader.load_prompt_library",
    "world.art.service.art_sync_all",
    "web.webclient.presentation.art_push.connect_art_push",
    "world.ai.narrator.register_narrator",
    "world.ai.npc_dialogue.register_npc_dialogue",
    "world.ai.scenario_director.register_scenario_director",
    "world.ai.character_creation.register_character_creation",
    "world.ai.scene_flavor.register_scene_flavor",
    "world.ai.action_options.register_action_options",
    "world.ai.title_nomination.register_title_nomination",
    "server.title_nomination_service.register_nomination_triggers",
)


class _StubbedStartup(EvenniaTestCase):
    """Runs at_server_start with every step stubbed once and the clock fixed."""

    def _run(self, overrides=None, assert_raises=None):
        overrides = overrides or {}
        with ExitStack() as stack:
            for target in _BODY_TARGETS:
                stack.enter_context(patch(target, **overrides.get(target, {})))
            stack.enter_context(
                patch.object(importlib, "import_module", **overrides.get("import_module", {}))
            )
            stack.enter_context(
                patch.object(
                    startup,
                    "_startup_clock",
                    side_effect=[0.0, 0.01] * (len(STARTUP_STEP_ORDER) + 2),
                )
            )
            info = stack.enter_context(patch.object(startup, "log_info"))
            warn = stack.enter_context(patch.object(startup, "log_warn"))
            error = stack.enter_context(patch.object(startup, "log_error"))
            if assert_raises is not None:
                with self.assertRaises(assert_raises):
                    startup.at_server_start()
            else:
                startup.at_server_start()
        return info, warn, error

    @staticmethod
    def _steps(info):
        return [
            call.kwargs["context"]["step"]
            for call in info.call_args_list
            if call.args and call.args[0] == "startup_step"
        ]


class StartupStepEventTests(_StubbedStartup):
    @covers_requirement('observability-logging::server-startup-emits-lifecycle-events')
    def test_every_catalog_step_emits_exactly_one_timed_event_in_order(self):
        info, warn, error = self._run()
        steps = [
            (call.kwargs["context"]["step"], call.kwargs["context"]["ms"])
            for call in info.call_args_list
            if call.args and call.args[0] == "startup_step"
        ]
        self.assertEqual([name for name, _ in steps], list(STARTUP_STEP_ORDER))
        self.assertTrue(all(ms == 10 for _, ms in steps))
        warn.assert_not_called()
        error.assert_not_called()

    def test_fail_loud_step_logs_and_reraises(self):
        info, warn, error = self._run(
            {"world.lore.sync.sync_all": {"side_effect": RuntimeError("boom")}},
            assert_raises=RuntimeError,
        )
        error.assert_called_once()
        self.assertEqual(error.call_args.args[0], "startup_step_failed")
        self.assertEqual(error.call_args.kwargs["context"], {"step": "sync_all"})
        self.assertIsInstance(error.call_args.kwargs["exc"], RuntimeError)
        warn.assert_not_called()
        # Steps before the failure emitted their events; nothing after ran.
        self.assertEqual(self._steps(info), ["world_clock_init", "equipment_rulebook_validation"])

    def test_tolerant_registration_failure_degrades_and_startup_continues(self):
        from world.ai.guardrail import GuardrailRegistrationError

        info, warn, error = self._run(
            {
                "world.ai.narrator.register_narrator": {
                    "side_effect": GuardrailRegistrationError("foreign narrator hook")
                }
            }
        )
        self.assertEqual(len(warn.call_args_list), 1)
        self.assertEqual(warn.call_args.args[0], "startup_step_degraded")
        self.assertEqual(warn.call_args.kwargs["context"]["step"], "register_narrator_layer")
        self.assertIn(
            "GuardrailRegistrationError", warn.call_args.kwargs["context"]["reason"]
        )
        self.assertIsInstance(warn.call_args.kwargs["exc"], GuardrailRegistrationError)
        # Startup completed: every other step still emitted its event.
        names = self._steps(info)
        self.assertNotIn("register_narrator_layer", names)
        self.assertEqual(len(names), len(STARTUP_STEP_ORDER) - 1)
        error.assert_not_called()

    def test_prompt_library_failure_degrades_at_error_level(self):
        info, warn, error = self._run(
            {
                "world.prompts.loader.load_prompt_library": {
                    "side_effect": RuntimeError("bad yaml")
                }
            }
        )
        error.assert_called_once()
        self.assertEqual(error.call_args.args[0], "startup_step_degraded")
        self.assertEqual(
            error.call_args.kwargs["context"]["step"], "load_prompt_library"
        )
        self.assertIsInstance(error.call_args.kwargs["exc"], RuntimeError)
        warn.assert_not_called()
