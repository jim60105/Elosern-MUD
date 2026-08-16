"""Tests for climax settlement, extension staging, and the 進行中 dead-end fix.

Covers the ``climax-settlement`` change: the settlement decision function,
the extension bookkeeping surface, the lifetime-counter increments, the two
new ``sexual.yaml`` rule rows, the combat/clock settlement wiring, the
clock early-exit fix, and the rollback coverage of the new attributes.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    RejectReason,
    _commit,
)
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat import Battlefield, _end_of_round_upkeep
from world.rules.sexual_state import climax_settlement_action, decay_tick
from world.rules.sexual_transitions import apply_event

class FixedRng:
    """RNG stub returning a chosen in-range value."""

    def __init__(self, value: int):
        self.value = value

    def randint(self, lower: int, upper: int) -> int:
        if not lower <= self.value <= upper:
            raise AssertionError(f"{self.value} is outside [{lower}, {upper}]")
        return self.value


def _player(key="climax player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    return player


class ClimaxSettlementActionTests(EvenniaTestCase):
    """Unit tests for ``climax_settlement_action()`` in isolation."""

    def _entity_at(self, level: str):
        entity = _player(f"settle {level}")
        entity.sexual.climax_phase.value = level
        return entity

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time")
    def test_not_in_progress_returns_none_and_resets_bookkeeping(self):
        entity = self._entity_at("餘韻")
        entity.attributes.add("climax_turns", 3, category="sexual_state")
        entity.sexual.stage_climax_extension(2)
        self.assertIsNone(climax_settlement_action(entity))
        self.assertEqual(entity.sexual.climax_turns, 0)
        self.assertEqual(entity.sexual.pending_climax_extension, 0)
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time")
    def test_no_sexual_handler_is_a_noop(self):
        self.assertIsNone(climax_settlement_action(object()))

    @covers_requirement("climax-settlement::高潮次數-and-連續高潮次數-increment-exactly-once-per-climax-ends-climax-extended")
    def test_unstaged_in_progress_returns_end_and_increments_only_climax_counter(self):
        entity = self._entity_at("進行中")
        self.assertEqual(climax_settlement_action(entity), "end")
        self.assertEqual(entity.sexual.climax_count, 1)
        self.assertEqual(entity.sexual.climax_extension_count, 0)
        self.assertEqual(entity.sexual.climax_turns, 1)

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time", "climax-settlement::高潮次數-and-連續高潮次數-increment-exactly-once-per-climax-ends-climax-extended")
    def test_staged_extensions_consume_one_at_a_time(self):
        entity = self._entity_at("進行中")
        entity.sexual.stage_climax_extension(3)
        for expected_pending in (2, 1, 0):
            with self.subTest(expected_pending=expected_pending):
                self.assertEqual(climax_settlement_action(entity), "extend")
                self.assertEqual(
                    entity.sexual.pending_climax_extension, expected_pending
                )
                self.assertEqual(entity.sexual.climax_phase.level, "進行中")
        self.assertEqual(climax_settlement_action(entity), "end")
        self.assertEqual(entity.sexual.climax_turns, 4)
        self.assertEqual(entity.sexual.climax_count, 1)
        self.assertEqual(entity.sexual.climax_extension_count, 3)

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time")
    def test_stage_outside_in_progress_does_not_carry_forward(self):
        entity = self._entity_at("接近")
        entity.sexual.stage_climax_extension(2)
        self.assertIsNone(climax_settlement_action(entity))
        self.assertEqual(entity.sexual.pending_climax_extension, 0)
        self.assertEqual(entity.sexual.climax_turns, 0)

    @covers_requirement("climax-settlement::climax-turns-counts-consecutive-settlement-points-spent-in-進行中-reset-on-leaving-it")
    def test_climax_turns_increments_once_per_settlement_and_resets_on_leaving(self):
        entity = self._entity_at("進行中")
        entity.sexual.stage_climax_extension(3)
        for expected in (1, 2, 3):
            self.assertEqual(climax_settlement_action(entity), "extend")
            self.assertEqual(entity.sexual.climax_turns, expected)
        entity.sexual.climax_phase.value = "餘韻"
        self.assertIsNone(climax_settlement_action(entity))
        self.assertEqual(entity.sexual.climax_turns, 0)

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time")
    def test_stage_climax_extension_validation(self):
        entity = self._entity_at("進行中")
        for invalid in (0, -1, True, 1.5, "1"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    entity.sexual.stage_climax_extension(invalid)
                self.assertEqual(entity.sexual.pending_climax_extension, 0)


class CombatClimaxSettlementTests(EvenniaTestCase):
    """Integration tests on ``_end_of_round_upkeep``."""

    def _field(self, *entities):
        teams = {}
        roster = {}
        for index, entity in enumerate(entities):
            team = "party" if index == 0 else "foes"
            teams.setdefault(team, set()).add(entity.key)
            roster[entity.key] = entity
        teams.setdefault("foes", set())
        return Battlefield(
            {team: frozenset(members) for team, members in teams.items()},
            roster,
        )

    def _climaxing_player(self, key="upkeep climaxer"):
        entity = _player(key)
        entity.sexual.pleasure.base = 90
        entity.sexual.climax_phase.value = "進行中"
        entity.traits.sp.current = 100
        return entity

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time", "combat-resolution::per-round-upkeep-ticks-buffs-and-advances-sexual-decay-by-the-round-duration")
    def test_unstaged_climax_resolves_during_round_upkeep(self):
        entity = self._climaxing_player()
        before_sp = entity.traits.sp.value
        with patch("world.rules.combat.tick_buffs", return_value=()):
            _end_of_round_upkeep(self._field(entity))
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")
        self.assertEqual(entity.sexual.pleasure.value, 15)
        self.assertEqual(entity.sexual.climax_count, 1)
        self.assertEqual(entity.sexual.climax_extension_count, 0)
        self.assertEqual(entity.sexual.climax_turns, 1)
        self.assertIn(before_sp - entity.traits.sp.value, range(20, 31))

    @covers_requirement("combat-resolution::per-round-upkeep-ticks-buffs-and-advances-sexual-decay-by-the-round-duration")
    def test_staged_extension_keeps_phase_during_round_upkeep(self):
        entity = self._climaxing_player()
        entity.sexual.stage_climax_extension(1)
        before_sp = entity.traits.sp.value
        with patch("world.rules.combat.tick_buffs", return_value=()):
            _end_of_round_upkeep(self._field(entity))
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")
        self.assertEqual(entity.sexual.pending_climax_extension, 0)
        self.assertEqual(entity.sexual.climax_count, 0)
        self.assertEqual(entity.sexual.climax_extension_count, 1)
        self.assertIn(before_sp - entity.traits.sp.value, range(10, 16))

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time")
    def test_mid_round_entry_into_in_progress_resolves_in_the_same_upkeep(self):
        from dataclasses import replace

        from world.rules.action import ActionRequest
        from world.rules.combat import BattlefieldActionContext, run_round
        from world.skills.registry import SKILL_REGISTRY

        entity = _player("mid-round climaxer")
        entity.sexual.pleasure.base = 85
        entity.traits.sp.current = 100
        entity.db.skills = {"active": ["status_disguise"], "passive": []}
        original = SKILL_REGISTRY["status_disguise"]
        SKILL_REGISTRY["status_disguise"] = replace(
            original,
            effects=[
                "sexual_event:stimulus_applied",
                "sexual_event:stimulus_applied",
            ],
        )
        field = self._field(entity)
        try:
            with (
                patch(
                    "world.rules.combat.roll_initiative",
                    return_value=[entity.key],
                ),
                patch("world.rules.combat.tick_buffs", return_value=()),
            ):
                run_round(
                    field,
                    lambda actor, battlefield: ActionRequest(
                        actor,
                        "status_disguise",
                        [],
                        BattlefieldActionContext(battlefield),
                    ),
                )
        finally:
            SKILL_REGISTRY["status_disguise"] = original
        # The cast drove the phase to 進行中 mid-round; the same round's
        # upkeep then resolved it with no external climax_ends call.
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")
        self.assertEqual(entity.sexual.climax_count, 1)
        self.assertEqual(entity.sexual.climax_turns, 1)


class ClockClimaxSettlementTests(EvenniaTestCase):
    """Integration tests on ``WorldClock.advance`` and the early-exit fix."""

    def _entity_at_floor_in_progress(self, key="clock climaxer"):
        entity = _player(key)
        entity.sexual.pleasure.base = 0
        entity.sexual.wetness.value = "乾燥"
        entity.sexual.shame.value = "無"
        entity.sexual.exposure.value = "極低"
        entity.sexual.climax_phase.value = "進行中"
        return entity

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time", "settlement-stage-order::long-jumps-settle-in-quanta-not-per-second-steps-with-an-early-exit-once-nothing")
    def test_long_skip_resolves_in_progress_even_when_every_other_field_is_at_floor(self):
        entity = self._entity_at_floor_in_progress()
        WorldClock().advance(28800, AdvanceSource.SKIP, [entity])
        self.assertEqual(entity.sexual.climax_phase.level, "未達")
        self.assertEqual(entity.sexual.climax_count, 1)
        self.assertEqual(entity.sexual.climax_extension_count, 0)

    @covers_requirement("settlement-stage-order::long-jumps-settle-in-quanta-not-per-second-steps-with-an-early-exit-once-nothing")
    def test_remainder_branch_still_settles_in_progress(self):
        entity = self._entity_at_floor_in_progress()
        WorldClock().advance(6, AdvanceSource.COMMAND, [entity])
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")
        self.assertEqual(entity.sexual.climax_count, 1)


class ClimaxDeadEndRegressionTests(EvenniaTestCase):
    """The original dead end: 進行中 driven by rules resolves back to 未達."""

    @covers_requirement("climax-settlement::an-entity-whose-climax-phase-reaches-進行中-always-resolves-within-finite-settlement-time")
    def test_rules_driven_climax_cycle_returns_to_rest_through_combat_upkeep(self):
        entity = _player("dead-end regression")
        entity.sexual.pleasure.base = 85
        apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.climax_phase.level, "接近")
        apply_event(entity, "stimulus_applied", rng=FixedRng(8))
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")

        field = Battlefield(
            {"a": frozenset({entity.key}), "b": frozenset()},
            {entity.key: entity},
        )
        with patch("world.rules.combat.tick_buffs", return_value=()):
            _end_of_round_upkeep(field)
        self.assertEqual(entity.sexual.climax_phase.level, "餘韻")
        decay_tick(entity, 300)
        self.assertEqual(entity.sexual.climax_phase.level, "未達")


class ClimaxRollbackTests(EvenniaTest):
    """Rolled-back transactions restore the new bookkeeping attributes."""

    @staticmethod
    def _climax_count(entity):
        return entity.attributes.get("sexual_traits", category="traits")[
            "climax_count"
        ]["base"]

    @staticmethod
    def _climax_extension_count(entity):
        return entity.attributes.get("sexual_traits", category="traits")[
            "climax_extension_count"
        ]["base"]

    def _staged_player(self, key="rollback player"):
        entity = _player(key)
        entity.sexual.climax_phase.value = "進行中"
        entity.attributes.add("climax_turns", 2, category="sexual_state")
        entity.sexual.stage_climax_extension(1)
        for _ in range(5):
            entity.sexual.record_climax_count()
        for _ in range(3):
            entity.sexual.record_climax_extension()
        entity.traits.sp.current = 100
        return entity

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time")
    def test_failed_advance_restores_climax_bookkeeping(self):
        from world.rules.clock import get_world_clock

        entity = self._staged_player()
        clock = get_world_clock()
        before_tick = clock.tick

        def failing_persist(tick):
            raise RuntimeError("simulated persist failure")

        clock._persist = failing_persist
        with self.assertRaises(RuntimeError):
            clock.advance(3600, AdvanceSource.SKIP, [entity])
        self.assertEqual(clock.tick, before_tick)
        self.assertEqual(
            entity.attributes.get("climax_turns", category="sexual_state"), 2
        )
        self.assertEqual(
            entity.attributes.get(
                "pending_climax_extension", category="sexual_state"
            ),
            1,
        )
        self.assertEqual(self._climax_count(entity), 5)
        self.assertEqual(self._climax_extension_count(entity), 3)
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time")
    def test_failed_action_commit_restores_climax_bookkeeping(self):
        entity = _player("commit rollback")
        effects = [
            PendingEffect(
                entity,
                "stage",
                frozenset({"sexual"}),
                lambda: (
                    entity.sexual.stage_climax_extension(2),
                    entity.attributes.add(
                        "climax_turns", 7, category="sexual_state"
                    ),
                ),
            ),
            PendingEffect(
                entity,
                "boom",
                frozenset({"sexual"}),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects)
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertFalse(
            entity.attributes.has("climax_turns", category="sexual_state")
        )
        self.assertEqual(entity.sexual.pending_climax_extension, 0)
        self.assertEqual(self._climax_count(entity), 0)
        self.assertEqual(self._climax_extension_count(entity), 0)

    @covers_requirement("climax-settlement::pending-climax-extension-is-staged-additively-through-one-sole-mutator-and-consumed-one-at-a-time")
    def test_failed_combat_round_restores_climax_bookkeeping(self):
        from typeclasses.monsters import Monster
        from typeclasses.rooms import Room
        from world.rules.combat_session import engage, read_session, submit_player_action

        entity = self._staged_player()
        monster = create_object(Monster, key="rollback goblin")
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 1
        monster.traits.hp.current = 1
        arena = create_object(Room, key="rollback arena")
        entity.location = arena
        monster.location = arena
        entity.db.skills = {"active": ["fire_ball"], "passive": []}
        engage(entity, monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.action_preview.evaluate_combat_modifiers_no_create",
                return_value={},
            ),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            submit_player_action(entity, "fire_ball", [monster])
        self.assertEqual(
            entity.attributes.get("climax_turns", category="sexual_state"), 2
        )
        self.assertEqual(
            entity.attributes.get(
                "pending_climax_extension", category="sexual_state"
            ),
            1,
        )
        self.assertEqual(self._climax_count(entity), 5)
        self.assertEqual(self._climax_extension_count(entity), 3)
        self.assertEqual(entity.sexual.climax_phase.level, "進行中")
        self.assertIsNotNone(read_session(entity))


if __name__ == "__main__":
    unittest.main()
