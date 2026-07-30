"""Tests for bounded single-call overwhelm resolution."""

import random
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.combat import (
    Battlefield,
    default_attack_policy,
    is_battle_over,
    run_round,
)
from world.rules.event_log import EventEntry, EventLog
from world.rules.event_log import render_plain_text
from world.rules.overwhelm import (
    _resolve_overwhelm_raw,
    resolve_overwhelm,
)

from .combat_fixtures import FakeEntity


def battlefield() -> Battlefield:
    attacker = FakeEntity(
        "elf",
        hp=10000,
        max_hp=10000,
        atk_phys=88,
        agility=92,
        defense=90,
        magic_level=250,
    )
    defender = FakeEntity(
        "human",
        hp=120,
        atk_phys=8,
        agility=9,
        defense=7,
        magic_level=40,
    )
    return Battlefield(
        {
            "elves": frozenset({"elf"}),
            "humans": frozenset({"human"}),
        },
        {"elf": attacker, "human": defender},
    )


def damage_log(amount: int) -> EventLog:
    return EventLog(
        "elf",
        "attack",
        ("human",),
        (
            EventEntry(
                "roll",
                "elf",
                "human",
                {"raw_roll": 80, "hit": True},
                "{actor} 的擲骰結果為 {data[raw_roll]}。",
            ),
            EventEntry(
                "damage",
                "elf",
                "human",
                {"amount": amount},
                "{actor} 對 {target} 造成 {data[amount]} 點傷害。",
            ),
        ),
        6,
    )


class ResolutionTests(unittest.TestCase):
    def test_single_round_completion_and_time(self):
        field = battlefield()

        def run_round(current, provider):
            current.roster["human"].traits.hp.value = 0
            return [damage_log(120)]

        with (
            patch(
                "world.rules.overwhelm.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.overwhelm.combat.run_round",
                side_effect=run_round,
            ) as runner,
        ):
            result = resolve_overwhelm(field, lambda entity, current: None)
        runner.assert_called_once()
        self.assertEqual(result.rounds_elapsed, 1)
        self.assertEqual(result.total_seconds, 6)
        self.assertTrue(result.battle_over)
        self.assertEqual(result.overwhelming_team, "elves")
        self.assertEqual(result.verdict_after, "elves")

    def test_reclassification_stops_resolution(self):
        field = battlefield()

        def run_round(current, provider):
            current.roster["elf"].skills.values["agility"] = 10
            current.roster["elf"].skills.values["atk_phys"] = 1
            current.roster["elf"].skills.values["defense"] = 1
            current.roster["elf"].skills.values["magic_level"] = 1
            return []

        with (
            patch(
                "world.rules.overwhelm.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.overwhelm.combat.run_round",
                side_effect=run_round,
            ) as runner,
        ):
            result = resolve_overwhelm(field, lambda entity, current: None)
        runner.assert_called_once()
        self.assertEqual(result.rounds_elapsed, 1)
        self.assertIsNone(result.verdict_after)
        self.assertFalse(result.battle_over)

    def test_contested_and_finished_battles_do_not_run_round(self):
        contested = Battlefield(
            {
                "first": frozenset({"first"}),
                "second": frozenset({"second"}),
            },
            {
                "first": FakeEntity("first"),
                "second": FakeEntity("second"),
            },
        )
        finished = battlefield()
        finished.roster["human"].traits.hp.value = 0
        with (
            patch(
                "world.rules.overwhelm.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.overwhelm.combat.run_round") as runner,
        ):
            self.assertEqual(
                resolve_overwhelm(
                    contested,
                    lambda entity, current: None,
                ).rounds_elapsed,
                0,
            )
            self.assertEqual(
                resolve_overwhelm(
                    finished,
                    lambda entity, current: None,
                ).rounds_elapsed,
                0,
            )
        runner.assert_not_called()

    def test_max_rounds_is_honest_safety_cap(self):
        field = battlefield()
        with (
            patch(
                "world.rules.overwhelm.classify_overwhelm",
                return_value="elves",
            ),
            patch(
                "world.rules.overwhelm.combat.is_battle_over",
                return_value=False,
            ),
            patch(
                "world.rules.overwhelm.combat.run_round",
                return_value=[],
            ) as runner,
        ):
            result = resolve_overwhelm(
                field,
                lambda entity, current: None,
                max_rounds=3,
            )
        self.assertEqual(runner.call_count, 3)
        self.assertEqual(result.rounds_elapsed, 3)
        self.assertEqual(result.total_seconds, 18)
        self.assertFalse(result.battle_over)

    def test_raw_logs_are_exactly_the_run_round_outputs(self):
        field = battlefield()
        expected = [damage_log(20), damage_log(30)]
        with (
            patch(
                "world.rules.overwhelm.classify_overwhelm",
                return_value="elves",
            ),
            patch(
                "world.rules.overwhelm.combat.is_battle_over",
                side_effect=[False, False, False, True],
            ),
            patch(
                "world.rules.overwhelm.combat.run_round",
                side_effect=[[expected[0]], [expected[1]]],
            ),
        ):
            _, _, raw, rounds = _resolve_overwhelm_raw(
                field,
                lambda entity, current: None,
                max_rounds=12,
            )
        self.assertEqual(raw, expected)
        self.assertEqual(rounds, 2)

    def test_negative_round_cap_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            resolve_overwhelm(
                battlefield(),
                lambda entity, current: None,
                max_rounds=-1,
            )


