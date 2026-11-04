"""Commit-qualified travel notices (wilderness-travel-log-ui, task 1.1).

The comparison is exercised on synthetic captures whose expected notices are
known independently; the recorder is exercised against real Django commit and
rollback behaviour; the producer hooks are exercised with patched reads so no
shipped geography is named.
"""

from types import SimpleNamespace
from unittest import mock
import unittest

from django.db import transaction
from django.test import TestCase

from tools.spec_traceability import covers_requirement
from world.rules import travel_events
from world.rules.presentation_events import publication_group
from world.rules.travel_events import (
    TravelCapture,
    TravellerRow,
    build_travel_events,
    clear_travel_observers,
    look_summary,
    record_room_look,
    record_travel_fact,
    register_travel_observer,
)

NODE = "wild:elosern:12:34"


def _capture(**overrides):
    fields = {
        "cell": (10, 10),
        "tick": 3600 * 30 + 60 * 5,
        "region_key": "r_a",
        "region_name": "甲原",
        "woodland": False,
        "ford": False,
        "landmarks": (),
        "lit_districts": frozenset(),
        "hostiles": (),
        "travellers": (TravellerRow("7", "伊蓮", "normal", "精神充沛"),),
    }
    fields.update(overrides)
    return TravelCapture(**fields)


def _kinds(drafts):
    return [draft.kind for draft in drafts]


