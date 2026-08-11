"""Tests for the explicit time-skip safety boundary."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.skip_safety import (
    SkipRejectReason,
    evaluate_skip_safety,
    register_active_battlefield,
)
from .combat_fixtures import BattlefieldIsolation, FakeGauge


def actor(key, hp=10, contents=()):
    return SimpleNamespace(
        key=key,
        traits=SimpleNamespace(hp=FakeGauge(hp, max(hp, 1))),
        location=SimpleNamespace(contents=list(contents)),
    )


class SkipSafetyTests(BattlefieldIsolation, unittest.TestCase):
    @covers_requirement("skip-safety-gate::a-safe-actor-s-skip-is-unconditionally-allowed", "skip-safety-gate::evaluate-skip-safety-rejects-a-skip-when-the-actor-is-actively-in-combat")
    @covers_requirement("skip-safety-gate::fled-battlefield-membership-is-not-by-itself-a-reject-condition")
    @covers_requirement("skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-compute-a-partial-safety-shortened")
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

    @covers_requirement("skip-safety-gate::evaluate-skip-safety-rejects-a-skip-when-a-living-monster-shares-the-actor-s-location")
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
