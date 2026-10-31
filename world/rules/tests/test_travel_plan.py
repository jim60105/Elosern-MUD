"""``travel.plan`` routing, sequential prediction and read isolation.

The pure planner cases build a synthetic revealed window over a synthetic
terrain map: the canonical passability rule and wilderness terrain join are
patched at their owner modules, so routing really runs through
``wilderness_neighbor``/``wilderness_step_cost`` while no shipped geography is
pinned. The integration cases run the real wilderness contrib, gate entry and
``WildernessReturnExit`` settlement, and compare every prediction with the
committed transactional step.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
import unittest
from unittest import mock

from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.rules import sight
from world.rules import travel_cost
from world.rules.fatigue import (
    FatigueActivity,
    FatigueStage,
    FatigueState,
    IntervalCompletion,
    SleepPosture,
    fatigue_stage,
    get_policy,
    predict_interval,
)
from world.rules.travel_plan import (
    MAX_PLAN_STEPS,
    PLAN_OUTSIDE_WINDOW,
    PLAN_PARTY_CANNOT_TRAVEL,
    PLAN_TOO_LONG,
    PLAN_UNREACHABLE,
    PLAN_UNREVEALED,
    TravelPlanRefused,
    TravelSnapshot,
    TravellerState,
    plan_travel,
)
from world.tests.geography_fixture import publish_shipped_geography
from world.maps.wilderness_destination import normalize_wilderness_direction

publish_shipped_geography()

_SPEEDS = dict(travel_cost.TERRAIN_SPEEDS)
_OPEN = "open_ground"
_ROAD = "road"
_WOODLAND = "woodland"
_MOUNTAIN = "mountain_trail"

# The authored region->terrain join owner, taken from the canonical module
# itself so the test never spells a catalog-data token.
_TERRAIN_JOIN = travel_cost.wilderness_terrain.__name__

_MINUTE = 60

#: Reserves near each awake band's floor, so a single short step crosses it.
_STAGE_RESERVES = {
    FatigueStage.NORMAL: 260000,
    FatigueStage.LIGHT: 146000,
    FatigueStage.MODERATE: 74000,
    FatigueStage.SEVERE: 70000,
}

_STAGE_RANK = {
    FatigueStage.NORMAL: 0,
    FatigueStage.LIGHT: 1,
    FatigueStage.MODERATE: 2,
    FatigueStage.SEVERE: 3,
    FatigueStage.SLEEPING: 4,
    FatigueStage.FORCED_SLEEP: 5,
}


def _traveller(
    reserve: int | None, posture: SleepPosture | None = None
) -> TravellerState:
    if reserve is None:
        return TravellerState(reserve_units=None, posture=None)
    return TravellerState(
        reserve_units=reserve,
        posture=SleepPosture.AWAKE if posture is None else posture,
    )


def _snapshot(
    origin: tuple[int, int],
    revealed,
    travellers=(),
    *,
    tick: int = 0,
    waived: bool = False,
    bounds: tuple[int, int, int, int] | None = None,
) -> TravelSnapshot:
    if bounds is None:
        bounds = (0, 0, 120, 120)
    return TravelSnapshot(
        origin=tuple(origin),
        bounds=bounds,
        revealed=frozenset(tuple(cell) for cell in revealed),
        travellers=tuple(travellers),
        charge_waived=waived,
        tick=tick,
    )


def _box(x0, y0, x1, y1):
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def _night_start_tick() -> int:
    """One tick at the first second of the rulebook's night phase."""

    start_hour = next(
        entry[1] for entry in sight.POLICY.phases if entry[0] == "night"
    )
    return start_hour * 3600


