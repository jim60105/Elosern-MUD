"""Tests for the instance_reclamation settlement-stage wiring and the
quest_deadlines-before-instance_reclamation existence-differs proof
(map-instance tasks 8.4-8.7, 9.1-9.2)."""

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.rooms import InstanceRoom
from world.maps.instance import (
    pin_instance_room,
    reclaim_due_instances,
    register_instance_reclamation,
    unpin_instance_room,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules import clock as clock_module
from world.rules.clock import AdvanceSource, ScheduledEvent, get_world_clock
from world.rules.tests.combat_fixtures import BattlefieldIsolation

EXPECTED_STAGE_ORDER = (
    "gauge_regen",
    "buff_ticks",
    "sexual_decay",
    "magic_study",
    "daily_resets",
    "caravan_arrivals",
    "shop_hours",
    "quest_deadlines",
    "npc_schedules",
    "instance_reclamation",
)
BLOCKING_PIN = "quest:1:stage:0"


class InstanceStageWiringTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        clock_module._EVENT_SOURCES.pop("quest_deadlines", None)

    def tearDown(self):
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        clock_module._EVENT_SOURCES.pop("quest_deadlines", None)
        super().tearDown()

    def test_stage_order_is_exactly_the_pinned_sequence(self):
        self.assertEqual(clock_module._STAGE_ORDER, EXPECTED_STAGE_ORDER)

    def test_instance_reclamation_is_a_noop_stage_before_registration(self):
        room = create_object(InstanceRoom, key="unregistered_due")
        room.db.expire_tick = 10
        clock = get_world_clock()
        events = clock.advance(100, AdvanceSource.COMMAND, [])
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertNotIn("instance_reclaimed", [event.kind for event in events])
        self.assertNotIn("instance_promoted", [event.kind for event in events])

    def test_advance_reclaims_due_room_after_registration(self):
        register_instance_reclamation()
        room = create_object(InstanceRoom, key="registered_due")
        room.db.expire_tick = 10
        clock = get_world_clock()
        events = clock.advance(100, AdvanceSource.COMMAND, [])
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", clock.tick, {"room": room.key}),
            events,
        )

    @covers_requirement("instance-reclamation::reclaim-due-instances-is-registered-as-the-instance-reclamation-event-source-at-server-start")
    def test_server_start_registers_instance_reclamation(self):
        at_server_start()
        self.assertIs(clock_module._EVENT_SOURCES["instance_reclamation"], reclaim_due_instances)


class QuestDeadlinesOrderProofTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        clock_module._EVENT_SOURCES.pop("quest_deadlines", None)

    def tearDown(self):
        clock_module._EVENT_SOURCES.pop("instance_reclamation", None)
        clock_module._EVENT_SOURCES.pop("quest_deadlines", None)
        super().tearDown()

    def _pinned_due_room(self):
        room = create_object(InstanceRoom, key="quest_target")
        room.db.expire_tick = 10
        pin_instance_room(room, BLOCKING_PIN)
        return room

    def test_declared_order_reclaims_within_one_advance(self):
        def release_deadlines(start, end):
            if end >= 10:
                unpin_instance_room(room, BLOCKING_PIN)
            return []

        room = self._pinned_due_room()
        clock_module.register_event_source("quest_deadlines", release_deadlines)
        register_instance_reclamation()

        clock = get_world_clock()
        events = clock.advance(100, AdvanceSource.COMMAND, [])
        self.assertFalse(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertIn(
            ScheduledEvent("instance_reclaimed", clock.tick, {"room": room.key}),
            events,
        )

    def test_transposed_order_leaves_room_existing_after_single_pass(self):
        def release_deadlines(start, end):
            if end >= 10:
                unpin_instance_room(room, BLOCKING_PIN)
            return []

        room = self._pinned_due_room()
        # Construct the transposed order in isolation: instance_reclamation
        # runs first (still pinned -> deferred), quest_deadlines second
        # (releases the pin). Equivalent to one advance() pass under the wrong
        # order -- and it leaves the room existing, deferred.
        first_pass = reclaim_due_instances(0, 100)
        self.assertIn(
            ScheduledEvent("instance_reclaim_deferred", 100, {"room": room.key}),
            first_pass,
        )
        release_deadlines(0, 100)
        self.assertTrue(InstanceRoom.objects.filter(id=room.id).exists())
        self.assertEqual(room.db.pin_reasons, [])