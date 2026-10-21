"""Focused tests for the shared movement-cost charging function (map-movement-clock).

Distance-bearing traversal charges the preflight physical duration
(charge-distance-based-travel); explicit non-distance connectors keep their
authored ``CLOCK_YAML`` ``command_defaults`` duration.
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
    distance_traversal_cost,
    member_speed_m_per_hour,
    party_speed_m_per_hour,
    traversal_seconds,
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
        move_call = clock.return_value.advance.call_args_list[0]
        wild_call = clock.return_value.advance.call_args_list[1]
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
                clock.return_value.advance.assert_called_once()
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
        from fractions import Fraction

        from world.rules import travel_cost

        member = create_object(NPC, key="slow member")
        real_scale = travel_cost._fatigue_scale

        def scale(entity):
            if entity is member:
                # 4/5 of 1.25 m/s = 1 m/s exactly.
                return Fraction(4, 5)
            return real_scale(entity)

        with patch.object(travel_cost, "_fatigue_scale", scale):
            cost = distance_traversal_cost(100, "settlement", [self.char1, member])
        self.assertEqual(cost.seconds, 100)
        # Remote members are excluded from the party passed to the calculation.
        self.assertEqual(
            distance_traversal_cost(100, "settlement", [self.char1]).seconds, 80
        )

    @covers_requirement("movement-cost-charging::distance-bearing-traversal-uses-authored-physical-geometry")
    def test_two_sub_second_legs_commit_one_second(self):
        from fractions import Fraction

        # 0.5 m at 1.25 m/s = 0.4 s per leg; per-leg rounding would charge 2 s.
        self.assertEqual(traversal_seconds([0.5, 0.5], Fraction(4500)), 1)

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
        # ordinary charge, and 1200 km is only arithmetic (never one advance).
        self.assertEqual(distance_traversal_cost(27000, "road", self.party).seconds, 21600)
        self.assertEqual(distance_traversal_cost(31500, "road", self.party).seconds, 25200)
        hours = distance_traversal_cost(1_200_000, "road", self.party).seconds / 3600
        self.assertAlmostEqual(hours, 266.67, delta=0.01)
        self.assertAlmostEqual(hours / 6, 44.44, delta=0.01)

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
                travel_cost.ANCHOR_PLACEMENT_REGISTRY,
                {"t_gate_anchor": AnchorPlacement("t_gate_anchor", "t_gate_map", (0, 0))},
            ),
            patch.dict(
                wilderness_entry_module.WILDERNESS_ENTRY_REGISTRY,
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

    @covers_requirement("movement-cost-charging::physical-gate-approaches-are-charged-exactly-once")
    def test_shipped_gate_segments_pin_their_absolute_meter_endpoints(self):
        from math import hypot

        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_destination import gate_approach_distance_m

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        # 南門: gate local (3050,150) -> absolute (604550,1002300); approach
        # cell (60,97) center (605000,975000): hypot(450, 27300).
        south = gate_approach_distance_m(entry, entry.gate_for("n"))
        self.assertAlmostEqual(south, hypot(450, 27300), places=6)
        # 東門: gate local (6500,3010) -> absolute (608000,1005160); approach
        # cell (63,100) center (635000,1005000): hypot(27000, 160).
        east = gate_approach_distance_m(entry, entry.gate_for("w"))
        self.assertAlmostEqual(east, hypot(27000, 160), places=6)
        # One segment, charged in either direction from the same authored
        # geometry at the settlement calibration.
        self.assertEqual(distance_traversal_cost(south, "settlement", [self.char1]).seconds, 21843)
        self.assertEqual(distance_traversal_cost(east, "settlement", [self.char1]).seconds, 21601)
