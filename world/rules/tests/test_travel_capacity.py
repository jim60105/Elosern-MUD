"""Read-only travel status: foot capacity and neighbour quotes
(wilderness-travel-leg-ui, task 1.1).

The pure cases use literal expectations derived by hand from the rulebook
(foot travel -8 units per second; awake bands normal >= 252000, light >=
144000, moderate >= 72000, severe >= 1; foot-speed scales 1, 9/10, 3/4, 1/2;
open ground 3000 m/h; a 1000 m step), never by re-running the calculator.
The world cases stand a real party on a real wilderness cell and check the
status object against the committed exploration rows, the disclosure rule,
the flight waiver and the no-write contract.
"""

from __future__ import annotations

import unittest
from unittest import mock

from world.rules import travel_cost
from world.rules.fatigue import SleepPosture
from world.rules.tests.test_travel_plan import WildernessPlanTestCase
from world.rules.travel_capacity import (
    MAX_NEIGHBOUR_QUOTES,
    CapacitySnapshot,
    build_travel_status,
    capacity_by_stage,
    neighbour_quotes,
    pace_state,
)
from world.rules.travel_plan import TravellerState

_OPEN = "open_ground"
#: The canonical edge-terrain join, named through the owner (not a literal).
_TERRAIN_JOIN = travel_cost.wilderness_terrain.__name__
_STEP_M = 1000


def _awake(reserve):
    return TravellerState(reserve_units=reserve, posture=SleepPosture.AWAKE)


def _bare():
    return TravellerState(reserve_units=None, posture=None)


def _capacity(*travellers):
    return capacity_by_stage(
        CapacitySnapshot(travellers=tuple(travellers)), _OPEN, cell_size_m=_STEP_M
    )


def _counts(normal=0, light=0, moderate=0, severe=0):
    return {"normal": normal, "light": light, "moderate": moderate, "severe": severe}


class CapacityByStageTests(unittest.TestCase):
    def test_exact_zero_arrival_is_counted_severe_and_ends(self):
        # 19200 units at the severe half speed: 1000 m at 1500 m/h is 2400 s,
        # which consumes exactly 19200 units. The admitted step arrives at
        # zero (canonical forced sleep), counts once in severe, and ends.
        self.assertEqual(_capacity(_awake(19200)), _counts(severe=1))

    def test_a_step_that_would_deplete_before_arrival_is_refused(self):
        # One unit more: the first 2400 s step leaves 1 unit (still severe and
        # awake); the next one would empty the reserve before arrival.
        self.assertEqual(_capacity(_awake(19201)), _counts(severe=1))
        # A body that cannot even finish the first step has no capacity.
        self.assertEqual(_capacity(_awake(19199)), _counts())

    def test_the_slowest_present_traveller_sets_every_step(self):
        # A fresh body walks 1000 m in 1200 s, but it travels with a severe
        # body at 38400 units: each step takes the slow 2400 s, so the slow
        # body arrives at 19200 (severe) and then exactly at zero. At the
        # fresh body's pace the slow one would have lasted four steps.
        self.assertEqual(_capacity(_awake(360000), _awake(38400)), _counts(severe=2))

    def test_a_band_floor_belongs_to_its_band_and_slows_the_next_step(self):
        # 84800 units at the moderate 3/4 speed: 1000 m at 2250 m/h is 1600 s
        # (12800 units) and lands exactly on the moderate floor 72000, still
        # moderate. The next step starts on the floor, so it already walks at
        # the severe half speed: 2400 s each, 72000 -> 52800 -> 33600 ->
        # 14400, and a fifth step would empty the reserve before arrival.
        self.assertEqual(_capacity(_awake(84800)), _counts(moderate=1, severe=3))

    def test_a_party_already_asleep_has_zero_capacity(self):
        for posture in (SleepPosture.VOLUNTARY, SleepPosture.FORCED):
            with self.subTest(posture=posture):
                asleep = TravellerState(reserve_units=300000, posture=posture)
                self.assertEqual(_capacity(_awake(360000), asleep), _counts())

    def test_a_party_without_physiology_has_no_estimate(self):
        # Nobody ever tires, so no count would be real.
        self.assertIsNone(_capacity(_bare()))
        self.assertIsNone(capacity_by_stage(CapacitySnapshot(travellers=()), _OPEN))
        # An unconstructed companion walks at base speed; the constructed
        # severe body still sets the pace and the end.
        self.assertEqual(_capacity(_bare(), _awake(19200)), _counts(severe=1))

    def test_a_fresh_day_fills_every_bucket_in_order(self):
        counts = _capacity(_awake(360000))
        self.assertTrue(all(counts[bucket] > 0 for bucket in counts), counts)
        # A full reserve lasts 45000 s of foot travel; no step is shorter than
        # the fresh 1200 s, so fewer than 38 steps fit.
        self.assertLess(sum(counts.values()), 38)

    def test_pace_state_reads_the_current_worst_stage(self):
        cases = (
            ((_awake(300000),), {"cautious": False, "standard": False}),
            ((_awake(300000), _awake(200000)), {"cautious": True, "standard": False}),
            ((_awake(100000),), {"cautious": True, "standard": True}),
            ((_bare(),), {"cautious": False, "standard": False}),
        )
        for travellers, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(pace_state(CapacitySnapshot(travellers=travellers)), expected)


