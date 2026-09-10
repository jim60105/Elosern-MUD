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

from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillPrerequisite
from world.tests.synthetic_data import SYNTH_SKILLS, synthetic_registries

from ._combat_session_helpers import synth_damage_skill, synth_innate_overlay
from .combat_fixtures import FakeEntity, FakeGauge

# Synthetic vehicles (test-data-independence): the kit's affordable spell is
# made unaffordable by fixture MP, and a file-local deep skill carries a
# prerequisite edge so the lineage gate is exercised over synthetic rows.
_T_CAST = SYNTH_SKILLS["t_ember_burst"].key
_T_DEEP = synth_damage_skill(
    "t_rune_barrage",
    "符文彈幕",
    cost={"mp": 20},
    prerequisites=(SkillPrerequisite(skill_key=_T_CAST, min_proficiency=1),),
)
_SCOPE = synthetic_registries(
    "skills", extra={"skills": {**synth_innate_overlay()["skills"], _T_DEEP.key: _T_DEEP}}
)


@_SCOPE
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
        actor.skills._owned = [_T_CAST]
        actor.traits.mp = type(
            "Gauge",
            (),
            {
                "trait_type": "gauge",
                "_data": {"base": 0, "mod": 0, "mult": 1, "current": 0},
            },
        )()
        self.assertIsNone(default_attack_policy(actor, battlefield))


@_SCOPE
class DefaultAttackPolicyAffordabilityTests(unittest.TestCase):
    """The generic policy only proposes resolver-backed affordable skills."""

    def _npc(self, key: str, owned: list[str], mp: int) -> FakeEntity:
        # Ownership, the shared lineage gate (can_use_skill), and MP
        # affordability are the eligibility gates: a deep spell owned without
        # its prerequisite chain is not usable and the innate basic_attack
        # (no cost) takes over.
        actor = FakeEntity(key, owned=[*owned, BASIC_ATTACK_KEY])
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
        actor = self._npc("npc", [_T_CAST], mp=10)
        request = default_attack_policy(actor, self._field(actor))
        # basic_attack carries no cost, so the resolver's own gate accepts.
        self.assertEqual(request.skill_key, BASIC_ATTACK_KEY)
        self.assertEqual([str(target.key) for target in request.targets], ["enemy"])

    def test_affordable_owned_spell_is_chosen_ahead_of_the_innate(self):
        actor = self._npc("npc-caster", [_T_DEEP.key], mp=30)
        # The caster closes the lineage with exactly-seeded XP so the deep
        # spell passes the shared use gate; the policy picks it (it precedes
        # the innate in ownership order) over basic_attack.
        add_active, add_passive = lineage_ownership_closure([_T_DEEP.key])
        actor.skills._owned = [
            _T_DEEP.key,
            *add_active,
            *add_passive,
            BASIC_ATTACK_KEY,
        ]
        actor.db.skill_proficiency = seed_lineage_proficiency(
            actor.skills._owned
        )
        request = default_attack_policy(actor, self._field(actor))
        self.assertEqual(request.skill_key, _T_DEEP.key)

    def test_owned_deep_spell_skipped_when_unaffordable(self):
        # The deep synthetic spell costs 20 MP; at 12 MP the policy skips it
        # and proposes the affordable prerequisite spell instead — MP
        # affordability is enforced per owned skill, never by lineage order.
        actor = self._npc("npc-cheap", [_T_DEEP.key], mp=12)
        add_active, add_passive = lineage_ownership_closure([_T_DEEP.key])
        actor.skills._owned = [_T_DEEP.key, *add_active, *add_passive, BASIC_ATTACK_KEY]
        actor.db.skill_proficiency = seed_lineage_proficiency(actor.skills._owned)
        request = default_attack_policy(actor, self._field(actor))
        self.assertEqual(request.skill_key, _T_CAST)


