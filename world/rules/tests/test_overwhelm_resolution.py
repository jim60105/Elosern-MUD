"""Tests for bounded single-call overwhelm resolution."""

from tools.spec_traceability import covers_requirement

import random
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

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

from ._combat_session_helpers import open_synthetic_scope, synth_damage_skill
from .combat_fixtures import FakeEntity


# File-local registered row (data independence): the real-combat
# equivalence fixtures own exactly this damage skill, and the
# commanded-action key below is the same row.
_T_STRIKE = synth_damage_skill("t_equiv_strike", "合成打擊")


def battlefield() -> Battlefield:
    attacker = FakeEntity(
        "elf",
        hp=10000,
        max_hp=10000,
        atk_phys=88,
        agility=92,
        defense=90,
        magic_power=250,
    )
    defender = FakeEntity(
        "human",
        hp=120,
        atk_phys=8,
        agility=9,
        defense=7,
        magic_power=40,
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
    @covers_requirement("single-shot-resolution::single-shot-resolution-is-exactly-consistent-with-per-round-resolution-under-the-same")
    def test_single_round_completion_and_time(self):
        field = battlefield()

        def run_round(current, provider, **kwargs):
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

        def run_round(current, provider, **kwargs):
            current.roster["elf"].skills.values["agility"] = 10
            current.roster["elf"].skills.values["atk_phys"] = 1
            current.roster["elf"].skills.values["defense"] = 1
            current.roster["elf"].skills.values["magic_power"] = 1
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

    @covers_requirement("single-shot-resolution::resolve-overwhelm-resolves-an-overwhelm-classified-encounter-by-reusing-run-round")
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

    @covers_requirement("single-shot-resolution::a-finite-max-rounds-safety-cap-is-a-named-tested-outcome-not-an-implicit-assumption")
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
            _, _, raw, rounds, _ = _resolve_overwhelm_raw(
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


class FirstActorForwardingTests(unittest.TestCase):
    """resolve_overwhelm(first_actor=...) reaches round one and only round one."""

    def recorder(self):
        calls: list[tuple[tuple, dict]] = []

        def record(*args, **kwargs):
            calls.append((args, dict(kwargs)))
            return []

        return calls, record

    @covers_requirement("single-shot-resolution::resolve-overwhelm-accepts-a-first-actor-override-that-applies-to-round-one-only")
    def test_override_reaches_round_one_and_none_after(self):
        field = battlefield()

        def provider(entity, current):
            return None

        calls, record = self.recorder()
        with (
            patch(
                "world.rules.overwhelm.classify_overwhelm",
                return_value="elves",
            ),
            patch(
                "world.rules.overwhelm.combat.is_battle_over",
                return_value=False,
            ),
            patch("world.rules.overwhelm.combat.run_round", side_effect=record),
        ):
            result = resolve_overwhelm(
                field,
                provider,
                max_rounds=3,
                first_actor="elf",
            )
        self.assertEqual(result.rounds_elapsed, 3)
        self.assertEqual(result.total_seconds, 18)
        self.assertEqual(len(calls), 3)
        for args, _ in calls:
            self.assertEqual(args, (field, provider))
        self.assertEqual(calls[0][1], {"first_actor": "elf"})
        self.assertEqual(calls[1][1], {"first_actor": None})
        self.assertEqual(calls[2][1], {"first_actor": None})

    @covers_requirement("single-shot-resolution::resolve-overwhelm-accepts-a-first-actor-override-that-applies-to-round-one-only")
    def test_default_mode_call_forwards_nothing_new(self):
        field = battlefield()

        def provider(entity, current):
            return None

        calls, record = self.recorder()
        with (
            patch(
                "world.rules.overwhelm.classify_overwhelm",
                return_value="elves",
            ),
            patch(
                "world.rules.overwhelm.combat.is_battle_over",
                # Initial check, round-1 loop check, loop exit, final report.
                side_effect=[False, False, True, False],
            ),
            patch("world.rules.overwhelm.combat.run_round", side_effect=record),
        ):
            resolve_overwhelm(field, provider)
        # fix-dot-kill-credit D4 discipline: a default-mode call's call into
        # run_round() is exactly the pre-change (battlefield, provider) call.
        self.assertEqual(calls, [((field, provider), {})])

    @covers_requirement("single-shot-resolution::resolve-overwhelm-accepts-a-first-actor-override-that-applies-to-round-one-only")
    def test_override_starts_no_round_when_none_can_run(self):
        for label, rounds_cap, over in (
            ("zero-round cap", 0, False),
            ("battle already over", 3, True),
        ):
            with self.subTest(case=label):
                field = battlefield()

                def provider(entity, current):
                    return None

                calls, record = self.recorder()
                with (
                    patch(
                        "world.rules.overwhelm.classify_overwhelm",
                        return_value="elves",
                    ),
                    patch(
                        "world.rules.overwhelm.combat.is_battle_over",
                        return_value=over,
                    ),
                    patch(
                        "world.rules.overwhelm.combat.run_round",
                        side_effect=record,
                    ),
                ):
                    resolve_overwhelm(
                        field, provider, max_rounds=rounds_cap, first_actor="elf"
                    )
                self.assertEqual(calls, [])


class RealCombatEquivalenceTests(EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(
            self, "skills", "elements", extra={"skills": {_T_STRIKE.key: _T_STRIKE}}
        )
        super().setUp()

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
                "magic_power": 250,
            }
            if strong
            else {
                "hp": 120,
                "sp": 100,
                "atk_phys": 8,
                "agility": 9,
                "defense": 7,
                "magic_power": 40,
            }
        )
        for trait_key, value in values.items():
            trait = getattr(entity.traits, trait_key)
            trait.base = value
            if hasattr(trait, "current"):
                trait.current = value
        entity.db.skills = {"active": [_T_STRIKE.key], "passive": []}
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
        def _data(item):
            # Normalize stable dbref identity to the entry's team-relative
            # target label so exact-equivalence holds across separately created
            # battlefields (quest-runtime: target_defeated carries target_id).
            rows = []
            for key, value in item.data.items():
                if key == "target_id":
                    value = None if item.target is None else item.target.split("-")[0]
                rows.append((key, value))
            return tuple(sorted(rows))

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
                        _data(item),
                    )
                    for item in log.entries
                ),
            )
            for log in logs
        ]

    @staticmethod
    def _full_logs(logs):
        """Every EventLog field, with only unstable dbref identity normalized.

        Unlike ``_logs``, this keeps ``skill_key``, ``targets``, and
        ``time_cost_seconds`` so result-equality claims cover the whole
        emitted log sequence, including every ``"roll"``-kind entry.
        """

        def _data(item):
            rows = []
            for key, value in item.data.items():
                if key == "target_id":
                    value = None if item.target is None else item.target.split("-")[0]
                rows.append((key, value))
            return tuple(sorted(rows))

        return [
            (
                log.actor.split("-")[0],
                log.skill_key,
                tuple(target.split("-")[0] for target in log.targets),
                log.time_cost_seconds,
                tuple(
                    (
                        item.kind,
                        item.actor.split("-")[0],
                        None
                        if item.target is None
                        else item.target.split("-")[0],
                        _data(item),
                    )
                    for item in log.entries
                ),
            )
            for log in logs
        ]

    def _recording_provider(self, order):
        def provider(entity, field):
            order.append(str(entity.key).split("-")[0])
            return default_attack_policy(entity, field)

        return provider

    @covers_requirement("combat-resolution::run-round-accepts-an-optional-first-actor-override-that-reorders-the-rolled-sequence-and-nothing-else")
    def test_first_actor_none_is_byte_identical_to_omitted(self):
        omitted = self._field("omitted", strong_first=True)
        explicit = self._field("explicit", strong_first=True)
        omitted_order: list[str] = []
        explicit_order: list[str] = []
        random.seed(1017)
        omitted_logs = run_round(omitted, self._recording_provider(omitted_order))
        random.seed(1017)
        explicit_logs = run_round(
            explicit,
            self._recording_provider(explicit_order),
            first_actor=None,
        )
        self.assertEqual(omitted_order, explicit_order)
        self.assertEqual(self._state(omitted), self._state(explicit))
        self.assertEqual(
            self._full_logs(omitted_logs), self._full_logs(explicit_logs)
        )
        # The compared sequence really carried the dice evidence.
        self.assertTrue(
            any(
                entry.kind == "roll"
                for log in omitted_logs
                for entry in log.entries
            )
        )

    @covers_requirement("single-shot-resolution::the-first-actor-override-influences-turn-order-alone-never-resolution-outputs")
    def test_stale_override_leaves_every_result_field_unchanged(self):
        plain = self._field("plain", strong_first=True)
        stale = self._field("stale", strong_first=True)
        random.seed(1017)
        baseline = resolve_overwhelm(plain, default_attack_policy)
        random.seed(1017)
        result = resolve_overwhelm(
            stale,
            default_attack_policy,
            first_actor="not-in-roster",
        )
        self.assertEqual(result.rounds_elapsed, baseline.rounds_elapsed)
        self.assertEqual(result.total_seconds, result.rounds_elapsed * 6)
        self.assertEqual(result.total_seconds, baseline.total_seconds)
        self.assertEqual(result.overwhelming_team, baseline.overwhelming_team)
        self.assertEqual(result.verdict_after, baseline.verdict_after)
        self.assertEqual(result.battle_over, baseline.battle_over)
        self.assertEqual(self._state(stale), self._state(plain))
        self.assertEqual(
            self._full_logs(result.event_logs),
            self._full_logs(baseline.event_logs),
        )

    def _assert_direction_is_exact(self, *, strong_first: bool) -> None:
        resolved = self._field("resolved", strong_first=strong_first)
        random.seed(1017)
        initial, verdict, raw, rounds, _ = _resolve_overwhelm_raw(
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

    @covers_requirement("single-shot-resolution::resolve-overwhelm-stops-the-moment-classify-overwhelm-s-verdict-changes")
    def test_real_combat_exact_equivalence_in_first_team_direction(self):
        self._assert_direction_is_exact(strong_first=True)

    def test_real_combat_exact_equivalence_in_reverse_direction(self):
        # Resolver-math coverage only: `resolve_overwhelm` stays
        # direction-agnostic (fix-combat-session-roster-and-overwhelm D3),
        # but the session facade never dispatches it for a foe-overwhelming
        # verdict, so this is not a production dispatch contract.
        self._assert_direction_is_exact(strong_first=False)

    @covers_requirement("single-shot-resolution::resolve-overwhelm-resolves-an-overwhelm-classified-encounter-by-reusing-run-round")
    def test_commanded_identity_never_changes_resolution(self):
        plain = self._field("plain", strong_first=True)
        random.seed(1017)
        baseline = resolve_overwhelm(plain, default_attack_policy)
        marked = self._field("marked", strong_first=True)
        random.seed(1017)
        result = resolve_overwhelm(
            marked,
            default_attack_policy,
            commanded_actor="first-marked",
            commanded_action_kind="skill", commanded_action_key=_T_STRIKE.key,
        )
        self.assertEqual(result.rounds_elapsed, baseline.rounds_elapsed)
        self.assertEqual(result.total_seconds, baseline.total_seconds)
        self.assertEqual(result.verdict_after, baseline.verdict_after)
        self.assertEqual(result.battle_over, baseline.battle_over)
        self.assertEqual(self._state(marked), self._state(plain))

        def without_markers(logs):
            return [
                (actor, tuple(row for row in entries if row[0] != "commanded_action"))
                for actor, entries in self._logs(logs)
            ]

        self.assertEqual(
            without_markers(result.event_logs),
            without_markers(baseline.event_logs),
        )
        markers = [
            (actor, entries)
            for actor, entries in self._logs(result.event_logs)
            if any(row[0] == "commanded_action" for row in entries)
        ]
        self.assertEqual(len(markers), 1)
        self.assertEqual(
            [
                (actor, entries)
                for actor, entries in self._logs(baseline.event_logs)
                if any(row[0] == "commanded_action" for row in entries)
            ],
            [],
        )

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
            monster.traits.magic_power.base = 0
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