class NeighbourQuoteBoundTests(unittest.TestCase):
    def test_quotes_dedupe_and_stop_at_the_wire_bound(self):
        # Disabled and withheld rows quote null without any preflight, so the
        # bound and the dedupe are observable on their own.
        rows = [{"exit_ref": "r0", "destination": None, "enabled": True}]
        rows += [{"exit_ref": "r0", "destination": None, "enabled": True}]
        rows += [
            {"exit_ref": f"r{i}", "destination": f"wild:elosern:{i}:0", "enabled": False}
            for i in range(1, 14)
        ]
        with mock.patch(
            "world.rules.travel_capacity.flight_waives_wilderness_charge", return_value=False
        ):
            quotes = neighbour_quotes(object(), None, (0, 0), (), rows)
        self.assertEqual(len(quotes), MAX_NEIGHBOUR_QUOTES)
        self.assertEqual([q["exit_ref"] for q in quotes], [f"r{i}" for i in range(12)])
        self.assertTrue(all(q["seconds"] is None for q in quotes))


def _stored(entity):
    return {attribute.key: attribute.value for attribute in entity.attributes.all()}


class TravelStatusWorldTests(WildernessPlanTestCase):
    """A real party on a real wilderness cell."""

    def _rows(self):
        from web.webclient.presentation.exploration import _move_rows

        return _move_rows(self.char1)

    def _wild_rows(self, rows):
        return [row for row in rows if (row["destination"] or "").startswith("wild:")]

    def test_status_quotes_the_committed_rows_and_writes_nothing(self):
        from world.rules.clock import get_world_clock
        from world.rules.travel_cost import wilderness_cell_size_m

        self.assertEqual(wilderness_cell_size_m(), 1000)
        self.set_reserve(self.char1, 360000)
        companion = self.add_companion(300000)
        bare = self.add_companion(300000)
        bare.attributes.remove("mental_reserve_units")
        bare.attributes.remove("sleep_posture")
        before = (
            _stored(self.char1), _stored(companion), _stored(bare), get_world_clock().tick,
        )
        rows = self._rows()
        status = build_travel_status(self.char1)
        self.assertEqual(set(status), {"capacity", "neighbours", "at_pace"})
        self.assertEqual(set(status["capacity"]), {"normal", "light", "moderate", "severe"})
        self.assertGreater(sum(status["capacity"].values()), 0)
        self.assertEqual(status["at_pace"], {"cautious": False, "standard": False})
        # One quote per committed row, keyed by that row's opaque reference.
        self.assertLessEqual(len(status["neighbours"]), MAX_NEIGHBOUR_QUOTES)
        self.assertEqual(
            [quote["exit_ref"] for quote in status["neighbours"]],
            [row["exit_ref"] for row in rows][:MAX_NEIGHBOUR_QUOTES],
        )
        for quote in status["neighbours"]:
            self.assertEqual(set(quote), {"exit_ref", "seconds"})
        by_ref = {quote["exit_ref"]: quote["seconds"] for quote in status["neighbours"]}
        wild = [row for row in self._wild_rows(rows) if row["enabled"]]
        self.assertTrue(wild)
        for row in wild:
            # A disclosed orthogonal or diagonal step on fresh legs takes at
            # least the road pace's 800 s per kilometre.
            self.assertGreaterEqual(by_ref[row["exit_ref"]], 800)
        for row in rows:
            if row["destination"] is None or not row["enabled"]:
                self.assertIsNone(by_ref[row["exit_ref"]])
        # Reading twice wrote nothing anywhere: no physiology for the bare
        # body, no reserve change, no clock tick.
        build_travel_status(self.char1)
        after = (
            _stored(self.char1), _stored(companion), _stored(bare), get_world_clock().tick,
        )
        self.assertEqual(after, before)
        self.assertFalse(bare.attributes.has("mental_reserve_units"))

    def test_withheld_destinations_quote_null_whatever_lies_there(self):
        self.set_reserve(self.char1, 360000)
        # Only the party's own cell is known: every wilderness neighbour is
        # withheld, yet its row stays a usable opaque control.
        self.pin_knowledge({self.origin: 0})
        rows = self._rows()
        withheld = [row for row in rows if row["destination"] is None]
        self.assertTrue(withheld)
        self.assertTrue(any(row["enabled"] for row in withheld))
        real = getattr(travel_cost, _TERRAIN_JOIN)

        def quotes(slow):
            def terrain(source, destination):
                if tuple(destination) != tuple(self.origin):
                    return "mountain_trail" if slow else "road"
                return real(source, destination)

            with mock.patch.object(travel_cost, _TERRAIN_JOIN, side_effect=terrain):
                return build_travel_status(self.char1)["neighbours"]

        hidden_slow, hidden_fast = quotes(True), quotes(False)
        self.assertEqual(hidden_slow, hidden_fast)
        refs = {row["exit_ref"] for row in withheld}
        self.assertTrue(all(q["seconds"] is None for q in hidden_slow if q["exit_ref"] in refs))

        # Control: once revealed, the same hidden-terrain difference shows.
        self.pin_knowledge({self.origin: 8})
        disclosed = {row["exit_ref"] for row in self._wild_rows(self._rows()) if row["enabled"]}
        self.assertTrue(disclosed)
        slow = {q["exit_ref"]: q["seconds"] for q in quotes(True)}
        fast = {q["exit_ref"]: q["seconds"] for q in quotes(False)}
        self.assertTrue(all(slow[ref] > fast[ref] for ref in disclosed))

    def test_flight_waives_quotes_but_never_the_foot_capacity(self):
        from world.rules import travel_capacity

        self.set_reserve(self.char1, 360000)
        walking = build_travel_status(self.char1)
        with mock.patch.object(
            travel_capacity, "flight_waives_wilderness_charge", return_value=True
        ):
            flying = build_travel_status(self.char1)
        self.assertEqual(flying["capacity"], walking["capacity"])
        for before, after in zip(walking["neighbours"], flying["neighbours"]):
            self.assertEqual(after["seconds"], None if before["seconds"] is None else 0)

    def test_a_sleeping_companion_zeroes_capacity_and_every_quote(self):
        self.set_reserve(self.char1, 360000)
        self.add_companion(300000, SleepPosture.VOLUNTARY)
        status = build_travel_status(self.char1)
        self.assertEqual(status["capacity"], {"normal": 0, "light": 0, "moderate": 0, "severe": 0})
        self.assertTrue(all(quote["seconds"] is None for quote in status["neighbours"]))
        self.assertEqual(status["at_pace"], {"cautious": True, "standard": True})

    def test_corrupt_companion_physiology_degrades_only_the_capacity(self):
        from web.webclient.presentation.context import PresentationContext
        from web.webclient.presentation.status import status_presenter
        from world.rules.fatigue import FatigueStateError

        self.set_reserve(self.char1, 360000)
        companion = self.add_companion(300000)
        companion.attributes.add("sleep_posture", "dozing")
        with self.assertRaises(FatigueStateError):
            build_travel_status(self.char1)
        with mock.patch("web.webclient.presentation.status.log_warn") as warn:
            payload = status_presenter(PresentationContext(self.char1, 1))
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["travel_capacity"])
        self.assertEqual(warn.call_args.args[0], "status_travel_capacity_unavailable")

    def test_possession_reads_the_controlled_body_cohort(self):
        from web.webclient.presentation.context import PresentationContext
        from web.webclient.presentation.status import status_presenter
        from world.rules.possession import enter_possession

        self.set_reserve(self.char1, 360000)
        companion = self.add_companion(19200)
        enter_possession(self.char1, companion)
        payload = status_presenter(PresentationContext(companion, 1))
        expected = build_travel_status(companion)
        self.assertEqual(payload["travel_capacity"], expected)
        # The controlled companion's own exhausted legs bound the estimate.
        self.assertEqual(sum(expected["capacity"].values()), expected["capacity"]["severe"])
        self.assertLessEqual(expected["capacity"]["severe"], 1)

    def test_outside_exploration_there_is_no_travel_status(self):
        with mock.patch(
            "web.webclient.presentation.affordances.in_exploration_mode", return_value=False
        ):
            self.assertIsNone(build_travel_status(self.char1))
        self.char1.location = self.room1
        self.assertIsNone(build_travel_status(self.char1))