class BuildTravelEventsTests(unittest.TestCase):
    def test_unchanged_repeat_view_produces_nothing(self):
        before = _capture()
        after = _capture(cell=(11, 10))
        self.assertEqual(build_travel_events(before, after, "move"), ())
        self.assertEqual(build_travel_events(before, before, "skip"), ())

    def test_region_change_names_the_new_region_only(self):
        drafts = build_travel_events(
            _capture(), _capture(region_key="r_b", region_name="乙谷"), "move"
        )
        self.assertEqual(_kinds(drafts), ["region_entered"])
        self.assertEqual(dict(drafts[0].params), {"name": "乙谷"})
        self.assertIn("乙谷", drafts[0].text)

    def test_woodland_entry_only_from_outside(self):
        inside = _capture(woodland=True)
        self.assertEqual(_kinds(build_travel_events(_capture(), inside, "move")), ["woodland_entered"])
        self.assertEqual(build_travel_events(inside, _capture(woodland=True, cell=(9, 9)), "move"), ())

    def test_ford_only_on_an_actual_ford_step(self):
        self.assertEqual(_kinds(build_travel_events(_capture(), _capture(ford=True), "move")), ["ford_crossed"])
        # A skip on a ford cell crosses nothing.
        self.assertEqual(build_travel_events(_capture(ford=True), _capture(ford=True), "skip"), ())

    def test_landmark_arrival_lights_only_when_newly_lit(self):
        """A declaration carries no prose field: the notice's prose is the
        reached room's ordinary appearance handed in by the owner."""
        after = _capture(landmarks=(("d_tower", "合成塔"),), lit_districts=frozenset({"d_tower"}))
        first = build_travel_events(
            _capture(), after, "move", landmark_prose="塔下風大。", arrival_node=NODE
        )
        self.assertEqual(_kinds(first), ["landmark_reached"])
        self.assertEqual(
            dict(first[0].params),
            {"arrival_node": NODE, "name": "合成塔", "lit_district": "合成塔", "prose": "塔下風大。", "artwork": None},
        )
        repeat = build_travel_events(after, after, "move", landmark_prose="塔下風大。", arrival_node=NODE)
        self.assertEqual(_kinds(repeat), ["landmark_reached"])
        self.assertIsNone(repeat[0].params["lit_district"])

    def test_new_hostiles_group_by_label_threat_and_count(self):
        after = _capture(
            cell=(11, 10),
            hostiles=(("k1", "灰狼", "甲"), ("k2", "灰狼", "甲"), ("k5", "灰狼", "甲"), ("k3", "野豬", None)),
        )
        drafts = build_travel_events(_capture(hostiles=(("k1", "灰狼", "甲"),)), after, "move")
        self.assertEqual(
            [dict(d.params) for d in drafts],
            [{"name": "灰狼", "count": 2, "threat": "甲"}, {"name": "野豬", "count": 1, "threat": None}],
        )
        # The same cell after a skip: only the newly present one is reported.
        same = build_travel_events(
            _capture(hostiles=(("k1", "灰狼", None),)), _capture(hostiles=(("k1", "灰狼", None), ("k4", "野豬", None))), "skip"
        )
        self.assertEqual([dict(d.params)["count"] for d in same], [1])

    @covers_requirement("webclient-travel-window::travel-observations-follow-canonical-sight-and-phase-facts")
    def test_sightings_compare_observation_identities_across_moves(self):
        """An observation still in sight after a step is never resighted,
        whatever cell the party stands on, and leaving and re-entering sight
        is a new sighting (no permanent sighting memory)."""
        wolf = ("ambient:t:1", "灰狼", "甲")
        first = _capture(cell=(10, 10), hostiles=(wolf,))
        second = _capture(cell=(11, 10), hostiles=(wolf,))
        self.assertEqual(build_travel_events(first, second, "move"), ())
        gone = _capture(cell=(12, 10))
        self.assertEqual(build_travel_events(second, gone, "move"), ())
        back = _capture(cell=(11, 10), hostiles=(wolf,))
        self.assertEqual(_kinds(build_travel_events(gone, back, "move")), ["hostile_sighted"])

    def test_a_recycled_room_keeps_the_same_identity_and_raises_no_notice(self):
        """Room recycling keeps the existing individual, so its persistent key
        is unchanged across the step and no synthetic sighting is produced."""
        beast = ("object:7", "灰狼", None)
        self.assertEqual(
            build_travel_events(_capture(hostiles=(beast,)), _capture(cell=(11, 10), hostiles=(beast,)), "move"),
            (),
        )

    def test_a_new_live_identity_raises_the_hostile_notice(self):
        before = _capture(hostiles=(("object:7", "灰狼", None),))
        after = _capture(
            cell=(11, 10),
            hostiles=(("object:7", "灰狼", None), ("object:8", "灰狼", None)),
        )
        drafts = build_travel_events(before, after, "move")
        self.assertEqual([(draft.kind, draft.params["count"]) for draft in drafts], [("hostile_sighted", 1)])

    def test_an_unchanged_read_emits_nothing(self):
        view = _capture(
            hostiles=(("k1", "灰狼", "甲"),),
            distant=(("settlement:t", "北", 15, None),),
        )
        self.assertEqual(build_travel_events(view, view, "skip"), ())
        self.assertEqual(build_travel_events(view, view, "move"), ())

    @covers_requirement("webclient-travel-window::travel-observations-follow-canonical-sight-and-phase-facts")
    def test_new_distant_sources_are_sighted_once_with_their_permitted_name(self):
        before = _capture(distant=(("settlement:a", "北", 15, None),))
        after = _capture(
            cell=(11, 10),
            distant=(("settlement:a", "北北東", 15, None), ("landmark:b", "西", 20, "合成塔"), ("landmark:c", "東", 25, None)),
        )
        drafts = build_travel_events(before, after, "move")
        self.assertEqual(
            [dict(d.params) for d in drafts],
            [
                {"name": "合成塔", "bearing": "西", "distance_km": 20},
                {"name": None, "bearing": "東", "distance_km": 25},
            ],
        )
        # The internal source keys never reach a notice.
        for draft in drafts:
            self.assertNotIn("landmark:", repr(dict(draft.params)) + draft.text)
        self.assertIn("地標", drafts[1].text)

    def test_fatigue_stage_change_per_member(self):
        before = _capture(travellers=(TravellerRow("7", "伊蓮", "normal", "精神充沛"), TravellerRow("8", "莉亞", "light", "微倦")))
        after = _capture(travellers=(TravellerRow("7", "伊蓮", "light", "微倦"), TravellerRow("8", "莉亞", "light", "微倦")))
        drafts = build_travel_events(before, after, "skip")
        self.assertEqual(
            [dict(d.params) for d in drafts],
            [{"member_id": "7", "name": "伊蓮", "stage": "light", "label": "微倦"}],
        )

    @covers_requirement(
        "webclient-travel-log::travel-notices-are-committed-structured-events"
    )
    def test_unreadable_before_never_invents_a_change(self):
        drafts = build_travel_events(
            None, _capture(region_key="r_b", woodland=True, hostiles=(("k", "狼", None),), tick=3600 * 20), "move"
        )
        self.assertEqual(drafts, ())

    def test_look_summary_is_one_line(self):
        prose = "|c北風|n 吹過草原。\n遠處有一座塔。"
        drafts = build_travel_events(None, _capture(), "look", look_prose=prose)
        self.assertEqual(_kinds(drafts), ["look"])
        self.assertEqual(drafts[0].params["prose"], prose)
        self.assertNotIn("\n", drafts[0].text)
        self.assertNotIn("|c", drafts[0].text)
        # The place's name line is skipped for the scenery after it.
        self.assertEqual(drafts[0].text, "環顧四周：遠處有一座塔。")
        self.assertEqual(look_summary("|c北風|n"), "環顧四周：北風")
        self.assertEqual(look_summary(""), "環顧四周。")

    def test_long_prose_stays_within_the_wire_string_bound(self):
        drafts = build_travel_events(None, _capture(), "look", look_prose="字" * 5000)
        self.assertEqual(len(drafts[0].params["prose"]), travel_events.MAX_PROSE_CODE_POINTS)


