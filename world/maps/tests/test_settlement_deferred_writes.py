"""Behaviour tests: one settlement pass stores each written record once.

A lifecycle settlement pass inside a clock advance buffers the attribute stores
its writers make: every ordinary reader sees the new value while the database
row is written once when the pass completes, and once more before a field
contact block (which then runs unbuffered). A failed pass stores nothing and
puts every buffered value back in memory. Outside a clock advance nothing
changes.

Every scenario is synthetic, and every assertion is deterministic: state
equality, named failures and statement/call counts, never wall-clock time or
hardware speed. Each behaviour test carries the ``covers_requirement``
annotation of the requirement it establishes, using the canonical identifier
archive sync assigns.
"""

from __future__ import annotations

import contextlib
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext

from evennia.objects.models import ObjectDB
from evennia.typeclasses.attributes import Attribute
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from typeclasses.monsters import Monster

from world.maps import monster_activity, population_lifecycle, regional_population
from world.maps.monster_activity import read_monster_activity
from world.maps.regional_population import (
    ITEMCOORDINATES_ATTRIBUTE,
    POPULATION_TIMELINE_ATTRIBUTE,
    presence_at,
    read_population_timeline,
    zone_states,
)
from world.maps.tests._settlement_projection import settlement_projection
from world.maps.tests.test_monster_activity import (
    GROUP_ACTIVITY,
    PROBE,
    RESERVE,
    SOLO_ACTIVITY,
    STATIONARY_ACTIVITY,
    ActivityFixture,
)
from world.maps.tests.test_population_catch_up import place_player
from world.maps.tests.test_settlement_decode_reuse import (
    SITE_KEY,
    START,
    TRAVELLING_CELL,
    ZONE_KEY,
    ScenarioSettlementFixture,
)
from world.rules import field_contact, surfaces
from world.rules.clock import (
    AdvanceSource,
    get_world_clock,
    settle_gauge_regeneration,
)
from world.rules.fatigue import (
    RESERVE_ATTRIBUTE,
    SleepPosture,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.surfaces import (
    DeferredStoreLost,
    deferred_attribute_stores,
    flushed_attribute_stores,
    persisted_hp,
    store_attribute,
)

#: The SQL prefix of an Attribute row update issued by Django on SQLite.
UPDATE_ATTRIBUTE = 'UPDATE "typeclasses_attribute"'

#: The three gauges a body regenerates.
GAUGE_KEYS = ("hp", "mp", "sp")


def _captured(queries: CaptureQueriesContext) -> list[str]:
    """Every statement text captured by a query context."""
    return [query["sql"] for query in queries.captured_queries]


def _update_statement_counts(
    statements, attribute_ids
) -> dict[int, int]:
    """Count Attribute row updates per primary key in a list of statements."""
    counts = {int(attribute_id): 0 for attribute_id in attribute_ids}
    for statement in statements:
        text = str(statement).strip()
        if not text.startswith(UPDATE_ATTRIBUTE):
            continue
        for attribute_id in counts:
            if text.endswith(f"= {attribute_id}"):
                counts[attribute_id] += 1
    return counts


def _stored_attribute(attribute_id: int):
    """One Attribute row's stored value, read past every live cache.

    ``values_list`` queries the row instead of returning the idmapper instance
    whose ``db_value`` the write already replaced, so it answers what a commit
    would persist.
    """
    return (
        Attribute.objects.filter(pk=attribute_id)
        .values_list("db_value", flat=True)
        .get()
    )


def _drop_attribute_caches(wilderness, entities) -> None:
    """Force the next read of each surface to come from the database."""
    wilderness.attributes.reset_cache()
    for entity in entities:
        entity.attributes.reset_cache()
        entity.traits.trait_data = entity.attributes.get(
            "traits", default={}, category="traits"
        )
        entity.traits._cache.clear()


class _DoubleAttributes:
    """The immediate-only attribute store a pure test double exposes."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def get(self, key, default=None, category=None, return_obj=False):
        if return_obj:
            raise TypeError("this attribute double has no return_obj read")
        return self.values.get(key, default)

    def add(self, key, value, category=None):
        self.values[key] = value


class _Double:
    """An entity with no Evennia attribute handler behind its store."""

    def __init__(self) -> None:
        self.attributes = _DoubleAttributes()


class DeferredBufferTests(EvenniaTest):
    """The one write buffer the lifecycle pass opens."""

    def setUp(self):
        super().setUp()
        self.holder = create_object(ObjectDB, key="t_deferred_holder")
        self.holder.attributes.add("probe", {"count": 0})
        self.attribute = self.holder.attributes.get("probe", return_obj=True)
        self.attribute_id = int(self.attribute.pk)

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_a_deferred_value_reads_new_and_stays_unstored(self):
        self.assertFalse(surfaces.attribute_stores_deferred())
        with CaptureQueriesContext(connection) as queries:
            with deferred_attribute_stores():
                self.assertTrue(surfaces.attribute_stores_deferred())
                store_attribute(self.holder, "probe", {"count": 1})
                # The ordinary reader sees the new value immediately.
                self.assertEqual(self.holder.db.probe, {"count": 1})
                # The row is still the pre-pass value.
                self.assertEqual(_stored_attribute(self.attribute_id), {"count": 0})
        self.assertFalse(surfaces.attribute_stores_deferred())
        self.assertEqual(_stored_attribute(self.attribute_id), {"count": 1})
        self.assertEqual(
            _update_statement_counts(_captured(queries), (self.attribute_id,)),
            {self.attribute_id: 1},
        )

    @covers_requirement("world-clock::a-failed-pass-stores-nothing-it-deferred")
    def test_a_failed_buffer_restores_the_original_and_stores_nothing(self):
        with self.assertRaises(ZeroDivisionError):
            with CaptureQueriesContext(connection) as queries:
                with deferred_attribute_stores():
                    store_attribute(self.holder, "probe", {"count": 7})
                    self.assertEqual(self.holder.db.probe, {"count": 7})
                    raise ZeroDivisionError("injected pass failure")
        self.assertEqual(self.holder.db.probe, {"count": 0})
        self.assertEqual(_stored_attribute(self.attribute_id), {"count": 0})
        self.assertEqual(
            _update_statement_counts(_captured(queries), (self.attribute_id,)),
            {self.attribute_id: 0},
        )

    @covers_requirement("world-clock::a-failed-pass-stores-nothing-it-deferred")
    def test_a_pending_value_lost_before_the_store_fails_closed(self):
        pending = self.attribute
        with self.assertRaises(DeferredStoreLost) as caught:
            with deferred_attribute_stores():
                store_attribute(self.holder, "probe", {"count": 9})
                # An attribute cache reset and a replaced row: the buffered
                # Attribute is no longer the one this object reads.
                self.holder.attributes.remove("probe")
                self.holder.attributes.add("probe", {"count": 0})
        self.assertFalse(surfaces.attribute_stores_deferred())
        # The flush failure restored the recorded original in memory too.
        self.assertEqual(pending.db_value, {"count": 0})
        self.assertEqual(self.holder.db.probe, {"count": 0})
        self.assertIn("probe", str(caught.exception))

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_a_flush_stores_now_and_then_resumes_buffering(self):
        with deferred_attribute_stores():
            store_attribute(self.holder, "probe", {"count": 1})
            with flushed_attribute_stores():
                self.assertFalse(surfaces.attribute_stores_deferred())
                self.assertEqual(self.holder.db.probe, {"count": 1})
                store_attribute(self.holder, "probe", {"count": 2})
                # A write inside the unbuffered block is stored immediately.
                self.assertEqual(_stored_attribute(self.attribute_id), {"count": 2})
            self.assertTrue(surfaces.attribute_stores_deferred())
            store_attribute(self.holder, "probe", {"count": 3})
            self.assertEqual(_stored_attribute(self.attribute_id), {"count": 2})
        self.assertEqual(_stored_attribute(self.attribute_id), {"count": 3})

    def test_a_missing_row_is_created_through_the_handler(self):
        with deferred_attribute_stores():
            store_attribute(self.holder, "fresh", {"count": 4})
            created = self.holder.attributes.get("fresh", return_obj=True)
            self.assertIsNotNone(created)
            self.assertEqual(created.db_value, {"count": 4})
            self.assertEqual(surfaces._DEFERRED.pending, {})
        self.assertEqual(self.holder.db.fresh, {"count": 4})

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_a_nested_buffer_reuses_the_open_one(self):
        with CaptureQueriesContext(connection) as queries:
            with deferred_attribute_stores():
                store_attribute(self.holder, "probe", {"count": 1})
                with deferred_attribute_stores():
                    store_attribute(self.holder, "probe", {"count": 2})
                    self.assertEqual(len(surfaces._DEFERRED.pending), 1)
                self.assertTrue(surfaces.attribute_stores_deferred())
                self.assertEqual(_stored_attribute(self.attribute_id), {"count": 0})
        self.assertEqual(_stored_attribute(self.attribute_id), {"count": 2})
        self.assertEqual(
            _update_statement_counts(_captured(queries), (self.attribute_id,)),
            {self.attribute_id: 1},
        )

    def test_a_pure_attribute_double_falls_back_to_an_immediate_store(self):
        double = _Double()
        with deferred_attribute_stores():
            store_attribute(double, "probe", {"count": 5})
            self.assertEqual(double.attributes.values["probe"], {"count": 5})
            self.assertEqual(surfaces._DEFERRED.pending, {})


class _PassScenarioFixture(ActivityFixture):
    """One file-local travelling group whose first decision departs."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    def _travelling_seed(self) -> int:
        return self._departure_seed(
            tick=START + 60,
            activity=SOLO_ACTIVITY,
            cell=TRAVELLING_CELL,
            members=2,
        )

    def _build_travelling_world(self):
        """Reset the world and create the identical travelling group."""
        seed = self._travelling_seed()
        self._reset_activity(tick=START)
        # The clock stage settles the units a player observes; the fixture's own
        # zone is that unit here, so the party stands inside it.
        place_player(self, TRAVELLING_CELL)
        return self._group(
            cell=TRAVELLING_CELL,
            seed=seed,
            tick=START,
            activity=SOLO_ACTIVITY,
            members=2,
        )

    def _advance(self, seconds: int) -> None:
        clock = get_world_clock()
        clock.tick = START
        clock._persist(START)
        clock.advance(seconds, AdvanceSource.COMMAND, ())


class StatementBoundTests(_PassScenarioFixture):
    """Deferred rows are stored once, whatever the boundary count."""

    def _boundary_ticks(self, end_tick: int) -> list[int]:
        self._build_travelling_world()
        seen: list[int] = []
        settle_at = population_lifecycle._settle_population_at

        def probe(wilderness, tick, **kwargs):
            seen.append(int(tick))
            return settle_at(wilderness, tick, **kwargs)

        with patch.object(population_lifecycle, "_settle_population_at", probe):
            self._advance(end_tick - START)
        return seen

    def _measure(self, end_tick: int, *, deferred: bool):
        """One advance's per-row update counts and the boundaries it settled."""
        _group_id, bodies = self._build_travelling_world()
        wilderness = self.wilderness
        rows = {
            "timeline": int(
                wilderness.attributes.get(
                    POPULATION_TIMELINE_ATTRIBUTE, return_obj=True
                ).pk
            ),
            "coordinates": int(
                wilderness.attributes.get(
                    ITEMCOORDINATES_ATTRIBUTE, return_obj=True
                ).pk
            ),
            **{
                f"reserve:{index}": int(
                    body.attributes.get(
                        RESERVE_ATTRIBUTE, return_obj=True
                    ).pk
                )
                for index, body in enumerate(bodies)
            },
        }
        seen: list[int] = []
        contacts: list[int] = []
        settle_at = population_lifecycle._settle_population_at

        def probe(wilderness, tick, **kwargs):
            seen.append(int(tick))
            return settle_at(wilderness, tick, **kwargs)

        def contact_probe(*args, **kwargs):
            contacts.append(1)
            return []

        stack = contextlib.ExitStack()
        stack.enter_context(
            patch.object(population_lifecycle, "_settle_population_at", probe)
        )
        stack.enter_context(
            patch.object(field_contact, "settle_population_contact_at", contact_probe)
        )
        if not deferred:
            stack.enter_context(
                patch.object(
                    population_lifecycle,
                    "deferred_attribute_stores",
                    contextlib.nullcontext,
                )
            )
        with stack:
            with CaptureQueriesContext(connection) as queries:
                self._advance(end_tick - START)
        counts = _update_statement_counts(_captured(queries), rows.values())
        return seen, contacts, {
            label: counts[attribute_id] for label, attribute_id in rows.items()
        }

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_statements_do_not_grow_with_boundary_ticks(self):
        ticks = self._boundary_ticks(START + 4000)
        self.assertGreaterEqual(len(ticks), 7, "the discovery interval is long enough")
        two_end = ticks[1] + 1
        six_end = ticks[5] + 1
        self.assertLess(two_end, ticks[2], "the short interval is mid-way")
        self.assertLess(six_end, ticks[6], "the long interval is mid-way")

        two_ticks, two_contacts, two_counts = self._measure(two_end, deferred=True)
        six_ticks, six_contacts, six_counts = self._measure(six_end, deferred=True)
        self.assertEqual(two_ticks, ticks[:2])
        self.assertEqual(six_ticks, ticks[:6])
        self.assertEqual(two_contacts, [])
        self.assertEqual(six_contacts, [])
        self.assertEqual(two_counts, six_counts)
        self.assertTrue(all(count > 0 for count in two_counts.values()))
        self.assertTrue(
            all(count == 1 for count in two_counts.values()),
            msg=f"each record is stored once per pass: {two_counts}",
        )

        # The equality is not vacuous: immediate storage (the reference mode)
        # writes the same rows once per boundary.
        _ticks, _contacts, immediate_counts = self._measure(
            six_end, deferred=False
        )
        self.assertGreater(immediate_counts["timeline"], 1)
        for label, count in six_counts.items():
            self.assertGreaterEqual(immediate_counts[label], count)


class PendingVisibilityTests(_PassScenarioFixture):
    """A reader inside the pass sees the value the pass already wrote."""

    def _timeline_attribute_id(self) -> int:
        return int(
            self.wilderness.attributes.get(
                POPULATION_TIMELINE_ATTRIBUTE, return_obj=True
            ).pk
        )

    def _arrival_tick(self) -> int:
        self._build_travelling_world()
        arrivals: list[int] = []
        arrive = monster_activity._arrive

        def probe(wilderness, journey, bodies, **kwargs):
            arrivals.append(int(kwargs["tick"]))
            return arrive(wilderness, journey, bodies, **kwargs)

        with patch.object(monster_activity, "_arrive", probe):
            self._advance(2000)
        self.assertEqual(len(arrivals), 1, "the journey arrives exactly once")
        return arrivals[0]

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_readers_see_pending_values(self):
        arrival_tick = self._arrival_tick()
        _group_id, bodies = self._build_travelling_world()
        timeline_id = self._timeline_attribute_id()
        observed: dict = {}
        arrive = monster_activity._arrive

        def probe(wilderness, journey, bodies, **kwargs):
            result = arrive(wilderness, journey, bodies, **kwargs)
            destination = journey.destination
            cell = (destination.x, destination.y)
            coordinates = dict(wilderness.db.itemcoordinates or {})
            timeline = read_population_timeline(wilderness)
            observed.update(
                deferred=surfaces.attribute_stores_deferred(),
                coordinates={body: coordinates.get(body) for body in bodies},
                cell=cell,
                timeline=timeline,
                presence=presence_at(wilderness),
                stored_timeline=_stored_attribute(timeline_id),
            )
            return result

        with patch.object(monster_activity, "_arrive", probe):
            self._advance(arrival_tick - START)

        self.assertTrue(observed["deferred"])
        for body in bodies:
            self.assertEqual(observed["coordinates"][body], observed["cell"])
            presence = observed["presence"][int(body.pk)]
            self.assertTrue(presence.alive)
            self.assertEqual(
                (presence.position.x, presence.position.y), observed["cell"]
            )
        arrivals = [
            transition
            for transition in observed["timeline"].transitions
            if transition.occurred_tick == arrival_tick
            and transition.individual_id in {int(body.pk) for body in bodies}
        ]
        self.assertEqual(len(arrivals), len(bodies))
        for transition in arrivals:
            self.assertEqual(
                (transition.after.position.x, transition.after.position.y),
                observed["cell"],
            )
        # None of it is stored yet.
        self.assertLess(
            len(observed["stored_timeline"]["transitions"]),
            len(observed["timeline"].transitions),
        )

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_the_contact_block_starts_from_stored_state(self):
        arrival_tick = self._arrival_tick()
        _group_id, bodies = self._build_travelling_world()
        timeline_id = self._timeline_attribute_id()
        reserve_id = int(
            bodies[0].attributes.get(RESERVE_ATTRIBUTE, return_obj=True).pk
        )
        body = bodies[0]
        observed: dict = {}
        real_contact = field_contact.settle_population_contact_at

        def contact_probe(wilderness, tick, contact_tick):
            observed["deferred"] = surfaces.attribute_stores_deferred()
            observed["activity_unbatched"] = monster_activity._ACTIVE_BATCH is None
            observed["timeline_stored_equals_memory"] = (
                _stored_attribute(timeline_id)
                == dict(wilderness.db.population_timeline)
            )
            observed["reserve_stored"] = _stored_attribute(reserve_id)
            observed["reserve_memory"] = read_optional_fatigue_state(
                body
            ).reserve_units
            write_fatigue_state(body, RESERVE - 1000, SleepPosture.AWAKE)
            observed["reserve_after_in_block_write"] = _stored_attribute(reserve_id)
            return real_contact(wilderness, tick, contact_tick)

        with patch.object(
            field_contact, "settle_population_contact_at", contact_probe
        ):
            self._advance(arrival_tick - START)

        self.assertFalse(observed["deferred"])
        self.assertTrue(observed["activity_unbatched"])
        self.assertTrue(observed["timeline_stored_equals_memory"])
        self.assertEqual(observed["reserve_stored"], observed["reserve_memory"])
        self.assertNotEqual(observed["reserve_stored"], RESERVE - 1000)
        self.assertEqual(observed["reserve_after_in_block_write"], RESERVE - 1000)
        self.assertEqual(read_optional_fatigue_state(body).reserve_units, RESERVE - 1000)

    @covers_requirement("world-clock::a-failed-pass-stores-nothing-it-deferred")
    def test_a_fault_after_the_contact_flush_restores_every_surface(self):
        arrival_tick = self._arrival_tick()
        _group_id, bodies = self._build_travelling_world()
        before = settlement_projection(self.wilderness)
        observed: dict = {}
        real_contact = field_contact.settle_population_contact_at

        def contact_probe(wilderness, tick, contact_tick):
            observed["deferred"] = surfaces.attribute_stores_deferred()
            real_contact(wilderness, tick, contact_tick)
            raise RuntimeError("injected fault after the contact flush")

        with patch.object(
            field_contact, "settle_population_contact_at", contact_probe
        ):
            with self.assertRaises(RuntimeError):
                self._advance(arrival_tick - START)

        # The fault landed after the flush: the buffer was already closed.
        self.assertFalse(observed["deferred"])
        self.assertFalse(surfaces.attribute_stores_deferred())
        self.assertEqual(settlement_projection(self.wilderness), before)
        _drop_attribute_caches(self.wilderness, Monster.objects.all_family())
        self.assertEqual(settlement_projection(self.wilderness), before)


class ZoneCacheInvalidationTests(ScenarioSettlementFixture):
    """A zone-state write replaces the decode it supersedes."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_a_zone_state_write_invalidates_the_decode_caches(self):
        self._build_scenario()
        regional_population._state_map(self.wilderness)
        self.assertIsNotNone(regional_population._DECODED_ZONE_MAP)
        zone_states(self.wilderness)
        self.assertIsNotNone(regional_population._DECODED_ZONE_STATES)
        regional_population._write_state(
            self.wilderness, regional_population._state_map(self.wilderness)
        )
        self.assertIsNone(regional_population._DECODED_ZONE_MAP)
        self.assertIsNone(regional_population._DECODED_ZONE_STATES)


class FaultAfterDeferredWritesTests(_PassScenarioFixture):
    """A fault after deferred writes stores none of them."""

    @covers_requirement("world-clock::a-failed-pass-stores-nothing-it-deferred")
    def test_a_fault_after_deferred_writes(self):
        _group_id, bodies = self._build_travelling_world()
        wilderness = self.wilderness
        rows = [
            int(
                wilderness.attributes.get(
                    POPULATION_TIMELINE_ATTRIBUTE, return_obj=True
                ).pk
            ),
            int(
                wilderness.attributes.get(
                    ITEMCOORDINATES_ATTRIBUTE, return_obj=True
                ).pk
            ),
            *[
                int(
                    body.attributes.get(
                        RESERVE_ATTRIBUTE, return_obj=True
                    ).pk
                )
                for body in bodies
            ],
        ]
        timeline_id = rows[0]
        before = settlement_projection(wilderness)
        real_decisions = monster_activity.settle_group_decisions_at
        calls = {"count": 0}
        recording = {"on": True}
        issued: list[str] = []

        def wrapper(execute, sql, params, many, context):
            if recording["on"] and str(sql).lstrip().startswith(UPDATE_ATTRIBUTE):
                issued.append(str(sql))
            return execute(sql, params, many, context)

        def fail_on_third(wilderness, tick, *, scope=None):
            calls["count"] += 1
            if calls["count"] == 3:
                # The pass already deferred timeline, coordinate and reserve
                # writes: the failure must leave them un-stored.
                self.assertTrue(surfaces.attribute_stores_deferred())
                self.assertTrue(surfaces._DEFERRED.pending)
                self.assertNotEqual(
                    _stored_attribute(timeline_id),
                    dict(wilderness.db.population_timeline),
                )
                recording["on"] = False
                raise RuntimeError("injected third-decision fault")
            return real_decisions(wilderness, tick, scope=scope)

        with patch.object(
            monster_activity, "settle_group_decisions_at", fail_on_third
        ):
            with connection.execute_wrapper(wrapper):
                with self.assertRaises(RuntimeError):
                    self._advance(2000)

        self.assertEqual(calls["count"], 3)
        self.assertFalse(surfaces.attribute_stores_deferred())
        self.assertEqual(_update_statement_counts(issued, rows), {
            attribute_id: 0 for attribute_id in rows
        })
        self.assertEqual(settlement_projection(wilderness), before)
        _drop_attribute_caches(wilderness, Monster.objects.all_family())
        self.assertEqual(settlement_projection(wilderness), before)


class GaugeRecordStoreTests(ActivityFixture):
    """One body's three gauges store its trait record once per settlement."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    @staticmethod
    def _prepare_gauges(entity) -> None:
        """Give every gauge a known maximum, rate and below-maximum current."""
        for key in GAUGE_KEYS:
            gauge = getattr(entity.traits, key, None)
            if gauge is None:
                continue
            gauge.base = 1000
            gauge.rate = 1.0
            # Saturated by the settled interval: the deferred clamp/round
            # must store exactly what the gauge setter stores.
            gauge.current = 900

    @staticmethod
    def _gauge_pairs(entity) -> dict[str, tuple[int, float]]:
        return {
            key: (
                int(getattr(entity.traits, key).current),
                float(
                    getattr(getattr(entity.traits, key), "regen_remainder", 0.0)
                    or 0.0
                ),
            )
            for key in GAUGE_KEYS
        }

    @covers_requirement(
        "world-clock::gauge-regeneration-stores-a-body-s-trait-record-once-per-settlement"
    )
    def test_three_regenerating_gauges(self):
        self._reset_activity(tick=START)
        # The clock stage settles the units a player observes; the fixture's own
        # zone is that unit here, so the party stands inside it.
        place_player(self, PROBE)
        _group_id, bodies = self._group(
            cell=PROBE,
            tick=START,
            activity=STATIONARY_ACTIVITY,
            members=1,
        )
        body = bodies[0]
        twin = self._monster(PROBE)
        self._prepare_gauges(body)
        self._prepare_gauges(twin)
        before = self._gauge_pairs(body)
        for key in GAUGE_KEYS:
            self.assertLess(
                int(getattr(body.traits, key).current),
                float(getattr(body.traits, key).max),
            )
        trait_id = int(
            body.attributes.get("traits", category="traits", return_obj=True).pk
        )

        clock = get_world_clock()
        clock.tick = START
        clock._persist(START)
        with CaptureQueriesContext(connection) as queries:
            clock.advance(300, AdvanceSource.COMMAND, ())

        counts = _update_statement_counts(_captured(queries), (trait_id,))
        self.assertEqual(counts[trait_id], 1, "one trait record per settlement")

        # The reference writer runs with no buffer open.
        settle_gauge_regeneration((twin,), 300)
        settled = self._gauge_pairs(body)
        reference = self._gauge_pairs(twin)
        self.assertNotEqual(settled, before, "the gauges really regenerated")
        self.assertEqual(settled, reference)
        for key in GAUGE_KEYS:
            self.assertGreaterEqual(settled[key][0], before[key][0])
            self.assertIsInstance(settled[key][0], int)


class DifferentialDeferredWritesTests(ScenarioSettlementFixture):
    """Deferred and immediate storage leave the same settled state."""

    def setUp(self):
        super().setUp()
        self._register_lifecycle()

    @staticmethod
    def _mode(deferred: bool):
        if deferred:
            return contextlib.nullcontext()
        # The reference: every write is stored when the writer makes it.
        return patch.object(
            population_lifecycle, "deferred_attribute_stores", contextlib.nullcontext
        )

    @staticmethod
    def _lower_gauges() -> None:
        for body in Monster.objects.all_family():
            if persisted_hp(body) <= 0:
                continue
            for key in GAUGE_KEYS:
                gauge = getattr(body.traits, key, None)
                if gauge is None:
                    continue
                gauge.current = max(1, int(gauge.current) - 3)

    def _advance(self, parts: tuple[int, ...], *, deferred: bool) -> dict:
        self._build_scenario()
        # The clock stage settles the units a player observes; the fixture's own
        # zone is that unit here, so the party stands inside it.
        place_player(self, PROBE)
        self._lower_gauges()
        clock = get_world_clock()
        clock.tick = START
        clock._persist(START)
        with self._mode(deferred):
            for part in parts:
                clock.advance(part, AdvanceSource.COMMAND, ())
        in_memory = settlement_projection(self.wilderness)
        _drop_attribute_caches(self.wilderness, Monster.objects.all_family())
        from_database = settlement_projection(self.wilderness)
        self.assertEqual(
            from_database,
            in_memory,
            msg="the deferred pass committed exactly what it settled",
        )
        return in_memory

    @covers_requirement(
        "world-clock::a-lifecycle-pass-inside-an-advance-stores-each-written-record-once"
    )
    def test_results_are_unchanged(self):
        partitions = ((1500,), (700, 800), (61, 1439))
        projections = {
            (parts, deferred): self._advance(parts, deferred=deferred)
            for parts in partitions
            for deferred in (True, False)
        }
        reference = projections[((1500,), True)]
        for (parts, deferred), projection in projections.items():
            self.assertEqual(
                projection,
                reference,
                msg=f"partition {parts} with deferred={deferred}",
            )
        # The scenario really settled, so the equality is not an untouched
        # state: a due episode, a site recovery and a journey all happened.
        self.assertGreater(reference["zones"][ZONE_KEY]["generation_sequence"], 0)
        self.assertEqual(
            reference["sites"][SITE_KEY]["state"], "populated"
        )
        self.assertTrue(reference["activity"]["journeys"] or reference["timeline"])