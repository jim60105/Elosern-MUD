"""Behaviour tests for the pure world-escape contract and its settlement.

The synthetic species catalog is injected, the real wilderness provider and
construction owner build every individual, and the assertions establish route
legality, affordability, deterministic selection and exact physiology rather
than any shipped coordinate, count or copy value.
"""

from __future__ import annotations

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.maps import monster_activity, regional_population as owner
from world.maps.monster_activity import (
    MemberTime,
    commit_monster_departure,
    create_group,
    group_of_member,
    read_monster_activity,
    record_combat_interval,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.action import RejectReason, RejectedAction
from world.rules.disengage import _handle_disengage
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    FatigueActivity,
    IntervalCompletion,
    SleepPosture,
    predict_interval,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef
from world.rules.world_escape import (
    AbstractEscapeContext,
    WorldEscapeContext,
    WorldEscapeError,
    plan_individual_escape,
    project_monster_combat_state,
    settle_monster_combat_through,
)
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

PROBE = (500, 700)
ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
SEED = 0
RESERVE = 360000


class WorldEscapeTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        owner.initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=PROBE, name=WILDERNESS_NAME)
        )
        self.room = self.char1.location

    # -- helpers ------------------------------------------------------------

    def _monster(self, cell=PROBE):
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        self.wilderness.db.itemcoordinates[individual] = cell
        room = (self.wilderness.db.rooms or {}).get(cell)
        if room is not None:
            individual.location = room
            room.contents_cache.add(individual)
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id=f"test:{individual.pk}",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            position=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        return individual

    def _context(self, individual, *, cell=PROBE, tick=12):
        return WorldEscapeContext(
            session_id="hostile:1:0",
            occurred_tick=tick,
            source=LocationRef.wilderness(WILDERNESS_NAME, *cell),
            operation_id="escape",
        )

    def _expected_reserve(self, state, activity, seconds):
        return predict_interval(
            state,
            activity,
            seconds,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end.reserve_units

    # -- planning -----------------------------------------------------------

    def test_a_missing_escape_context_is_a_named_rejection(self):
        from world.rules.combat import Battlefield
        from world.rules.combat_identity import stable_actor_id

        monster = self._monster()
        pursuer = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        field = Battlefield(
            {
                "foes": frozenset({stable_actor_id(monster)}),
                "party": frozenset({stable_actor_id(pursuer)}),
            },
            {stable_actor_id(monster): monster, stable_actor_id(pursuer): pursuer},
        )
        with self.assertRaises(RejectedAction) as caught:
            _handle_disengage(
                monster, [monster], "disengage:self", {"battlefield": field}, 1.0
            )
        self.assertIs(caught.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertIn("escape_context", caught.exception.detail)

    @covers_requirement(
        "monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure"
    )
    def test_an_abstract_context_changes_eligibility_only(self):
        from world.rules.combat import Battlefield
        from world.rules.combat_identity import stable_actor_id

        monster = self._monster()
        field = Battlefield(
            {
                "foes": frozenset({stable_actor_id(monster)}),
                "party": frozenset(),
            },
            {stable_actor_id(monster): monster},
        )
        effect = _handle_disengage(
            monster,
            [monster],
            "disengage:self",
            {"battlefield": field, "escape_context": AbstractEscapeContext()},
            1.0,
        )[0]
        effect.apply()
        self.assertIn(stable_actor_id(monster), field.fled)
        self.assertEqual(group_of_member(self.wilderness, monster.pk).journey_id, None)

    @covers_requirement(
        "monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure"
    )
    def test_no_lawful_route_returns_no_plan_even_without_a_pursuer(self):
        from evennia.utils.create import create_object

        from typeclasses.rooms import Room

        sealed = create_object(Room, key="t_sealed_room")
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="no-route",
            owner_kind="explicit",
            owner_key="test",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=LocationRef.room(sealed.pk),
            position=LocationRef.room(sealed.pk),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        individual.location = sealed
        sealed.contents_cache.add(individual)
        context = WorldEscapeContext(
            session_id="hostile:2:0",
            occurred_tick=6,
            source=LocationRef.room(sealed.pk),
            operation_id="escape",
        )
        self.assertIsNone(plan_individual_escape(individual, None, context))

    def test_partial_physiology_is_a_named_rejection_not_a_skip(self):
        individual = self._monster()
        individual.attributes.add(RESERVE_ATTRIBUTE, RESERVE)
        individual.attributes.remove(POSTURE_ATTRIBUTE)
        with self.assertRaises(WorldEscapeError) as caught:
            plan_individual_escape(individual, None, self._context(individual))
        self.assertTrue(str(caught.exception.reason))

    def test_post_action_reserve_prices_the_real_neighbor(self):
        individual = self._monster()
        group = group_of_member(self.wilderness, individual.pk)
        monster_activity.update_member_time(
            self.wilderness,
            group_id=group.group_id,
            individual_id=individual.pk,
            member_time=MemberTime(0, monster_activity.MODE_COMBAT, "s", ()),
        )
        record_combat_interval(
            self.wilderness,
            group_id=group.group_id,
            individual_id=individual.pk,
            start_tick=0,
            end_tick=6,
            activity=monster_activity.ACTIVITY_AWAKE_COMBAT,
        )
        context = self._context(individual, tick=12)
        plan = plan_individual_escape(individual, None, context)
        self.assertIsNotNone(plan)
        self.assertIsNotNone(plan.traversal.cost)
        self.assertGreaterEqual(plan.traversal.cost.seconds, 0)
        projected = project_monster_combat_state(individual, through_tick=12)
        live = read_optional_fatigue_state(individual)
        self.assertLess(projected.reserve_units, live.reserve_units)
        self.assertEqual(plan.state_after_combat.reserve_units, projected.reserve_units)
        self.assertEqual(plan.committed_plan["seconds"], plan.traversal.cost.seconds)
        self.assertEqual(plan.expected_group_sequence, group.sequence)
        # The selection is deterministic for the same occurrence.
        replay = plan_individual_escape(individual, None, context)
        self.assertEqual(replay.edge, plan.edge)
        self.assertEqual(replay.expected_fingerprint, plan.expected_fingerprint)

    @covers_requirement(
        "monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure"
    )
    def test_an_out_of_bounds_refuge_is_still_a_legal_escape(self):
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        self.wilderness.db.itemcoordinates[individual] = PROBE
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="far-home",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.wilderness(WILDERNESS_NAME, 900, 900),
            position=LocationRef.wilderness(WILDERNESS_NAME, *PROBE),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        plan = plan_individual_escape(individual, None, self._context(individual))
        self.assertIsNotNone(plan)
        self.assertNotEqual(
            plan.edge.destination,
            LocationRef.wilderness(WILDERNESS_NAME, 900, 900),
        )

    # -- settlement ---------------------------------------------------------

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_two_deferred_combat_rounds_pay_twelve_seconds_once(self):
        individual = self._monster()
        group = group_of_member(self.wilderness, individual.pk)
        monster_activity.update_member_time(
            self.wilderness,
            group_id=group.group_id,
            individual_id=individual.pk,
            member_time=MemberTime(0, monster_activity.MODE_COMBAT, "s", ()),
        )
        before = read_optional_fatigue_state(individual)
        settled = settle_monster_combat_through(
            individual, through_tick=12, operation_id="escape"
        )
        expected = self._expected_reserve(before, FatigueActivity.AWAKE_COMBAT, 12)
        self.assertEqual(settled.reserve_units, expected)
        self.assertEqual(
            group_of_member(self.wilderness, individual.pk)
            .member_time[str(individual.pk)]
            .settled_through_tick,
            12,
        )
        # Repeating the same settlement pays nothing again.
        repeated = settle_monster_combat_through(
            individual, through_tick=12, operation_id="escape"
        )
        self.assertEqual(repeated.reserve_units, expected)

    @covers_requirement(
        "monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure",
        "monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay",
    )
    def test_departure_removes_presence_and_replays_from_the_receipt(self):
        individual = self._monster()
        plan = plan_individual_escape(individual, None, self._context(individual))
        before_cell = self.wilderness.db.itemcoordinates.get(individual)
        first = commit_monster_departure(self.wilderness, plan)
        second = commit_monster_departure(self.wilderness, plan)
        self.assertEqual(first, second)
        state = read_monster_activity(self.wilderness)
        self.assertEqual(len(state.journeys), 1)
        journey = state.journeys[first]
        self.assertEqual(journey.member_ids, (individual.pk,))
        self.assertEqual(journey.depart_tick, plan.occurred_tick)
        self.assertNotIn(individual, self.wilderness.db.itemcoordinates)
        self.assertIsNone(individual.location)
        self.assertEqual(before_cell, PROBE)
        group = state.groups[journey.group_id]
        self.assertEqual(group.home_owner, ("zone", "t_zone"))
        self.assertIsNone(group.position)
        self.assertEqual(group.journey_id, first)
        # Neither endpoint reports it as present before arrival.
        self.assertIsNone(
            owner.actual_cell(self.wilderness, individual)
        )
        self.assertIsNone(
            self.wilderness.db.itemcoordinates.get(individual)
        )
        self.assertNotEqual(
            self.wilderness.db.itemcoordinates.get(individual), PROBE
        )

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_a_protected_arrival_waits_without_a_second_travel_charge(self):
        individual = self._monster()
        plan = plan_individual_escape(individual, None, self._context(individual))
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        destination = journey.destination
        owner.record_population_protection(
            self.wilderness,
            engagement_id="other-fight",
            cell=(destination.x, destination.y),
            start_tick=0,
            end_tick=None,
        )
        events = monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        self.assertEqual([event.kind for event in events], ["monster_arrival_deferred"])
        deferred = read_monster_activity(self.wilderness).journeys[journey_id]
        self.assertIsNotNone(deferred.retry_tick)
        self.assertGreater(deferred.retry_tick, journey.arrival_tick)
        arrived_state = read_optional_fatigue_state(individual)
        owner.record_population_protection(
            self.wilderness,
            engagement_id="other-fight",
            cell=(destination.x, destination.y),
            start_tick=0,
            end_tick=journey.arrival_tick,
        )
        # Closing the protection at the deferred boundary lets the same
        # journey arrive without re-paying its passage.
        monster_activity.settle_monster_activity_at(
            self.wilderness, deferred.retry_tick
        )
        remaining = read_monster_activity(self.wilderness)
        self.assertNotIn(journey_id, remaining.journeys)
        arrived = read_optional_fatigue_state(individual)
        expected_wait = predict_interval(
            arrived_state,
            FatigueActivity.AWAKE,
            deferred.retry_tick - deferred.arrival_tick,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end
        self.assertEqual(arrived.reserve_units, expected_wait.reserve_units)
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(individual),
            (destination.x, destination.y),
        )

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_inactive_arrival_creates_no_room_and_preserves_identity(self):
        individual = self._monster()
        plan = plan_individual_escape(individual, None, self._context(individual))
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        rooms_before = dict(self.wilderness.db.rooms)
        monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        self.assertEqual(dict(self.wilderness.db.rooms), rooms_before)
        self.assertTrue(ObjectDB.objects.filter(pk=individual.pk).exists())
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(individual),
            (journey.destination.x, journey.destination.y),
        )
        self.assertIsNone(individual.location)

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_equal_partitions_and_a_reload_preserve_resources_and_progress(self):
        individual = self._monster()
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        start = read_optional_fatigue_state(individual)
        plan = plan_individual_escape(individual, None, self._context(individual))
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        # Pay the passage in two equivalent partitions, re-reading the record
        # between them (the restart seam).
        midpoint = journey.depart_tick + (journey.arrival_tick - journey.depart_tick) // 2
        monomer = read_monster_activity(self.wilderness).journeys[journey_id]
        self.assertEqual(monomer.settled_through_tick, journey.depart_tick)
        monster_activity.settle_monster_activity_at(self.wilderness, midpoint)
        after_first = read_optional_fatigue_state(individual)
        reloaded = read_monster_activity(self.wilderness)
        self.assertIn(journey_id, reloaded.journeys)
        monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        arrived = read_optional_fatigue_state(individual)
        total = journey.arrival_tick - journey.depart_tick
        expected = self._expected_reserve(start, FatigueActivity.FOOT_TRAVEL, total)
        self.assertLessEqual(arrived.reserve_units, after_first.reserve_units)
        # The integrated journey pays one passage, not two: the reserve is
        # exactly the single-interval prediction from the departure state.
        self.assertEqual(arrived.reserve_units, expected)
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(individual),
            (journey.destination.x, journey.destination.y),
        )

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_the_population_lifecycle_settles_a_journey_in_equal_partitions(self):
        from types import MappingProxyType
        from unittest.mock import patch

        from world.maps import monster_sites, population_lifecycle

        from world.rules.clock import get_world_clock

        self.enterContext(
            patch.object(monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({}))
        )
        population_lifecycle.register_regional_population()
        from world.rules import clock as clock_module

        self.addCleanup(
            clock_module._EVENT_SOURCES.pop, population_lifecycle.STAGE_KIND, None
        )
        individual = self._monster()
        departure_state = read_optional_fatigue_state(individual)
        plan = plan_individual_escape(individual, None, self._context(individual))
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        self.assertGreater(journey.arrival_tick, journey.depart_tick)
        clock = get_world_clock()
        clock.tick = journey.depart_tick
        midpoint = journey.depart_tick + (journey.arrival_tick - journey.depart_tick) // 2

        population_lifecycle.settle_population_lifecycle(
            journey.depart_tick, midpoint
        )
        self.assertIn(
            journey_id,
            read_monster_activity(self.wilderness).journeys,
            "a partition without a boundary must not advance the passage",
        )
        population_lifecycle.settle_population_lifecycle(
            midpoint, journey.arrival_tick
        )
        arrived = read_optional_fatigue_state(individual)
        expected = self._expected_reserve(
            departure_state,
            FatigueActivity.FOOT_TRAVEL,
            journey.arrival_tick - journey.depart_tick,
        )
        self.assertEqual(arrived.reserve_units, expected)
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(individual),
            (journey.destination.x, journey.destination.y),
        )
        self.assertNotIn(
            journey_id, read_monster_activity(self.wilderness).journeys
        )

    @covers_requirement(
        "monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay"
    )
    def test_a_late_lifecycle_failure_restores_the_whole_journey(self):
        from unittest.mock import patch
        from types import MappingProxyType

        from world.maps import monster_sites, population_lifecycle

        from world.rules.clock import AdvanceSource, get_world_clock

        self.enterContext(
            patch.object(monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({}))
        )
        population_lifecycle.register_regional_population()
        from world.rules import clock as clock_module

        self.addCleanup(
            clock_module._EVENT_SOURCES.pop, population_lifecycle.STAGE_KIND, None
        )
        individual = self._monster()
        plan = plan_individual_escape(individual, None, self._context(individual))
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        before_activity = monster_activity.state_to_dict(
            read_monster_activity(self.wilderness)
        )
        before_reserve = read_optional_fatigue_state(individual).reserve_units
        self.assertEqual(
            self.wilderness.db.itemcoordinates.get(individual), None
        )
        from world.rules.sleep_receipt import SLEEP_RECEIPT_SURFACES

        surface = monster_activity.snapshot_activity_surfaces(self.wilderness)[
            id(individual)
        ]
        self.assertTrue(
            all(
                (key, category) in surface.attributes
                for key, category in SLEEP_RECEIPT_SURFACES
            )
        )
        clock = get_world_clock()
        clock.tick = journey.depart_tick
        real_settle = owner.settle_timeline_through

        def fail_after_arrival(wilderness, tick, **kwargs):
            if tick >= journey.arrival_tick:
                raise RuntimeError("synthetic late lifecycle failure")
            return real_settle(wilderness, tick, **kwargs)

        with patch.object(
            owner, "settle_timeline_through", side_effect=fail_after_arrival
        ):
            with self.assertRaises(RuntimeError):
                clock.advance(
                    journey.arrival_tick - journey.depart_tick,
                    AdvanceSource.SKIP,
                    [],
                )
        self.assertEqual(
            monster_activity.state_to_dict(read_monster_activity(self.wilderness)),
            before_activity,
        )
        self.assertEqual(
            read_optional_fatigue_state(individual).reserve_units, before_reserve
        )
        self.assertIsNone(self.wilderness.db.itemcoordinates.get(individual))
        self.assertIn(
            journey_id, read_monster_activity(self.wilderness).journeys
        )

    def test_admission_pays_the_idle_prefix_before_combat_ownership(self):
        from world.maps.monster_activity import begin_member_combat

        individual = self._monster()
        before = read_optional_fatigue_state(individual)
        self.assertTrue(
            begin_member_combat(
                self.wilderness,
                individual_id=individual.pk,
                session_id="s",
                tick=10,
            )
        )
        expected = self._expected_reserve(before, FatigueActivity.AWAKE, 10)
        self.assertEqual(read_optional_fatigue_state(individual).reserve_units, expected)
        group = group_of_member(self.wilderness, individual.pk)
        cursor = group.member_time[str(individual.pk)]
        self.assertEqual((cursor.settled_through_tick, cursor.mode), (10, "combat"))

    def test_a_real_authored_room_session_has_world_escape_authority(self):
        from evennia.utils.create import create_object

        from typeclasses.exits import Exit
        from typeclasses.rooms import Room

        from world.rules.combat_session.battlefield import _escape_context_for
        from world.rules.combat_session.records import CombatSessionRecord
        from world.rules.world_escape import WorldEscapeContext

        room = create_object(Room, key="t_escape_source")
        other = create_object(Room, key="t_escape_destination")
        create_object(
            Exit, key="out", location=room, destination=other
        )
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        individual.location = room
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="room",
            owner_kind="explicit",
            owner_key="test",
            activity_key=monster_activity.STAGED_STATIONARY_ACTIVITY,
            home=LocationRef.room(room.pk),
            position=LocationRef.room(room.pk),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        record = CombatSessionRecord(
            session_id="hostile:1:0",
            engagement_id="hostile:1:0:1",
            mode="hostile",
            room_id=int(room.pk),
            player_ids=(int(self.char1.pk),),
            enemy_ids=(int(individual.pk),),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
            started_tick=12,
            population_cell=None,
        )
        context = _escape_context_for(record)
        self.assertIsInstance(context, WorldEscapeContext)
        self.assertEqual(context.source, LocationRef.room(room.pk))
        plan = plan_individual_escape(individual, None, context)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.edge.destination, LocationRef.room(other.pk))

    def test_a_locked_room_exit_defers_arrival_and_retries_without_repricing(self):
        from evennia.utils.create import create_object

        from typeclasses.exits import Exit
        from typeclasses.rooms import Room

        from world.rules.world_escape import EscapePlan

        room = create_object(Room, key="t_room_source")
        other = create_object(Room, key="t_room_destination")
        exit_obj = create_object(
            Exit, key="out", location=room, destination=other
        )
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        individual.location = room
        write_fatigue_state(individual, RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="room-lock",
            owner_kind="explicit",
            owner_key="test",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.room(room.pk),
            position=LocationRef.room(room.pk),
            member_ids=(individual.pk,),
            seed=SEED,
            tick=0,
        )
        context = WorldEscapeContext(
            session_id="hostile:4:0",
            occurred_tick=6,
            source=LocationRef.room(room.pk),
            operation_id="room-lock:escape",
        )
        plan = plan_individual_escape(individual, None, context)
        self.assertIsInstance(plan, EscapePlan)
        journey_id = commit_monster_departure(self.wilderness, plan)
        journey = read_monster_activity(self.wilderness).journeys[journey_id]
        exit_obj.locks.add("traverse:false()")
        events = monster_activity.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        self.assertEqual([event.kind for event in events], ["monster_arrival_deferred"])
        deferred = read_monster_activity(self.wilderness).journeys[journey_id]
        after_defer = read_optional_fatigue_state(individual)
        self.assertIsNone(individual.location)
        exit_obj.locks.add("traverse:all()")
        arrived_events = monster_activity.settle_monster_activity_at(
            self.wilderness, deferred.retry_tick
        )
        self.assertEqual([event.kind for event in arrived_events], ["monster_arrived"])
        from world.rules.fatigue import predict_interval

        waiting = predict_interval(
            after_defer,
            FatigueActivity.AWAKE,
            deferred.retry_tick - deferred.arrival_tick,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end
        self.assertEqual(
            read_optional_fatigue_state(individual).reserve_units,
            waiting.reserve_units,
        )
        self.assertIs(individual.location, other)
        self.assertNotIn(
            journey_id, read_monster_activity(self.wilderness).journeys
        )
