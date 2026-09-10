"""Combat-loop integration for the monster action provider."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.rules.action import ActionResolver
from world.rules.combat import Battlefield, _max_hp, _stored_hp, run_round
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import EventLog
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    MONSTER_BEHAVIOUR_YAML,
    monster_behaviour_policy,
)
from world.rules.overwhelm import (
    OverwhelmResult,
    classify_overwhelm,
    resolve_overwhelm,
    team_effective_power,
)

from ._combat_session_helpers import open_synthetic_scope, synth_innate_overlay
from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import (
    FakeMonster,
    _SCOPE_EXTRA,
    _T_CLAW,
    _T_SPELL,
)


def _scope_extra():
    """Kit rows plus the runtime-keyed innate attack/flee rows.

    The resolver reaches for ``BASIC_ATTACK_KEY``/``FLEE_SKILL_KEY`` on
    every monster turn, so any scope whose requests may RESOLVE must carry
    synthetic rows under those runtime keys.
    """
    extra = {logical: dict(rows) for logical, rows in _SCOPE_EXTRA.items()}
    extra["skills"].update(synth_innate_overlay()["skills"])
    return extra


def _expected_default_skill(tier: str) -> str:
    """The skill the tier's DEFAULT archetype must produce at near-zero hp.

    A profile with a flee threshold flees; the null-threshold apex tier is
    built with zero magic_power and zero sp, so the only damage skill it can
    afford is the innate attack row — the highest-expected-damage choice.
    """
    profile = BEHAVIOUR_PROFILES[MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][tier]]
    return FLEE_SKILL_KEY if profile.flee_hp_fraction is not None else BASIC_ATTACK_KEY


class MonsterBehaviourIntegrationTests(unittest.TestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)
        self.monster = FakeMonster(
            "monster",
            hp=10000,
            max_hp=10000,
            owned=[_T_CLAW.key],
            atk_phys=1000,
            agility=1000,
            defense=1000,
            magic_power=1000,
        )
        self.enemy = FakeEntity("enemy", hp=100, agility=1)
        self.field = Battlefield(
            {
                "monsters": frozenset({"monster"}),
                "party": frozenset({"enemy"}),
            },
            {"monster": self.monster, "enemy": self.enemy},
        )

    @covers_requirement("monster-action-policy::monster-behaviour-policy-is-a-complete-drop-in-action-provider")
    def test_run_round_resolves_policy_request(self):
        log = EventLog("monster", _T_CLAW.key, ("enemy",), (), 6)
        result = type(
            "Result",
            (),
            {"outcome": "success", "event_log": log},
        )()
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=["monster"],
            ),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.combat.ActionResolver.resolve", return_value=result),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(self.field, monster_behaviour_policy)
        self.assertEqual(logs, [log])

    def test_overwhelm_accepts_policy_without_special_case(self):
        observed = []

        def run_one_round(field, provider, **kwargs):
            observed.append(provider(self.monster, field))
            self.monster.skills.values.update(
                atk_phys=1,
                agility=1,
                defense=1,
                magic_power=1,
            )
            return []

        with (
            patch(
                "world.rules.overwhelm.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.overwhelm.combat.run_round",
                side_effect=run_one_round,
            ),
        ):
            result = resolve_overwhelm(
                self.field,
                monster_behaviour_policy,
                max_rounds=1,
            )
        self.assertIsInstance(result, OverwhelmResult)
        self.assertEqual(observed[0].skill_key, _T_CLAW.key)
        self.assertEqual(observed[0].targets, [self.enemy])

    @covers_requirement("monster-action-policy::a-monster-with-zero-actions-per-turn-is-skipped-by-the-existing-gate-with-no")
    def test_zero_actions_gate_never_calls_policy(self):
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=["monster"],
            ),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={"actions_per_turn": 0},
            ),
            patch(
                "world.rules.tests.test_monster_behaviour_integration."
                "monster_behaviour_policy"
            ) as policy,
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(self.field, policy)
        policy.assert_not_called()
        self.assertEqual(logs[0].entries[0].kind, "action_skipped")


class MonsterBehaviourResolverIntegrationTests(EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()

    def test_depleted_resource_falls_back_and_resolves(self):
        monster = create_object(Monster, key="resource-monster")
        monster.threat_tier = "mid"
        monster.apply_monster_tier()
        monster.db.skills = {
            "active": [_T_CLAW.key, _T_SPELL.key],
            "passive": [],
        }
        monster.traits.mp.current = 0
        monster.traits.sp.base = 100
        monster.traits.sp.current = 100

        target = create_object(PlayerCharacter, key="resource-target")
        target.race = "human"
        target.apply_race_baseline()
        battlefield = Battlefield(
            {
                "monsters": frozenset({monster.key}),
                "party": frozenset({target.key}),
            },
            {monster.key: monster, target.key: target},
        )

        # The mid-tier pack-hunter profile picks by highest expected damage.
        # The mp-costing spell is unaffordable; the zero-cost physical strike
        # and the innate attack row tie on expected damage, so the dice
        # tie-break must be pinned to the first owned candidate.
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=0,
        ):
            request = monster_behaviour_policy(monster, battlefield)
        self.assertEqual(request.skill_key, _T_CLAW.key)
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")


class MonsterFleeResolverIntegrationTests(EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(self, "skills", "elements", extra=_scope_extra())
        super().setUp()
        self.monster = create_object(Monster, key="flee-monster")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier()
        self.monster.db.skills = {"active": [], "passive": []}
        self.monster.traits.hp.current = 1

        self.target = create_object(PlayerCharacter, key="flee-target")
        self.target.race = "human"
        self.target.apply_race_baseline()
        self.target.db.skills = {"active": [], "passive": []}
        self.field = Battlefield(
            {
                "monsters": frozenset({self.monster.key}),
                "party": frozenset({self.target.key}),
            },
            {self.monster.key: self.monster, self.target.key: self.target},
        )

    def _assert_flee_preconditions(self):
        self.assertEqual(self.monster.threat_tier, "low")
        self.assertLessEqual(
            _stored_hp(self.monster) / _max_hp(self.monster),
            BEHAVIOUR_PROFILES[
                MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]["low"]
            ].flee_hp_fraction,
        )

    def test_generated_flee_request_is_registered_and_resolves(self):
        self._assert_flee_preconditions()
        request = monster_behaviour_policy(self.monster, self.field)
        self.assertEqual(request.skill_key, FLEE_SKILL_KEY)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertIn(self.monster.key, self.field.fled)
        self.assertEqual(result.event_log.entries[0].kind, "disengage_attempt")

    def test_run_round_successful_flee_removes_monster_from_combat(self):
        self._assert_flee_preconditions()
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=[self.monster.key, self.target.key],
            ),
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(self.field, monster_behaviour_policy)
        self.assertEqual(logs[0].entries[0].kind, "disengage_attempt")
        self.assertTrue(logs[0].entries[0].data["success"])
        self.assertIn(self.monster.key, self.field.fled)
        self.assertEqual(
            team_effective_power(self.field, "monsters"),
            0,
        )

    def test_run_round_failed_flee_costs_turn_without_attack(self):
        self._assert_flee_preconditions()
        before = self.target.traits.hp.current
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=[self.monster.key, self.target.key],
            ),
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            logs = run_round(self.field, monster_behaviour_policy)
        self.assertEqual(logs[0].entries[0].kind, "disengage_attempt")
        self.assertFalse(logs[0].entries[0].data["success"])
        self.assertNotIn(self.monster.key, self.field.fled)
        self.assertEqual(self.target.traits.hp.current, before)

    @covers_requirement("monster-flee-policy::existing-combat-orchestration-resolves-monster-flee-through-the-sole-writer")
    def test_overwhelm_uses_policy_without_a_flee_branch(self):
        self.target.race = "elf"
        self.target.apply_race_baseline()
        self._assert_flee_preconditions()
        self.assertEqual(classify_overwhelm(self.field), "party")
        source = (
            Path(__file__).parents[1] / "overwhelm.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("FLEE_SKILL_KEY", source)
        with (
            patch(
                "world.rules.combat.roll_initiative",
                return_value=[self.monster.key, self.target.key],
            ),
            patch(
                "world.rules.disengage._attempt_flee",
                return_value=(
                    True,
                    {
                        "roll": 100,
                        "actor_agility": 10.0,
                        "pursuer_agility": 10.0,
                    },
                ),
            ),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            result = resolve_overwhelm(
                self.field,
                monster_behaviour_policy,
                max_rounds=1,
        )
        self.assertTrue(result.battle_over)
        self.assertIn(self.monster.key, self.field.fled)
        self.assertEqual(result.verdict_after, "party")

    def test_tier_default_and_override_decisions_have_fixed_outcomes(self):
        # Every near-zero-hp monster follows its tier DEFAULT archetype — the
        # flee-threshold profiles flee, the null-threshold apex profile
        # strikes with the zero-cost physical row — and the instance override
        # re-routes the decision without touching the tier assignment.
        apex_tier = next(
            tier
            for tier, archetype in MONSTER_BEHAVIOUR_YAML[
                "tier_default_archetype"
            ].items()
            if BEHAVIOUR_PROFILES[archetype].flee_hp_fraction is None
        )
        other_tiers = [
            tier
            for tier in MONSTER_BEHAVIOUR_YAML["tier_default_archetype"]
            if tier != apex_tier
        ]
        cases = (
            [(tier, None) for tier in other_tiers]
            + [(apex_tier, None)]
            + [(other_tiers[0], "tactical_caster")]
        )
        for index, (tier, override) in enumerate(cases):
            with self.subTest(tier=tier, override=override):
                expected_skill = (
                    FLEE_SKILL_KEY
                    if override is not None
                    else _expected_default_skill(tier)
                )
                monster = create_object(Monster, key=f"golden-monster-{index}")
                monster.threat_tier = tier
                monster.behaviour_tree = override
                monster.apply_monster_tier()
                monster.db.skills = {"active": [_T_CLAW.key], "passive": []}
                monster.traits.mp.base = 100
                monster.traits.mp.current = 100
                monster.traits.hp.current = 1
                target = create_object(
                    PlayerCharacter,
                    key=f"golden-target-{index}",
                )
                target.race = "human"
                target.apply_race_baseline()
                target.db.skills = {"active": [], "passive": []}
                battlefield = Battlefield(
                    {
                        "monsters": frozenset({monster.key}),
                        "party": frozenset({target.key}),
                    },
                    {monster.key: monster, target.key: target},
                )
                request = monster_behaviour_policy(monster, battlefield)
                self.assertEqual(request.skill_key, expected_skill)
                if expected_skill == FLEE_SKILL_KEY:
                    with patch(
                        "world.rules.disengage.roll_d100",
                        return_value=100,
                    ):
                        result = ActionResolver.resolve(request)
                    self.assertEqual(result.outcome, "success")
                    self.assertTrue(result.event_log.entries[0].data["success"])
                    self.assertIn(monster.key, battlefield.fled)
                else:
                    with (
                        patch(
                            "world.rules.combat.evaluate_combat_modifiers",
                            return_value={},
                        ),
                        patch("world.rules.combat.roll_d100", return_value=100),
                    ):
                        result = ActionResolver.resolve(request)
                    self.assertEqual(result.outcome, "success")
                    self.assertNotIn(monster.key, battlefield.fled)
