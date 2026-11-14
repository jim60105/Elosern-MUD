"""Behaviour tests: a settlement pass relies on its enclosing advance rollback.

A population lifecycle pass inside ``WorldClock.advance`` takes no
per-operation snapshot and opens no savepoint: the advance's own registry
restores every surface a failed stage wrote. Every other caller keeps its own
protection, and so does the field-contact block a pass recovers from.

The assertions establish mechanisms, never shipped copy or wall-clock time:
the flag scopes, the savepoints the lifecycle owners themselves issue, and the
state a fault leaves behind in cache and after a reload.
"""

from __future__ import annotations

import contextlib
import traceback
import unittest
from dataclasses import replace
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext

from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

from tools.spec_traceability import covers_requirement

from world.maps import population_lifecycle, regional_population
from world.maps import monster_activity as activity_owner
from world.maps.monster_activity import (
    read_monster_activity,
    state_to_dict,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    ActivityFixture,
    GROUP_ACTIVITY,
    PROBE,
    RESERVE,
    SOLO_ACTIVITY,
)
from world.maps.tests.test_settlement_decode_reuse import (
    SITE_KEY,
    START,
    ZONE_KEY,
    ScenarioSettlementFixture,
)
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules import fatigue, field_contact, surfaces
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.combat_session import read_session
from world.rules.fatigue import (
    SleepPosture,
    project_fatigue_status,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.sleep_receipt import read_sleep_receipt
from world.rules.tests.test_field_contact import _CONTACT, _ContactBase
from world.rules.time_skip import begin_sleep

#: The tick the pass's contact block admits at (the advance endpoint).
CONTACT_TICK = 60

#: The five lifecycle operations that drop their own protection under an owner.
OWNED_SITES = frozenset(
    {
        "_commit_stay",
        "_commit_departure",
        "_commit_planned_wave",
        "commit_population_wave",
        "settle_fatigue_intervals",
        "settle_site_recovery",
    }
)


def _write_physiology(body, reserve: int, posture: SleepPosture) -> None:
    """Install one body's reserve and posture with its projection."""
    write_fatigue_state(body, reserve, posture)
    project_fatigue_status(body)


def _drop_attribute_caches(*entities) -> None:
    """Force the next read to come from the database, not a live cache."""
    for entity in entities:
        entity.attributes.reset_cache()
    for entity in entities[1:]:
        # The TraitHandler keeps its own decoded copy of the trait record.
        entity.traits.trait_data = entity.attributes.get(
            "traits", default={}, category="traits"
        )
        entity.traits._cache.clear()


def _atomic_caller(stack) -> str | None:
    """The function that opened the innermost ``transaction.atomic()``."""
    for index, frame in enumerate(stack):
        if frame.name == "__enter__" and frame.filename.endswith(
            "django/db/transaction.py"
        ):
            return stack[index - 1].name if index else None
    return None


class OuterRollbackFlagTests(unittest.TestCase):
    """The one flag a lifecycle site consults."""

    def setUp(self):
        surfaces._OUTER_ROLLBACK = False
        self.addCleanup(setattr, surfaces, "_OUTER_ROLLBACK", False)

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_no_owner_is_active_by_default(self):
        self.assertFalse(surfaces.outer_rollback_active())

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_an_owner_holds_the_rollback_inside_its_scope_only(self):
        with surfaces.outer_rollback_owner():
            self.assertTrue(surfaces.outer_rollback_active())
        self.assertFalse(surfaces.outer_rollback_active())

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_a_suspension_takes_the_protection_back_then_resumes_the_owner(self):
        with surfaces.outer_rollback_owner():
            with surfaces.suspended_outer_rollback():
                self.assertFalse(surfaces.outer_rollback_active())
            self.assertTrue(surfaces.outer_rollback_active())

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_either_scope_restores_the_previous_value_on_an_exception(self):
        with self.assertRaises(ZeroDivisionError):
            with surfaces.outer_rollback_owner():
                raise ZeroDivisionError("owner scope failure")
        self.assertFalse(surfaces.outer_rollback_active())
        with surfaces.outer_rollback_owner():
            with self.assertRaises(ZeroDivisionError):
                with surfaces.suspended_outer_rollback():
                    raise ZeroDivisionError("suspension failure")
            self.assertTrue(surfaces.outer_rollback_active())


class SavepointBoundTests(ActivityFixture):
    """A pass issues the same savepoint count whatever the population is."""

    def _lifecycle_savepoints(self, groups: int, *, owned: bool) -> int:
        self._register_lifecycle()
        self._reset_activity(tick=100)
        for index in range(groups):
            self._group(
                cell=PROBE,
                seed=index,
                tick=100,
                activity=SOLO_ACTIVITY,
                members=1,
            )
        clock = get_world_clock()
        clock.tick = 100
        clock._persist(100)
        opened: list[str] = []

        def wrapper(execute, sql, params, many, context):
            if sql.lstrip().upper().startswith("SAVEPOINT"):
                caller = _atomic_caller(traceback.extract_stack())
                if caller in OWNED_SITES:
                    opened.append(caller)
            return execute(sql, params, many, context)

        with contextlib.ExitStack() as stack:
            if not owned:
                stack.enter_context(
                    patch.object(
                        population_lifecycle,
                        "outer_rollback_owner",
                        contextlib.nullcontext,
                    )
                )
            stack.enter_context(connection.execute_wrapper(wrapper))
            clock.advance(60, AdvanceSource.COMMAND, ())
        settled = [
            group
            for group in read_monster_activity(self.wilderness).groups.values()
            if group.sequence > 0
        ]
        self.assertEqual(len(settled), groups, "every group really decided")
        return len(opened)

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_savepoints_do_not_grow_with_the_population(self):
        one = self._lifecycle_savepoints(1, owned=True)
        four = self._lifecycle_savepoints(4, owned=True)
        self.assertEqual(one, 0, "a lifecycle operation opens no savepoint")
        self.assertEqual(four, one)
        # The measure is not vacuous: with the pass's owner removed, the same
        # operations keep their own savepoint and the count grows with the
        # population that decides.
        guarded_one = self._lifecycle_savepoints(1, owned=False)
        guarded_four = self._lifecycle_savepoints(4, owned=False)
        self.assertGreater(guarded_one, 0)
        self.assertGreater(guarded_four, guarded_one)


class DepartureFaultTests(ActivityFixture):
    """A fault mid-departure leaves the whole advance intact."""

    def _body_state(self, bodies) -> dict[int, dict]:
        return {
            int(body.pk): {
                "reserve": read_optional_fatigue_state(body),
                "receipt": read_sleep_receipt(body),
            }
            for body in bodies
        }

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_fault_after_a_partial_departure(self):
        self._register_lifecycle()
        seed = self._departure_seed(
            tick=160,
            activity=SOLO_ACTIVITY,
            cell=(505, 705),
            members=1,
            wilderness_only=True,
        )
        self._reset_activity(tick=100)
        # The source cell must own a materialized room: the departure detaches
        # the body from it, so its membership is a surface of this write.
        enter_wilderness(self.char1, coordinates=(505, 705), name=WILDERNESS_NAME)
        room = (self.wilderness.db.rooms or {}).get((505, 705))
        self.assertIsNotNone(room, "the source cell materialized")
        group_id, bodies = self._group(
            cell=(505, 705), seed=seed, tick=100, activity=SOLO_ACTIVITY, members=1
        )
        body = bodies[0]
        self.assertIn(body, room.contents, "the body starts at the source")
        self.assertIsNotNone(
            activity_owner.plan_group_decision(
                self.wilderness, group_id, tick=160
            ).edge,
            "the interval contains a lawful departure",
        )
        clock = get_world_clock()
        clock.tick = 100
        clock._persist(100)
        before = settlement_projection(self.wilderness)
        physical = self._body_state(bodies)
        with patch.object(
            regional_population,
            "record_population_transition",
            side_effect=RuntimeError("injected transition fault"),
        ):
            with self.assertRaises(RuntimeError):
                clock.advance(60, AdvanceSource.COMMAND, ())

        self.assertEqual(clock.tick, 100)
        self.assertEqual(settlement_projection(self.wilderness), before)
        self.assertEqual(self._body_state(bodies), physical)
        self.assertIn(body, room.contents, "the source room still holds the body")
        # The same values survive dropping every live cache.
        _drop_attribute_caches(self.wilderness, *bodies)
        self.assertEqual(settlement_projection(self.wilderness), before)


class DirectDepartureFaultTests(ActivityFixture):
    """A departure committed outside an advance keeps its own protection."""

    @covers_requirement(
        "world-clock::operations-that-recover-and-continue-keep-their-own-protection"
    )
    def test_a_direct_departure_failure_restores_before_the_error_reaches_the_caller(
        self,
    ):
        seed = self._departure_seed(
            tick=160,
            activity=SOLO_ACTIVITY,
            cell=(505, 705),
            members=1,
            wilderness_only=True,
        )
        self._reset_activity(tick=100)
        # The source cell must own a materialized room: the departure detaches
        # the body from it, so its membership is a surface of this write.
        enter_wilderness(self.char1, coordinates=(505, 705), name=WILDERNESS_NAME)
        room = (self.wilderness.db.rooms or {}).get((505, 705))
        self.assertIsNotNone(room, "the source cell materialized")
        group_id, bodies = self._group(
            cell=(505, 705), seed=seed, tick=100, activity=SOLO_ACTIVITY, members=1
        )
        body = bodies[0]
        plan = activity_owner.plan_group_decision(self.wilderness, group_id, tick=160)
        self.assertIsNotNone(plan.edge, "the decision is a lawful departure")
        self.assertIn(body, room.contents, "the body starts at the source")
        before = settlement_projection(self.wilderness)
        physical = (
            read_optional_fatigue_state(body),
            read_sleep_receipt(body),
        )
        # The fault lands after the departure wrote its record and timeline
        # entry, and no advance owns any rollback around this caller.
        self.assertFalse(surfaces.outer_rollback_active())
        with patch.object(
            activity_owner,
            "_emit_decided",
            side_effect=RuntimeError("injected post-write departure fault"),
        ):
            with self.assertRaises(RuntimeError):
                activity_owner.commit_group_decision(self.wilderness, plan)

        self.assertEqual(settlement_projection(self.wilderness), before)
        self.assertIn(body, room.contents, "the source room still holds the body")
        self.assertEqual(
            (read_optional_fatigue_state(body), read_sleep_receipt(body)), physical
        )
        # The same values survive dropping every live cache.
        _drop_attribute_caches(self.wilderness, body)
        self.assertEqual(settlement_projection(self.wilderness), before)


class FatigueFaultTests(ActivityFixture):
    """A fault mid-physiology restores both members in cache and on reload."""

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_fault_during_a_fatigue_write(self):
        self._register_lifecycle()
        self._reset_activity(tick=100)
        _group_id, bodies = self._group(
            cell=PROBE,
            tick=100,
            activity=GROUP_ACTIVITY,
            members=2,
            reserves=(RESERVE, RESERVE - 1000),
        )
        clock = get_world_clock()
        clock.tick = 100
        clock._persist(100)
        physical = tuple(
            (read_optional_fatigue_state(body), read_sleep_receipt(body))
            for body in bodies
        )
        real_write = fatigue.write_fatigue_state
        calls = {"count": 0}

        def fail_on_second_member(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise RuntimeError("injected fatigue write fault")
            return real_write(*args, **kwargs)

        with patch.object(fatigue, "write_fatigue_state", fail_on_second_member):
            with self.assertRaises(RuntimeError):
                clock.advance(90, AdvanceSource.COMMAND, ())

        self.assertEqual(calls["count"], 2, "the first member was written")
        self.assertEqual(clock.tick, 100)
        self.assertEqual(
            tuple(
                (read_optional_fatigue_state(body), read_sleep_receipt(body))
                for body in bodies
            ),
            physical,
        )
        _drop_attribute_caches(self.wilderness, *bodies)
        self.assertEqual(
            tuple(
                (read_optional_fatigue_state(body), read_sleep_receipt(body))
                for body in bodies
            ),
            physical,
        )


class DifferentialSettlementTests(ScenarioSettlementFixture):
    """Owned and per-operation protection leave the same settled state."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    @staticmethod
    def _protection(owned: bool):
        if owned:
            return contextlib.nullcontext()
        # A pass that keeps its own per-operation protection is the reference.
        return patch.object(
            population_lifecycle, "outer_rollback_owner", contextlib.nullcontext
        )

    def _advance(self, parts: tuple[int, ...], *, owned: bool) -> dict:
        self._build_scenario()
        clock = get_world_clock()
        clock.tick = START
        clock._persist(START)
        with self._protection(owned):
            for part in parts:
                clock.advance(part, AdvanceSource.COMMAND, ())
        return settlement_projection(self.wilderness)

    @covers_requirement(
        "world-clock::lifecycle-operations-inside-an-advance-rely-on-the-advance-rollback"
    )
    def test_results_are_unchanged(self):
        projections = {
            (parts, owned): self._advance(parts, owned=owned)
            for parts in ((1500,), (700, 800))
            for owned in (True, False)
        }
        reference = projections[((1500,), True)]
        for (parts, owned), projection in projections.items():
            self.assertEqual(
                projection,
                reference,
                msg=f"partition {parts} with owned={owned}",
            )
        # The scenario really settled: a due episode, a site recovery and a
        # journey all happened, so the equality above is not an untouched
        # state.
        self.assertGreater(reference["zones"][ZONE_KEY]["generation_sequence"], 0)
        self.assertTrue(reference["activity"]["journeys"])
        self.assertTrue(reference["sites"][SITE_KEY])


class FailedContactInsidePassTests(_ContactBase):
    """The pass's contact block keeps its own protection and participants."""

    def setUp(self):
        super().setUp()
        # The subject is the pass's own contact block, not the separate clock
        # source that also admits at an interval endpoint.
        from world.rules import clock as clock_module

        clock_module._EVENT_SOURCES.pop("field_contact", None)

    def _sleeping_party_at_the_contact(self):
        """A voluntarily sleeping commander whose cell holds one hostile body."""
        _write_physiology(self.player, 100000, SleepPosture.AWAKE)
        begin_sleep(self.player, mode="duration", seconds=600, allow_continue=False)
        receipt_before = read_sleep_receipt(self.player)
        state_before = read_optional_fatigue_state(self.player)
        enemy = self._enemy("contact enemy", _CONTACT)
        state = read_monster_activity(self.wilderness)
        groups = {
            group_id: replace(group, next_decision_tick=CONTACT_TICK)
            for group_id, group in state.groups.items()
        }
        self.wilderness.db.monster_activity = state_to_dict(
            replace(state, groups=groups)
        )
        self.player.location = self.destination
        self.destination.contents_cache.add(self.player)
        return enemy, receipt_before, state_before

    @covers_requirement(
        "world-clock::operations-that-recover-and-continue-keep-their-own-protection"
    )
    def test_the_contact_block_runs_with_its_own_protection(self):
        enemy, receipt_before, state_before = self._sleeping_party_at_the_contact()
        group_id = activity_owner.group_of_member(
            self.wilderness, int(enemy.pk)
        ).group_id
        sequence_before = (
            read_monster_activity(self.wilderness).groups[group_id].sequence
        )
        observed: dict = {"decisions": []}
        real_contact = field_contact.settle_population_contact_at
        real_decisions = activity_owner.settle_group_decisions_at

        def contact_probe(wilderness, tick, contact_tick):
            observed["contact_owner"] = surfaces.outer_rollback_active()
            with CaptureQueriesContext(connection) as queries:
                try:
                    events = real_contact(wilderness, tick, contact_tick)
                except RuntimeError:
                    # A lifecycle operation that recovers and continues: the
                    # block's own protection must have rolled its write back.
                    events = []
            observed["contact_savepoints"] = sum(
                1
                for query in queries.captured_queries
                if query["sql"].lstrip().upper().startswith("SAVEPOINT")
            )
            return events

        def decisions_probe(wilderness, tick, *, scope=None):
            observed["decisions"].append(surfaces.outer_rollback_active())
            return real_decisions(wilderness, tick, scope=scope)

        clock = get_world_clock()
        clock.tick = 0
        clock._persist(0)
        with (
            patch.object(field_contact, "settle_population_contact_at", contact_probe),
            patch.object(activity_owner, "settle_group_decisions_at", decisions_probe),
            patch(
                "world.rules.combat_session.lifecycle._persist",
                side_effect=RuntimeError("injected session write failure"),
            ),
            patch("world.rules.field_contact.log_error") as logged,
        ):
            clock.advance(CONTACT_TICK, AdvanceSource.COMMAND, (self.player,))

        # The contact block suspended the pass's owner and kept its own
        # protection: the interrupted physiology rolled back to its savepoint.
        self.assertFalse(observed["contact_owner"])
        self.assertGreaterEqual(
            observed["contact_savepoints"], 2, "own savepoint plus the physiology"
        )
        self.assertTrue(observed["decisions"])
        self.assertTrue(all(observed["decisions"]))
        self.assertEqual(clock.tick, CONTACT_TICK)
        self.assertEqual(read_sleep_receipt(self.player), receipt_before)
        self.assertEqual(read_optional_fatigue_state(self.player), state_before)
        events = [call.args[0] for call in logged.call_args_list if call.args]
        self.assertIn("field_contact_failed", events)
        # The advance committed and the idle decision due at that tick settled.
        self.assertGreater(
            read_monster_activity(self.wilderness).groups[group_id].sequence,
            sequence_before,
        )

    @covers_requirement(
        "world-clock::operations-that-recover-and-continue-keep-their-own-protection"
    )
    def test_an_unrecovered_contact_failure_fails_the_advance(self):
        _enemy, receipt_before, state_before = self._sleeping_party_at_the_contact()
        activity_before = state_to_dict(read_monster_activity(self.wilderness))
        clock = get_world_clock()
        clock.tick = 0
        clock._persist(0)
        with (
            patch(
                "world.rules.combat_session.lifecycle._persist",
                side_effect=RuntimeError("injected session write failure"),
            ),
            patch("world.rules.field_contact.log_error") as logged,
        ):
            with self.assertRaises(RuntimeError):
                clock.advance(CONTACT_TICK, AdvanceSource.COMMAND, (self.player,))

        # Nothing recovers the failure, so the advance's own rollback owns the
        # result; the admission still restored its participants first.
        events = [call.args[0] for call in logged.call_args_list if call.args]
        self.assertIn("field_contact_failed", events)
        self.assertEqual(clock.tick, 0)
        self.assertIsNone(read_session(self.player))
        self.assertEqual(read_sleep_receipt(self.player), receipt_before)
        self.assertEqual(read_optional_fatigue_state(self.player), state_before)
        self.assertEqual(
            state_to_dict(read_monster_activity(self.wilderness)), activity_before
        )