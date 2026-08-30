"""Initiative dominance and per-round upkeep tests."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from world.rules.combat import (
    Battlefield,
    default_attack_policy,
    roll_initiative,
    run_round,
)

from .combat_fixtures import FakeEntity, FakeGauge


class InitiativeAndTurnLoopTests(unittest.TestCase):
    def battlefield(self, gap: int = 10):
        fast = FakeEntity("fast", agility=10 + gap)
        slow = FakeEntity("slow", agility=10)
        return Battlefield(
            {"a": frozenset({"fast"}), "b": frozenset({"slow"})},
            {"fast": fast, "slow": slow},
        )

    def test_ten_point_gap_dominates_every_roll_pair(self):
        battlefield = self.battlefield()
        with patch("world.rules.combat.roll_d100", side_effect=[1, 100]):
            self.assertEqual(roll_initiative(battlefield), ["fast", "slow"])

    @covers_requirement("combat-resolution::initiative-order-is-agility-dominant-with-d100-jitter")
    def test_small_gap_can_be_reordered(self):
        battlefield = self.battlefield(gap=9)
        with patch("world.rules.combat.roll_d100", side_effect=[1, 100]):
            self.assertEqual(roll_initiative(battlefield), ["slow", "fast"])

    @covers_requirement("combat-resolution::actions-per-turn-0-skips-a-combatant-s-turn-before-actionresolver-is-called")
    def test_action_lock_skips_resolver_and_upkeep_runs(self):
        battlefield = self.battlefield()
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "slow"]),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                side_effect=[{"actions_per_turn": 0}, {}],
            ),
            patch("world.rules.combat.ActionResolver.resolve") as resolve,
            patch("world.rules.combat.tick_buffs") as tick,
            patch("world.rules.combat.decay_tick") as decay,
        ):
            logs = run_round(battlefield, lambda entity, field: None)
        self.assertEqual(logs[0].entries[0].kind, "action_skipped")
        resolve.assert_not_called()
        self.assertEqual(tick.call_count, 2)
        self.assertEqual(decay.call_count, 2)
        for call in decay.call_args_list:
            self.assertEqual(call.args[1], 6)

    def test_default_policy_does_not_retry_an_unaffordable_skill(self):
        battlefield = self.battlefield()
        actor = battlefield.roster["fast"]
        actor.skills._owned = ["fire_ball"]
        actor.traits.mp = type(
            "Gauge",
            (),
            {
                "trait_type": "gauge",
                "_data": {"base": 0, "mod": 0, "mult": 1, "current": 0},
            },
        )()
        self.assertIsNone(default_attack_policy(actor, battlefield))


class DefaultAttackPolicyCastGateTests(unittest.TestCase):
    """The generic policy never proposes a tier-blocked elemental spell."""

    def _npc(self, key: str, owned: list[str]) -> FakeEntity:
        # magic_power 15 with no affinities and no mastery: floor(15 * 1.0)
        # is below the 術師 threshold, so an owned 術師-tier firestorm is
        # blocked even though the entity could afford its 30 MP cost. The
        # innate basic_attack is always owned, exactly as the skills handler
        # guarantees for real entities.
        actor = FakeEntity(key, magic_power=15, owned=[*owned, "basic_attack"])
        actor.traits.mp = FakeGauge(30, 30)
        return actor

    def _field(self, actor: FakeEntity) -> Battlefield:
        enemy = FakeEntity("enemy")
        return Battlefield(
            {"a": frozenset({actor.key}), "b": frozenset({enemy.key})},
            {actor.key: actor, enemy.key: enemy},
        )

    @covers_requirement("monster-action-policy::a-delegated-non-monster-entity-is-never-proposed-a-tier-blocked-elemental-spell")
    def test_over_tier_affordable_spell_falls_back_to_basic_attack(self):
        actor = self._npc("npc", ["firestorm"])
        request = default_attack_policy(actor, self._field(actor))
        self.assertEqual(request.skill_key, "basic_attack")
        self.assertEqual([str(target.key) for target in request.targets], ["enemy"])

    def test_mastery_owned_spell_is_still_chosen_by_the_delegated_policy(self):
        actor = self._npc("npc-master", ["firestorm", "fire_mastery"])
        request = default_attack_policy(actor, self._field(actor))
        self.assertEqual(request.skill_key, "firestorm")