class FirstActorOverrideTests(unittest.TestCase):
    """run_round(first_actor=...) reorders the rolled sequence and nothing else."""

    _ROLLS = (70, 10, 40)

    def battlefield(self):
        # 100-point agility gaps (weight 10) dominate every d100 jitter, so
        # the rolled baseline order is fixed under any seeded rolls.
        fast = FakeEntity("fast", agility=40)
        mid = FakeEntity("mid", agility=30)
        slow = FakeEntity("slow", agility=20)
        return Battlefield(
            {"a": frozenset({"fast", "mid"}), "b": frozenset({"slow"})},
            {"fast": fast, "mid": mid, "slow": slow},
        )

    def stale_battlefield(self):
        field = Battlefield(
            {
                "a": frozenset({"fast", "dead", "fled", "fainted"}),
                "b": frozenset({"slow"}),
            },
            {
                "fast": FakeEntity("fast", agility=40),
                "dead": FakeEntity("dead", agility=40, hp=0),
                "fled": FakeEntity("fled", agility=40),
                "fainted": FakeEntity("fainted", agility=40),
                "slow": FakeEntity("slow", agility=20),
            },
        )
        field.fled.add("fled")
        field.knocked_out.add("fainted")
        return field

    def acting_order(self, battlefield, first_actor=(), rolls=_ROLLS):
        seen: list[str] = []

        def provider(entity, field):
            seen.append(str(entity.key))
            return None

        kwargs = {} if first_actor == () else {"first_actor": first_actor}
        with (
            patch(
                "world.rules.combat.roll_d100", side_effect=list(rolls)
            ) as roller,
            patch(
                "world.rules.combat.evaluate_combat_modifiers", return_value={}
            ),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(battlefield, provider, **kwargs)
        return seen, roller

    @covers_requirement("combat-resolution::run-round-accepts-an-optional-first-actor-override-that-reorders-the-rolled-sequence-and-nothing-else")
    def test_named_key_acts_first_and_rolls_stay_one_per_combatant(self):
        baseline, baseline_rolls = self.acting_order(self.battlefield())
        overridden, overridden_rolls = self.acting_order(
            self.battlefield(), first_actor="slow"
        )
        self.assertEqual(baseline, ["fast", "mid", "slow"])
        # The named key moves to the head; every other key keeps its rolled
        # relative order. The override never re-rolls: exactly one roll per
        # eligible combatant in both runs.
        self.assertEqual(overridden, ["slow", "fast", "mid"])
        self.assertEqual(baseline_rolls.call_count, 3)
        self.assertEqual(overridden_rolls.call_count, 3)

    @covers_requirement("combat-resolution::run-round-accepts-an-optional-first-actor-override-that-reorders-the-rolled-sequence-and-nothing-else")
    def test_override_changes_order_never_the_action_multiset(self):
        baseline, _ = self.acting_order(self.battlefield())
        overridden, _ = self.acting_order(
            self.battlefield(), first_actor="slow"
        )
        # Exactly one action per capable combatant under both runs; the
        # override grants no extra action and skips nobody.
        self.assertEqual(baseline, ["fast", "mid", "slow"])
        self.assertEqual(sorted(overridden), sorted(baseline))
        self.assertEqual(len(overridden), len(set(overridden)))

    @covers_requirement("combat-resolution::run-round-accepts-an-optional-first-actor-override-that-reorders-the-rolled-sequence-and-nothing-else")
    def test_stale_first_actor_keys_are_silent_noops(self):
        baseline, _ = self.acting_order(self.stale_battlefield())
        self.assertEqual(baseline, ["fast", "slow"])
        for stale_key in ("dead", "fled", "fainted", "not-in-roster"):
            with self.subTest(first_actor=stale_key):
                order, _ = self.acting_order(
                    self.stale_battlefield(), first_actor=stale_key
                )
                self.assertEqual(order, baseline)

    @covers_requirement("combat-resolution::run-round-accepts-an-optional-first-actor-override-that-reorders-the-rolled-sequence-and-nothing-else")
    def test_roll_initiative_sequence_is_the_only_source_of_order(self):
        # A deliberately non-score-derived order: any implementation that
        # re-scored or re-rolled to honour the override could not reproduce
        # this exact sequence.
        rolled = ["mid", "slow", "fast"]
        seen: list[str] = []

        def provider(entity, field):
            seen.append(str(entity.key))
            return None

        with (
            patch(
                "world.rules.combat.roll_initiative", return_value=list(rolled)
            ) as roller,
            patch(
                "world.rules.combat.roll_d100",
                side_effect=AssertionError("re-rolled"),
            ),
            patch(
                "world.rules.combat.evaluate_combat_modifiers", return_value={}
            ),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield(), provider, first_actor="slow")
        self.assertEqual(roller.call_count, 1)
        self.assertEqual(seen, ["slow", "mid", "fast"])