class PlannerTestCase(unittest.TestCase):
    """One synthetic terrain world with the canonical owners patched."""

    def setUp(self):
        super().setUp()
        from world.maps import wilderness_destination

        self.terrain: dict[tuple[int, int], str] = {}
        self.gateways: set[tuple[tuple[int, int], str]] = set()
        patches = (
            mock.patch.object(
                wilderness_destination,
                "is_provider_valid_coordinates",
                side_effect=lambda cell: tuple(cell) in self.terrain,
            ),
            mock.patch.object(
                travel_cost,
                _TERRAIN_JOIN,
                side_effect=self._terrain_for,
            ),
            mock.patch.object(
                wilderness_destination,
                "find_gateway",
                side_effect=lambda cell, direction: (
                    object() if (tuple(cell), direction) in self.gateways else None
                ),
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def _terrain_for(self, source, destination):
        first = self.terrain[(source[0], source[1])]
        second = self.terrain[(destination[0], destination[1])]
        return first if _SPEEDS[first] <= _SPEEDS[second] else second

    def fill(self, cells, terrain=_OPEN):
        for cell in cells:
            self.terrain[tuple(cell)] = terrain

    def step_seconds(self, source, destination, travellers):
        return travel_cost.wilderness_step_cost(
            tuple(source),
            tuple(destination),
            tuple(traveller.detached() for traveller in travellers),
        ).seconds

    def replay(self, origin, route, travellers):
        """Independently re-price one path with the canonical sequential owner."""

        states = list(travellers)
        seconds: list[int] = []
        stages: list[FatigueStage] = []
        previous = tuple(origin)
        for cell in route:
            step = self.step_seconds(previous, cell, states)
            seconds.append(step)
            states = [traveller.advance(step) for traveller in states]
            stages.append(
                max(
                    (state.stage() or FatigueStage.NORMAL for state in states),
                    key=lambda stage: _STAGE_RANK[stage],
                )
            )
            previous = tuple(cell)
        return seconds, stages


class PlannerRoutingTests(PlannerTestCase):
    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_route_goes_around_water_and_prefers_the_lower_canonical_duration(self):
        self.fill(_box(4, 3, 9, 7))
        del self.terrain[(6, 5)]  # impassable river cell on the direct line
        self.fill([(5, 4), (6, 4), (7, 4), (8, 4)], _MOUNTAIN)
        revealed = set(_box(4, 3, 9, 7))
        traveller = _traveller(get_policy().max_units)
        plan = plan_travel(_snapshot((5, 5), revealed, [traveller]), (7, 5), "forced", False)
        # The direct diagonal east is refused (its western orthogonal is the
        # river cell), so the route steps south first and then follows the
        # cheaper open row.
        self.assertEqual(
            [step.cell for step in plan.steps], [(5, 6), (6, 6), (7, 6), (7, 5)]
        )
        self.assertEqual(plan.stop_reason, "destination_reached")
        seconds, stages = self.replay((5, 5), [step.cell for step in plan.steps], [traveller])
        self.assertEqual([step.seconds for step in plan.steps], seconds)
        self.assertEqual([step.fatigue_stage for step in plan.steps], stages)
        self.assertEqual(plan.total_seconds, sum(seconds))

    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_a_diagonal_needs_both_crossed_orthogonals_passable_and_revealed(self):
        self.fill(_box(4, 4, 7, 7))
        traveller = _traveller(get_policy().max_units)
        # (5, 6) is passable but unrevealed: the direct diagonal is refused.
        plan = plan_travel(
            _snapshot((5, 5), [cell for cell in _box(4, 4, 7, 7) if cell != (5, 6)], [traveller]),
            (6, 6),
            "forced",
            False,
        )
        self.assertEqual([step.cell for step in plan.steps], [(6, 5), (6, 6)])
        # The reciprocal unrevealed-to-passable case refuses the same diagonal.
        del self.terrain[(6, 5)]
        plan = plan_travel(
            _snapshot((5, 5), [cell for cell in _box(4, 4, 7, 7) if cell != (6, 5)], [traveller]),
            (6, 6),
            "forced",
            False,
        )
        self.assertEqual([step.cell for step in plan.steps], [(5, 6), (6, 6)])
        # With both orthogonals open and revealed, the cheaper diagonal wins.
        self.fill([(6, 5)], _OPEN)
        plan = plan_travel(
            _snapshot((5, 5), _box(4, 4, 7, 7), [traveller]),
            (6, 6),
            "forced",
            False,
        )
        self.assertEqual([step.cell for step in plan.steps], [(6, 6)])

    @covers_requirement(
        "wilderness-gateway::wildernessreturnexit-routes-every-registered-approach-cell-and-direction-pair-back-to-the-grid"
    )
    def test_a_registered_gateway_direction_is_never_an_ordinary_route(self):
        self.fill([(5, 5), (6, 5)])
        snapshot = _snapshot((5, 5), [(5, 5), (6, 5)], [_traveller(360000)])
        self.gateways.add(((5, 5), "e"))
        with self.assertRaises(TravelPlanRefused) as caught:
            plan_travel(snapshot, (6, 5), "forced", False)
        self.assertEqual(caught.exception.code, PLAN_UNREACHABLE)
        self.gateways.clear()
        plan = plan_travel(snapshot, (6, 5), "forced", False)
        self.assertEqual([step.cell for step in plan.steps], [(6, 5)])

    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_each_domain_error_keeps_its_stable_code(self):
        self.fill(_box(0, 0, 61, 2))
        traveller = [_traveller(360000)]
        cases = {
            PLAN_OUTSIDE_WINDOW: (
                _snapshot(
                    (5, 5), _box(0, 5, 10, 10), traveller, bounds=(0, 5, 10, 10)
                ),
                (11, 5),
            ),
            PLAN_UNREVEALED: (_snapshot((5, 5), [(5, 5)], traveller), (6, 5)),
            PLAN_TOO_LONG: (_snapshot((0, 0), _box(0, 0, 61, 0), traveller), (61, 0)),
        }
        for code, (snapshot, destination) in cases.items():
            with self.subTest(code=code):
                with self.assertRaises(TravelPlanRefused) as caught:
                    plan_travel(snapshot, destination, "forced", False)
                self.assertEqual(caught.exception.code, code)
        # Connectivity is searched before the step bound: the corridor is
        # reachable, so a >60-step route is too_long, never unreachable.
        self.assertGreater(61, MAX_PLAN_STEPS)
        # A revealed corridor whose only entrance is impassable is unreachable.
        del self.terrain[(1, 0)]
        with self.assertRaises(TravelPlanRefused) as caught:
            plan_travel(
                _snapshot((0, 0), _box(0, 0, 5, 0), traveller), (5, 0), "forced", False
            )
        self.assertEqual(caught.exception.code, PLAN_UNREACHABLE)

    @covers_requirement(
        "movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion"
    )
    def test_same_cell_destination_is_an_empty_arrival_but_sleepers_refuse(self):
        self.fill(_box(4, 4, 6, 6))
        snapshot = _snapshot((5, 5), _box(4, 4, 6, 6), [_traveller(360000)])
        plan = plan_travel(snapshot, (5, 5), "cautious", True)
        self.assertEqual(plan.steps, ())
        self.assertEqual(plan.total_seconds, 0)
        self.assertIsNone(plan.nightfall_index)
        self.assertIsNone(plan.stop_index)
        self.assertEqual(plan.stop_reason, "destination_reached")
        for posture in (SleepPosture.VOLUNTARY, SleepPosture.FORCED):
            with self.subTest(posture=posture):
                sleeper = _traveller(360000, posture)
                with self.assertRaises(TravelPlanRefused) as caught:
                    plan_travel(
                        _snapshot((5, 5), _box(4, 4, 6, 6), [sleeper]),
                        (5, 5),
                        "forced",
                        False,
                    )
                self.assertEqual(caught.exception.code, PLAN_PARTY_CANNOT_TRAVEL)

    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_an_absent_physiology_traveller_is_admitted_at_base_speed(self):
        self.fill([(5, 5), (6, 5)])
        plan = plan_travel(
            _snapshot((5, 5), [(5, 5), (6, 5)], [_traveller(None)]),
            (6, 5),
            "cautious",
            False,
        )
        self.assertEqual(
            plan.steps[0].seconds,
            self.step_seconds((5, 5), (6, 5), [_traveller(None)]),
        )
        self.assertEqual(plan.steps[0].fatigue_stage, FatigueStage.NORMAL)


class PlannerReplayTests(PlannerTestCase):
    def corridor(self, length=4, terrain=_OPEN):
        cells = [(5 + index, 5) for index in range(length + 1)]
        self.fill(cells, terrain)
        return cells

    @covers_requirement(
        "movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion"
    )
    def test_first_refusal_is_party_cannot_travel_and_a_later_one_keeps_the_prefix(self):
        cells = self.corridor(2)
        with self.assertRaises(TravelPlanRefused) as caught:
            plan_travel(
                _snapshot((5, 5), cells, [_traveller(100)]),
                cells[-1],
                "forced",
                False,
            )
        self.assertEqual(caught.exception.code, PLAN_PARTY_CANNOT_TRAVEL)
        plan = plan_travel(
            _snapshot((5, 5), cells, [_traveller(20000)]),
            cells[-1],
            "forced",
            False,
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.stop_index, 0)
        self.assertEqual(plan.stop_reason, "preflight_refused")
        self.assertEqual(plan.total_seconds, plan.steps[0].seconds)

    @covers_requirement(
        "movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion"
    )
    def test_exact_zero_arrival_is_admitted_and_ends_with_member_asleep(self):
        self.fill([(5, 5), (6, 5)])
        # In the severe band one open step lasts 2,400 s and drains 19,200 units.
        plan = plan_travel(
            _snapshot((5, 5), [(5, 5), (6, 5)], [_traveller(19200)]),
            (6, 5),
            "forced",
            True,
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[-1].fatigue_stage, FatigueStage.FORCED_SLEEP)
        self.assertEqual(plan.stop_index, 0)
        self.assertEqual(plan.stop_reason, "member_asleep")

    @covers_requirement(
        "movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance"
    )
    def test_preview_steps_continue_past_a_voluntary_stop(self):
        cells = self.corridor(4)
        traveller = _traveller(265000)
        plan = plan_travel(
            _snapshot((5, 5), cells, [traveller]), cells[-1], "cautious", False
        )
        self.assertEqual(len(plan.steps), 4)
        self.assertEqual(plan.stop_index, 1)
        self.assertEqual(plan.stop_reason, "pace_threshold")
        self.assertEqual(
            plan.total_seconds,
            sum(step.seconds for step in plan.steps[: plan.stop_index + 1]),
        )
        seconds, stages = self.replay(
            (5, 5), [step.cell for step in plan.steps], [traveller]
        )
        self.assertEqual([step.seconds for step in plan.steps], seconds)
        self.assertEqual([step.fatigue_stage for step in plan.steps], stages)

    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_each_pace_stops_at_the_first_step_at_or_beyond_its_threshold(self):
        cells = self.corridor(3)
        for pace, threshold in (
            ("cautious", FatigueStage.LIGHT),
            ("standard", FatigueStage.MODERATE),
        ):
            for initial in (
                FatigueStage.LIGHT,
                FatigueStage.MODERATE,
                FatigueStage.SEVERE,
            ):
                with self.subTest(pace=pace, initial=initial):
                    traveller = _traveller(_STAGE_RESERVES[initial])
                    plan = plan_travel(
                        _snapshot((5, 5), cells, [traveller]),
                        cells[-1],
                        pace,
                        False,
                    )
                    _, stages = self.replay(
                        (5, 5), [step.cell for step in plan.steps], [traveller]
                    )
                    crossed = [
                        index
                        for index, stage in enumerate(stages)
                        if _STAGE_RANK[stage] >= _STAGE_RANK[threshold]
                    ]
                    if crossed:
                        self.assertEqual(plan.stop_reason, "pace_threshold")
                        self.assertEqual(plan.stop_index, crossed[0])
                    else:
                        self.assertNotEqual(plan.stop_reason, "pace_threshold")
        # Forced has no voluntary threshold: the same advanced states walk on.
        for initial in (
            FatigueStage.LIGHT,
            FatigueStage.MODERATE,
            FatigueStage.SEVERE,
        ):
            with self.subTest(pace="forced", initial=initial):
                plan = plan_travel(
                    _snapshot((5, 5), cells, [_traveller(_STAGE_RESERVES[initial])]),
                    cells[-1],
                    "forced",
                    False,
                )
                self.assertNotEqual(plan.stop_reason, "pace_threshold")
                self.assertEqual(plan.stop_reason, "destination_reached")

    @covers_requirement(
        "movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed"
    )
    def test_heterogeneous_party_pays_the_slowest_member_and_reports_the_worst_stage(self):
        cells = self.corridor(2)
        slow = _traveller(30000)  # severe band: half the base foot speed
        absent = _traveller(None)
        plan = plan_travel(
            _snapshot((5, 5), cells, [absent, slow]), cells[-1], "forced", False
        )
        self.assertEqual(
            plan.steps[0].seconds, self.step_seconds((5, 5), (6, 5), [slow])
        )
        self.assertEqual(plan.steps[0].fatigue_stage, FatigueStage.SEVERE)

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function"
    )
    def test_a_waived_plan_charges_zero_and_keeps_every_reserve_and_the_calendar(self):
        cells = self.corridor(3)
        night_tick = _night_start_tick() - _MINUTE
        plan = plan_travel(
            _snapshot(
                (5, 5), cells, [_traveller(360000)], tick=night_tick, waived=True
            ),
            cells[-1],
            "cautious",
            True,
        )
        self.assertEqual([step.seconds for step in plan.steps], [0, 0, 0])
        self.assertEqual(plan.total_seconds, 0)
        self.assertIsNone(plan.nightfall_index)
        self.assertEqual(
            {step.fatigue_stage for step in plan.steps}, {FatigueStage.NORMAL}
        )
        self.assertEqual(plan.stop_reason, "destination_reached")

    @covers_requirement(
        "movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance"
    )
    def test_nightfall_index_uses_absolute_calendar_boundaries(self):
        cells = self.corridor(2)
        traveller = _traveller(360000)
        just_before = _night_start_tick() - _MINUTE
        plan = plan_travel(
            _snapshot((5, 5), cells, [traveller], tick=just_before),
            cells[-1],
            "forced",
            True,
        )
        self.assertEqual(plan.nightfall_index, 0)
        self.assertEqual(plan.stop_index, 0)
        self.assertEqual(plan.stop_reason, "nightfall")
        # Already night: no new entry, so no night stop.
        inside_night = _night_start_tick() + _MINUTE
        plan = plan_travel(
            _snapshot((5, 5), cells, [traveller], tick=inside_night),
            cells[-1],
            "forced",
            True,
        )
        self.assertIsNone(plan.nightfall_index)
        self.assertEqual(plan.stop_reason, "destination_reached")
        # Without the switch the same night entry never stops the walk.
        plan = plan_travel(
            _snapshot((5, 5), cells, [traveller], tick=just_before),
            cells[-1],
            "forced",
            False,
        )
        self.assertEqual(plan.nightfall_index, 0)
        self.assertEqual(plan.stop_reason, "destination_reached")

    @covers_requirement(
        "movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance"
    )
    def test_frozen_route_choice_is_separate_from_sequential_replay(self):
        # Path A: three road cardinals (frozen 3 x 889 s from a light start).
        # Path B: one road diagonal + one woodland cardinal (frozen 2,932 s),
        # dearer at selection time but still below A's fatigue-aware replay.
        self.fill([(5, 5), (6, 5), (7, 5), (8, 5)], _ROAD)
        self.fill([(6, 6), (7, 6)], _ROAD)
        self.terrain[(7, 6)] = _WOODLAND
        revealed = [(5, 5), (6, 5), (7, 5), (8, 5), (6, 6), (7, 6)]
        traveller = _traveller(_STAGE_RESERVES[FatigueStage.LIGHT])
        plan = plan_travel(
            _snapshot((5, 5), revealed, [traveller]), (8, 5), "forced", False
        )
        self.assertEqual([step.cell for step in plan.steps], [(6, 5), (7, 5), (8, 5)])
        seconds, stages = self.replay(
            (5, 5), [step.cell for step in plan.steps], [traveller]
        )
        self.assertEqual([step.seconds for step in plan.steps], seconds)
        self.assertEqual([step.fatigue_stage for step in plan.steps], stages)
        self.assertEqual(plan.total_seconds, sum(seconds))
        frozen_seconds, _ = self.replay((5, 5), [(6, 6), (7, 6)], [traveller])
        self.assertLess(sum(seconds), sum(frozen_seconds))


# ---------------------------------------------------------------------------
# Committed wilderness settlement equivalence and the snapshot reads.
# ---------------------------------------------------------------------------

def _gate_anchor_entry():
    """The registered entry row behind the production east gate (probed)."""

    import importlib

    registry = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )
    matches = [
        entry
        for entry in registry.values()
        if entry.gate_for("w") is not None and entry.gate_for("n") is not None
    ]
    assert len(matches) == 1, matches
    return matches[0]


