"""Combat-loop integration for the monster action provider."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import ActionResolver
from world.rules.combat import Battlefield, run_round
from world.rules.event_log import EventLog
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.overwhelm import OverwhelmResult, resolve_overwhelm

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

        def run_one_round(field, provider):
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


class MonsterBehaviourResolverIntegrationTests(EvenniaTest):
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

        request = monster_behaviour_policy(monster, battlefield)
        self.assertEqual(request.skill_key, "shadow_slash")
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={},
        ):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
