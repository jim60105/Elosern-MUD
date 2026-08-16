"""Combat-loop integration for the monster action provider."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import ActionResolver
from world.rules.combat import Battlefield, _max_hp, _stored_hp, run_round
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.event_log import EventLog
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.overwhelm import (
    OverwhelmResult,
    classify_overwhelm,
    resolve_overwhelm,
    team_effective_power,
)

from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster


class MonsterBehaviourIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.monster = FakeMonster(
            "monster",
            hp=10000,
            max_hp=10000,
            owned=["shadow_slash"],
            atk_phys=1000,
            agility=1000,
            defense=1000,
            magic_level=1000,
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
        log = EventLog("monster", "shadow_slash", ("enemy",), (), 6)
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
                magic_level=1,
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
        self.assertEqual(observed[0].skill_key, "shadow_slash")
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
    def test_depleted_resource_falls_back_and_resolves(self):
        monster = create_object(Monster, key="resource-monster")
        monster.threat_tier = "mid"
        monster.apply_monster_tier()
        monster.db.skills = {
            "active": ["wind_blade", "shadow_slash"],
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

        # The mid-tier pack-hunter profile picks by highest expected damage, and
        # both affordable single-target physical skills tie at the same attack
        # value, so the dice tie-break must be pinned for a deterministic test.
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100",
            return_value=0,
        ):
            request = monster_behaviour_policy(monster, battlefield)
        self.assertEqual(request.skill_key, "shadow_slash")
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")


class MonsterFleeResolverIntegrationTests(EvenniaTestCase):
    def setUp(self):
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
            0.35,
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
        # The calamity apex predator has no magic level, so the innate
        # physical `basic_attack` is its highest-expected-damage choice over a
        # zero-magic `fire_ball` (deliberate second-innate update, task 7.13).
        cases = (
            ("low", None, FLEE_SKILL_KEY),
            ("mid", None, FLEE_SKILL_KEY),
            ("high", None, FLEE_SKILL_KEY),
            ("calamity", None, "basic_attack"),
            ("high", "tactical_caster", FLEE_SKILL_KEY),
        )
        for index, (tier, override, expected_skill) in enumerate(cases):
            with self.subTest(tier=tier, override=override):
                monster = create_object(Monster, key=f"golden-monster-{index}")
                monster.threat_tier = tier
                monster.behaviour_tree = override
                monster.apply_monster_tier()
                monster.db.skills = {"active": ["fire_ball"], "passive": []}
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
