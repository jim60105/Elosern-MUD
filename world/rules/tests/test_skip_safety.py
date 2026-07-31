"""Tests for the explicit time-skip safety boundary."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.skip_safety import (
    SkipRejectReason,
    evaluate_skip_safety,
    register_active_battlefield,
)
from .combat_fixtures import FakeGauge


def actor(key, hp=10, contents=()):
    return SimpleNamespace(
        key=key,
        traits=SimpleNamespace(hp=FakeGauge(hp, max(hp, 1))),
        location=SimpleNamespace(contents=list(contents)),
    )


class SkipSafetyTests(unittest.TestCase):
    def test_active_battlefield_rejects_but_fled_actor_does_not(self):
        first, second = actor("first"), actor("second")
        field = Battlefield(
            {"a": frozenset({"first"}), "b": frozenset({"second"})},
            {"first": first, "second": second},
        )
        register_active_battlefield(field)
        self.assertEqual(evaluate_skip_safety(first), SkipRejectReason.IN_COMBAT)
        field.fled.add("first")
        self.assertIsNone(evaluate_skip_safety(first))

    def test_living_monster_in_location_rejects(self):
        player = actor("player")
        monster = actor("monster")
        player.location.contents.append(monster)
        with patch("world.rules.skip_safety.Monster", object):
            self.assertEqual(
                evaluate_skip_safety(player),
                SkipRejectReason.HOSTILE_PRESENT,
            )
        monster.traits.hp.value = 0
        with patch("world.rules.skip_safety.Monster", object):
            self.assertIsNone(evaluate_skip_safety(player))
