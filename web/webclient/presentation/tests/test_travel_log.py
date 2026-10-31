"""The ``travel_log`` panel and its group-owned delivery (wilderness-travel-log-ui, task 2.1).

The validator is exercised against every kind of the closed union and its
malformed neighbours; the delivery runs the production coordinator with a
queued reactor seam so several groups can be recorded before one drain.
Notices are synthetic, already-identified facts.
"""

import copy
import unittest
from types import MappingProxyType, SimpleNamespace
from unittest import mock

from web.webclient.presentation import travel_log_push
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from web.webclient.presentation.travel_log import (
    TRAVEL_LOG_SCHEMA_VERSION,
    travel_log_presenter,
    validate_travel_log,
)
from world.rules.travel_events import TravelEvent, TravelLogFact

GROUP_A = "a" * 32
GROUP_B = "b" * 32


def _entry(kind, params, *, ident="x:1.0", text="一則旅途紀錄。"):
    return {"id": ident, "kind": kind, "tick": 90000, "day": 2, "time": "01:00", "text": text, "params": params}


VALID = {
    "region_entered": {"name": "甲原"},
    "woodland_entered": {"name": "甲原"},
    "ford_crossed": {"name": "甲原"},
    "hostile_sighted": {"name": "灰狼", "count": 2, "threat": None},
    "landmark_sighted": {"name": None, "bearing": "東北", "distance_km": 4},
    "landmark_reached": {"arrival_node": "wild:elosern:1:2", "name": "合成塔", "lit_district": None, "prose": "塔。", "artwork": None},
    "fatigue_stage": {"member_id": "7", "name": "伊蓮", "stage": "light", "label": "微倦"},
    "dusk": {},
    "nightfall": {},
    "camp_result": {"summary": "一夜無事。"},
    "look": {"prose": "草原。\n<b>風</b>"},
}