_CAPITAL = _gate_anchor_entry()
_EAST_GATE = _CAPITAL.gate_for("w")
EAST_GATE_XYZ = __import__(
    "world.maps.static_references", fromlist=["settlement_node_xyz"]
).settlement_node_xyz(_EAST_GATE.destination)


def _knowledge(visits):
    """A synthetic schema-2 record: ``visits`` maps a wild cell to its sight."""

    from world.maps.wilderness_provider import WILDERNESS_NAME
    from world.rules.map_knowledge import CHUNK_CELLS, SCHEMA_VERSION

    chunks: dict[str, dict[str, dict[str, int]]] = {}
    for (x, y), sight in visits.items():
        chunk = chunks.setdefault(f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}", {})
        chunk[str((y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS))] = {
            "first_seen_tick": 1,
            "last_seen_tick": 1,
            "sight": sight,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "visited": {},
        "wilderness": {WILDERNESS_NAME: chunks},
    }


class WildernessPlanTestCase(EvenniaTest):
    """A real wilderness world with the party standing on the entrance cell."""

    def setUp(self):
        super().setUp()
        from evennia.utils.create import create_object
        from typeclasses.exits import WildernessGateExit
        from typeclasses.rooms import GridRoom, Room, TerrainRoom
        from world.maps.bootstrap import sync_grid, sync_wilderness

        self.room1.key = "Room1"
        self.room1.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.location = self.east_gate
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.origin = self.char1.location.coordinates
        self.pin_knowledge({self.origin: 8})

    def pin_knowledge(self, visits):
        from world.rules.map_knowledge import KNOWLEDGE_ATTR

        self.char1.attributes.add(KNOWLEDGE_ATTR, _knowledge(visits))

    def add_companion(self, reserve, posture=None):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from evennia.utils.create import create_object
        from typeclasses.npcs import NPC
        from world.rules.fatigue import (
            SleepPosture,
            initialize_fatigue_state,
            write_fatigue_state,
        )
        from world.rules.party import join_party
        from world.maps.wilderness_provider import WILDERNESS_NAME

        companion = create_object(NPC, key="同伴")
        companion.race = "human"
        companion.apply_race_baseline()
        # Register the companion through the contrib's own entry so its
        # wilderness itemcoordinates binding exists before the first step.
        self.assertTrue(
            enter_wilderness(
                companion,
                coordinates=self.origin,
                name=WILDERNESS_NAME,
            )
        )
        join_party(companion, self.char1)
        initialize_fatigue_state(companion)
        write_fatigue_state(
            companion,
            reserve,
            SleepPosture.AWAKE if posture is None else posture,
        )
        return companion

    def set_reserve(self, entity, reserve):
        from world.rules.fatigue import (
            initialize_fatigue_state,
            read_optional_fatigue_state,
            write_fatigue_state,
        )

        state = read_optional_fatigue_state(entity)
        if state is None:
            initialize_fatigue_state(entity)
        write_fatigue_state(entity, reserve, SleepPosture.AWAKE)

    def choose_destination(self, snapshot, depth=2):
        """The first revealed, gateway-free cell ``depth`` steps away."""

        from world.maps import wilderness_destination
        from world.maps.wilderness_destination import DIRECTION_DELTAS
        from world.rules.travel_plan import DIRECTION_ORDER

        frontier = [snapshot.origin]
        seen = {snapshot.origin}
        for level in range(depth):
            candidates = []
            for cell in frontier:
                for direction in DIRECTION_ORDER:
                    dx, dy = DIRECTION_DELTAS[direction]
                    if wilderness_destination.find_gateway(cell, direction) is not None:
                        continue
                    target = wilderness_destination.wilderness_neighbor(
                        cell[0], cell[1], direction
                    )
                    if target is None or target in seen or target not in snapshot.revealed:
                        continue
                    if dx and dy and (
                        (cell[0] + dx, cell[1]) not in snapshot.revealed
                        or (cell[0], cell[1] + dy) not in snapshot.revealed
                    ):
                        continue
                    seen.add(target)
                    candidates.append(target)
            if not candidates:
                break
            if level == depth - 1:
                return candidates[0]
            frontier = candidates
        return None

    def execute_steps(self, plan):
        """Commit every admitted step through the real wilderness exits."""

        from world.maps.wilderness_destination import DIRECTION_DELTAS
        from world.rules.clock import get_world_clock

        from world.rules.fatigue import read_optional_fatigue_state
        from world.rules.travel_cost import source_present_members

        deltas = {delta: direction for direction, delta in DIRECTION_DELTAS.items()}
        previous = self.origin
        observed = []
        states = []
        for step in plan.steps:
            direction = deltas[(step.cell[0] - previous[0], step.cell[1] - previous[1])]
            exit_obj = [
                exit_obj
                for exit_obj in self.char1.location.exits
                if normalize_wilderness_direction(exit_obj.key) == direction
            ][0]
            before = get_world_clock().tick
            self.assertTrue(exit_obj.at_traverse(self.char1, self.char1.location))
            observed.append(get_world_clock().tick - before)
            states.append(
                {
                    member.pk: read_optional_fatigue_state(member)
                    for member in source_present_members(
                        self.char1,
                        self.char1.location,
                        self.char1.location.coordinates,
                    )
                }
            )
            previous = step.cell
        return observed, states

    def assert_step_states_match(self, plan, states, snapshot):
        """Every committed after-step state equals its sequential prediction."""

        predicted = list(snapshot.travellers)
        for step, committed in zip(plan.steps, states):
            predicted = [traveller.advance(step.seconds) for traveller in predicted]
            for traveller in predicted:
                state = committed[traveller.member_id]
                self.assertEqual(
                    getattr(state, "reserve_units", None), traveller.reserve_units
                )
                self.assertIs(getattr(state, "posture", None), traveller.posture)


