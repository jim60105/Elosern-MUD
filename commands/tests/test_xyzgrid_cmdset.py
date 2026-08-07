"""Cmdset wiring checks for the xyzgrid contrib (map-anchor-grid)."""

from importlib import import_module
from pathlib import Path

from django.conf import settings
from evennia.utils.test_resources import EvenniaTest

from commands.default_cmdsets import CharacterCmdSet


class XyzGridCmdSetTests(EvenniaTest):
    def test_character_cmdset_contains_xyzgrid_commands(self):
        cmdset = CharacterCmdSet()
        cmdset.at_cmdset_creation()
        keys = {cmd.key for cmd in cmdset.commands}
        # The localized wrappers replace the English-keyed contrib commands
        # (localize-limbo-zhtw); the builder commands stay native.
        self.assertIn("地圖", keys)
        self.assertIn("前往", keys)
        self.assertNotIn("map", keys)
        self.assertNotIn("goto", keys)
        self.assertIn("@teleport", keys)
        self.assertIn("@open", keys)

    def test_xyzgrid_launcher_command_resolves(self):
        module_path, _, attr = settings.EXTRA_LAUNCHER_COMMANDS["xyzgrid"].rpartition(".")
        module = import_module(module_path)
        command = getattr(module, attr)
        self.assertTrue(callable(command))

    def test_xyzgrid_prototypes_module_is_registered(self):
        self.assertIn("evennia.contrib.grid.xyzgrid.prototypes", settings.PROTOTYPE_MODULES)
        self.assertIn("world.prototypes", settings.PROTOTYPE_MODULES)

    def test_launcher_command_file_is_installed(self):
        evennia_root = Path(import_module("evennia").__file__).parent
        launchcmd = evennia_root / "contrib/grid/xyzgrid/launchcmd.py"
        self.assertTrue(launchcmd.is_file())