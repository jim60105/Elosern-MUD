"""Self-arming integration coverage owned by the later sexual-state change."""

import importlib
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.combat_modifiers import evaluate_combat_modifiers

try:
    SEXUAL_STATE_MODULE = importlib.import_module("world.rules.sexual_state")
except ModuleNotFoundError as error:
    if error.name != "world.rules.sexual_state":
        raise
    SEXUAL_STATE_MODULE = None


class SexualStateLandingTests(EvenniaTest):
    @unittest.skipUnless(
        SEXUAL_STATE_MODULE is not None,
        "world.rules.sexual_state has not landed yet",
    )
    def test_high_arousal_rule_fires_once_sexual_state_exists(self):
        entity = create_object(PlayerCharacter, key="sexual-state integration")
        self.assertIsNotNone(entity.sexual)
        entity.sexual.arousal.value = "高度"
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-20%", "accuracy": -15},
        )