class TravelSnapshotTests(WildernessPlanTestCase):
    @covers_requirement(
        "wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection"
    )
    @covers_requirement(
        "wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection"
    )
    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_the_snapshot_matches_its_canonical_owners_and_writes_nothing(self):
        from world.rules.clock import get_world_clock
        from world.rules.map_knowledge import KNOWLEDGE_ATTR, revealed_in_bounds
        from world.rules.travel_cost import source_present_members
        from world.rules.travel_plan import read_travel_snapshot

        from world.rules.map_knowledge import KNOWLEDGE_ATTR as ATTR

        self.set_reserve(self.char1, 300000)
        knowledge = self.char1.attributes.get(ATTR)
        attribute_count = len(self.char1.attributes.all())
        tick = get_world_clock().tick
        coordinates = self.char1.location.coordinates
        snapshot = read_travel_snapshot(self.char1)
        self.assertEqual(snapshot.origin, coordinates)
        self.assertEqual(
            snapshot.bounds,
            (
                max(0, coordinates[0] - 20),
                max(0, coordinates[1] - 20),
                coordinates[0] + 20,
                coordinates[1] + 20,
            ),
        )
        self.assertEqual(
            snapshot.revealed,
            frozenset(revealed_in_bounds(self.char1, snapshot.bounds)),
        )
        self.assertEqual(
            len(snapshot.travellers),
            len(
                source_present_members(
                    self.char1, self.char1.location, coordinates
                )
            ),
        )
        self.assertFalse(snapshot.charge_waived)
        self.assertEqual(snapshot.tick, tick)
        self.assertEqual(self.char1.attributes.get(ATTR), knowledge)
        self.assertEqual(len(self.char1.attributes.all()), attribute_count)
        self.assertEqual(get_world_clock().tick, tick)
        self.assertEqual(self.char1.location.coordinates, coordinates)

    @covers_requirement(
        "movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion"
    )
    def test_malformed_physiology_is_party_cannot_travel_not_an_internal_error(self):
        from world.rules.fatigue import POSTURE_ATTRIBUTE, RESERVE_ATTRIBUTE
        from world.rules.travel_plan import read_travel_snapshot

        self.char1.attributes.remove(POSTURE_ATTRIBUTE)
        self.char1.attributes.add(RESERVE_ATTRIBUTE, 360000)  # no posture half
        with self.assertRaises(TravelPlanRefused) as caught:
            read_travel_snapshot(self.char1)
        self.assertEqual(caught.exception.code, PLAN_PARTY_CANNOT_TRAVEL)