def _panel(*entries):
    return {"schema_version": TRAVEL_LOG_SCHEMA_VERSION, "available": True, "entries": list(entries)}


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("world.rules.map_knowledge.validate_node", side_effect=lambda node: node.startswith("wild:"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_every_kind_adopts_its_exact_params(self):
        for kind, params in VALID.items():
            with self.subTest(kind=kind):
                validate_travel_log(_panel(_entry(kind, copy.deepcopy(params))))

    def test_extra_or_missing_kind_specific_fields_reject(self):
        for kind, params in VALID.items():
            with self.subTest(kind=kind, case="extra"):
                with self.assertRaises(ProtocolValidationError):
                    validate_travel_log(_panel(_entry(kind, {**params, "source": "hidden"})))
            if params:
                with self.subTest(kind=kind, case="missing"):
                    trimmed = dict(params)
                    trimmed.pop(next(iter(trimmed)))
                    with self.assertRaises(ProtocolValidationError):
                        validate_travel_log(_panel(_entry(kind, trimmed)))

    def test_malformed_entries_reject(self):
        cases = {
            "unknown kind": _entry("camp_started", {}),
            "blank text": _entry("dusk", {}, text="  "),
            "non-ascii id": _entry("dusk", {}, ident="甲"),
            "long id": _entry("dusk", {}, ident="x" * 81),
            "zero count": _entry("hostile_sighted", {**VALID["hostile_sighted"], "count": 0}),
            "bad stage": _entry("fatigue_stage", {**VALID["fatigue_stage"], "stage": "tired"}),
            "parsed node": _entry("landmark_reached", {**VALID["landmark_reached"], "arrival_node": "合成塔"}),
            "null region name": _entry("region_entered", {"name": None}),
            "long prose": _entry("look", {"prose": "字" * 2049}),
        }
        for name, entry in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ProtocolValidationError):
                    validate_travel_log(_panel(entry))
        with self.assertRaises(ProtocolValidationError):
            validate_travel_log(_panel(_entry("dusk", {}), _entry("dusk", {})))
        with self.assertRaises(ProtocolValidationError):
            validate_travel_log({**_panel(), "cursor": 1})

    def test_count_and_byte_ceilings_are_independent_of_field_bounds(self):
        many = [_entry("dusk", {}, ident=f"x:1.{i}") for i in range(65)]
        with self.assertRaises(ProtocolValidationError):
            validate_travel_log(_panel(*many))
        # 40 bounded look entries: every field is in bounds, the batch is not.
        heavy = [_entry("look", {"prose": "字" * 2000}, ident=f"x:1.{i}") for i in range(40)]
        with self.assertRaises(ProtocolValidationError):
            validate_travel_log(_panel(*heavy))


# -- delivery ----------------------------------------------------------------
class _Calendar:
    year, season_index, season_name, day_in_season, hour, minute, second = 1, 0, "春", 1, 6, 0, 0


class FakeSession:
    def __init__(self, sessid=7):
        self.sent = []
        self.ndb = SimpleNamespace()
        self.sessid = sessid

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def travel_ids(self):
        """The travel_log entry ids of every frame, frame by frame."""
        out = []
        for call in self.sent:
            for name, payload in call.items():
                panel = payload[0][0].get("panels", {}).get("travel_log")
                if panel is not None:
                    out.append((name, [entry["id"] for entry in panel.get("entries", [])]))
        return out


class QueuedScheduler:
    def __init__(self):
        self.callbacks = []

    def __call__(self, callback):
        self.callbacks.append(callback)

    def run(self):
        while self.callbacks:
            self.callbacks.pop(0)()


def _event(group, token, index, kind="dusk"):
    return TravelEvent(
        id=f"{group}:{token}.{index}", kind=kind, params=MappingProxyType({}),
        text="暮色降臨。", tick=90000, day=2, time="01:00",
    )


def _fact(group, token, count=1, actor_id=41):
    return TravelLogFact(
        actor_id=actor_id, group_id=group, fact_id=f"{group}:{token}",
        events=tuple(_event(group, token, i) for i in range(count)),
    )


def _registry():
    registry = PresentationRegistry("test")
    registry.register(PresenterSpec(
        name="travel_log", schema_version=TRAVEL_LOG_SCHEMA_VERSION,
        unavailable_reason=("presentation_unavailable", "目前無法顯示此介面"),
        presenter=travel_log_presenter,
    ))
    registry.attach_validator("travel_log", validate_travel_log)
    return registry


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("world.rules.travel_interrupts.wilderness_cell", return_value=(1, 1))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.actor = SimpleNamespace(pk=41, location=object(), creation_pending=False)
        self.scheduler = QueuedScheduler()
        self.session = FakeSession()
        self.coordinator = self._coordinator(self.session)
        self.coordinator.full_snapshot(self._context())
        self.scheduler.run()
        self.session.sent.clear()

    def _coordinator(self, session):
        return PresentationCoordinator(
            session, _registry(), calendar_provider=_Calendar,
            mode_provider=lambda _context: "exploration", scheduler=self.scheduler,
        )

    def _context(self, actor=None):
        return PresentationContext(actor=actor or self.actor, protocol_version=1)

    def _record(self, fact, coordinator=None):
        target = coordinator or self.coordinator
        return target.record_travel_events(fact, self._context, expected_epoch=target.epoch)

    def test_groups_recorded_before_one_drain_publish_only_their_own_notices(self):
        self._record(_fact(GROUP_A, "aaaa0001", 2))
        self._record(_fact(GROUP_B, "bbbb0001"))
        self._record(_fact(GROUP_A, "aaaa0002"))
        self.scheduler.run()
        self.assertEqual(
            self.session.travel_ids(),
            [
                ("ui_update", [f"{GROUP_A}:aaaa0001.0", f"{GROUP_A}:aaaa0001.1", f"{GROUP_A}:aaaa0002.0"]),
                ("ui_update", [f"{GROUP_B}:bbbb0001.0"]),
            ],
        )

    def test_duplicate_fact_delivery_is_inert(self):
        fact = _fact(GROUP_A, "aaaa0001", 2)
        self._record(fact)
        self._record(fact)
        self.scheduler.run()
        self.assertEqual(self.session.travel_ids(), [("ui_update", [e.id for e in fact.events])])
        self._record(fact)
        self.scheduler.run()
        self.assertEqual(len(self.session.travel_ids()), 1)

    def test_snapshot_replays_only_the_latest_published_batch(self):
        self._record(_fact(GROUP_A, "aaaa0001"))
        self.scheduler.run()
        # A snapshot queued before a pending group never borrows its notices.
        self.coordinator.full_snapshot(self._context())
        self._record(_fact(GROUP_B, "bbbb0001"))
        self.scheduler.run()
        self.coordinator.full_snapshot(self._context())
        self.scheduler.run()
        self.assertEqual(
            self.session.travel_ids(),
            [
                ("ui_update", [f"{GROUP_A}:aaaa0001.0"]),
                ("ui_snapshot", [f"{GROUP_A}:aaaa0001.0"]),
                ("ui_update", [f"{GROUP_B}:bbbb0001.0"]),
                ("ui_snapshot", [f"{GROUP_B}:bbbb0001.0"]),
            ],
        )

    def test_a_new_epoch_or_another_puppet_never_replays_a_stale_batch(self):
        self._record(_fact(GROUP_A, "aaaa0001"))
        self.scheduler.run()
        other = SimpleNamespace(pk=42, location=object(), creation_pending=False)
        self.coordinator.full_snapshot(self._context(other))
        self.scheduler.run()
        self.coordinator.reset()
        self.coordinator.full_snapshot(self._context())
        self.scheduler.run()
        self.assertEqual(
            self.session.travel_ids(),
            [("ui_update", [f"{GROUP_A}:aaaa0001.0"]), ("ui_snapshot", []), ("ui_snapshot", [])],
        )

    def test_retired_pending_notices_never_publish(self):
        self._record(_fact(GROUP_A, "aaaa0001"))
        self.coordinator.reset()
        self.scheduler.run()
        self.assertEqual(self.session.travel_ids(), [])

    def test_every_watcher_receives_identical_ids(self):
        second = FakeSession(sessid=8)
        other = self._coordinator(second)
        other.full_snapshot(self._context())
        self.scheduler.run()
        second.sent.clear()
        self.session.ndb.elosern_coordinator = self.coordinator
        second.ndb.elosern_coordinator = other
        watchers = ((self.session, self.coordinator.epoch), (second, other.epoch))
        fact = _fact(GROUP_A, "aaaa0001", 2)
        with mock.patch.object(travel_log_push, "_resolve_actor", return_value=self.actor), \
                mock.patch("web.webclient.presentation.watchers.watchers_for", return_value=watchers), \
                mock.patch("web.webclient.presentation.ingress.build_presentation_context", side_effect=lambda _s, a: self._context(a)):
            travel_log_push.deliver_travel_fact(fact)
        self.scheduler.run()
        expected = [("ui_update", [e.id for e in fact.events])]
        self.assertEqual(self.session.travel_ids(), expected)
        self.assertEqual(second.travel_ids(), expected)

    def test_off_the_wilderness_the_batch_is_empty(self):
        context = PresentationContext(actor=self.actor, protocol_version=1, travel_events=_fact(GROUP_A, "aaaa0001").events)
        with mock.patch("world.rules.travel_interrupts.wilderness_cell", return_value=None):
            self.assertEqual(travel_log_presenter(context)["entries"], [])
