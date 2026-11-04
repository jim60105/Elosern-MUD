"""Behaviour tests for seeded global monster activity decisions.

The synthetic species catalog and a file-local activity/area registry are
injected into the owners' own bindings, the real wilderness provider and
construction owners build every individual, and every assertion establishes a
mechanism (saved determinism, group cohesion, legality, exact elapsed
physiology, chronological ordering) rather than shipped copy, coordinates or
balance values.
"""

from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.monsters import Monster

import world.lore.monster_activity as lore_activity
from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.monster_placement import EcologyZone
from world.maps import (
    monster_activity,
    monster_sites,
    population_lifecycle,
    regional_population,
)
from world.maps import monster_activity as activity_owner
from world.maps.monster_activity import (
    MemberTime,
    MonsterActivityState,
    commit_group_decision,
    create_group,
    plan_group_decision,
    read_monster_activity,
    state_to_dict,
)
from world.maps.population_lifecycle import settle_population_lifecycle
from world.maps.regional_population import (
    initialize_population_seed,
    population_counts,
    read_population_timeline,
    record_population_protection,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.fatigue import (
    SleepPosture,
    read_optional_fatigue_state,
    write_fatigue_state,
)
from world.rules.mental_time import plan_for
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef, quote_edge
from world.rules.sleep_receipt import read_sleep_receipt
from world.rules.travel_cost import TraversalStatus
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries

PROBE = (500, 700)
ORDINARY = next(iter(SYNTH_MONSTER_VARIANTS))
SEED = 11
RESERVE = 360000

#: One file-local movable extent bounded to the real published region around
#: the probe cell, and one zero-radius stationary home. No shipped key, cell
#: list or copy value is pinned by these names.
AREA_KEY = "t_activity_probe_ground"
HOME_AREA_KEY = "t_activity_probe_home"
GROUP_ACTIVITY = "t_activity_probe_group"
SOLO_ACTIVITY = "t_activity_probe_solo"
STATIONARY_ACTIVITY = "t_activity_probe_stationary"


class ActivityFixture(RegistryIsolationMixin, EvenniaTest):
    """Real wilderness world, synthetic catalogs and file-local activity rows."""

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
        initialize_population_seed(self.wilderness, seed=SEED, tick=0)
        self.region = region_for_coordinates(*PROBE)
        area = ActivityArea(AREA_KEY, self.region, ((500, 519, 700, 719),))
        home = ActivityArea(HOME_AREA_KEY, home_radius=0)
        self.enterContext(
            patch.object(
                lore_activity,
                "ACTIVITY_AREA_REGISTRY",
                MappingProxyType({AREA_KEY: area, HOME_AREA_KEY: home}),
            )
        )
        self.enterContext(
            patch.object(
                lore_activity,
                "MONSTER_ACTIVITY_REGISTRY",
                MappingProxyType(
                    {
                        GROUP_ACTIVITY: MonsterActivity(
                            GROUP_ACTIVITY,
                            "cohesive_group",
                            AREA_KEY,
                            90,
                            AggressionCondition("passive"),
                        ),
                        SOLO_ACTIVITY: MonsterActivity(
                            SOLO_ACTIVITY,
                            "solitary_roaming",
                            AREA_KEY,
                            60,
                            AggressionCondition("passive"),
                        ),
                        STATIONARY_ACTIVITY: MonsterActivity(
                            STATIONARY_ACTIVITY,
                            "stationary",
                            HOME_AREA_KEY,
                            120,
                            AggressionCondition("passive"),
                        ),
                    }
                ),
            )
        )
        # The owner's own module resolves the same registries, so its
        # interval/declaration readers see exactly these rows.
        self.enterContext(
            patch.object(
                activity_owner,
                "_declaration",
                self._declaration,
            )
        )
        self.enterContext(
            patch.object(
                monster_sites, "MONSTER_SITE_REGISTRY", MappingProxyType({})
            )
        )
        self.enterContext(
            patch.object(
                regional_population,
                "ECOLOGY_ZONE_REGISTRY",
                MappingProxyType(
                    {
                        "t_activity_zone": EcologyZone(
                            "t_activity_zone",
                            self.region,
                            ((500, 519, 700, 719),),
                            (),
                            1,
                            100,
                            100,
                            3600,
                            600,
                            1,
                        )
                    }
                ),
            )
        )
        self._ordinal = 0
        self._registered = False

    # -- seams --------------------------------------------------------------

    @staticmethod
    def _declaration(activity_key: str):
        return {
            GROUP_ACTIVITY: MonsterActivity(
                GROUP_ACTIVITY,
                "cohesive_group",
                AREA_KEY,
                90,
                AggressionCondition("passive"),
            ),
            SOLO_ACTIVITY: MonsterActivity(
                SOLO_ACTIVITY,
                "solitary_roaming",
                AREA_KEY,
                60,
                AggressionCondition("passive"),
            ),
            STATIONARY_ACTIVITY: MonsterActivity(
                STATIONARY_ACTIVITY,
                "stationary",
                HOME_AREA_KEY,
                120,
                AggressionCondition("passive"),
            ),
        }.get(activity_key)

    def _register_lifecycle(self) -> None:
        if self._registered:
            return
        from world.rules import clock as clock_module

        population_lifecycle.register_regional_population()
        self.addCleanup(
            clock_module._EVENT_SOURCES.pop,
            population_lifecycle.STAGE_KIND,
            None,
        )
        self._registered = True

    def _monster(
        self,
        cell: tuple[int, int] = PROBE,
        *,
        reserve: int = RESERVE,
        posture: SleepPosture = SleepPosture.AWAKE,
        home_zone: str | None = "t_activity_zone",
    ):
        individual = construct_species_individual(
            next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key, ORDINARY
        )
        individual.traits.hp.base = 100000
        individual.traits.hp.current = 100000
        if home_zone is not None:
            individual.db.home_ecology_zone = home_zone
        self.wilderness.db.itemcoordinates[individual] = cell
        room = (self.wilderness.db.rooms or {}).get(cell)
        if room is not None:
            individual.location = room
            room.contents_cache.add(individual)
        write_fatigue_state(individual, reserve, posture)
        return individual

    def _group(
        self,
        *,
        cell: tuple[int, int] = PROBE,
        members: int = 2,
        activity: str = GROUP_ACTIVITY,
        owner_kind: str = "zone",
        owner_key: str = "t_activity_zone",
        seed: int = SEED,
        tick: int = 0,
        reserves: tuple[int, ...] | None = None,
        postures: tuple[SleepPosture, ...] | None = None,
    ):
        count = members
        bodies = tuple(
            self._monster(
                cell,
                reserve=RESERVE if reserves is None else reserves[index],
                posture=(
                    SleepPosture.AWAKE
                    if postures is None
                    else postures[index]
                ),
            )
            for index in range(count)
        )
        ref = LocationRef.wilderness(WILDERNESS_NAME, *cell)
        self._ordinal += 1
        group_id = create_group(
            self.wilderness,
            operation_id=f"activity-test:{self._ordinal}",
            owner_kind=owner_kind,
            owner_key=owner_key,
            activity_key=activity,
            home=ref,
            position=ref,
            member_ids=tuple(body.pk for body in bodies),
            seed=seed,
            tick=tick,
        )
        return group_id, bodies

    def _due(self, group_id: str) -> int:
        return read_monster_activity(self.wilderness).groups[group_id].next_decision_tick

    def _reset_activity(self, *, tick: int) -> None:
        for individual in Monster.objects.all_family():
            individual.delete()
        self._ordinal = 0
        self.wilderness.db.itemcoordinates = {}
        self.wilderness.db.monster_activity = state_to_dict(
            MonsterActivityState({}, {}, {}, (), tick)
        )
        self.wilderness.db.population_timeline = {
            "settled_through_tick": tick,
            "transitions": [],
            "protection": [],
        }
        get_world_clock().tick = tick

    def _departure_seed(
        self,
        *,
        tick: int,
        activity: str = GROUP_ACTIVITY,
        cell: tuple[int, int] = PROBE,
        members: int = 2,
        wilderness_only: bool = False,
    ) -> int:
        """A saved seed whose decision at ``tick`` is a lawful departure.

        Each candidate is evaluated from a fresh, identically shaped state so
        the group identity and sequence are exactly the ones the caller will
        recreate; the draw stream therefore stays comparable.
        """
        for seed in range(32):
            self._reset_activity(tick=0)
            group_id, _bodies = self._group(
                cell=cell,
                seed=seed,
                tick=0,
                activity=activity,
                members=members,
            )
            decision = plan_group_decision(self.wilderness, group_id, tick=tick)
            if decision.edge is None:
                continue
            if wilderness_only and (
                decision.edge.destination.kind != "wilderness"
                or not decision.edge.route.startswith("direction:")
            ):
                continue
            return seed
        raise AssertionError("no seed produced a lawful departure")

    def _stay_seed(self, *, tick: int, activity: str = GROUP_ACTIVITY) -> int:
        """A saved seed whose decision at ``tick`` is a scheduled stay."""
        for seed in range(32):
            self._reset_activity(tick=0)
            group_id, _bodies = self._group(seed=seed, tick=0, activity=activity)
            if plan_group_decision(self.wilderness, group_id, tick=tick).edge is None:
                return seed
        raise AssertionError("no seed produced a scheduled stay")

    def _seal_exits(self, cell: tuple[int, int], *, keep: str | None = None) -> None:
        """Materialize ``cell`` and lock every direction exit except ``keep``."""
        from world.maps.wilderness_destination import normalize_wilderness_direction

        room = (self.wilderness.db.rooms or {}).get(cell)
        if room is None:
            enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME)
            room = (self.wilderness.db.rooms or {}).get(cell)
        if room is None:
            raise AssertionError(f"no materialized room at {cell}")
        for exit_obj in room.exits:
            direction = normalize_wilderness_direction(getattr(exit_obj, "key", None))
            if direction == keep:
                continue
            exit_obj.locks.add("traverse:false()")


