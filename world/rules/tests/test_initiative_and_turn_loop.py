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
from world.rules.progression import (
    lineage_ownership_closure,
    seed_lineage_proficiency,
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


class DefaultAttackPolicyAffordabilityTests(unittest.TestCase):
    """The generic policy only proposes resolver-backed affordable skills."""

    def _npc(self, key: str, owned: list[str], mp: int) -> FakeEntity:
        # Ownership, the shared lineage gate (can_use_skill), and MP
        # affordability are the eligibility gates: a deep spell owned without
        # its prerequisite chain is not usable and the innate basic_attack
        # (no cost) takes over.
        actor = FakeEntity(key, owned=[*owned, "basic_attack"])
        actor.traits.mp = FakeGauge(mp, 30)
        return actor

    def _field(self, actor: FakeEntity) -> Battlefield:
        enemy = FakeEntity("enemy")
        return Battlefield(
            {"a": frozenset({actor.key}), "b": frozenset({enemy.key})},
            {actor.key: actor, enemy.key: enemy},
        )

    @covers_requirement("monster-action-policy::a-delegated-non-monster-entity-proposes-the-first-usable-resolver-backed-damage-skill")
    def test_unaffordable_spell_falls_back_to_basic_attack(self):
        actor = self._npc("npc", ["firestorm"], mp=10)
        request = default_attack_policy(actor, self._field(actor))
        # basic_attack carries no cost, so the resolver's own gate accepts.
        self.assertEqual(request.skill_key, "basic_attack")
        self.assertEqual([str(target.key) for target in request.targets], ["enemy"])

    def test_affordable_owned_spell_is_chosen_ahead_of_the_innate(self):
        actor = self._npc("npc-caster", ["firestorm"], mp=30)
        # The caster closes the lineage with exactly-seeded XP so firestorm
        # passes the shared use gate.
        add_active, add_passive = lineage_ownership_closure(["firestorm"])
        actor.skills._owned = [
            "firestorm",
            *add_active,
            *add_passive,
            "basic_attack",
        ]
        actor.db.skill_proficiency = seed_lineage_proficiency(
            actor.skills._owned
        )
        request = default_attack_policy(actor, self._field(actor))
        self.assertEqual(request.skill_key, "firestorm")
