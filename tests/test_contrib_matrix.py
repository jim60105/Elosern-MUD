"""Regression checks for the contrib reuse matrix in the design document."""

import importlib
import os
import unittest
from pathlib import Path


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django

django.setup()

import evennia

evennia._init()


MATRIX_IMPORTS = {
    "traits": (
        "evennia.contrib.rpg.traits",
        ("TraitHandler", "Trait", "StaticTrait", "CounterTrait", "GaugeTrait"),
    ),
    "buffs": ("evennia.contrib.rpg.buffs", ("BuffHandler", "BaseBuff")),
    "components": (
        "evennia.contrib.base_systems.components",
        ("Component", "ComponentHolderMixin", "ComponentProperty"),
    ),
    "xyzgrid": ("evennia.contrib.grid.xyzgrid.xyzroom", ("XYZRoom", "XYZExit")),
    "xyzgrid runtime": (
        "evennia.contrib.grid.xyzgrid.xyzgrid",
        ("XYZGrid", "get_xyzgrid"),
    ),
    "xyzgrid xymap": ("evennia.contrib.grid.xyzgrid.xymap", ("XYMap",)),
    "wilderness": (
        "evennia.contrib.grid.wilderness.wilderness",
        ("WildernessMapProvider",),
    ),
    "prototype spawner": ("evennia.prototypes.spawner", ("spawn",)),
    "llm client": ("evennia.contrib.rpg.llm.llm_client", ("LLMClient",)),
    "llm npc": ("evennia.contrib.rpg.llm.llm_npc", ("LLMNPC",)),
    "evadventure rolls": (
        "evennia.contrib.tutorials.evadventure.rules",
        ("EvAdventureRollEngine",),
    ),
    "evadventure combat": (
        "evennia.contrib.tutorials.evadventure.combat_base",
        ("EvAdventureCombatBaseHandler",),
    ),
    "dice": ("evennia.contrib.rpg.dice", ("roll",)),
}


class ContribMatrixTests(unittest.TestCase):
    def test_matrix_imports_and_attributes(self):
        for row, (module_path, names) in MATRIX_IMPORTS.items():
            with self.subTest(row=row):
                module = importlib.import_module(module_path)
                for name in names:
                    self.assertTrue(
                        hasattr(module, name),
                        f"{row}: {module_path}.{name} no longer resolves",
                    )

    def test_webclient_goldenlayout_configuration_path_exists(self):
        evennia_root = Path(evennia.__file__).parent
        config_path = (
            evennia_root
            / "web/static/webclient/js/plugins/goldenlayout_default_config.js"
        )
        self.assertTrue(config_path.is_file(), f"WebClient config path is missing: {config_path}")

    def test_wilderness_documentation_example_is_not_treated_as_api(self):
        module = importlib.import_module("evennia.contrib.grid.wilderness.wilderness")
        self.assertFalse(hasattr(module, "PyramidMapProvider"))
