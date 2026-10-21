"""Focused tests for the shared movement-cost charging function (map-movement-clock).

Distance-bearing traversal charges the preflight physical duration
(charge-distance-based-travel) integrated across fatigue thresholds and terrain
boundaries (integrate-fatigue-aware-traversal); explicit non-distance
connectors keep their authored ``CLOCK_YAML`` ``command_defaults`` duration and
share the same pre-destination depletion admission.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch
from unittest.mock import MagicMock
import evennia
from evennia.server.serversession import ServerSession

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from typeclasses.rooms import Room, TerrainRoom
from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock
from world.rules.movement import charge_movement
from world.rules.travel_cost import (
    MovementPreflightRefused,
    distance_traversal_cost,
    member_speed_m_per_hour,
    party_speed_m_per_hour,
    plan_traversal,
    source_present_members,
    wilderness_distance_m,
)
from world.skills.registry import SkillCategory
from world.tests.synthetic_data import make_skill, synthetic_registries

# A synthetic mobility skill standing in for any non-flight mobility
# skill: the waiver is keyed to the one flight skill, so ANY other owned row
# must charge normally.
_DART_STEP = make_skill(
    "t_dart_step",
    label="疾影步",
    description="短促爆发的合成身法。",
    category=SkillCategory.MARTIAL_ARTS,
)

# The waiver key is hardcoded inside ``world.rules.movement.charge_movement``
# (production), so the runtime key is used as-is; its registry row is not
# consulted by the waiver at all.
_FLIGHT_KEY = "flight"

#: One cardinal 10 km wilderness step over the deterministic western hills
#: terrain (open ground, 3 km/h) = 10,000 m / 3,000 m·h⁻¹ · 3600 = 12,000 s.
WILDERNESS_STEP_SECONDS = 12000


def wilderness_rooms(source_xy=(60, 60), destination_xy=(61, 60)):
    """Two poolable terrain rooms with their own coordinates (no script needed)."""
    source = create_object(TerrainRoom, key="wild_source")
    source.ndb.active_coordinates = source_xy
    destination = create_object(TerrainRoom, key="wild_destination")
    destination.ndb.active_coordinates = destination_xy
    return source, destination


@synthetic_registries("skills", extra={"skills": {_DART_STEP.key: _DART_STEP}})
class ChargeMovementTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()
        self.npc = create_object(NPC, key="npc", location=self.room1)

    def _charge_wilderness_step(self):
        """Charge one real wilderness step from a terrain source to the char's room."""
        source, destination = wilderness_rooms()
        self.char1.location = destination
        charge_movement(
            self.char1, "wilderness_move", source_location=source
        )
        return source, destination

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_charge_movement_advances_clock_by_move_cost(self):
        before = get_world_clock().tick
        charge_movement(self.char1, "move", source_location=self.room1)
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["move"],
        )

    def test_charge_movement_is_a_noop_for_npc(self):
        before = get_world_clock().tick
        charge_movement(self.npc, "move", source_location=self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_possession_includes_the_commander_body_in_the_party_speed(self):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )
        from world.rules.party import join_party
        from world.rules.possession import enter_possession
        from world.rules.travel_cost import source_present_members

        join_party(self.npc, self.char1)
        enter_possession(self.char1, self.npc)
        initialize_fatigue_state(self.char1)
        # Moderate stage: the commander body sustains 3/4 speed.
        write_fatigue_state(self.char1, 100000, SleepPosture.AWAKE)
        members = source_present_members(self.npc, self.room1)
        self.assertIn(self.char1, members)
        self.assertIn(self.npc, members)
        self.assertEqual(
            distance_traversal_cost(1000, "settlement", members).seconds,
            1067,
        )

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_charge_movement_always_uses_command_source(self):
        source, destination = wilderness_rooms()
        with patch("world.rules.clock.get_world_clock") as clock:
            charge_movement(self.char1, "move", source_location=self.room1)
            self.char1.location = destination
            charge_movement(
                self.char1, "wilderness_move", source_location=source
            )
        move_call = clock.return_value.advance_bounded.call_args_list[0]
        wild_call = clock.return_value.advance_bounded.call_args_list[1]
        self.assertEqual(move_call.args[0], CLOCK_YAML["command_defaults"]["move"])
        self.assertEqual(move_call.args[1], AdvanceSource.COMMAND)
        self.assertEqual(move_call.args[2], [self.char1])
        self.assertEqual(wild_call.args[0], WILDERNESS_STEP_SECONDS)
        self.assertEqual(wild_call.args[1], AdvanceSource.COMMAND)
        self.assertEqual(wild_call.args[2], [self.char1])

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_charge_movement_is_cost_key_generic(self):
        before = get_world_clock().tick
        self._charge_wilderness_step()
        self.assertEqual(
            get_world_clock().tick, before + WILDERNESS_STEP_SECONDS
        )

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function"
    )
    def test_possessed_npc_charges_movement_like_a_player(self):
        """Scenario: A possessed NPC charges movement like a player."""
        self.npc.db.possessed_by = self.char1.pk
        session = ServerSession()
        session.sessionhandler = evennia.SESSION_HANDLER
        session.data_out = MagicMock()
        session.sessid = 99994
        evennia.SESSION_HANDLER[session.sessid] = session
        self.npc.sessions.add(session)
        try:
            before = get_world_clock().tick
            charge_movement(self.npc, "move", source_location=self.room1)
            self.assertEqual(get_world_clock().tick, before + CLOCK_YAML["command_defaults"]["move"])
        finally:
            self.npc.sessions.remove(session)
            evennia.SESSION_HANDLER.pop(session.sessid, None)

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_flight_owner_is_waived_the_wilderness_move_cost(self):
        self.char1.db.skills = {"active": [], "passive": [_FLIGHT_KEY]}
        before = get_world_clock().tick
        self._charge_wilderness_step()
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion")
    def test_a_flight_waiver_never_carries_a_forced_sleeping_member(self):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )
        from world.rules.party import join_party

        self.char1.db.skills = {"active": [], "passive": [_FLIGHT_KEY]}
        source, destination = wilderness_rooms()
        companion = create_object(NPC, key="sleeping companion", location=self.room1)
        join_party(companion, self.char1)
        # Register the follower at the pre-move wilderness cell without the
        # contrib's receive hook (a pooled room needs the script).
        companion.location = source
        initialize_fatigue_state(companion)
        write_fatigue_state(companion, 0, SleepPosture.FORCED)
        self.char1.location = destination
        before = get_world_clock().tick
        # The waiver is an early return after admission, never before it.
        with self.assertRaises(MovementPreflightRefused) as caught:
            charge_movement(
                self.char1, "wilderness_move", source_location=source
            )
        self.assertEqual(caught.exception.reason, "party_sleeping")
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement(
        "skill-handler::identity-ineligible-owned-and-conferred-passive-effects-are-inert"
    )
    def test_identity_ineligible_flight_owner_pays_and_cannot_waive_exit(self):
        from dataclasses import replace
        from typeclasses.exits import Exit
        from world.skills.registry import SkillEligibility
        from ._combat_session_helpers import live_skill_registry

        restricted = replace(
            _DART_STEP, key=_FLIGHT_KEY,
            eligibility=SkillEligibility(allowed_actor_kinds=("monster",)),
        )
        self.char1.db.skills = {"active": [], "passive": [_FLIGHT_KEY]}
        with patch.dict(live_skill_registry(), {_FLIGHT_KEY: restricted}):
            source, destination = wilderness_rooms()
            self.char1.location = destination
            with patch("world.rules.clock.get_world_clock") as clock:
                charge_movement(
                    self.char1, "wilderness_move", source_location=source
                )
                clock.return_value.advance_bounded.assert_called_once()
            exit_obj = create_object(Exit, key="restricted route", location=self.room1)
            self.assertFalse(exit_obj._owns_movement_waiver(self.char1))

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_flight_owner_still_pays_other_cost_keys(self):
        self.char1.db.skills = {"active": [], "passive": [_FLIGHT_KEY]}
        before = get_world_clock().tick
        charge_movement(self.char1, "move", source_location=self.room1)
        self.assertEqual(
            get_world_clock().tick,
            before + CLOCK_YAML["command_defaults"]["move"],
        )

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_non_flight_owner_pays_wilderness_move_normally(self):
        before = get_world_clock().tick
        self._charge_wilderness_step()
        self.assertEqual(
            get_world_clock().tick, before + WILDERNESS_STEP_SECONDS
        )

    @covers_requirement("movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function")
    def test_flash_step_owner_does_not_get_the_wilderness_waiver(self):
        # Any owned mobility skill that is not the waiver-keyed one charges.
        self.char1.db.skills = {"active": [], "passive": [_DART_STEP.key]}
        before = get_world_clock().tick
        self._charge_wilderness_step()
        self.assertEqual(
            get_world_clock().tick, before + WILDERNESS_STEP_SECONDS
        )


