"""Tests for the explicit time-skip safety boundary."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.skip_safety import (
    SkipRejectReason,
    _BATTLEFIELDS,
    evaluate_skip_safety,
    register_active_battlefield,
    unregister_active_battlefield,
)
from .combat_fixtures import BattlefieldIsolation, FakeGauge


def actor(key, pk, hp=10, contents=()):
    return SimpleNamespace(
        key=key,
        pk=pk,
        traits=SimpleNamespace(hp=FakeGauge(hp, max(hp, 1))),
        location=SimpleNamespace(contents=list(contents)),
    )


class SkipSafetyTests(BattlefieldIsolation, unittest.TestCase):
    @covers_requirement("skip-safety-gate::a-safe-actor-s-skip-is-unconditionally-allowed", "skip-safety-gate::evaluate-skip-safety-rejects-a-skip-when-the-actor-is-actively-in-combat")
    @covers_requirement("skip-safety-gate::fled-battlefield-membership-is-not-by-itself-a-reject-condition")
    @covers_requirement("skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-compute-a-partial-safety-shortened")
    def test_active_battlefield_rejects_but_fled_actor_does_not(self):
        first, second = actor("first", 1), actor("second", 2)
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
        player = actor("player", 1)
        monster = actor("monster", 2)
        player.location.contents.append(monster)
        with patch("world.rules.skip_safety.Monster", object):
            self.assertEqual(
                evaluate_skip_safety(player),
                SkipRejectReason.HOSTILE_PRESENT,
            )
        monster.traits.hp.value = 0
        with patch("world.rules.skip_safety.Monster", object):
            self.assertIsNone(evaluate_skip_safety(player))

    @covers_requirement("skip-safety-gate::skip-safety-registers-battlefields-by-participant-dbref")
    def test_same_key_entities_in_separate_battlefields_do_not_cross_evict(self):
        first, second = actor("shared", 1), actor("shared", 2)
        field_a = Battlefield(
            {"a": frozenset({"shared"}), "b": frozenset({"other-a"})},
            {"shared": first, "other-a": actor("other-a", 3)},
        )
        field_b = Battlefield(
            {"a": frozenset({"shared"}), "b": frozenset({"other-b"})},
            {"shared": second, "other-b": actor("other-b", 4)},
        )
        register_active_battlefield(field_a)
        register_active_battlefield(field_b)
        self.assertIs(_BATTLEFIELDS["1"], field_a)
        self.assertIs(_BATTLEFIELDS["2"], field_b)
        unregister_active_battlefield(first)
        self.assertNotIn("1", _BATTLEFIELDS)
        self.assertIs(_BATTLEFIELDS["2"], field_b)
        self.assertIsNone(evaluate_skip_safety(first))
        self.assertEqual(evaluate_skip_safety(second), SkipRejectReason.IN_COMBAT)

    @covers_requirement("skip-safety-gate::skip-safety-registers-battlefields-by-participant-dbref")
    def test_in_combat_lookup_resolves_by_actor_dbref(self):
        fighter, bystander = actor("fighter", 10), actor("bystander", 11)
        field = Battlefield(
            {"a": frozenset({"fighter"}), "b": frozenset({"foe"})},
            {"fighter": fighter, "foe": actor("foe", 12)},
        )
        register_active_battlefield(field)
        self.assertEqual(
            evaluate_skip_safety(fighter),
            SkipRejectReason.IN_COMBAT,
        )
        # A different entity sharing the fighter's display key is not in combat.
        clone = actor("fighter", 13)
        self.assertIsNone(evaluate_skip_safety(clone))
