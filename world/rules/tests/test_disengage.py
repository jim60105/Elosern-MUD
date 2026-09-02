"""Pure tests for disengagement odds, staging, and event conversion."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import random
import unittest
from unittest.mock import patch

from world.rules.action import (
    PendingEffect,
    RejectReason,
    RejectedAction,
    SNAPSHOTTED_SURFACES,
    UnsnapshottedSurfaceError,
    _EFFECT_HANDLER_SURFACES,
    _commit,
    _entries_from_effect,
    register_effect_handler,
)
from world.rules.combat import Battlefield
from world.rules.disengage import (
    _adjusted_agility,
    _attempt_flee,
    _fastest_pursuer_agility,
    _handle_disengage,
)
from world.rules.monster_behaviour import monster_behaviour_policy

from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster


def _field(actor, *pursuers):
    roster = {entity.key: entity for entity in (actor, *pursuers)}
    return Battlefield(
        {
            "escaping": frozenset({actor.key}),
            "pursuing": frozenset(entity.key for entity in pursuers),
        },
        roster,
    )


class DisengageFormulaTests(unittest.TestCase):
    @covers_requirement("disengage-action::the-disengage-effect-handler-computes-flee-success-from-the-same-agility-difference")
    def test_parity_is_about_half_over_fixed_seed_trials(self):
        actor = FakeEntity("actor", agility=10)
        field = _field(actor, FakeEntity("pursuer", agility=10))
        generator = random.Random(20260731)
        with (
            patch(
                "world.rules.disengage.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.disengage.roll_d100",
                side_effect=lambda: generator.randint(1, 100),
            ),
        ):
            successes = sum(_attempt_flee(actor, field)[0] for _ in range(10_000))
        self.assertLess(abs(successes / 10_000 - 0.5), 0.02)

    def test_saturated_race_scale_outcomes_ignore_seed(self):
        human = FakeEntity("human", agility=9)
        elf = FakeEntity("elf", agility=92)
        with patch(
            "world.rules.disengage.evaluate_combat_modifiers",
            return_value={},
        ):
            for raw_roll in (1, 25, 50, 75, 100):
                with patch(
                    "world.rules.disengage.roll_d100",
                    return_value=raw_roll,
                ):
                    self.assertFalse(_attempt_flee(human, _field(human, elf))[0])
                    self.assertTrue(_attempt_flee(elf, _field(elf, human))[0])

    def test_fastest_living_non_fled_pursuer_is_used(self):
        actor = FakeEntity("actor", agility=20)
        slow = FakeEntity("slow", agility=5)
        fast = FakeEntity("fast", agility=30)
        dead = FakeEntity("dead", hp=0, agility=90)
        fled = FakeEntity("fled", agility=80)
        field = _field(actor, slow, fast, dead, fled)
        field.fled.add("fled")
        with patch(
            "world.rules.disengage.evaluate_combat_modifiers",
            return_value={},
        ):
            self.assertEqual(_fastest_pursuer_agility(field, actor), 30)

    def test_adjusted_agility_reads_no_accuracy_modifier(self):
        actor = FakeEntity("actor", agility=20)
        with patch(
            "world.rules.disengage.evaluate_combat_modifiers",
            return_value={"agility": "-25%", "accuracy": -1000},
        ):
            self.assertEqual(_adjusted_agility(actor), 15)
        source = Path(__file__).parents[1] / "disengage.py"
        function_source = source.read_text(encoding="utf-8").split(
            "def _adjusted_agility", 1
        )[1].split("def _fastest_pursuer_agility", 1)[0]
        self.assertNotIn('"accuracy"', function_source)

    def test_no_remaining_pursuer_succeeds_without_roll(self):
        actor = FakeEntity("actor")
        pursuer = FakeEntity("pursuer", hp=0)
        with (
            patch(
                "world.rules.disengage.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.disengage.roll_d100") as roller,
        ):
            self.assertTrue(_attempt_flee(actor, _field(actor, pursuer))[0])
        roller.assert_not_called()

    def test_source_has_no_overwhelm_special_case(self):
        source = (
            Path(__file__).parents[1] / "disengage.py"
        ).read_text(encoding="utf-8")
        for token in ("effective_power(", "classify_overwhelm(", "power_ratio"):
            self.assertNotIn(token, source)


class DisengageStagingTests(unittest.TestCase):
    @covers_requirement("battlefield-commit-surface::snapshotted-surfaces-gains-a-battlefield-surface-covering-battlefield-fled")
    def test_handler_registration_uses_battlefield_surface(self):
        self.assertIn("battlefield", SNAPSHOTTED_SURFACES)
        self.assertEqual(
            _EFFECT_HANDLER_SURFACES["disengage"],
            frozenset({"battlefield"}),
        )
        with self.assertRaises(UnsnapshottedSurfaceError):
            register_effect_handler(
                "test_inventory_disengage",
                lambda actor, targets, effect_id, context, scale: [],
                frozenset({"inventory"}),
                requires_event_context=frozenset(),
            )

    @covers_requirement("disengage-action::a-missing-battlefield-reference-in-event-context-is-a-named-rejection-not-a-crash")
    def test_missing_battlefield_is_named_rejection(self):
        actor = FakeEntity("actor")
        with self.assertRaises(RejectedAction) as caught:
            _handle_disengage(actor, [actor], "disengage:self", {}, 1.0)
        self.assertIs(
            caught.exception.reason,
            RejectReason.EFFECT_RESOLUTION_FAILED,
        )
        self.assertIn("battlefield", caught.exception.detail)

    @covers_requirement("disengage-action::a-successful-flee-adds-the-fleeing-entity-s-key-to-battlefield-fled-a-failed-attempt")
    def test_success_and_failure_stage_expected_mutations_and_entries(self):
        actor = FakeEntity("actor", agility=10)
        field = _field(actor, FakeEntity("pursuer", agility=10))
        with (
            patch(
                "world.rules.disengage.evaluate_combat_modifiers",
                return_value={},
            ),
            patch("world.rules.disengage.roll_d100", side_effect=[100, 1]),
        ):
            success = _handle_disengage(
                actor,
                [actor],
                "disengage:self",
                {"battlefield": field},
                1.0,
            )[0]
            failure = _handle_disengage(
                actor,
                [actor],
                "disengage:self",
                {"battlefield": field},
                1.0,
            )[0]
        success_entry = _entries_from_effect(actor.key, success)[0]
        failure_entry = _entries_from_effect(actor.key, failure)[0]
        self.assertEqual(success_entry.kind, "disengage_attempt")
        self.assertEqual(
            success_entry.data,
            {
                "success": True,
                "roll": 100,
                "actor_agility": 10.0,
                "pursuer_agility": 10.0,
            },
        )
        self.assertFalse(failure_entry.data["success"])
        failure.apply()
        self.assertNotIn(actor.key, field.fled)
        success.apply()
        self.assertIn(actor.key, field.fled)

    @covers_requirement("battlefield-commit-surface::a-commit-failure-rolls-back-a-battlefield-mutation-exactly-as-it-rolls-back-an-entity")
    def test_mixed_surface_commit_rolls_back_battlefield(self):
        actor = FakeEntity("actor")
        field = _field(actor, FakeEntity("pursuer"))
        effects = [
            PendingEffect(
                field,
                "disengage_attempt|actor|1|100|10|10",
                frozenset({"battlefield"}),
                lambda: field.fled.add(actor.key),
            ),
            PendingEffect(
                field,
                "synthetic",
                frozenset({"battlefield"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(Exception) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(field.fled, set())

    @covers_requirement("battlefield-commit-surface::a-battlefield-shaped-object-is-snapshotted-and-restored-by-shape-not-by-explicit")
    def test_action_module_uses_shape_dispatch_without_combat_import(self):
        source = (
            Path(__file__).parents[1] / "action.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("from world.rules.combat import Battlefield", source)
        self.assertNotIn("isinstance(context, Battlefield", source)

    def test_monster_policy_ignores_fled_enemies_without_modification(self):
        monster = FakeMonster("monster", owned=["fire_ball"])
        active = FakeEntity("active")
        fled = FakeEntity("fled")
        field = _field(monster, active, fled)
        field.fled.add("fled")
        request = monster_behaviour_policy(monster, field)
        self.assertEqual(request.targets, [active])


class DisengageGoldenTests(unittest.TestCase):
    def _seeded_effect(self, actor, field, seed):
        generator = random.Random(seed)
        with (
            patch(
                "world.rules.disengage.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.disengage.roll_d100",
                side_effect=lambda: generator.randint(1, 100),
            ),
        ):
            return _handle_disengage(
                actor,
                [actor],
                "disengage:self",
                {"battlefield": field},
                1.0,
            )[0]

    def test_same_tier_fixed_seed_has_exact_event_and_state(self):
        actor = FakeEntity("actor", agility=10)
        field = _field(actor, FakeEntity("pursuer", agility=10))
        effect = self._seeded_effect(actor, field, 7)
        entry = _entries_from_effect(actor.key, effect)[0]
        self.assertEqual(entry.data["roll"], 42)
        self.assertFalse(entry.data["success"])
        effect.apply()
        self.assertEqual(field.fled, set())

    def test_human_never_escapes_elf_across_fixed_seeds(self):
        for seed in (1, 7, 99, 2026):
            human = FakeEntity("human", agility=9)
            field = _field(human, FakeEntity("elf", agility=92))
            effect = self._seeded_effect(human, field, seed)
            entry = _entries_from_effect(human.key, effect)[0]
            self.assertFalse(entry.data["success"])
            effect.apply()
            self.assertEqual(field.fled, set())

    def test_elf_always_escapes_human_across_fixed_seeds(self):
        for seed in (1, 7, 99, 2026):
            elf = FakeEntity("elf", agility=92)
            field = _field(elf, FakeEntity("human", agility=9))
            effect = self._seeded_effect(elf, field, seed)
            entry = _entries_from_effect(elf.key, effect)[0]
            self.assertTrue(entry.data["success"])
            effect.apply()
            self.assertEqual(field.fled, {"elf"})