class RealCombatEquivalenceTests(EvenniaTest):
    def _entity(self, key: str, *, strong: bool) -> PlayerCharacter:
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "human"
        entity.apply_race_baseline()
        values = (
            {
                "hp": 10000,
                "sp": 1000,
                "atk_phys": 1000,
                "agility": 92,
                "defense": 90,
                "magic_level": 250,
            }
            if strong
            else {
                "hp": 120,
                "sp": 100,
                "atk_phys": 8,
                "agility": 9,
                "defense": 7,
                "magic_level": 40,
            }
        )
        for trait_key, value in values.items():
            trait = getattr(entity.traits, trait_key)
            trait.base = value
            if hasattr(trait, "current"):
                trait.current = value
        entity.db.skills = {"active": ["shadow_slash"], "passive": []}
        return entity

    def _field(self, suffix: str, *, strong_first: bool) -> Battlefield:
        first = self._entity(f"first-{suffix}", strong=strong_first)
        second = self._entity(f"second-{suffix}", strong=not strong_first)
        return Battlefield(
            {
                "first": frozenset({first.key}),
                "second": frozenset({second.key}),
            },
            {first.key: first, second.key: second},
        )

    @staticmethod
    def _state(field: Battlefield) -> dict[str, float]:
        return {
            key.split("-")[0]: entity.traits.hp.value
            for key, entity in field.roster.items()
        }

    @staticmethod
    def _logs(logs):
        return [
            (
                log.actor.split("-")[0],
                tuple(
                    (
                        item.kind,
                        item.actor.split("-")[0],
                        None
                        if item.target is None
                        else item.target.split("-")[0],
                        tuple(sorted(item.data.items())),
                    )
                    for item in log.entries
                ),
            )
            for log in logs
        ]

    def _assert_direction_is_exact(self, *, strong_first: bool) -> None:
        resolved = self._field("resolved", strong_first=strong_first)
        random.seed(1017)
        initial, verdict, raw, rounds = _resolve_overwhelm_raw(
            resolved,
            default_attack_policy,
            12,
        )
        manual = self._field("manual", strong_first=strong_first)
        random.seed(1017)
        manual_logs = []
        for _ in range(rounds):
            manual_logs.extend(run_round(manual, default_attack_policy))
        expected_team = "first" if strong_first else "second"
        self.assertEqual(initial, expected_team)
        self.assertEqual(verdict, expected_team)
        self.assertEqual(self._state(resolved), self._state(manual))
        self.assertEqual(self._logs(raw), self._logs(manual_logs))
        self.assertEqual(is_battle_over(resolved), is_battle_over(manual))
        self.assertTrue(is_battle_over(resolved))
        self.assertEqual(rounds, 1)

    def test_real_combat_exact_equivalence_in_first_team_direction(self):
        self._assert_direction_is_exact(strong_first=True)

    def test_real_combat_exact_equivalence_in_reverse_direction(self):
        self._assert_direction_is_exact(strong_first=False)

    def test_real_bounded_multi_round_encounter_completes_and_renders(self):
        elf = self._entity("elf-multi", strong=True)
        elf.traits.atk_phys.base = 88
        monsters = [
            self._entity(f"monster-{index}-multi", strong=False)
            for index in range(3)
        ]
        for monster in monsters:
            monster.traits.hp.base = 90
            monster.traits.hp.current = 90
            monster.traits.atk_phys.base = 6
            monster.traits.agility.base = 6
            monster.traits.defense.base = 6
            monster.traits.magic_level.base = 0
        field = Battlefield(
            {
                "elves": frozenset({elf.key}),
                "monsters": frozenset(monster.key for monster in monsters),
            },
            {
                elf.key: elf,
                **{monster.key: monster for monster in monsters},
            },
        )
        random.seed(2029)
        result = resolve_overwhelm(field, default_attack_policy)
        self.assertTrue(result.battle_over)
        self.assertGreater(result.rounds_elapsed, 1)
        self.assertLessEqual(result.rounds_elapsed, 5)
        rendered_once = "\n".join(
            render_plain_text(log) for log in result.event_logs
        )
        rendered_twice = "\n".join(
            render_plain_text(log) for log in result.event_logs
        )
        self.assertTrue(rendered_once)
        self.assertNotIn("{", rendered_once)
        self.assertEqual(rendered_once, rendered_twice)
