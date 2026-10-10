"""Self-arming integration coverage owned by the later sexual-state change."""

from tools.spec_traceability import covers_requirement

import importlib
import unittest
from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.rulebook.schema import load_rules

RULES = {
    rule.id: rule
    for rule in load_rules(
        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
    )
}

try:
    SEXUAL_STATE_MODULE = importlib.import_module("world.rules.sexual_state")
except ModuleNotFoundError as error:
    if error.name != "world.rules.sexual_state":
        raise
    SEXUAL_STATE_MODULE = None


class SexualStateLandingTests(EvenniaTestCase):
    @unittest.skipUnless(
        SEXUAL_STATE_MODULE is not None,
        "world.rules.sexual_state has not landed yet",
    )
    @covers_requirement("combat-modifier-table::sexual-field-rules-degrade-to-inert-until-entity-sexual-is-real-then-self-arm", "sexual-state-handler::change-6-s-self-arming-combat-modifier-test-fires-once-entity-sexual-is-real")
    def test_high_arousal_rule_fires_once_sexual_state_exists(self):
        entity = create_object(PlayerCharacter, key="sexual-state integration")
        self.assertIsNotNone(entity.sexual)
        entity.sexual.pleasure.base = 60
        # The row fires and its declared adjustment reaches the merged bundle;
        # the authored magnitude stays data and is never repeated here.
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["high_arousal_agility_accuracy_penalty"].then,
        )