HOUR = 3600


class PhaseIntervalTests(unittest.TestCase):
    """Dusk and nightfall from the rulebook's phases over the committed
    charged interval; expected entries come from the sight policy itself."""

    def _entries(self, start_hour, end_hour, tick_offset=0):
        before = _capture(tick=int(start_hour * HOUR) + tick_offset)
        after = _capture(tick=int(end_hour * HOUR) + tick_offset)
        return [
            (draft.kind, draft.tick) for draft in build_travel_events(before, after, "skip") if draft.kind in ("dusk", "nightfall")
        ]

    def _start(self, name):
        from world.rules import sight

        return next(start for phase, start, _column in sight.POLICY.phases if phase == name)

    @covers_requirement("webclient-travel-window::travel-observations-follow-canonical-sight-and-phase-facts")
    def test_crossing_an_entry_inside_the_interval_reports_it(self):
        dusk, night = self._start("dusk"), self._start("night")
        # Endpoints on either side of the dusk entry.
        self.assertEqual(self._entries(dusk - 0.5, dusk + 0.5), [("dusk", dusk * HOUR)])
        # Both endpoints in the same (day) phase a whole cycle apart still
        # cross dusk and nightfall, in order.
        self.assertEqual(
            self._entries(dusk - 1, dusk - 1 + 24),
            [("dusk", dusk * HOUR), ("nightfall", night * HOUR)],
        )

    def test_several_entries_keep_chronological_order_and_lead_the_batch(self):
        dusk, night = self._start("dusk"), self._start("night")
        before = _capture(tick=(dusk - 1) * HOUR)
        after = _capture(tick=(dusk - 1 + 48) * HOUR, hostiles=(("k9", "灰狼", None),))
        drafts = build_travel_events(before, after, "skip")
        self.assertEqual(
            [(d.kind, d.tick) for d in drafts],
            [
                ("dusk", dusk * HOUR),
                ("nightfall", night * HOUR),
                ("dusk", (dusk + 24) * HOUR),
                ("nightfall", (night + 24) * HOUR),
                ("hostile_sighted", after.tick),
            ],
        )
        ticks = [d.tick for d in drafts]
        self.assertEqual(ticks, sorted(ticks))

    @covers_requirement("webclient-travel-window::travel-observations-follow-canonical-sight-and-phase-facts")
    def test_no_entry_inside_the_interval_reports_nothing(self):
        dusk, night = self._start("dusk"), self._start("night")
        # Starting at dusk and stopping before night enters nothing new.
        self.assertEqual(self._entries(dusk, night - 0.5), [])
        # A zero-charge step reports nothing even exactly on a boundary.
        self.assertEqual(self._entries(dusk, dusk), [])
        before = _capture(tick=dusk * HOUR - 1)
        self.assertEqual(build_travel_events(before, before, "move"), ())

    @covers_requirement("webclient-travel-window::travel-observations-follow-canonical-sight-and-phase-facts")
    def test_a_move_reports_its_crossing_before_its_arrival(self):
        dusk = self._start("dusk")
        before = _capture(tick=dusk * HOUR - 600)
        after = _capture(tick=dusk * HOUR + 600, region_key="r_b", region_name="乙谷")
        self.assertEqual(_kinds(build_travel_events(before, after, "move")), ["dusk", "region_entered"])

    def test_phase_starts_are_whole_hours(self):
        """The hour-boundary scan is exact only because every phase starts on
        a whole hour; the policy's integer start hours are that guarantee."""
        from world.rules import sight

        for _phase, start, _column in sight.POLICY.phases:
            self.assertIsInstance(start, int)


