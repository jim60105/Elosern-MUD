"""The read-only ``travel.plan`` action: payload, mapping and isolation.

The validator cases are pure. The adapter and dispatch cases run against a
real wilderness actor behind the production gate, so the query's read-only
contract and the result-only publication path are exercised end to end.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from typeclasses.exits import WildernessGateExit
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import (
    ActionRegistry,
    ActionSpec,
    build_production_action_registry,
)
from web.webclient.actions.tests.test_dispatcher._support import (
    FakeSession,
    _coordinator,
    _presenter_registry,
)
from web.webclient.actions.travel_actions import (
    CODE_SUCCESS,
    NOT_EXPLORING_CODE,
    PLAN_MESSAGES,
    travel_plan_adapter,
    validate_travel_plan_payload,
)
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    validate_ui_action_result,
)
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.static_references import settlement_node_xyz
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import KNOWLEDGE_ATTR
from world.rules.travel_plan import (
    PLAN_OUTSIDE_WINDOW,
    PLAN_PARTY_CANNOT_TRAVEL,
    PLAN_UNREACHABLE,
    PLAN_UNREVEALED,
)


def _gate_anchor_entry():
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


def _knowledge(visits):
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


class TravelPlanPayloadTests(unittest.TestCase):
    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_the_exact_payload_is_normalized_and_every_deviation_is_rejected(self):
        valid = {
            "destination": {"x": 12, "y": -3},
            "pace": "cautious",
            "stop_at_night": True,
        }
        self.assertEqual(validate_travel_plan_payload(valid), valid)
        for bad in (
            None,
            [],
            {"destination": {"x": 1, "y": 2}, "pace": "standard"},
            {
                "destination": {"x": 1, "y": 2},
                "pace": "standard",
                "stop_at_night": False,
                "extra": 1,
            },
            {
                "destination": {"x": 1},
                "pace": "standard",
                "stop_at_night": False,
            },
            {
                "destination": {"x": True, "y": 2},
                "pace": "standard",
                "stop_at_night": False,
            },
            {
                "destination": {"x": 1.5, "y": 2},
                "pace": "standard",
                "stop_at_night": False,
            },
            {
                "destination": {"x": 10**20, "y": 2},
                "pace": "standard",
                "stop_at_night": False,
            },
            {
                "destination": {"x": 1, "y": 2},
                "pace": "run",
                "stop_at_night": False,
            },
            {
                "destination": {"x": 1, "y": 2},
                "pace": "forced",
                "stop_at_night": "yes",
            },
        ):
            with self.subTest(payload=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_travel_plan_payload(bad)

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_the_production_registry_binds_the_travel_plan_spec(self):
        registry = build_production_action_registry()
        spec = registry.spec("travel.plan")
        self.assertIs(spec.validate_payload, validate_travel_plan_payload)
        self.assertIs(spec.adapter, travel_plan_adapter)
        self.assertEqual(spec.affected_panels, ())


class TravelPlanWildernessTests(EvenniaTest):
    """``EvenniaTest``: the production gate and a registered wilderness actor."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        east_gate_xyz = settlement_node_xyz(
            _gate_anchor_entry().gate_for("w").destination
        )
        self.east_gate = GridRoom.objects.filter_xyz(xyz=east_gate_xyz).first()
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
        self.char1.attributes.add(KNOWLEDGE_ATTR, _knowledge({self.origin: 8}))

    def _payload(self, destination=None, pace="forced", stop_at_night=False):
        cell = self.origin if destination is None else destination
        return {
            "destination": {"x": cell[0], "y": cell[1]},
            "pace": pace,
            "stop_at_night": stop_at_night,
        }

    def _revealed_neighbour(self):
        from world.maps import wilderness_destination
        from world.rules.map_knowledge import revealed_in_bounds
        from world.rules.travel_plan import DIRECTION_ORDER

        x, y = self.origin
        revealed = revealed_in_bounds(self.char1, (x - 20, y - 20, x + 20, y + 20))
        for direction in DIRECTION_ORDER:
            target = wilderness_destination.wilderness_neighbor(x, y, direction)
            if target is not None and target in revealed:
                return target
        return None

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_success_is_a_result_only_plan_and_a_mode_refusal_keeps_its_code(self):
        result = travel_plan_adapter(self.char1, self._payload())
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], CODE_SUCCESS)
        self.assertIs(result["no_presentation"], True)
        self.assertEqual(result["affected_panels"], ())
        data = result["data"]
        self.assertEqual(
            set(data),
            {
                "origin",
                "destination",
                "steps",
                "total_seconds",
                "nightfall_index",
                "stop_index",
                "stop_reason",
            },
        )
        self.assertEqual((data["origin"]["x"], data["origin"]["y"]), self.origin)
        self.assertEqual(data["stop_reason"], "destination_reached")
        # The same result validates inside a real success envelope.
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": "A" * 22,
            "request_id": "r1",
            "outcome": "success",
            "code": CODE_SUCCESS,
            "message": "已規劃行程。",
            "presentation_revision": 1,
            "data": data,
        }
        self.assertEqual(validate_ui_action_result(envelope)["data"], data)
        # Outside the wilderness the existing mode code is retained.
        self.char1.location = self.room1
        refused = travel_plan_adapter(self.char1, self._payload())
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], NOT_EXPLORING_CODE)
        self.assertNotIn("data", refused)

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_every_domain_refusal_maps_to_its_stable_code_and_message(self):
        x, y = self.origin
        outside = travel_plan_adapter(
            self.char1, self._payload((x + 21, y))
        )
        self.assertEqual(outside["outcome"], "rejected")
        self.assertEqual(outside["code"], PLAN_OUTSIDE_WINDOW)
        self.assertEqual(outside["message"], PLAN_MESSAGES[PLAN_OUTSIDE_WINDOW])
        self.assertNotIn("data", outside)
        unrevealed = travel_plan_adapter(
            self.char1, self._payload((x + 19, y + 19))
        )
        self.assertEqual(unrevealed["code"], PLAN_UNREVEALED)
        self.assertIs(unrevealed["no_presentation"], True)
        # A sleeping party refuses even the same-cell preview.
        from world.rules.fatigue import (
            SleepPosture,
            get_policy,
            initialize_fatigue_state,
            write_fatigue_state,
        )

        initialize_fatigue_state(self.char1)
        write_fatigue_state(self.char1, get_policy().max_units, SleepPosture.VOLUNTARY)
        refused = travel_plan_adapter(self.char1, self._payload())
        self.assertEqual(refused["code"], PLAN_PARTY_CANNOT_TRAVEL)
        self.assertEqual(refused["message"], PLAN_MESSAGES[PLAN_PARTY_CANNOT_TRAVEL])

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_an_unexpected_failure_is_logged_and_answers_plan_unreachable(self):
        with mock.patch(
            "web.webclient.actions.travel_actions.read_travel_snapshot",
            side_effect=RuntimeError("boom"),
        ), mock.patch(
            "web.webclient.actions.travel_actions.log_error"
        ) as log_error:
            result = travel_plan_adapter(self.char1, self._payload())
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], PLAN_UNREACHABLE)
        self.assertEqual(result["message"], PLAN_MESSAGES[PLAN_UNREACHABLE])
        self.assertEqual(log_error.call_args[0][0], "travel_plan_failed")
        self.assertEqual(log_error.call_args[1]["context"]["char"], str(self.char1.pk))

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_a_mode_read_failure_is_result_only_and_never_re_snapshots(self):
        session = FakeSession()
        _coordinator(session)
        session.puppet = self.char1
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=self.char1, protocol_version=1))
        session.sent.clear()  # the establishing baseline is setup, not the action
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="travel.plan",
                validate_payload=validate_travel_plan_payload,
                adapter=travel_plan_adapter,
                affected_panels=(),
            )
        )
        revision = coordinator.revision
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "plan-mode-failure",
            "base_revision": revision,
            "action_id": "travel.plan",
            "payload": self._payload(),
        }
        with mock.patch(
            "web.webclient.presentation.affordances.in_exploration_mode",
            side_effect=RuntimeError("boom"),
        ), mock.patch(
            "web.webclient.actions.travel_actions.log_error"
        ) as log_error:
            handle_ui_action(
                session, self.char1, envelope, registry, _presenter_registry()
            )
        names = [name for call in session.sent for name in call]
        self.assertNotIn("ui_update", names)
        self.assertNotIn("ui_snapshot", names)
        result = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ][-1]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], PLAN_UNREACHABLE)
        self.assertNotIn("data", result)
        self.assertEqual(coordinator.revision, revision)
        self.assertEqual(log_error.call_args[0][0], "travel_plan_failed")

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_dispatch_publishes_only_the_correlated_result_and_writes_nothing(self):
        neighbour = self._revealed_neighbour()
        self.assertIsNotNone(neighbour)
        session = FakeSession()
        _coordinator(session)
        session.puppet = self.char1
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=self.char1, protocol_version=1))
        session.sent.clear()  # the establishing baseline is setup, not the action
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="travel.plan",
                validate_payload=validate_travel_plan_payload,
                adapter=travel_plan_adapter,
                affected_panels=(),
            )
        )
        attributes = {
            attribute.key: attribute.value
            for attribute in self.char1.attributes.all()
        }
        tick = get_world_clock().tick
        location = self.char1.location
        revision = coordinator.revision
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "plan-1",
            "base_revision": revision,
            "action_id": "travel.plan",
            "payload": self._payload(neighbour, stop_at_night=False),
        }
        handle_ui_action(
            session, self.char1, envelope, registry, _presenter_registry()
        )
        names = [name for call in session.sent for name in call]
        self.assertIn("ui_action_result", names)
        self.assertNotIn("ui_update", names)
        self.assertNotIn("ui_snapshot", names)
        result = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ][-1]
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], CODE_SUCCESS)
        self.assertEqual(result["data"]["origin"], {"x": self.origin[0], "y": self.origin[1]})
        self.assertEqual(coordinator.revision, revision)
        self.assertEqual(
            {
                attribute.key: attribute.value
                for attribute in self.char1.attributes.all()
            },
            attributes,
        )
        self.assertEqual(get_world_clock().tick, tick)
        self.assertIs(self.char1.location, location)

    @covers_requirement(
        "wilderness-travel-planning::travel-queries-route-within-revealed-wilderness"
    )
    def test_a_domain_refusal_publishes_no_presentation_and_keeps_state(self):
        session = FakeSession()
        _coordinator(session)
        session.puppet = self.char1
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=self.char1, protocol_version=1))
        session.sent.clear()  # the establishing baseline is setup, not the action
        registry = ActionRegistry("test")
        registry.register(
            ActionSpec(
                action_id="travel.plan",
                validate_payload=validate_travel_plan_payload,
                adapter=travel_plan_adapter,
                affected_panels=(),
            )
        )
        attributes = {
            attribute.key: attribute.value
            for attribute in self.char1.attributes.all()
        }
        tick = get_world_clock().tick
        location = self.char1.location
        revision = coordinator.revision
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "plan-refused",
            "base_revision": coordinator.revision,
            "action_id": "travel.plan",
            "payload": self._payload((self.origin[0] + 21, self.origin[1])),
        }
        handle_ui_action(
            session, self.char1, envelope, registry, _presenter_registry()
        )
        names = [name for call in session.sent for name in call]
        self.assertNotIn("ui_update", names)
        self.assertNotIn("ui_snapshot", names)
        result = [
            call["ui_action_result"][0][0]
            for call in session.sent
            if "ui_action_result" in call
        ][-1]
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], PLAN_OUTSIDE_WINDOW)
        self.assertNotIn("data", result)
        self.assertEqual(coordinator.revision, revision)
        self.assertEqual(
            {
                attribute.key: attribute.value
                for attribute in self.char1.attributes.all()
            },
            attributes,
        )
        self.assertEqual(get_world_clock().tick, tick)
        self.assertIs(self.char1.location, location)