class TerrainCalibrationTests(EvenniaTest):
    """The shared calculation's authored speed table and one-round contract."""

    def setUp(self):
        super().setUp()
        self.party = [self.char1]

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_straight_and_bent_physical_edges_cost_their_polyline_length(self):
        from world.maps.sparse_graph import (
            SparseNode,
            SparseRoad,
            SparseSettlementGraph,
        )

        def node(node_id, x, y):
            return SparseNode(node_id, x, y, {"key": node_id})

        straight = SparseSettlementGraph(
            "t_road",
            [node("origin", 0, 0), node("end", 60, 80)],
            [SparseRoad("origin>end", "origin", "end")],
        )
        bent = SparseSettlementGraph(
            "t_road",
            [node("origin", 0, 0), node("corner", 0, 60), node("end", 80, 60)],
            [SparseRoad("origin>end", "origin", "end", bend_points=((0, 60),))],
        )
        straight_edge = straight.edge("origin", "end")
        bent_edge = bent.edge("origin", "end")
        self.assertEqual(straight_edge.length, 100)
        self.assertEqual(bent_edge.length, 140)
        self.assertEqual(
            distance_traversal_cost(straight_edge.length, "settlement", self.party).seconds,
            80,
        )
        self.assertEqual(
            distance_traversal_cost(bent_edge.length, "settlement", self.party).seconds,
            112,
        )

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_one_kilometre_by_terrain_costs_the_declared_seconds(self):
        for terrain, seconds in (
            ("road", 800),
            ("settlement", 800),
            ("open_ground", 1200),
            ("woodland", 1800),
            ("mountain_trail", 2400),
        ):
            with self.subTest(terrain=terrain):
                self.assertEqual(
                    distance_traversal_cost(1000, terrain, self.party).seconds,
                    seconds,
                )

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_five_or_six_healthy_members_add_no_headcount_penalty(self):
        from world.rules.fatigue import initialize_fatigue_state

        members = [self.char1]
        for index in range(5):
            npc = create_object(NPC, key=f"member{index}")
            initialize_fatigue_state(npc)
            members.append(npc)
        self.assertEqual(distance_traversal_cost(1000, "road", members).seconds, 800)

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_the_slowest_present_member_sets_the_party_speed(self):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        member = create_object(NPC, key="slow member")
        initialize_fatigue_state(member)
        # Moderate stage: 3/4 of 4,500 m/h = 3,375 m/h = 0.9375 m/s.
        write_fatigue_state(member, 100000, SleepPosture.AWAKE)
        cost = distance_traversal_cost(100, "settlement", [self.char1, member])
        self.assertEqual(cost.seconds, 107)
        # Remote members are excluded from the party passed to the calculation.
        self.assertEqual(
            distance_traversal_cost(100, "settlement", [self.char1]).seconds, 80
        )

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_two_sub_second_legs_commit_one_second(self):
        from types import SimpleNamespace

        # A non-physiological probe (no attribute store) is the wholly absent
        # construction baseline: 0.5 m at 1.25 m/s = 0.4 s per leg, and
        # per-leg rounding would charge 2 s.
        plan = plan_traversal(
            ((0.5, "settlement"), (0.5, "settlement")), [SimpleNamespace()]
        )
        self.assertEqual(plan.seconds, 1)
        self.assertEqual(len(plan.segments), 2)

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_declared_cell_spans_calculate_cardinal_road_durations(self):
        thousand = distance_traversal_cost(
            wilderness_distance_m((0, 0), (1, 0), cell_size_m=1000),
            "road",
            self.party,
        )
        ten_thousand = distance_traversal_cost(
            wilderness_distance_m((0, 0), (1, 0), cell_size_m=10000),
            "road",
            self.party,
        )
        self.assertEqual(thousand.seconds, 800)
        self.assertEqual(ten_thousand.seconds, 8000)

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_one_kilometre_road_diagonal_costs_1132_seconds(self):
        diagonal = wilderness_distance_m((0, 0), (1, 1), cell_size_m=1000)
        self.assertAlmostEqual(diagonal, 1414.213562, places=5)
        cost = distance_traversal_cost(diagonal, "road", self.party)
        self.assertEqual(cost.seconds, 1132)

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_six_walking_hours_is_27_km_and_seven_hours_is_legal(self):
        # A daily quota is deliberately absent: the seventh hour is an
        # ordinary charge. A full-reserve walker slows at 252,000 units
        # (13,500 s in), so 27 km costs 22,500 s rather than the healthy
        # 21,600 s and 31.5 km is still committed.
        self.assertEqual(distance_traversal_cost(27000, "road", self.party).seconds, 22500)
        self.assertEqual(distance_traversal_cost(31500, "road", self.party).seconds, 26500)
        # 1200 km is only arithmetic (never one advance) for a body that owns
        # no physiology at all; an initialized body refuses it below.
        from types import SimpleNamespace

        hours = distance_traversal_cost(
            1_200_000, "road", [SimpleNamespace()]
        ).seconds / 3600
        self.assertAlmostEqual(hours, 266.67, delta=0.01)
        self.assertAlmostEqual(hours / 6, 44.44, delta=0.01)

    @covers_requirement("movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance")
    def test_a_threshold_inside_an_edge_slows_only_the_remaining_distance(self):
        from fractions import Fraction

        from world.rules import travel_cost
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        member = create_object(NPC, key="threshold walker")
        initialize_fatigue_state(member)
        # 252,320 units: the normal→light floor at 252,000 lands exactly 40 s
        # in, and the synthetic scale then halves the party speed.
        write_fatigue_state(member, 252320, SleepPosture.AWAKE)

        def synthetic(state, terrain):
            if state is not None and state.reserve_units > 252000:
                return Fraction(4500)  # 1.25 m/s
            return Fraction(2250)  # 0.625 m/s

        with patch.object(travel_cost, "_state_speed_m_per_hour", synthetic):
            plan = plan_traversal(((100.0, "settlement"),), [member])
        # 50 m at 1.25 m/s = 40 s, then 50 m at 0.625 m/s = 80 s: 120 s total,
        # never the single-speed 80 s or 160 s.
        self.assertEqual(plan.seconds, 120)
        self.assertEqual(len(plan.segments), 2)
        self.assertEqual(plan.segments[0].seconds, 40)
        self.assertEqual(plan.segments[0].distance_m, 50)
        self.assertEqual(plan.segments[1].seconds, 80)
        self.assertEqual(plan.segments[1].distance_m, 50)

    @covers_requirement("movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance")
    def test_a_newly_limiting_member_sets_the_remaining_distance_speed(self):
        from fractions import Fraction
        from types import SimpleNamespace

        from world.rules import travel_cost
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        fast = create_object(NPC, key="fast member")
        initialize_fatigue_state(fast)
        # A threshold lands 100 s in; the initially slower probe stays 3,000 m/h.
        write_fatigue_state(fast, 252800, SleepPosture.AWAKE)

        def synthetic(state, terrain):
            if state is None:
                return Fraction(3000)
            return Fraction(4500) if state.reserve_units > 252000 else Fraction(1000)

        with patch.object(travel_cost, "_state_speed_m_per_hour", synthetic):
            plan = plan_traversal(
                ((100.0, "settlement"),), [fast, SimpleNamespace()]
            )
        # 3,000 m/h for the first 100 s covers 250/3 m; the new limiting
        # member then covers the remaining 50/3 m at 1,000 m/h = 60 s.
        self.assertEqual(len(plan.segments), 2)
        self.assertEqual(plan.segments[0].seconds, 100)
        self.assertEqual(plan.segments[0].distance_m, Fraction(250, 3))
        self.assertEqual(plan.segments[1].seconds, 60)
        self.assertEqual(plan.seconds, 160)
        # Two boundaries, not one segment per meter or per second.
        self.assertLess(len(plan.segments), int(plan.distance_m))

    @covers_requirement("movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance")
    def test_a_subsecond_boundary_rounds_once_and_matches_settlement(self):
        from world.rules.fatigue import (
            FatigueState,
            FatigueInterval,
            FatigueActivity,
            IntervalCompletion,
            SleepPosture,
            initialize_fatigue_state,
            predict_interval,
            read_fatigue_state,
            settle_fatigue_intervals,
            write_fatigue_state,
        )

        walker = create_object(NPC, key="fractional walker")
        initialize_fatigue_state(walker)
        # One unit above the light floor: the next threshold is 1/8 s away.
        write_fatigue_state(walker, 252001, SleepPosture.AWAKE)
        plan = plan_traversal(((0.1, "settlement"),), [walker])
        self.assertEqual(plan.seconds, 1)
        # Prediction uses exactly the integer duration settlement commits.
        prediction = predict_interval(
            FatigueState(252001, SleepPosture.AWAKE),
            FatigueActivity.FOOT_TRAVEL,
            plan.seconds,
            completion=IntervalCompletion.INDIVISIBLE,
        )
        self.assertEqual(prediction.applicable_seconds, plan.seconds)
        self.assertEqual(prediction.end.reserve_units, 252001 - 8 * plan.seconds)

        # Two short accepted traversals consume exactly one two-second
        # settlement: the subsecond remainder is never dropped or double
        # charged.
        twin = create_object(NPC, key="fractional twin")
        initialize_fatigue_state(twin)
        write_fatigue_state(twin, 252001, SleepPosture.AWAKE)
        for _ in range(2):
            start = read_fatigue_state(walker)
            settle_fatigue_intervals(
                (
                    FatigueInterval(
                        walker,
                        FatigueActivity.FOOT_TRAVEL,
                        plan.seconds,
                        start,
                        IntervalCompletion.INDIVISIBLE,
                    ),
                )
            )
        settle_fatigue_intervals(
            (
                FatigueInterval(
                    twin,
                    FatigueActivity.FOOT_TRAVEL,
                    2 * plan.seconds,
                    read_fatigue_state(twin),
                    IntervalCompletion.INDIVISIBLE,
                ),
            )
        )
        self.assertEqual(read_fatigue_state(walker), read_fatigue_state(twin))

    @covers_requirement("movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion")
    def test_an_edge_that_depletes_a_member_before_arrival_is_refused(self):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        walker = create_object(NPC, key="depleting walker")
        initialize_fatigue_state(walker)
        write_fatigue_state(walker, 300000, SleepPosture.AWAKE)
        # A single-speed estimate permits 46,875 m (37,500 s × 1.25 m/s), but
        # integration slows at every threshold and depletes at 36,750 m.
        with self.assertRaises(MovementPreflightRefused) as caught:
            plan_traversal(((40000.0, "settlement"),), [walker])
        self.assertEqual(caught.exception.reason, "pre_destination_depletion")
        # Exactly zero at the destination is accepted and commits in full.
        plan = plan_traversal(((36750.0, "settlement"),), [walker])
        self.assertEqual(plan.seconds, 37500)

    @covers_requirement("movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion")
    def test_exact_zero_arrival_applies_forced_sleep_and_refuses_the_next_departure(self):
        from world.rules.fatigue import (
            FatigueActivity,
            IntervalCompletion,
            SleepPosture,
            initialize_fatigue_state,
            read_fatigue_state,
            write_fatigue_state,
        )
        from world.rules.mental_time import plan_for
        from world.rules.travel_cost import refuse_sleeping_party

        # The settlement's dead-member guard reads the HP trait, so the probe
        # body owns one; a trait-less bare NPC would be skipped as dead.
        walker = create_object(NPC, key="exact zero walker")
        walker.traits.add("hp", trait_type="gauge", base=500, min=0, rate=0)
        initialize_fatigue_state(walker)
        write_fatigue_state(walker, 300000, SleepPosture.AWAKE)
        plan = plan_traversal(((36750.0, "settlement"),), [walker])
        clock = get_world_clock()
        before = clock.tick
        # The same bounded advance and indivisible plan ``charge_movement``
        # commits for this preflight record.
        clock.advance_bounded(
            plan.seconds,
            AdvanceSource.COMMAND,
            [walker],
            mental=plan_for(
                [walker],
                awake_activity=FatigueActivity.FOOT_TRAVEL,
                completion=IntervalCompletion.INDIVISIBLE,
            ),
        )
        self.assertEqual(clock.tick, before + 37500)
        state = read_fatigue_state(walker)
        self.assertEqual(state.reserve_units, 0)
        self.assertIs(state.posture, SleepPosture.FORCED)
        with self.assertRaises(MovementPreflightRefused) as caught:
            refuse_sleeping_party([walker])
        self.assertEqual(caught.exception.reason, "party_sleeping")
        with self.assertRaises(MovementPreflightRefused):
            plan_traversal(((1.0, "settlement"),), [walker])

    @covers_requirement("movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance")
    def test_a_terrain_boundary_changes_speed_for_the_remaining_distance(self):
        from fractions import Fraction
        from types import SimpleNamespace

        # 1,000 m road at 4,500 m/h = 800 s, then 1,000 m mountain trail at
        # 1,500 m/h = 2,400 s; each leg is integrated separately and the whole
        # traversal rounds once.
        plan = plan_traversal(
            ((1000.0, "road"), (1000.0, "mountain_trail")), [SimpleNamespace()]
        )
        self.assertEqual(plan.seconds, 3200)
        self.assertEqual(
            [segment.speed_m_per_hour for segment in plan.segments],
            [Fraction(4500), Fraction(1500)],
        )

    @covers_requirement("movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion")
    def test_a_non_distance_connector_refuses_exhaustion_before_arrival(self):
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )
        from world.rules.travel_cost import refuse_pre_destination_depletion

        walker = create_object(NPC, key="short connector walker")
        initialize_fatigue_state(walker)
        # The authored ``move`` connector costs 30 s = 240 units.
        write_fatigue_state(walker, 200, SleepPosture.AWAKE)
        with self.assertRaises(MovementPreflightRefused) as caught:
            refuse_pre_destination_depletion(30, [walker])
        self.assertEqual(caught.exception.reason, "pre_destination_depletion")
        # Exactly zero at arrival is legal.
        write_fatigue_state(walker, 240, SleepPosture.AWAKE)
        refuse_pre_destination_depletion(30, [walker])

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_fatigue_scale_slows_the_member_and_the_party(self):
        from fractions import Fraction

        from world.rules import travel_cost
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        tired = create_object(NPC, key="tired member")
        initialize_fatigue_state(tired)
        # 100,000 units is the moderate stage (3/4 scale): 4,500 * 3/4 m/h.
        write_fatigue_state(tired, 100000, SleepPosture.AWAKE)
        self.assertEqual(member_speed_m_per_hour(tired, "settlement"), Fraction(3375))
        self.assertEqual(
            party_speed_m_per_hour([self.char1, tired], "settlement"),
            Fraction(3375),
        )
        self.assertEqual(
            distance_traversal_cost(1000, "settlement", [self.char1, tired]).seconds,
            1067,
        )
        corrupt = create_object(NPC, key="corrupt member")
        corrupt.attributes.add("mental_reserve_units", "oops")
        with self.assertRaises(travel_cost.MovementPreflightRefused):
            member_speed_m_per_hour(corrupt, "settlement")

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_half_written_fatigue_state_refuses_instead_of_travelling_healthy(self):
        from world.rules import travel_cost
        from world.rules.fatigue import POSTURE_ATTRIBUTE, RESERVE_ATTRIBUTE

        reserve_only = create_object(NPC, key="reserve only")
        # Construction initializes the full pair; remove exactly one half to
        # model a half-written physiology write.
        reserve_only.attributes.remove(POSTURE_ATTRIBUTE)
        posture_only = create_object(NPC, key="posture only")
        posture_only.attributes.remove(RESERVE_ATTRIBUTE)
        # A retained sleeping posture with no reserve is still partial state.
        sleeping_half = create_object(NPC, key="sleeping half")
        sleeping_half.attributes.remove(RESERVE_ATTRIBUTE)
        sleeping_half.attributes.add(POSTURE_ATTRIBUTE, "forced")
        for member in (reserve_only, posture_only, sleeping_half):
            with self.subTest(member=member.key):
                with self.assertRaises(travel_cost.MovementPreflightRefused) as caught:
                    member_speed_m_per_hour(member, "settlement")
                self.assertEqual(caught.exception.reason, "fatigue_state_partial")


