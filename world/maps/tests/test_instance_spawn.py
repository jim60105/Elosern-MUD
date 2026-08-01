"""Integration tests for the instance prototype whitelist, spawn_instance_room,
and the rulebook TTL data (map-instance tasks 3.3-3.4, 4.4-4.9, 6.2)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.prototypes import prototypes as prototypes_module
from evennia.prototypes import spawner as spawner_module
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit
from typeclasses.rooms import InstanceRoom, Room
from world.maps.instance import (
    INSTANCE_PROTOTYPE_WHITELIST,
    INSTANCE_YAML,
    _validate_prototype_parent,
    pin_instance_room,
    register_owned_entity,
    spawn_instance_room,
)
from world.rules.clock import CLOCK_YAML, get_world_clock

WHITELISTED_PROTOTYPE = {
    "prototype_parent": "instance_room",
    "key": "cave_entrance",
}
NON_WHITELISTED_PROTOTYPE = {
    "prototype_parent": "some_other_parent",
    "key": "unapproved",
}


class InstancePrototypeWhitelistTests(EvenniaTest):
    def test_module_prototype_registers_with_whitelisted_key_and_typeclass(self):
        prototypes_module.load_module_prototypes("world.prototypes")
        prototype = spawner_module.search_prototype("instance_room", require_single=True)[0]
        self.assertEqual(prototype["prototype_key"], "instance_room")
        self.assertEqual(prototype["typeclass"], "typeclasses.rooms.InstanceRoom")

    @covers_requirement("instance-spawn::instance-room-is-a-module-prototype-resolving-to-prototype-key-instance-room")
    def test_whitelist_has_exactly_one_entry(self):
        self.assertEqual(INSTANCE_PROTOTYPE_WHITELIST, ("instance_room",))

    def test_validate_accepts_whitelisted_parent(self):
        _validate_prototype_parent(WHITELISTED_PROTOTYPE)

    def test_validate_rejects_non_whitelisted_parent(self):
        with self.assertRaises(ValueError):
            _validate_prototype_parent(NON_WHITELISTED_PROTOTYPE)


class InstanceSpawnTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.origin_room = create_object(Room, key="origin")

    def _tick(self):
        return get_world_clock().tick

    def test_spawn_returns_instance_room_for_whitelisted_parent(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="into the mist",
            return_key="back",
        )
        self.assertIsInstance(room, InstanceRoom)
        self.assertIs(room.db.origin_room, self.origin_room)

    def test_spawn_rejects_non_whitelisted_before_spawning(self):
        before = InstanceRoom.objects.all().count()
        with (
            patch("world.maps.instance.spawn") as mock_spawn,
            self.assertRaises(ValueError),
        ):
            spawn_instance_room(
                self.origin_room,
                NON_WHITELISTED_PROTOTYPE,
                exit_key="in",
                return_key="out",
            )
        mock_spawn.assert_not_called()
        self.assertEqual(InstanceRoom.objects.all().count(), before)

    @covers_requirement("instance-spawn::spawn-instance-room-validates-prototype-parent-against-the-whitelist-before-spawning")
    def test_spawn_rejects_typeclass_override_before_spawning(self):
        before = InstanceRoom.objects.all().count()
        override = dict(WHITELISTED_PROTOTYPE)
        override["typeclass"] = "typeclasses.rooms.Room"
        with (
            patch("world.maps.instance.spawn") as mock_spawn,
            self.assertRaises(ValueError),
        ):
            spawn_instance_room(
                self.origin_room,
                override,
                exit_key="in",
                return_key="out",
            )
        mock_spawn.assert_not_called()
        self.assertEqual(InstanceRoom.objects.all().count(), before)

    def test_spawn_rejects_non_instance_result_without_leaving_exits(self):
        # Defense-in-depth: even if spawner.spawn() somehow produced a
        # non-InstanceRoom object for a whitelisted input, the attach pair must
        # not be created and the stray object must be rolled back. The stray is
        # created inside the patched spawn() so it participates in the same
        # transaction that rolls back on rejection.
        exits_before = Exit.objects.all().count()
        rooms_before = InstanceRoom.objects.all().count()
        stray_ids = []

        def fake_spawn(prototype, caller=None, **kwargs):
            stray = create_object(Room, key="stray_in_tx")
            stray_ids.append(stray.id)
            return [stray]

        with (
            patch("world.maps.instance.spawn", side_effect=fake_spawn),
            self.assertRaises(ValueError),
        ):
            spawn_instance_room(
                self.origin_room,
                WHITELISTED_PROTOTYPE,
                exit_key="in",
                return_key="out",
            )
        self.assertEqual(Exit.objects.all().count(), exits_before)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)
        self.assertFalse(Room.objects.filter(id=stray_ids[0]).exists())

    def test_ttl_seconds_rejects_invalid_types_and_negative_values(self):
        for bad in (-1, "60", True, 1.5):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                spawn_instance_room(
                    self.origin_room,
                    WHITELISTED_PROTOTYPE,
                    exit_key="in",
                    return_key="out",
                    ttl_seconds=bad,
                )

    def test_ttl_seconds_zero_is_accepted_and_immediately_due(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="in",
            return_key="out",
            ttl_seconds=0,
        )
        self.assertEqual(room.db.expire_tick, self._tick())

    def test_failed_exit_creation_rolls_back_room_and_both_exits(self):
        exits_before = Exit.objects.all().count()
        rooms_before = InstanceRoom.objects.all().count()

        with patch.object(
            Exit,
            "create",
            side_effect=[None, RuntimeError("second exit refused")],
        ):
            with self.assertRaises(RuntimeError):
                spawn_instance_room(
                    self.origin_room,
                    WHITELISTED_PROTOTYPE,
                    exit_key="in",
                    return_key="out",
                )
        self.assertEqual(Exit.objects.all().count(), exits_before)
        self.assertEqual(InstanceRoom.objects.all().count(), rooms_before)

    def test_expire_tick_uses_default_ttl_when_omitted(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="in",
            return_key="out",
        )
        self.assertEqual(
            room.db.expire_tick,
            self._tick() + INSTANCE_YAML["default_ttl_seconds"],
        )

    def test_expire_tick_honors_explicit_ttl_override(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="in",
            return_key="out",
            ttl_seconds=60,
        )
        self.assertEqual(room.db.expire_tick, self._tick() + 60)

    def test_named_reflects_caller_supplied_value_and_defaults_false(self):
        named_room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="in1",
            return_key="out1",
            named=True,
        )
        self.assertTrue(named_room.db.named)

        unnamed_room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="in2",
            return_key="out2",
        )
        self.assertFalse(unnamed_room.db.named)

    def test_exactly_one_exit_pair_is_created_at_both_ends(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="into the mist",
            return_key="back",
        )
        forward = [exit_obj for exit_obj in self.origin_room.exits if exit_obj.key == "into the mist"]
        backward = [exit_obj for exit_obj in room.exits if exit_obj.key == "back"]
        self.assertEqual(len(forward), 1)
        self.assertEqual(len(backward), 1)
        self.assertIs(forward[0].destination, room)
        self.assertIs(backward[0].destination, self.origin_room)
        for exit_obj in forward + backward:
            self.assertIs(type(exit_obj), Exit)

    @covers_requirement("instance-spawn::spawn-instance-room-sets-expire-tick-named-and-origin-room-and-creates-a-bidirectional-attach-exit")
    def test_character_can_walk_in_and_back_via_ordinary_traversal(self):
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="into the mist",
            return_key="back",
        )
        forward = [exit_obj for exit_obj in self.origin_room.exits if exit_obj.key == "into the mist"][0]
        self.char1.move_to(forward.destination)
        self.assertIs(self.char1.location, room)
        backward = [exit_obj for exit_obj in room.exits if exit_obj.key == "back"][0]
        self.char1.move_to(backward.destination)
        self.assertIs(self.char1.location, self.origin_room)

    @covers_requirement("instance-spawn::spawn-instance-room-rejects-an-instanceroom-as-origin-room")
    def test_nested_instance_origin_is_rejected_before_spawning(self):
        inner = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="inner_in",
            return_key="inner_out",
        )
        room_count = InstanceRoom.objects.all().count()
        exit_count = Exit.objects.all().count()
        with self.assertRaises(ValueError):
            spawn_instance_room(
                inner,
                WHITELISTED_PROTOTYPE,
                exit_key="outside_in",
                return_key="outside_out",
            )
        self.assertEqual(InstanceRoom.objects.all().count(), room_count)
        self.assertEqual(Exit.objects.all().count(), exit_count)

    def test_spawn_instance_room_is_callable_from_bootstrap_prototype_module_scope(self):
        # Guards against an import-order surprise: the whitelist module loads
        # at import time, before any room exists, so nothing on this path may
        # require a database connection at import.
        room = spawn_instance_room(
            self.origin_room,
            WHITELISTED_PROTOTYPE,
            exit_key="import_guard_in",
            return_key="import_guard_out",
        )
        self.assertIsInstance(room, InstanceRoom)


class InstanceYamlTests(EvenniaTest):
    @covers_requirement("instance-reclamation::default-ttl-seconds-is-declared-rulebook-data")
    def test_default_ttl_seconds_matches_independent_arithmetic(self):
        self.assertEqual(INSTANCE_YAML["default_ttl_seconds"], 345600)
        self.assertEqual(
            INSTANCE_YAML["default_ttl_seconds"],
            4 * CLOCK_YAML["hours_per_day"] * CLOCK_YAML["seconds_per_hour"],
        )


class PinApiRyTests(EvenniaTest):
    """Pin/unpin and owned-entity registration (map-instance tasks 5.2-5.4, 5.6-5.7)."""

    def setUp(self):
        super().setUp()
        self.room = create_object(InstanceRoom, key="pinnable")

    def test_pinning_same_reason_twice_leaves_single_entry(self):
        pin_instance_room(self.room, "quest:1:stage:0")
        pin_instance_room(self.room, "quest:1:stage:0")
        self.assertEqual(self.room.db.pin_reasons, ["quest:1:stage:0"])

    def test_pinning_two_distinct_reasons_keeps_both(self):
        pin_instance_room(self.room, "quest:1:stage:0")
        pin_instance_room(self.room, "art_queue")
        self.assertEqual(len(self.room.db.pin_reasons), 2)

    def test_owned_entity_deduplicated(self):
        register_owned_entity(self.room, self.obj1)
        register_owned_entity(self.room, self.obj1)
        self.assertEqual(self.room.db.owned_entities, [self.obj1])

    def test_never_registered_entity_is_absent(self):
        # A second object that was never registered stays outside owned_entities.
        register_owned_entity(self.room, self.obj1)
        self.assertNotIn(self.obj2, self.room.db.owned_entities)

    @covers_requirement("instance-reclamation::pin-instance-room-and-unpin-instance-room-are-reason-keyed-reference-holders")
    def test_unpinning_absent_reason_does_not_raise(self):
        pin_instance_room(self.room, "quest:1:stage:0")
        from world.maps.instance import unpin_instance_room

        unpin_instance_room(self.room, "never_pinned")
        self.assertEqual(self.room.db.pin_reasons, ["quest:1:stage:0"])

    def test_unpinning_removes_only_matching_reason(self):
        from world.maps.instance import unpin_instance_room

        pin_instance_room(self.room, "quest:1:stage:0")
        pin_instance_room(self.room, "art_queue")
        unpin_instance_room(self.room, "quest:1:stage:0")
        self.assertEqual(self.room.db.pin_reasons, ["art_queue"])
