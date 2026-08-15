"""Integration tests for staged action commit and rollback."""

from copy import deepcopy

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
    _stored_trait_value,
)


class ActionPipelineAtomicityTests(EvenniaTest):
    def test_failed_second_effect_restores_first(self):
        entity = create_object(PlayerCharacter, key="atomic")
        entity.race = "human"
        entity.apply_race_baseline()
        raw_before = deepcopy(dict(entity.traits.trait_data))
        before = entity.traits.atk_phys.value
        effects = [
            PendingEffect(
                entity,
                "first",
                frozenset({"traits"}),
                lambda: setattr(entity.traits.atk_phys, "value", before + 10),
            ),
            PendingEffect(
                entity,
                "second",
                frozenset({"traits"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects)
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(entity.traits.atk_phys.value, before)
        self.assertEqual(dict(entity.traits.trait_data), raw_before)

    def test_failed_effect_restores_resource_and_attribute_absence(self):
        entity = create_object(PlayerCharacter, key="resource-atomic")
        entity.race = "human"
        entity.apply_race_baseline()
        before = _stored_trait_value(entity.traits.mp)
        self.assertFalse(entity.attributes.has("sexual_traits", category="traits"))
        effects = [
            PendingEffect(
                entity,
                "resource",
                frozenset({"traits"}),
                lambda: setattr(entity.traits.mp, "current", before - 10),
            ),
            PendingEffect(
                entity,
                "sexual failure",
                frozenset({"sexual"}),
                lambda: (
                    setattr(entity.sexual.pleasure, "base", 2),
                    (_ for _ in ()).throw(RuntimeError("injected")),
                ),
            ),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects)
        self.assertEqual(_stored_trait_value(entity.traits.mp), before)
        self.assertFalse(entity.attributes.has("sexual_traits", category="traits"))
        self.assertEqual(entity.sexual.arousal.value, 0)