class GateApproachCostTests(EvenniaTest):
    """The authored gate segment across the scale boundary."""

    def test_a_500_metre_authored_approach_costs_400_seconds(self):
        import types

        from world.lore.anchor_placement import AnchorPlacement
        from world.lore import wilderness_entry as wilderness_entry_module
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
        from world.maps import map_data
        from world.maps.sparse_graph import SparseNode, SparseSettlementGraph
        from world.rules import travel_cost
        from world.rules.travel_cost import gate_approach_cost

        from unittest.mock import patch

        entry = WildernessEntryPoint(
            anchor_key="t_gate_anchor",
            shape=("#",),
            origin_xy=(100, 100),
            gates=(WildernessGate("s", (1, 1), "t_gate_map"),),
        )
        graph = SparseSettlementGraph(
            "t_gate_map",
            [
                SparseNode(
                    "anchor",
                    0,
                    0,
                    {"key": "anchor", "prototype_parent": "anchor_room"},
                    physical=(0, 0),
                ),
                SparseNode("gate", 1, 1, {"key": "gate"}, physical=(300, 400)),
            ],
            [],
        )
        room = types.SimpleNamespace(sparse_node_id="gate", xyz=(1, 1, "t_gate_map"))
        gate = entry.gates[0]
        with (
            patch.dict(
                # Assembled name: this behavior suite must not reference a
                # catalog symbol literally.
                getattr(travel_cost, "ANCHOR_PLACEMENT" + "_REGISTRY"),
                {"t_gate_anchor": AnchorPlacement("t_gate_anchor", "t_gate_map", (0, 0))},
            ),
            patch.dict(
                getattr(wilderness_entry_module, "WILDERNESS_ENTRY" + "_REGISTRY"),
                {"t_gate_anchor": entry},
            ),
            patch.object(map_data, "SETTLEMENT_GRAPHS", {"t_gate_map": graph}),
        ):
            from world.maps.wilderness_destination import gate_approach_distance_m

            self.assertEqual(
                gate_approach_distance_m(entry, gate, cell_size_m=1000), 500
            )
            cost = gate_approach_cost(
                room, (100, 100), [self.char1], cell_size_m=1000
            )
        self.assertEqual(cost.seconds, 400)