class RecordTravelFactTests(TestCase):
    def setUp(self):
        self.delivered = []
        clear_travel_observers()
        register_travel_observer(self.delivered.append)
        self.addCleanup(clear_travel_observers)
        self.actor = SimpleNamespace(pk=41)

    def _drafts(self, count=2):
        after = _capture(region_key="r_b", ford=True)
        drafts = build_travel_events(_capture(), after, "move")
        return drafts[:count]

    @covers_requirement(
        "webclient-travel-log::travel-notices-are-committed-structured-events"
    )
    def test_committed_fact_is_identified_once_under_its_group(self):
        with self.captureOnCommitCallbacks(execute=True):
            with publication_group() as group:
                first = record_travel_fact(self.actor, self._drafts())
                second = record_travel_fact(self.actor, self._drafts(1))
        self.assertEqual(self.delivered, [first, second])
        ids = [event.id for event in first.events] + [event.id for event in second.events]
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(all(i.startswith(group.id + ":") and len(i) <= 80 and i.isascii() for i in ids))
        self.assertEqual(first.group_id, group.id)
        self.assertEqual(second.group_id, group.id)
        self.assertNotEqual(first.fact_id, second.fact_id)
        # Day and clock text come from the event's own tick (day 2, 06:05).
        self.assertEqual((first.events[0].day, first.events[0].time), (2, "06:05"))

    @covers_requirement(
        "webclient-travel-log::travel-notices-are-committed-structured-events"
    )
    def test_rollback_delivers_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                record_travel_fact(self.actor, self._drafts())
                transaction.set_rollback(True)
        self.assertEqual(self.delivered, [])

    def test_a_rolled_back_skip_delivers_no_phase_notice(self):
        from world.rules import sight

        dusk = next(start for phase, start, _column in sight.POLICY.phases if phase == "dusk")
        drafts = build_travel_events(_capture(tick=(dusk - 1) * HOUR), _capture(tick=(dusk + 1) * HOUR), "skip")
        self.assertEqual(_kinds(drafts), ["dusk"])
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                record_travel_fact(self.actor, drafts)
                transaction.set_rollback(True)
        self.assertEqual(self.delivered, [])
        with self.captureOnCommitCallbacks(execute=True):
            fact = record_travel_fact(self.actor, drafts)
        self.assertEqual(self.delivered, [fact])

    def test_overflow_keeps_the_earlier_events(self):
        draft = build_travel_events(None, _capture(), "look", look_prose="字" * 2000)[0]
        with self.captureOnCommitCallbacks(execute=True), mock.patch.object(travel_events, "log_warn") as warn:
            fact = record_travel_fact(self.actor, [draft] * 40)
        self.assertLess(len(fact.events), 40)
        self.assertGreater(len(fact.events), 0)
        self.assertEqual([e.id for e in fact.events], [f"{fact.fact_id}.{i}" for i in range(len(fact.events))])
        self.assertEqual(warn.call_args.args[0], "travel_events_overflow")

    def test_room_look_off_the_wilderness_records_nothing(self):
        with self.captureOnCommitCallbacks(execute=True), mock.patch.object(travel_events, "_wilderness_cell", return_value=None):
            self.assertIsNone(record_room_look(self.actor, "房間。"))
        self.assertEqual(self.delivered, [])

    def test_room_look_in_the_wilderness_records_one_look(self):
        actor = SimpleNamespace(pk=41, location=object())
        with self.captureOnCommitCallbacks(execute=True), mock.patch.object(travel_events, "_wilderness_cell", return_value=(1, 1)):
            fact = record_room_look(actor, "草原。\n風。")
        self.assertEqual([e.kind for e in fact.events], ["look"])
        self.assertEqual(self.delivered, [fact])


