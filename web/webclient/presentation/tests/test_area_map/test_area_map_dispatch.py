"""The on-demand ``area_map`` presenter and the ``map.view`` action (area map dispatch)."""

import json
from unittest import mock
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.area_map import area_map_presenter
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.protocol import ProtocolValidationError
from web.webclient.presentation.registry import PresentationRegistry, PresenterSpec, build_production_registry
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import encode_room, parse_knowledge, record_arrival
from ..test_local_map._support import _context


from ._support import _Session, _Calendar, _status_spec

class MapViewDispatchTests(EvenniaTestCase):
    def setUp(self):
        get_world_clock()
        self.rooms = [create_object(Room, key=f"合成廳{i}") for i in range(2)]
        create_object(Exit, key="東", location=self.rooms[0], destination=self.rooms[1])
        self.char = create_object(PlayerCharacter, key="t_char", location=self.rooms[0])
        record_arrival(self.char)
        self.calls = []

        def spy(context):
            self.calls.append(context)
            return area_map_presenter(context)

        self.registry = PresentationRegistry("test")
        self.registry.register(_status_spec())
        self.registry.register(
            PresenterSpec("area_map", 4, ("map_unavailable", "區域地圖目前無法顯示"), spy, on_demand=True)
        )
        self.session = _Session(self.char)
        self.coordinator = PresentationCoordinator(
            self.session, self.registry, calendar_provider=lambda: _Calendar(), mode_provider=lambda ctx: "exploration"
        )
        self.session.ndb.elosern_coordinator = self.coordinator
        self.coordinator.full_snapshot(_context(self.char))

    def _envelope(self, action_id, payload, request_id="t_r1"):
        return {
            "protocol_version": 1,
            "presentation_epoch": self.coordinator.epoch,
            "request_id": request_id,
            "base_revision": self.coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    @covers_requirement("webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay")
    def test_area_request_with_missing_instance_origin_never_creates_attributes(self):
        from evennia.typeclasses.attributes import Attribute
        from typeclasses.rooms import InstanceRoom
        from web.webclient.presentation.tests.test_map_quest_destinations import (
            _patch_geography, _record, _DEFINITIONS,
        )
        from world.quests.runtime import to_storage

        _patch_geography(self)
        entrance = create_object(InstanceRoom, key="Synthetic entrance")
        deep = create_object(InstanceRoom, key="Synthetic destination")
        create_object(Exit, key="Deeper", location=entrance, destination=deep)
        self.char.location = entrance
        record_arrival(self.char)
        entrance.attributes.remove("origin_room")
        deep.attributes.remove("origin_room")
        with mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", _DEFINITIONS):
            for index, log in enumerate(([], [
                to_storage(_record("bound", stage_room_id=int(deep.id))),
                to_storage(_record("anchor")), to_storage(_record("hunt")),
            ])):
                self.char.db.quest_log = log
                self.assertFalse(entrance.attributes.has("origin_room"))
                self.assertFalse(deep.attributes.has("origin_room"))
                before = (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                          sorted((a.id, a.db_key, repr(a.value)) for a in Attribute.objects.all()))
                handle_ui_action(self.session, self.char,
                                 self._envelope("map.view", {"scope": "area"}, f"t_orphan{index}"),
                                 build_production_action_registry(), self.registry)
                body = self.session.frames("ui_update")[-1]["panels"]["area_map"]
                self.assertTrue(body["available"])
                self.assertEqual(body["current_node"], encode_room(int(entrance.id)))
                self.assertEqual(body["quest_markers"], [] if not log else [{
                    "id": "q_bound", "title": _DEFINITIONS["map_dest_bound"].display_name,
                    "tracked": False, "destination": {"kind": "node", "node_id": encode_room(int(deep.id))},
                }])
                self.assertEqual(before, (self.char.location, parse_knowledge(self.char), get_world_clock().tick,
                                 sorted((a.id, a.db_key, repr(a.value)) for a in Attribute.objects.all())))
                self.assertFalse(entrance.attributes.has("origin_room"))
                self.assertFalse(deep.attributes.has("origin_room"))

    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_map_view_is_an_exact_allowlisted_read(self):
        spec = build_production_action_registry().spec("map.view")
        self.assertEqual(spec.affected_panels, ("area_map", "world_map"))
        self.assertEqual(spec.validate_payload({"scope": "area"}), {"scope": "area"})
        self.assertEqual(spec.validate_payload({"scope": "world"}), {"scope": "world"})
        for bad in ({}, {"scope": "galaxy"}, {"scope": "area", "x": 1}, {"scope": 1}, ["area"]):
            with self.subTest(payload=bad), self.assertRaises(ProtocolValidationError):
                spec.validate_payload(bad)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    @covers_requirement(
        "webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe"
    )
    def test_map_view_publishes_only_the_area_map(self):
        before_location = self.char.location
        before_knowledge = parse_knowledge(self.char)
        before_clock = get_world_clock().tick
        before_quest_log = self.char.attributes.get("quest_log")
        handle_ui_action(
            self.session, self.char, self._envelope("map.view", {"scope": "area"}),
            build_production_action_registry(), self.registry,
        )
        self.assertEqual(len(self.calls), 1)
        updates = self.session.frames("ui_update")
        self.assertEqual(len(updates), 1)
        self.assertEqual(list(updates[0]["panels"]), ["area_map"])
        self.assertTrue(updates[0]["panels"]["area_map"]["available"])
        result = self.session.frames("ui_action_result")[-1]
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["presentation_revision"], updates[0]["revision"])
        self.assertIs(self.char.location, before_location)
        self.assertEqual(parse_knowledge(self.char), before_knowledge)
        self.assertEqual(get_world_clock().tick, before_clock)
        self.assertEqual(self.char.attributes.get("quest_log"), before_quest_log)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_rejected_scope_never_runs_the_presenter(self):
        handle_ui_action(
            self.session, self.char, self._envelope("map.view", {"scope": "galaxy"}),
            build_production_action_registry(), self.registry,
        )
        self.assertEqual(self.calls, [])
        result = self.session.frames("ui_action_result")[-1]
        self.assertEqual(result["code"], "malformed_payload")

    @covers_requirement("webclient-world-map::world-scope-reveals-only-common-geography-and-permitted-district-knowledge")
    def test_world_request_publishes_only_filtered_world_without_gameplay_writes(self):
        from web.webclient.presentation.world_map import world_map_presenter
        from web.webclient.presentation.tests.test_world_map import fixtures, SECRET

        self.registry.register(PresenterSpec("world_map", 1, ("map_unavailable", "地圖無法顯示"),
                                             world_map_presenter, on_demand=True))
        before=(self.char.location,parse_knowledge(self.char),get_world_clock().tick,self.char.db.quest_log)
        with fixtures(), mock.patch("web.webclient.presentation.world_map_geometry.current_point",return_value=(1,2)), \
             mock.patch("web.webclient.presentation.world_map.quest_markers",return_value=[]):
            handle_ui_action(
                self.session,self.char,self._envelope("map.view",{"scope":"world"}),
                build_production_action_registry(),self.registry,
            )
        update=self.session.frames("ui_update")[-1]
        self.assertEqual(set(update["panels"]),{"world_map"})
        self.assertTrue(update["panels"]["world_map"]["available"])
        self.assertNotIn(SECRET,json.dumps(update))
        self.assertEqual(self.calls,[])
        self.assertEqual(before,(self.char.location,parse_knowledge(self.char),get_world_clock().tick,self.char.db.quest_log))

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    def test_movement_and_refresh_never_compute_or_push_a_map(self):
        exit_obj = self.rooms[0].exits[0]
        handle_ui_action(
            self.session,
            self.char,
            self._envelope(
                "explore.move",
                {"exit_ref": str(int(exit_obj.id)), "current_node": encode_room(int(self.rooms[0].id))},
            ),
            build_production_action_registry(),
            self.registry,
        )
        self.assertIs(self.char.location, self.rooms[1], "the move committed")
        self.coordinator.synchronize(_context(self.char))
        self.coordinator.enqueue_publication(
            lambda: _context(self.char), affected_panels={"status"}
        )
        self.assertEqual(self.calls, [])
        for name in ("ui_snapshot", "ui_update"):
            for frame in self.session.frames(name):
                self.assertNotIn("area_map", frame["panels"])

    def test_production_snapshot_omits_the_area_map(self):
        with mock.patch.object(area_map_module, "area_map_presenter") as presenter:
            registry = build_production_registry()
            self.assertIs(registry.spec("area_map").presenter, presenter)
            self.assertIn("area_map", registry.on_demand_panel_names)
            self.assertNotIn("area_map", registry.eager_panel_names)
            session = _Session(self.char)
            coordinator = PresentationCoordinator(session, registry, calendar_provider=lambda: _Calendar())
            coordinator.full_snapshot(_context(self.char))
        presenter.assert_not_called()
        self.assertNotIn("area_map", session.frames("ui_snapshot")[0]["panels"])
