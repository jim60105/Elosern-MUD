"""Source guards and command registration tests for the guild-economy layer (tasks 11.4, 11.6)."""

import inspect
import unittest
from pathlib import Path

from world.rules import economy, guild, guild_config, guild_offers, guild_exams, combat_session
from world.rules import guild_economy as guild_economy_sync
from world.rules import caravan_arrivals, shop_hours
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
        from server.conf.at_server_startstop import at_server_start

        source = inspect.getsource(at_server_start)
        self.assertLess(source.index("sync_quest_runtime()"), source.index("sync_guild_economy()"))
        self.assertLess(source.index("sync_grid()"), source.index("sync_guild_economy()"))


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