class ProducerHookTests(TestCase):
    """The owners' after-capture: landmark prose from the ordinary appearance,
    no extra look charge, and nothing recorded for a failed look."""

    def setUp(self):
        self.delivered = []
        clear_travel_observers()
        register_travel_observer(self.delivered.append)
        self.addCleanup(clear_travel_observers)

    def test_landmark_arrival_uses_the_reached_room_appearance_without_a_charge(self):
        location = object()
        actor = mock.Mock(pk=5, location=location)
        actor.at_look.return_value = "塔前石階。"
        before = _capture()
        after = _capture(cell=(12, 34), landmarks=(("d_tower", "合成塔"),), lit_districts=frozenset({"d_tower"}))
        clock = SimpleNamespace(tick=after.tick)
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(12, 34)), \
                mock.patch.object(travel_events, "capture_travel_facts", return_value=after), \
                mock.patch.object(travel_events, "_scene_artwork", return_value=None), \
                mock.patch("world.rules.map_knowledge.encode_wild", return_value=NODE), \
                mock.patch("world.rules.clock.read_world_clock", return_value=clock), \
                mock.patch.object(travel_events, "log_warn") as warn:
            fact = travel_events.record_position_change(actor, before, "move")
        self.assertEqual(warn.call_args_list, [])
        actor.at_look.assert_called_once_with(location)
        self.assertEqual(clock.tick, after.tick)
        reached = fact.events[0]
        self.assertEqual(reached.kind, "landmark_reached")
        self.assertEqual(reached.params["prose"], "塔前石階。")
        self.assertEqual(reached.params["arrival_node"], NODE)
        self.assertEqual(reached.params["lit_district"], "合成塔")

    def _landmark_step(self):
        actor = mock.Mock(pk=5, location=object())
        actor.at_look.return_value = "塔前石階。"
        after = _capture(cell=(12, 34), landmarks=(("d_tower", "合成塔"),))
        return actor, after

    def test_a_supplied_after_capture_is_never_read_again(self):
        actor, after = self._landmark_step()
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(12, 34)), \
                mock.patch.object(travel_events, "capture_travel_facts") as read, \
                mock.patch.object(travel_events, "_scene_artwork", return_value=None), \
                mock.patch("world.rules.map_knowledge.encode_wild", return_value=NODE):
            fact = travel_events.record_position_change(actor, _capture(), "move", after=after)
            self.assertIsNone(travel_events.record_position_change(actor, _capture(), "move", after=None))
        read.assert_not_called()
        self.assertEqual([e.kind for e in fact.events], ["landmark_reached"])
        self.assertEqual(self.delivered, [fact])

    def _step_with_release(self, actor, after, released):
        """One committed step's two commit-qualified deliveries: its travel
        notice and an adapter-style result release, under one group."""
        from world.rules.presentation_events import on_publication_commit

        with publication_group() as group:
            fact = travel_events.record_position_change(actor, _capture(), "move", after=after)
            on_publication_commit(lambda: released.append({"interrupts": ["landmark_reached"], "group": group.id}))
        return fact, group

    def test_one_committed_step_publishes_its_event_and_its_flags(self):
        actor, after = self._landmark_step()
        released = []
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(12, 34)), \
                mock.patch.object(travel_events, "_scene_artwork", return_value=None), \
                mock.patch("world.rules.map_knowledge.encode_wild", return_value=NODE):
            fact, group = self._step_with_release(actor, after, released)
        self.assertEqual(self.delivered, [fact])
        self.assertEqual(fact.group_id, group.id)
        self.assertEqual(released, [{"interrupts": ["landmark_reached"], "group": group.id}])

    def test_a_rolled_back_step_publishes_neither_event_nor_flags(self):
        actor, after = self._landmark_step()
        released = []
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(12, 34)), \
                mock.patch.object(travel_events, "_scene_artwork", return_value=None), \
                mock.patch("world.rules.map_knowledge.encode_wild", return_value=NODE):
            with transaction.atomic():
                self._step_with_release(actor, after, released)
                transaction.set_rollback(True)
        self.assertEqual(self.delivered, [])
        self.assertEqual(released, [])

    def test_failed_look_adapter_records_nothing(self):
        from web.webclient.actions.exploration_actions import _look_adapter

        actor = mock.Mock(pk=5, location=mock.Mock(pk=9))
        actor.at_look.side_effect = RuntimeError("broken appearance")
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch("web.webclient.actions.exploration_actions.log_warn"):
            result = _look_adapter(actor, {"room": True})
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(self.delivered, [])

    def test_look_result_names_the_group_its_notice_joined(self):
        from web.webclient.actions.dispatcher import PUBLICATION_GROUP_FIELD
        from web.webclient.actions.exploration_actions import _look_adapter

        actor = mock.Mock(pk=5, location=mock.Mock(pk=9))
        actor.at_look.return_value = "草原。"
        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(1, 1)):
            result = _look_adapter(actor, {"room": True})
        self.assertEqual(result["outcome"], "success")
        self.assertEqual([fact.group_id for fact in self.delivered], [result[PUBLICATION_GROUP_FIELD]])
        self.assertEqual([e.kind for e in self.delivered[0].events], ["look"])

    def test_a_failed_record_never_breaks_the_owner_transaction(self):
        """A database error inside the notice record rolls back its own
        savepoint only: the owner's enclosing atomic stays usable."""
        from django.db import DatabaseError, connection
        from evennia.objects.models import ObjectDB

        actor = SimpleNamespace(pk=5, location=object())

        def broken(*_args, **_kwargs):
            # A statement error that terminates the current transaction:
            # Django marks it for rollback, then the database rejects the read.
            transaction.set_rollback(True)
            ObjectDB.objects.raw("SELECT * FROM no_such_table")[0]

        with self.captureOnCommitCallbacks(execute=True), \
                mock.patch.object(travel_events, "_wilderness_cell", return_value=(1, 1)), \
                mock.patch.object(travel_events, "capture_travel_facts", side_effect=broken), \
                mock.patch.object(travel_events, "log_warn") as warn:
            with transaction.atomic():
                self.assertIsNone(travel_events.record_position_change(actor, None, "skip"))
                # The owner's transaction survived: it is not marked for
                # rollback and it still accepts a nested atomic block.
                self.assertFalse(connection.needs_rollback)
                with transaction.atomic():
                    ObjectDB.objects.count()
        self.assertIsInstance(warn.call_args.kwargs["exc"], DatabaseError)
        self.assertEqual(self.delivered, [])

    def test_capture_reads_live_sight_on_revealed_ground_only(self):
        """The capture asks the canonical disc for hostiles, keeps only the
        knowledge owner's revealed cells and states each canonical threat."""
        from world.maps.wilderness_population import PopulationFact

        location = SimpleNamespace(wilderness=object())
        seen = []
        disc = [(10, 10), (11, 10), (12, 10)]

        def view(_location, cells):
            seen.extend(cells)
            return tuple(
                PopulationFact(f"ambient:{x}", (x, y), "monster", True, "灰狼", threat_tier=None) for x, y in cells
            )

        owner = object()
        with mock.patch("world.rules.travel_interrupts.live_sight_disc", return_value=disc), \
                mock.patch("world.rules.travel_interrupts.live_hostile_facts", side_effect=view), \
                mock.patch("world.rules.map_knowledge.revealed_in_bounds", return_value=frozenset({(11, 10)})) as revealed:
            hostiles = travel_events._hostiles_in_sight(location, (10, 10), object(), owner)
        self.assertEqual(sorted(seen), [(10, 10), (11, 10)])
        self.assertEqual(revealed.call_args.args, (owner, (10, 10, 12, 10)))
        self.assertEqual(hostiles, (("ambient:10", "灰狼", None), ("ambient:11", "灰狼", None)))

    def test_capture_failure_is_reported_not_raised(self):
        actor = SimpleNamespace(pk=5, location=object())
        with mock.patch.object(travel_events, "_wilderness_cell", side_effect=RuntimeError("bad")), \
                mock.patch.object(travel_events, "log_warn") as warn:
            self.assertIsNone(travel_events.capture_travel_facts(actor))
        self.assertEqual(warn.call_args.args[0], "travel_events_capture_failed")