class CommittedEquivalenceTests(WildernessPlanTestCase):
    @covers_requirement(
        "movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance"
    )
    def test_predicted_prefix_matches_real_transactional_steps(self):
        from world.rules.travel_plan import read_travel_snapshot

        self.set_reserve(self.char1, 145000)  # crosses light -> moderate in-step
        companion = self.add_companion(90000)
        snapshot = read_travel_snapshot(self.char1)
        self.assertEqual(len(snapshot.travellers), 2)
        destination = self.choose_destination(snapshot, depth=2)
        self.assertIsNotNone(destination)
        plan = plan_travel(snapshot, destination, "forced", False)
        self.assertEqual(len(plan.steps), 2)
        observed, states = self.execute_steps(plan)
        self.assertEqual(observed, [step.seconds for step in plan.steps])
        self.assert_step_states_match(plan, states, snapshot)
        self.assertEqual(self.char1.location.coordinates, destination)

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function"
    )
    def test_allowed_flight_has_zero_charge_and_matches_real_steps(self):
        from world.rules.clock import get_world_clock
        from world.rules.travel_plan import read_travel_snapshot

        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        self.set_reserve(self.char1, 145000)
        snapshot = read_travel_snapshot(self.char1)
        self.assertTrue(snapshot.charge_waived)
        destination = self.choose_destination(snapshot, depth=2)
        self.assertIsNotNone(destination)
        plan = plan_travel(snapshot, destination, "forced", True)
        self.assertEqual([step.seconds for step in plan.steps], [0, 0])
        self.assertEqual(plan.total_seconds, 0)
        before = get_world_clock().tick
        observed, states = self.execute_steps(plan)
        self.assertEqual(observed, [0, 0])
        self.assertEqual(get_world_clock().tick, before)
        for step in plan.steps:
            self.assertEqual(
                step.fatigue_stage, FatigueStage.LIGHT
            )  # unchanged 145,000 reserve
        self.assert_step_states_match(plan, states, snapshot)

    def _charge_one_step(self, snapshot, plan):
        from world.rules.clock import get_world_clock
        from world.rules.movement import charge_movement
        from world.rules.travel_cost import preflight_movement_cost, source_present_members

        step = plan.steps[0]
        source = self.char1.location
        with preflight_movement_cost(
            self.char1,
            "wilderness_move",
            source_location=source,
            wilderness_source_coordinates=snapshot.origin,
            wilderness_destination_coordinates=step.cell,
            members=source_present_members(self.char1, source, snapshot.origin),
        ):
            before = get_world_clock().tick
            charge_movement(self.char1, "wilderness_move", source_location=source)
        return get_world_clock().tick - before

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function"
    )
    def test_restricted_flight_and_flash_step_use_foot_cost(self):
        from dataclasses import replace

        from world.rules.tests._combat_session_helpers import live_skill_registry
        from world.rules.travel_plan import read_travel_snapshot
        from world.skills.registry import SkillEligibility
        from world.tests.synthetic_data import make_skill
        from world.skills.registry import SkillCategory

        restricted = replace(
            make_skill(
                "t_travel_only_step",
                label="旅步",
                description="僅供合成測試的身法。",
                category=SkillCategory.MARTIAL_ARTS,
            ),
            key="flight",
            eligibility=SkillEligibility(allowed_actor_kinds=("monster",)),
        )
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        self.set_reserve(self.char1, 145000)
        with mock.patch.dict(live_skill_registry(), {"flight": restricted}):
            snapshot = read_travel_snapshot(self.char1)
            self.assertFalse(snapshot.charge_waived)
            destination = self.choose_destination(snapshot, depth=1)
            plan = plan_travel(snapshot, destination, "forced", False)
            self.assertGreater(plan.steps[0].seconds, 0)
            self.assertEqual(self._charge_one_step(snapshot, plan), plan.steps[0].seconds)
        # The non-waiving movement passive satisfies flight-required admission,
        # never the charge. Its key is resolved from the live registry's closed
        # movement-effect modes instead of being spelled here.
        from typing import get_args

        from world.skills.effects.parser import parse_effect
        from world.skills.effects.passives import MovementEffect

        flash_mode = next(
            mode
            for mode in get_args(MovementEffect.__annotations__["mode"])
            if mode != "flight"
        )
        flash_key = next(
            key
            for key, row in live_skill_registry().items()
            if any(
                getattr(parse_effect(effect), "mode", None) == flash_mode
                for effect in getattr(row, "effects", ())
            )
        )
        self.char1.db.skills = {"active": [], "passive": [flash_key]}
        self.set_reserve(self.char1, 145000)
        snapshot = read_travel_snapshot(self.char1)
        self.assertFalse(snapshot.charge_waived)
        destination = self.choose_destination(snapshot, depth=1)
        plan = plan_travel(snapshot, destination, "forced", False)
        self.assertGreater(plan.steps[0].seconds, 0)
        self.assertEqual(self._charge_one_step(snapshot, plan), plan.steps[0].seconds)

    @covers_requirement(
        "movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function"
    )
    @covers_requirement(
        "movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion"
    )
    def test_flight_does_not_bypass_sleep_or_depletion(self):
        from world.rules.clock import get_world_clock
        from world.rules.fatigue import SleepPosture
        from world.rules.movement import charge_movement
        from world.rules.travel_cost import (
            MovementPreflightRefused,
            preflight_movement_cost,
            source_present_members,
        )
        from world.rules.travel_plan import read_travel_snapshot

        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        self.set_reserve(self.char1, 360000)
        cases = (
            (SleepPosture.VOLUNTARY, 360000),
            (SleepPosture.FORCED, 0),
        )
        for posture, reserve in cases:
            with self.subTest(posture=posture):
                companion = self.add_companion(reserve, posture)
                snapshot = read_travel_snapshot(self.char1)
                destination = self.choose_destination(snapshot, depth=1)
                with self.assertRaises(TravelPlanRefused) as caught:
                    plan_travel(snapshot, destination, "forced", False)
                self.assertEqual(caught.exception.code, PLAN_PARTY_CANNOT_TRAVEL)
                source = self.char1.location
                before = get_world_clock().tick
                with self.assertRaises(MovementPreflightRefused) as refused:
                    with preflight_movement_cost(
                        self.char1,
                        "wilderness_move",
                        source_location=source,
                        wilderness_source_coordinates=snapshot.origin,
                        wilderness_destination_coordinates=destination,
                        members=source_present_members(
                            self.char1, source, snapshot.origin
                        ),
                    ):
                        charge_movement(
                            self.char1, "wilderness_move", source_location=source
                        )
                self.assertEqual(refused.exception.reason, "party_sleeping")
                self.assertEqual(get_world_clock().tick, before)
                companion.delete()
        # An awake but nearly depleted companion refuses the first edge.
        companion = self.add_companion(100)
        snapshot = read_travel_snapshot(self.char1)
        destination = self.choose_destination(snapshot, depth=1)
        with self.assertRaises(TravelPlanRefused) as caught:
            plan_travel(snapshot, destination, "forced", False)
        self.assertEqual(caught.exception.code, PLAN_PARTY_CANNOT_TRAVEL)

    @covers_requirement(
        "movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance"
    )
    def test_initial_pace_state_matches_the_committed_first_step(self):
        from world.rules.fatigue import read_optional_fatigue_state
        from world.rules.travel_plan import read_travel_snapshot

        thresholds = {
            "cautious": FatigueStage.LIGHT,
            "standard": FatigueStage.MODERATE,
            "forced": None,
        }
        for initial in (
            FatigueStage.LIGHT,
            FatigueStage.MODERATE,
            FatigueStage.SEVERE,
        ):
            for pace, threshold in thresholds.items():
                with self.subTest(initial=initial, pace=pace):
                    self.set_reserve(self.char1, _STAGE_RESERVES[initial])
                    snapshot = read_travel_snapshot(self.char1)
                    destination = self.choose_destination(snapshot, depth=1)
                    plan = plan_travel(snapshot, destination, pace, False)
                    committed_seconds = self._charge_one_step(snapshot, plan)
                    state = read_optional_fatigue_state(self.char1)
                    committed = fatigue_stage(state)
                    planner_stops = plan.stop_reason == "pace_threshold"
                    if threshold is None:
                        self.assertFalse(planner_stops)
                        self.assertNotEqual(committed, FatigueStage.NORMAL)
                    else:
                        self.assertEqual(
                            planner_stops,
                            _STAGE_RANK[committed] >= _STAGE_RANK[threshold],
                        )
                        self.assertEqual(plan.stop_index, 0 if planner_stops else None)
                    self.assertEqual(plan.steps[0].seconds, committed_seconds)