class SeededDecisionTests(ActivityFixture):
    """Saved stay/departure selection, cohesion, legality and bounds."""

    def test_saved_decision_is_stable_across_reads_and_reload(self):
        stay_seed = self._stay_seed(tick=90)
        self._reset_activity(tick=0)
        stay_id, _stay_bodies = self._group(seed=stay_seed, tick=0)
        first = plan_group_decision(self.wilderness, stay_id, tick=90)
        self.assertIsNone(first.edge)
        self.wilderness.attributes.reset_cache()
        again = plan_group_decision(self.wilderness, stay_id, tick=90)
        self.assertEqual(again, first)
        commit_group_decision(self.wilderness, again)
        stayed = read_monster_activity(self.wilderness).groups[stay_id]
        self.assertIsNone(stayed.journey_id)
        self.assertEqual(stayed.sequence, 1)
        self.assertGreater(stayed.next_decision_tick, 90)
        # A replayed commit is stale, never a second increment or a new draw.
        with self.assertRaises(monster_activity.MonsterActivityOperationInvalid):
            commit_group_decision(self.wilderness, again)
        self.assertEqual(
            read_monster_activity(self.wilderness).groups[stay_id].sequence, 1
        )

        departure_seed = self._departure_seed(tick=90)
        self._reset_activity(tick=0)
        moving_id, moving_bodies = self._group(seed=departure_seed, tick=0)
        decision = plan_group_decision(self.wilderness, moving_id, tick=90)
        self.assertIsNotNone(decision.edge)
        self.assertEqual(
            decision, plan_group_decision(self.wilderness, moving_id, tick=90)
        )
        commit_group_decision(self.wilderness, decision)
        state = read_monster_activity(self.wilderness)
        travelling = state.groups[moving_id]
        self.assertIsNotNone(travelling.journey_id)
        self.assertEqual(travelling.sequence, 1)
        self.assertIsNone(travelling.position)
        journey = state.journeys[travelling.journey_id]
        self.assertEqual(set(journey.member_ids), {body.pk for body in moving_bodies})
        self.assertNotIn(moving_bodies[0], self.wilderness.db.itemcoordinates)

    def test_mixed_group_travels_at_the_slowest_member_price(self):
        seed = None
        for candidate in range(64):
            group_id, bodies = self._group(
                seed=candidate,
                tick=0,
                reserves=(RESERVE, 100000),
                members=2,
            )
            decision = plan_group_decision(self.wilderness, group_id, tick=90)
            if (
                decision.edge is not None
                and decision.edge.route.startswith("direction:")
                and decision.edge.destination.kind == "wilderness"
            ):
                seed = candidate
                break
        self.assertIsNotNone(seed, "no wilderness departure seed")
        self._reset_activity(tick=0)
        group_id, bodies = self._group(
            seed=seed, tick=0, reserves=(RESERVE, 100000), members=2
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        commit_group_decision(self.wilderness, decision)
        state = read_monster_activity(self.wilderness)
        journey = state.journeys[state.groups[group_id].journey_id]
        self.assertEqual(len(journey.plan.members), 2)
        group_quote = quote_edge(
            bodies[0],
            journey.edge,
            tuple(ObjectDB.objects.get(pk=body.pk) for body in bodies),
        )
        self.assertIs(group_quote.status, TraversalStatus.RESOLVED)
        self.assertEqual(journey.plan.seconds, group_quote.cost.seconds)
        fastest = quote_edge(
            bodies[0],
            journey.edge,
            (ObjectDB.objects.get(pk=bodies[0].pk),),
        )
        self.assertGreaterEqual(group_quote.cost.seconds, fastest.cost.seconds)

    def test_sleeping_member_keeps_the_whole_group(self):
        group_id, _bodies = self._group(
            tick=0, postures=(SleepPosture.AWAKE, SleepPosture.VOLUNTARY)
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(decision.edge)
        self.assertEqual(decision.reason, monster_activity.STAY_MEMBER_SLEEPING)
        commit_group_decision(self.wilderness, decision)
        self.assertIsNone(
            read_monster_activity(self.wilderness).groups[group_id].journey_id
        )

    def test_unaffordable_member_keeps_the_whole_group(self):
        group_id, bodies = self._group(tick=0, reserves=(RESERVE, 100))
        for body in bodies:
            activity_owner.update_member_time(
                self.wilderness,
                group_id=group_id,
                individual_id=body.pk,
                member_time=MemberTime(90, monster_activity.MODE_IDLE, None, ()),
            )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(decision.edge)
        self.assertEqual(
            decision.reason, monster_activity.STAY_MEMBER_UNAFFORDABLE
        )

    def test_combat_owned_and_historical_members_never_wander(self):
        group_id, bodies = self._group(tick=0)
        activity_owner.update_member_time(
            self.wilderness,
            group_id=group_id,
            individual_id=bodies[0].pk,
            member_time=MemberTime(90, monster_activity.MODE_COMBAT, "s", ()),
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(decision.edge)
        self.assertEqual(decision.reason, monster_activity.STAY_MEMBER_ENGAGED)

        activity_owner.update_member_time(
            self.wilderness,
            group_id=group_id,
            individual_id=bodies[0].pk,
            member_time=MemberTime(180, monster_activity.MODE_IDLE, None, ()),
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(decision.edge)
        self.assertEqual(
            decision.reason, monster_activity.STAY_MEMBER_SETTLED_AHEAD
        )

    def test_active_combat_participant_never_wanders_even_when_released(self):
        group_id, bodies = self._group(tick=0, members=1)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        with patch.object(
            regional_population,
            "active_combat_participant_ids",
            return_value=frozenset({int(bodies[0].pk)}),
        ):
            blocked = plan_group_decision(self.wilderness, group_id, tick=90)
            self.assertIsNone(blocked.edge)
            self.assertEqual(blocked.reason, monster_activity.STAY_MEMBER_ENGAGED)
            if decision.edge is not None:
                before = state_to_dict(read_monster_activity(self.wilderness))
                with self.assertRaises(
                    monster_activity.MonsterActivityOperationInvalid
                ):
                    commit_group_decision(self.wilderness, decision)
                self.assertEqual(
                    state_to_dict(read_monster_activity(self.wilderness)), before
                )

    def test_immediate_posture_transitions_are_committed(self):
        depleted, depleted_bodies = self._group(
            cell=(505, 705), tick=0, members=1, reserves=(0,)
        )
        waking, waking_bodies = self._group(
            cell=(515, 715),
            tick=0,
            members=1,
            reserves=(72000,),
            postures=(SleepPosture.FORCED,),
        )
        activity_owner.settle_group_idle(self.wilderness, depleted, tick=10)
        activity_owner.settle_group_idle(self.wilderness, waking, tick=10)
        depleted_state = read_optional_fatigue_state(depleted_bodies[0])
        self.assertIs(depleted_state.posture, SleepPosture.FORCED)
        self.assertEqual(depleted_state.reserve_units, 120)
        waking_state = read_optional_fatigue_state(waking_bodies[0])
        self.assertIs(waking_state.posture, SleepPosture.AWAKE)
        self.assertEqual(waking_state.reserve_units, 71960)

    def test_bounds_corner_and_locked_gates_hold(self):
        corner = (500, 700)
        self._seal_exits(corner, keep="w")
        group_id, _bodies = self._group(cell=corner, tick=90, members=1)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        # West leaves the authored rectangle: the group stays rather than
        # stepping outside its bounded area.
        self.assertIsNone(decision.edge)
        self.assertEqual(decision.reason, monster_activity.STAY_NO_LEGAL_ROUTE)

        self._seal_exits(corner, keep=None)
        locked = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(locked.edge)

    def test_birth_exclusions_never_block_lawful_travel(self):
        group_id, _bodies = self._group(tick=0, members=1)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNotNone(decision.edge)
        with patch.object(
            regional_population,
            "eligible_birth_cells",
            side_effect=AssertionError("activity must not read birth geometry"),
        ):
            commit_group_decision(self.wilderness, decision)
        self.assertIsNotNone(
            read_monster_activity(self.wilderness).groups[group_id].journey_id
        )

    @covers_requirement(
        "monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay"
    )
    def test_commit_revalidates_every_members_access(self):
        group_id, _bodies = self._group(tick=0, members=2)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNotNone(decision.edge)
        before = state_to_dict(read_monster_activity(self.wilderness))
        self._seal_exits(PROBE, keep=None)
        with self.assertRaises(monster_activity.MonsterActivityOperationInvalid):
            commit_group_decision(self.wilderness, decision)
        self.assertEqual(
            state_to_dict(read_monster_activity(self.wilderness)), before
        )

    def test_protected_destination_prevents_departure(self):
        group_id, _bodies = self._group(tick=0, members=1)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (dx, dy) == (0, 0):
                    continue
                record_population_protection(
                    self.wilderness,
                    engagement_id=f"test:{dx}:{dy}",
                    cell=(PROBE[0] + dx, PROBE[1] + dy),
                    start_tick=0,
                    end_tick=None,
                )
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNone(decision.edge)
        self.assertEqual(decision.reason, monster_activity.STAY_NO_LEGAL_ROUTE)

    def test_gm_inspection_reports_the_committed_activity_binding(self):
        from web.gm.readers import monsters as reader

        _group_id, bodies = self._group(tick=0, members=1)
        section = reader.placement_section(ObjectDB.objects.get(pk=bodies[0].pk))
        labels = {entry["label"] for entry in section["rows"]}
        self.assertIn("活動", labels)
        self.assertIn("下一次決策", labels)

    def test_committed_decision_emits_the_catalog_event(self):
        group_id, _bodies = self._group(tick=0, members=1)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        with (
            patch.object(activity_owner, "log_info") as log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            commit_group_decision(self.wilderness, decision)
        events = [call.args[0] for call in log.call_args_list if call.args]
        self.assertIn("monster_activity_decided", events)
        context = next(
            call.kwargs["context"]
            for call in log.call_args_list
            if call.args and call.args[0] == "monster_activity_decided"
        )
        self.assertEqual(
            set(context), {"group", "sequence", "tick", "reason"}
        )

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence",
        "monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay",
    )
    def test_departure_is_atomic_and_arrival_is_one_unit(self):
        group_id, bodies = self._group(tick=0, members=3)
        decision = plan_group_decision(self.wilderness, group_id, tick=90)
        self.assertIsNotNone(decision.edge)
        rooms_before = dict(self.wilderness.db.rooms)
        commit_group_decision(self.wilderness, decision)
        state = read_monster_activity(self.wilderness)
        group = state.groups[group_id]
        journey = state.journeys[group.journey_id]
        for body in bodies:
            body = ObjectDB.objects.get(pk=body.pk)
            self.assertNotIn(body, self.wilderness.db.itemcoordinates)
            self.assertIsNone(body.location)
        self.assertEqual(group.home_owner, ("zone", "t_activity_zone"))
        # Home ownership survives transit: the same group keeps its owner and
        # no replacement identity is created. An emigrant never frees its
        # home-owned slot merely by leaving.
        in_transit = population_counts(self.wilderness, "t_activity_zone")
        self.assertEqual(
            set(in_transit.home_ids), {int(body.pk) for body in bodies}
        )
        self.assertEqual(in_transit.local_ids, frozenset())
        # A foreign visitor at a zone cell consumes local headroom without
        # changing home ownership.
        visitor = self._monster(cell=(510, 700), home_zone=None)
        visitor_counts = population_counts(self.wilderness, "t_activity_zone")
        self.assertIn(int(visitor.pk), visitor_counts.local_ids)
        self.assertNotIn(int(visitor.pk), visitor_counts.home_ids)
        coordinates = dict(self.wilderness.db.itemcoordinates)
        coordinates.pop(visitor, None)
        self.wilderness.db.itemcoordinates = coordinates
        visitor.delete()

        events = activity_owner.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        self.assertEqual(
            [event.kind for event in events],
            ["monster_arrived"] * len(bodies),
        )
        state = read_monster_activity(self.wilderness)
        arrived = state.groups[group_id]
        self.assertIsNone(arrived.journey_id)
        self.assertEqual(arrived.position, journey.destination)
        destination = (journey.destination.x, journey.destination.y)
        for body in bodies:
            body = ObjectDB.objects.get(pk=body.pk)
            self.assertEqual(self.wilderness.db.itemcoordinates[body], destination)
        arrived_counts = population_counts(self.wilderness, "t_activity_zone")
        self.assertEqual(
            set(arrived_counts.home_ids), {int(body.pk) for body in bodies}
        )
        # No unobserved cell grew a room, and the persisted shape reloads.
        self.assertEqual(dict(self.wilderness.db.rooms), rooms_before)
        self.wilderness.attributes.reset_cache()
        self.assertEqual(
            state_to_dict(read_monster_activity(self.wilderness)),
            state_to_dict(state),
        )


class ChokepointLifecycleTests(ActivityFixture):
    """Stationary bindings, return-after-escape and deterministic settlement."""

    def test_combat_prefix_regenerates_gauges_before_ownership_release(self):
        from world.rules import world_escape

        group_id, bodies = self._group(tick=0, members=1)
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        body.traits.hp.current = 1000
        activity_owner.update_member_time(
            self.wilderness,
            group_id=group_id,
            individual_id=body.pk,
            member_time=MemberTime(
                0, monster_activity.MODE_COMBAT, "session", ()
            ),
        )
        world_escape.settle_monster_combat_through(
            body, through_tick=60, operation_id="combat-gauge"
        )
        # hp rate is 0.4/s and no member is skipped for the combat prefix.
        self.assertEqual(body.traits.hp.current, 1024)
        released = read_monster_activity(self.wilderness).groups[group_id]
        member = released.member_time[str(body.pk)]
        self.assertEqual(member.mode, monster_activity.MODE_IDLE)
        self.assertEqual(member.settled_through_tick, 60)
        world_escape.settle_monster_combat_through(
            body, through_tick=60, operation_id="combat-gauge"
        )
        self.assertEqual(body.traits.hp.current, 1024)

    def test_a_member_killed_in_transit_is_not_resurrected(self):
        group_id, bodies = self._group(
            cell=(505, 705), tick=0, activity=SOLO_ACTIVITY, members=1
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=60)
        self.assertIsNotNone(decision.edge)
        commit_group_decision(self.wilderness, decision)
        state = read_monster_activity(self.wilderness)
        journey = state.journeys[state.groups[group_id].journey_id]
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        body.traits.hp.current = 0
        activity_owner.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        body.attributes.reset_cache()
        self.assertEqual(body.traits.hp.current, 0)
        self.assertNotIn(body, self.wilderness.db.itemcoordinates)
        timeline = regional_population.read_population_timeline(self.wilderness)
        arrivals = [
            transition
            for transition in timeline.transitions
            if transition.individual_id == int(body.pk)
            and transition.source_id.startswith("arrival:")
        ]
        self.assertTrue(arrivals)
        self.assertFalse(arrivals[-1].after.alive)
        self.assertIsNone(read_monster_activity(self.wilderness).groups[group_id].journey_id)

    def test_stationary_group_never_moves_or_restores_identity(self):
        group_id, bodies = self._group(
            activity=STATIONARY_ACTIVITY, owner_kind="quest", owner_key="t_quest"
        )
        before = read_monster_activity(self.wilderness).groups[group_id]
        settle_population_lifecycle(0, 500)
        after = read_monster_activity(self.wilderness).groups[group_id]
        self.assertEqual(after.position, before.position)
        self.assertEqual(after.member_ids, before.member_ids)
        self.assertEqual(after.home_owner, before.home_owner)
        self.assertIsNone(after.journey_id)
        self.assertGreater(after.sequence, before.sequence)

    def test_outside_bounds_member_returns_or_waits(self):
        outside = (499, 700)
        group_id, _bodies = self._group(cell=outside, tick=0, members=1, activity=SOLO_ACTIVITY)
        decision = plan_group_decision(self.wilderness, group_id, tick=60)
        self.assertIsNotNone(decision.edge)
        self.assertEqual(decision.edge.destination.kind, "wilderness")
        self.assertIn(
            decision.edge.destination.x,
            range(500, 520),
            "a returning member must step directly back inside the area",
        )

        self._seal_exits(outside, keep=None)
        waiting = plan_group_decision(self.wilderness, group_id, tick=60)
        self.assertIsNone(waiting.edge)
        self.assertEqual(
            waiting.reason, monster_activity.STAY_OUTSIDE_BOUNDS_WAITING
        )

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_equal_partitions_preserve_resources_and_schedule(self):
        self._register_lifecycle()
        seed = self._departure_seed(
            tick=160,
            activity=SOLO_ACTIVITY,
            cell=(505, 705),
            members=1,
            wilderness_only=True,
        )

        def projection():
            state = read_monster_activity(self.wilderness)
            bodies = tuple(
                ObjectDB.objects.get(pk=member_id)
                for group in state.groups.values()
                for member_id in group.member_ids
            )
            return {
                "groups": sorted(
                    (
                        group.group_id,
                        group.sequence,
                        group.next_decision_tick,
                        None if group.position is None else (
                            group.position.kind,
                            group.position.map,
                            group.position.x,
                            group.position.y,
                            group.position.id,
                        ),
                    )
                    for group in state.groups.values()
                ),
                "reserves": sorted(
                    read_optional_fatigue_state(body).reserve_units
                    for body in bodies
                ),
                "gauges": sorted(body.traits.hp.current for body in bodies),
                "cursors": sorted(
                    member.settled_through_tick
                    for group in state.groups.values()
                    for member in group.member_time.values()
                ),
            }

        def run(parts: tuple[int, ...]):
            self._reset_activity(tick=100)
            self._group(
                cell=(505, 705),
                seed=seed,
                tick=100,
                activity=SOLO_ACTIVITY,
                members=1,
            )
            self._group(
                cell=(515, 715), tick=100, activity=GROUP_ACTIVITY
            )
            tick = 100
            for seconds in parts:
                settle_population_lifecycle(tick, tick + seconds)
                tick += seconds
            return projection()

        single = run((1500,))
        halves = run((700, 800))
        steps = run((61, 1439))
        self.assertEqual(single, halves)
        self.assertEqual(single, steps)
        # A repeated endpoint on the same world never recharges or reschedules.
        settle_population_lifecycle(1600, 1600)
        self.assertEqual(projection(), steps)

    @covers_requirement(
        "world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities"
    )
    def test_forced_sleep_receipt_rolls_back_with_a_late_source_fault(self):
        self._register_lifecycle()
        clock = get_world_clock()
        clock.tick = 100
        group_id, bodies = self._group(
            tick=100, members=1, activity=STATIONARY_ACTIVITY, reserves=(20000,)
        )
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        state = read_monster_activity(self.wilderness)
        groups = dict(state.groups)
        groups[group_id] = replace(groups[group_id], next_decision_tick=90000)
        self.wilderness.db.monster_activity = state_to_dict(
            replace(state, groups=groups)
        )
        before = state_to_dict(read_monster_activity(self.wilderness))
        self.assertIsNone(read_sleep_receipt(body))

        with patch.object(
            activity_owner,
            "retire_room_protection",
            side_effect=RuntimeError("late source fault"),
        ):
            with self.assertRaises(RuntimeError):
                clock.advance(6000, AdvanceSource.SKIP, [])

        self.assertEqual(
            state_to_dict(read_monster_activity(self.wilderness)), before
        )
        self.assertEqual(read_optional_fatigue_state(body).reserve_units, 20000)
        self.assertIsNone(read_sleep_receipt(body))
        self.assertEqual(clock.tick, 100)

        clock.advance(6000, AdvanceSource.SKIP, [])
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        body.attributes.reset_cache()
        receipt = read_sleep_receipt(body)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt.sleeping)
        self.assertEqual(read_optional_fatigue_state(body).reserve_units, 12000)
        self.assertEqual(
            read_monster_activity(self.wilderness)
            .groups[group_id]
            .member_time[str(body.pk)]
            .settled_through_tick,
            6100,
        )

    @covers_requirement(
        "world-clock::advance-settles-exactly-the-entities-its-caller-supplies-never-a-global-registry"
    )
    def test_supplied_activity_member_settles_once_under_its_owner(self):
        self._register_lifecycle()
        clock = get_world_clock()
        clock.tick = 0
        supplied_group, supplied_bodies = self._group(
            cell=(505, 705), tick=0, members=1, reserves=(200000,)
        )
        unobserved_group, unobserved_bodies = self._group(
            cell=(515, 715), tick=0, members=1, reserves=(200000,)
        )
        supplied = ObjectDB.objects.get(pk=supplied_bodies[0].pk)
        supplied.traits.hp.current = 50000
        unobserved = ObjectDB.objects.get(pk=unobserved_bodies[0].pk)
        unobserved.traits.hp.current = 50000

        clock.advance(60, AdvanceSource.SKIP, [supplied], mental=plan_for((supplied,)))

        supplied_state = read_optional_fatigue_state(supplied)
        unobserved_state = read_optional_fatigue_state(unobserved)
        self.assertEqual(supplied_state.reserve_units, unobserved_state.reserve_units)
        self.assertEqual(supplied.traits.hp.current, unobserved.traits.hp.current)
        state = read_monster_activity(self.wilderness)
        self.assertEqual(
            state.groups[supplied_group].member_time[str(supplied.pk)].settled_through_tick,
            state.groups[unobserved_group]
            .member_time[str(unobserved.pk)]
            .settled_through_tick,
        )


class ChronologicalSettlementTests(ActivityFixture):
    """Same-advance ordering and newly due facts."""

    @covers_requirement(
        "regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically"
    )
    def test_same_tick_phases_run_arrivals_births_then_departures(self):
        from world.maps import monster_sites
        from world.maps.population_lifecycle import _settle_population_at

        order: list[str] = []

        def note(name):
            def record(*_args, **_kwargs):
                order.append(name)
                return []

            return record

        with (
            patch.object(
                population_lifecycle, "_zone_keys", return_value=("t_zone",)
            ),
            patch.object(
                regional_population,
                "note_population_boundary",
                return_value=None,
            ),
            patch.object(
                activity_owner,
                "settle_monster_activity_at",
                side_effect=note("arrival"),
            ),
            patch.object(
                monster_sites, "settle_monster_sites_at", side_effect=note("site")
            ),
            patch.object(
                regional_population,
                "settle_recovery_due",
                side_effect=note("regional"),
            ),
            patch.object(
                activity_owner,
                "settle_group_decisions_at",
                side_effect=note("departure"),
            ),
        ):
            _settle_population_at(self.wilderness, 100)
        # A zero-duration departure is re-settled at the same tick, which is
        # the only repeated phase; the relative order is the contract.
        self.assertEqual(order[:4], ["arrival", "site", "regional", "departure"])

    def test_newly_created_group_is_due_within_one_advance(self):
        self._register_lifecycle()
        self._reset_activity(tick=100)
        group_id, _bodies = self._group(
            cell=(505, 705), tick=100, activity=SOLO_ACTIVITY, members=1
        )
        start = self._due(group_id)
        settle_population_lifecycle(100, start + 1)
        group = read_monster_activity(self.wilderness).groups[group_id]
        self.assertGreaterEqual(group.sequence, 1)
        self.assertGreater(group.next_decision_tick, start)

    @covers_requirement(
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence"
    )
    def test_advance_processes_decision_arrival_then_next_decision(self):
        self._register_lifecycle()
        seed = self._departure_seed(
            tick=60,
            activity=SOLO_ACTIVITY,
            cell=(505, 705),
            members=1,
            wilderness_only=True,
        )
        self._reset_activity(tick=0)
        group_id, _bodies = self._group(
            cell=(505, 705), seed=seed, tick=0, activity=SOLO_ACTIVITY, members=1
        )
        self.assertIsNotNone(
            plan_group_decision(self.wilderness, group_id, tick=60).edge
        )
        decisions: list[int] = []
        arrivals: list[int] = []
        real_commit = activity_owner.commit_group_decision
        real_arrival = activity_owner.settle_monster_activity_at

        def commit_spy(wilderness, plan):
            decisions.append(plan.tick)
            return real_commit(wilderness, plan)

        def arrival_spy(wilderness, tick):
            events = real_arrival(wilderness, tick)
            if events:
                arrivals.append(tick)
            return events

        with (
            patch.object(
                activity_owner, "commit_group_decision", side_effect=commit_spy
            ),
            patch.object(
                activity_owner,
                "settle_monster_activity_at",
                side_effect=arrival_spy,
            ),
        ):
            settle_population_lifecycle(0, 3000)
        self.assertTrue(decisions)
        self.assertTrue(arrivals)
        self.assertEqual(decisions[0], 60)
        self.assertLess(decisions[0], arrivals[0])
        self.assertGreater(len(decisions), 1, "the arrived group decides again")
        self.assertGreater(decisions[1], arrivals[0])

    @covers_requirement(
        "wilderness-monster-population::runtime-population-uses-authored-regions-without-implicit-fallback",
        "monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence",
    )
    def test_unobserved_wandering_waits_for_a_live_encounter_then_reloads(self):
        group_id, bodies = self._group(
            cell=(505, 705), tick=0, activity=SOLO_ACTIVITY, members=1
        )
        decision = plan_group_decision(self.wilderness, group_id, tick=60)
        self.assertIsNotNone(decision.edge)
        rooms_before = dict(self.wilderness.db.rooms)
        commit_group_decision(self.wilderness, decision)
        state = read_monster_activity(self.wilderness)
        journey = state.journeys[state.groups[group_id].journey_id]
        destination = journey.destination
        cell = (destination.x, destination.y)
        # The destination is a live encounter at the arrival tick: the same
        # living journey waits without becoming present and without repricing.
        record_population_protection(
            self.wilderness,
            engagement_id="test:live",
            cell=cell,
            start_tick=0,
            end_tick=None,
        )
        deferred = activity_owner.settle_monster_activity_at(
            self.wilderness, journey.arrival_tick
        )
        self.assertEqual([event.kind for event in deferred], ["monster_arrival_deferred"])
        body = ObjectDB.objects.get(pk=bodies[0].pk)
        # Transit is present at neither endpoint.
        self.assertNotIn(body, self.wilderness.db.itemcoordinates)
        self.assertIsNone(body.location)
        self.wilderness.attributes.reset_cache()
        reloaded = read_monster_activity(self.wilderness)
        retry = reloaded.journeys[journey.journey_id].retry_tick
        self.assertIsNotNone(retry)
        self.assertEqual(reloaded.journeys[journey.journey_id].member_ids, (body.pk,))

        record_population_protection(
            self.wilderness,
            engagement_id="test:live",
            cell=cell,
            start_tick=0,
            end_tick=retry - 1,
        )
        arrived = activity_owner.settle_monster_activity_at(self.wilderness, retry)
        self.assertEqual([event.kind for event in arrived], ["monster_arrived"])
        self.assertEqual(self.wilderness.db.itemcoordinates[body], cell)
        self.assertEqual(dict(self.wilderness.db.rooms), rooms_before)
        self.assertIsNone(read_monster_activity(self.wilderness).groups[group_id].journey_id)

    def test_a_birth_and_departure_in_one_advance_roll_back_completely(self):
        self._register_lifecycle()
        clock = get_world_clock()
        clock.tick = 100
        created: dict = {}

        def birth_then_sites(tick):
            if not created:
                group_id, bodies = self._group(
                    cell=(505, 705),
                    tick=100,
                    activity=SOLO_ACTIVITY,
                    members=1,
                )
                created.update(group=group_id, body=int(bodies[0].pk))
            return []

        with (
            patch.object(
                monster_sites,
                "settle_monster_sites_at",
                side_effect=birth_then_sites,
            ),
            patch.object(
                activity_owner,
                "retire_room_protection",
                side_effect=RuntimeError("late source fault"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                clock.advance(2000, AdvanceSource.SKIP, [])

        # The rolled-back birth row and its group are gone, and the owner
        # record is the pre-advance one.
        self.assertFalse(
            ObjectDB.objects.filter(pk=created["body"]).exists()
        )
        self.assertNotIn(
            created["group"], read_monster_activity(self.wilderness).groups
        )
        self.assertEqual(clock.tick, 100)

        # A deterministic retry creates the same identity and lets it move.
        created.clear()
        with patch.object(
            monster_sites,
            "settle_monster_sites_at",
            side_effect=birth_then_sites,
        ):
            clock.advance(2000, AdvanceSource.SKIP, [])
        group = read_monster_activity(self.wilderness).groups[created["group"]]
        self.assertGreaterEqual(group.sequence, 1)
        self.assertTrue(
            ObjectDB.objects.filter(pk=created["body"]).exists()
        )

    def test_zero_duration_departure_arrives_at_the_same_tick(self):
        self._register_lifecycle()
        self._reset_activity(tick=60)
        group_id, _bodies = self._group(
            cell=(505, 705), tick=0, activity=SOLO_ACTIVITY, members=1
        )
        from world.rules import travel_cost

        with patch.object(
            travel_cost, "flight_waives_wilderness_charge", return_value=True
        ):
            settle_population_lifecycle(60, 60)
        state = read_monster_activity(self.wilderness)
        group = state.groups[group_id]
        self.assertIsNone(group.journey_id)
        self.assertIsNotNone(group.position)
        self.assertNotEqual(group.position, LocationRef.wilderness(WILDERNESS_NAME, 505, 705))
        self.assertGreater(group.next_decision_tick, 60)
        self.assertEqual(state.journeys, {})
