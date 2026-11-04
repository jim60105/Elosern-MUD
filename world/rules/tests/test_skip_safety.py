"""Tests for the explicit time-skip safety boundary."""

from tools.spec_traceability import covers_requirement

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from world.rules.combat import Battlefield
from world.rules.combat_identity import stable_actor_id
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
        first_id, second_id = stable_actor_id(first), stable_actor_id(second)
        field = Battlefield(
            {'a': frozenset({first_id}), 'b': frozenset({second_id})},
            {first_id: first, second_id: second},
        )
        register_active_battlefield(field)
        self.assertEqual(evaluate_skip_safety(first), SkipRejectReason.IN_COMBAT)
        field.fled.add(first_id)
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
    @covers_requirement(
        "evennia-test-optimization::registry-content-assertions-use-the-registry-s-key-domain"
    )
    def test_same_key_entities_in_separate_battlefields_do_not_cross_evict(self):
        first, second = actor("shared", 1), actor("shared", 2)
        other_a, other_b = actor("other-a", 3), actor("other-b", 4)
        first_id, second_id = stable_actor_id(first), stable_actor_id(second)
        other_a_id, other_b_id = stable_actor_id(other_a), stable_actor_id(other_b)
        field_a = Battlefield(
            {'a': frozenset({first_id}), 'b': frozenset({other_a_id})},
            {first_id: first, other_a_id: other_a},
        )
        field_b = Battlefield(
            {'a': frozenset({second_id}), 'b': frozenset({other_b_id})},
            {second_id: second, other_b_id: other_b},
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
        foe = actor("foe", 12)
        fighter_id, foe_id = stable_actor_id(fighter), stable_actor_id(foe)
        field = Battlefield(
            {'a': frozenset({fighter_id}), 'b': frozenset({foe_id})},
            {fighter_id: fighter, foe_id: foe},
        )
        register_active_battlefield(field)
        self.assertEqual(
            evaluate_skip_safety(fighter),
            SkipRejectReason.IN_COMBAT,
        )
        # A different entity sharing the fighter's display key is not in combat.
        clone = actor("fighter", 13)
        self.assertIsNone(evaluate_skip_safety(clone))

    @covers_requirement(
        "battlefield-action-context::battlefieldactioncontext-conforms-to-change-8-s-actioncontext-protocol"
    )
    def test_battlefield_construction_preserves_explicit_identity_domains(self):
        """Persisted doubles keep dbref identity; pure doubles use explicit ones."""
        first, second = actor("shared", 1), actor("shared", 2)
        first.combat_identity = "first"
        second.combat_identity = "second"
        first_id, second_id = stable_actor_id(first), stable_actor_id(second)
        self.assertEqual(first_id, "dbref:1")
        self.assertEqual(second_id, "dbref:2")

        field = Battlefield(
            {'a': frozenset({first_id}), 'b': frozenset({second_id})},
            {first_id: first, second_id: second},
        )
        self.assertIs(field.roster[first_id], first)
        self.assertIs(field.roster[second_id], second)
        self.assertEqual(field.team_of(first_id), 'a')
        self.assertEqual(field.team_of(second_id), 'b')

        snapshot = dict(_BATTLEFIELDS)
        with self.assertRaisesRegex(ValueError, "does not match combatant identity"):
            Battlefield(
                {'a': frozenset({"fixture:first"}), 'b': frozenset({second_id})},
                {"fixture:first": first, second_id: second},
            )
        self.assertEqual(dict(_BATTLEFIELDS), snapshot)

        pure_first = SimpleNamespace(key="shared", combat_identity="alpha")
        pure_second = SimpleNamespace(key="shared", combat_identity="beta")
        pure_first_id, pure_second_id = (
            stable_actor_id(pure_first),
            stable_actor_id(pure_second),
        )
        pure_field = Battlefield(
            {'a': frozenset({pure_first_id}), 'b': frozenset({pure_second_id})},
            {pure_first_id: pure_first, pure_second_id: pure_second},
        )
        self.assertEqual(set(pure_field.roster), {"fixture:alpha", "fixture:beta"})

        with self.assertRaisesRegex(ValueError, "multiple teams"):
            Battlefield(
                {'a': frozenset({first_id, second_id}), 'b': frozenset({first_id})},
                {first_id: first, second_id: second},
            )
