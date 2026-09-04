"""Source guards and command registration tests for the guild-economy layer (tasks 11.4, 11.6)."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
from pathlib import Path

from world.rules import economy, guild, guild_config, guild_offers, guild_exams, combat_session
from world.rules import guild_economy as guild_economy_sync
from world.rules import caravan_arrivals, shop_hours, npc_schedules
from world.rules import equipment
from world.quests import acquire
from typeclasses import components
from commands import guild as guild_commands
from commands import combat as combat_commands
from commands import economy as economy_commands

ROOT = Path(__file__).resolve().parents[3]


class NoGenerativeImportTests(unittest.TestCase):
    MODULES = (
        economy,
        guild,
        guild_config,
        guild_offers,
        guild_exams,
        combat_session,
        guild_economy_sync,
        caravan_arrivals,
        shop_hours,
        npc_schedules,
        equipment,
        acquire,
        components,
        guild_commands,
        combat_commands,
        economy_commands,
    )

    def test_no_module_imports_world_ai_or_a_client(self):
        for module in self.MODULES:
            source = inspect.getsource(module)
            with self.subTest(module=module.__name__):
                self.assertNotIn("world.ai", source)
                self.assertNotIn("world.ai", source)
                self.assertNotIn("import ollama", source.lower())
                self.assertNotIn("llm_client", source.lower())
                self.assertNotIn("requests", source.lower())

    def test_startup_composition_root_calls_quest_after_map(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_quest_runtime"),
            STARTUP_STEP_ORDER.index("sync_guild_economy"),
        )
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_grid"),
            STARTUP_STEP_ORDER.index("sync_guild_economy"),
        )

    def test_startup_restores_sessions_before_wilderness_sync(self):
        # Persisted combat sessions must be restored before wilderness
        # population reconciliation so a defeated population monster is never
        # deleted or respawned before its committed outcome settles (F10).
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("restore_persisted_sessions"),
            STARTUP_STEP_ORDER.index("sync_wilderness"),
        )

    def test_startup_registers_every_clock_source_before_session_restoration(self):
        # Every world-event clock source must be registered before any startup
        # operation can advance time: the five syncs that register the quest,
        # caravan, shop-hours, and NPC-schedule stages all run before session
        # restoration, and restoration still precedes wilderness sync
        # (fix-startup-clock-source-order D1).
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        for sync in (
            "sync_service_interiors",
            "sync_quest_runtime",
            "sync_guild_economy",
            "sync_npc_schedules",
        ):
            with self.subTest(sync=sync):
                self.assertLess(
                    STARTUP_STEP_ORDER.index(sync),
                    STARTUP_STEP_ORDER.index("restore_persisted_sessions"),
                )

    @covers_requirement("player-combat-session::startup-restores-combat-sessions-before-wilderness-population-reconciliation")
    @covers_requirement("player-combat-session::startup-combat-restoration-advances-time-only-after-every-deterministic-clock-source-is-registered")
    def test_startup_invokes_restore_before_wilderness_sync(self):
        # Behavioral twin of the source-order guard above: every startup step
        # is stubbed, so the assertion covers the actual invocation sequence of
        # the composition root, not its source text. All five clock-source
        # syncs must run strictly before session restoration, which runs
        # strictly before wilderness reconciliation.
        from contextlib import ExitStack
        from unittest.mock import patch

        from server.conf.at_server_startstop import at_server_start

        order: list[str] = []
        targets = {
            "world.lore.sync.sync_all": "sync_all",
            "world.maps.bootstrap.sync_limbo": "sync_limbo",
            "world.maps.bootstrap.sync_grid": "sync_grid",
            "world.rules.guild_economy.restore_persisted_sessions": "restore_persisted_sessions",
            "world.maps.bootstrap.sync_wilderness": "sync_wilderness",
            "world.maps.bootstrap.sync_service_interiors": "sync_service_interiors",
            "world.quests.bootstrap.sync_quest_runtime": "sync_quest_runtime",
            "world.rules.guild_economy.sync_guild_economy": "sync_guild_economy",
            "world.rules.npc_schedules.sync_npc_schedules": "sync_npc_schedules",
        }
        patchers = [
            patch("world.rules.clock.get_world_clock"),
            patch("world.prompts.loader.load_prompt_library"),
            patch("world.art.service.art_sync_all"),
            patch("web.webclient.presentation.art_push.connect_art_push"),
            *[
                patch("server.conf.at_server_startstop." + name)
                for name in (
                    "_register_narrator_layer",
                    "_register_npc_dialogue_layer",
                    "_register_scenario_director_layer",
                    "_register_character_creation_layer",
                    "_register_scene_flavor_layer",
                )
            ],
        ]
        for target, name in targets.items():
            patchers.append(
                patch(
                    target,
                    side_effect=lambda *args, name=name, **kwargs: order.append(name),
                )
            )
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            at_server_start()
        for sync in (
            "sync_service_interiors",
            "sync_quest_runtime",
            "sync_guild_economy",
            "sync_npc_schedules",
        ):
            self.assertLess(
                order.index(sync),
                order.index("restore_persisted_sessions"),
                f"{sync} must run before session restoration",
            )
        self.assertLess(
            order.index("restore_persisted_sessions"),
            order.index("sync_wilderness"),
        )

    def test_schedule_sync_runs_after_guild_economy_sync(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_guild_economy"),
            STARTUP_STEP_ORDER.index("sync_npc_schedules"),
        )


class CommandSetRegistrationTests(unittest.TestCase):
    def test_character_cmdset_registers_all_guild_economy_commands(self):
        from commands.default_cmdsets import CharacterCmdSet

        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {cmd.key for cmd in cmdset.commands}
        expected = {
            "guild register",
            "guild list",
            "guild accept",
            "guild log",
            "guild abandon",
            "guild turnin",
            "guild merit",
            "guild exam",
            "engage",
            "combat forfeit",
            "shop stock",
            "buy",
            "sell",
            "inventory",
        }
        self.assertTrue(expected <= keys, sorted(expected - keys))


if __name__ == "__main__":
    unittest.main()