class TravelPlanBenchmarkTests(WildernessPlanTestCase):
    @unittest.skipUnless(
        os.environ.get("MUD_TRAVEL_PLAN_BENCHMARK") == "1",
        "timing benchmark: set MUD_TRAVEL_PLAN_BENCHMARK=1",
    )
    @covers_requirement(
        "wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection"
    )
    def test_warmed_plan_with_twenty_thousand_visits_is_within_one_hundred_ms(self):
        import statistics
        import time

        from world.rules.travel_plan import read_travel_snapshot

        self.set_reserve(self.char1, 300000)
        self.pin_knowledge(_synthetic_visits(self.origin, 20_000))
        snapshot = read_travel_snapshot(self.char1)
        destination = self.choose_destination(snapshot, depth=8)
        self.assertIsNotNone(destination)
        plan_travel(snapshot, destination, "standard", True)  # warm caches
        samples = []
        for _ in range(20):
            began = time.perf_counter()
            fresh = read_travel_snapshot(self.char1)
            plan_travel(fresh, destination, "standard", True)
            samples.append((time.perf_counter() - began) * 1000)
        median = statistics.median(samples)
        print(f"travel.plan benchmark: median {median:.1f} ms over 20 samples")
        self.assertLessEqual(median, 100.0)


def _synthetic_visits(start, count):
    """``count`` deterministic visits: a dense block plus a frame-wide scatter."""

    from world.maps import wilderness_provider

    max_x = wilderness_provider.WILDERNESS_MAX_X
    max_y = wilderness_provider.WILDERNESS_MAX_Y
    visits: dict[tuple[int, int], int] = {}
    sx, sy = start
    for dy in range(-30, 31):
        for dx in range(-30, 31):
            if (dx * 7 + dy * 3) % 4 == 0:
                visits[(sx + dx, sy + dy)] = (dx * dx + dy) % 9
    seed = 12345
    while len(visits) < count:
        seed = (seed * 1103515245 + 12345) % (2**31)
        x = seed % (max_x + 1)
        seed = (seed * 1103515245 + 12345) % (2**31)
        y = seed % (max_y + 1)
        visits.setdefault((x, y), seed % 9)
    return visits
