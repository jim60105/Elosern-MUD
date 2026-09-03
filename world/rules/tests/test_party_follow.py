"""Integration tests for companion follow on exit traversal (party-follow).

Covers the follow contract across every exit success path: the shared
``MovementCostMixin.at_post_traverse`` hook (grid/instance/base exits), the
wilderness gate entry, the ordinary wilderness step, and the wilderness
return. Each test pins one scenario from the party-follow delta spec:
costless, silent, binding-preserving follow; the 跟丟了 fallback naming every
left-behind companion exactly once; exit-only scope (no teleport/spawn
pulling); stale-entry safety; and rejoin on a later traversal.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.lore.sync import sync_all
from world.maps.bootstrap import NORTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, get_world_clock
from world.rules.party import (
    FOLLOW_LOST_MESSAGE,
    join_party,
    leave_party,
    live_companions,
    party_ids,
)

MOVE = CLOCK_YAML["command_defaults"]["move"]
WILDERNESS_MOVE = CLOCK_YAML["command_defaults"]["wilderness_move"]

ENTRY_XY = (60, 103)  # the north-gate approach cell


def follow_lines(msg):
    """The player messages that are follow notifications (跟丟了 lines).

    ``msg`` also carries the player's own post-move look output, so the
    tests filter for the fixed follow template instead of counting calls.
    """
    return [
        str(call.args[0])
        for call in msg.call_args_list
        if call.args and "跟丟了" in str(call.args[0])
    ]


class SelectiveRejectingRoom(Room):
    """A room that refuses arrival to NPCs whose key is listed in ``rejected_keys``.

    The player and every other companion pass; only the rejected companion's
    ``move_to`` fails, so a single traversal exercises both the successful
    follow and the left-behind fallback at once.
    """

    rejected_keys: tuple[str, ...] = ()

    def at_pre_object_receive(self, moved_obj, source_location, **kwargs):
        if getattr(moved_obj, "key", None) in self.rejected_keys:
            return False
        return True


class GridFollowTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        self.door = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        self.char1.race = "human"
        self.char1.apply_race_baseline()

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1)
        join_party(npc, self.char1)
        return npc

    def _tick(self):
        return get_world_clock().tick

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_grid_traversal_follows_companions_without_extra_cost(self):
        first = self._companion("第一")
        second = self._companion("第二")
        before = self._tick()
        self.door.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(first.location, self.room2)
        self.assertIs(second.location, self.room2)
        self.assertEqual(self._tick(), before + MOVE)
        self.assertEqual(party_ids(self.char1), [first.pk, second.pk])
        self.assertEqual(int(first.db.party_member), int(self.char1.pk))

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_empty_party_traversal_has_no_follow_side_effects(self):
        with patch.object(self.char1, "msg") as msg:
            before = self._tick()
            self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(self._tick(), before + MOVE)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(follow_lines(msg), [])

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_distant_companion_is_not_pulled(self):
        third = create_object(Room, key="Room3", location=None)
        far = create_object(NPC, key="far", location=self.room1)
        join_party(far, self.char1)
        far.move_to(third, quiet=True)
        with patch.object(self.char1, "msg") as msg:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(far.location, third)
        self.assertEqual(follow_lines(msg), [])

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_teleport_relocation_does_not_pull_companions(self):
        companion = self._companion("teleport npc")
        self.char1.move_to(self.room2, move_type="teleport")
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(companion.location, self.room1)

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_spawn_style_location_assignment_does_not_pull_companions(self):
        companion = self._companion("spawn npc")
        self.char1.location = self.room2
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(companion.location, self.room1)

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_failed_follow_names_the_left_behind_companion_once(self):
        rejecting = create_object(SelectiveRejectingRoom, key="Rejecting", location=None)
        rejecting.rejected_keys = ("stuck",)
        door = create_object(Exit, key="trap", location=self.room1, destination=rejecting)
        stuck = self._companion("stuck")
        follower = self._companion("follower")
        with patch.object(self.char1, "msg") as msg:
            before = self._tick()
            door.at_traverse(self.char1, rejecting)
        self.assertIs(self.char1.location, rejecting)
        self.assertIs(follower.location, rejecting)
        self.assertIs(stuck.location, self.room1)
        self.assertEqual(self._tick(), before + MOVE)
        expected = FOLLOW_LOST_MESSAGE.format(names="stuck")
        self.assertEqual(follow_lines(msg), [expected])

    def test_follow_lost_names_a_titled_companion_by_plain_key(self):
        # NPC identity titles are display-routing only: the notification is
        # byte-identical with a title stored (npc-title-identity-core).
        rejecting = create_object(SelectiveRejectingRoom, key="Rejecting", location=None)
        rejecting.rejected_keys = ("stuck",)
        door = create_object(Exit, key="trap", location=self.room1, destination=rejecting)
        stuck = self._companion("stuck")
        stuck.npc_title = "南門守衛"
        with patch.object(self.char1, "msg") as msg:
            door.at_traverse(self.char1, rejecting)
        self.assertIs(stuck.location, self.room1)
        expected = FOLLOW_LOST_MESSAGE.format(names="stuck")
        self.assertEqual(follow_lines(msg), [expected])

    def test_multiple_failures_are_named_in_one_notification(self):
        rejecting = create_object(SelectiveRejectingRoom, key="Rejecting", location=None)
        rejecting.rejected_keys = ("stuck-a", "stuck-b")
        door = create_object(Exit, key="trap", location=self.room1, destination=rejecting)
        first = self._companion("stuck-a")
        second = self._companion("stuck-b")
        with patch.object(self.char1, "msg") as msg:
            door.at_traverse(self.char1, rejecting)
        self.assertIs(first.location, self.room1)
        self.assertIs(second.location, self.room1)
        expected = FOLLOW_LOST_MESSAGE.format(names="stuck-a、stuck-b")
        self.assertEqual(follow_lines(msg), [expected])

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_stale_party_entry_never_blocks_follow(self):
        stale = self._companion("gone")
        stale_pk = stale.pk
        stale.delete()
        survivor = self._companion("survivor")
        self.char1.db.party = [stale_pk, survivor.pk]
        with patch.object(self.char1, "msg") as msg:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(survivor.location, self.room2)
        self.assertEqual(follow_lines(msg), [])

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_left_behind_companion_rejoins_on_later_traversal(self):
        rejecting = create_object(SelectiveRejectingRoom, key="Rejecting", location=None)
        rejecting.rejected_keys = ("stuck",)
        trap = create_object(Exit, key="trap", location=self.room1, destination=rejecting)
        back = create_object(Exit, key="back", location=rejecting, destination=self.room1)
        third = create_object(Room, key="Room3", location=None)
        onward = create_object(Exit, key="onward", location=self.room1, destination=third)
        stuck = self._companion("stuck")
        trap.at_traverse(self.char1, rejecting)
        self.assertIs(stuck.location, self.room1)
        # The player returns to the companion's room; the companion is not
        # pulled on a traversal that does not originate from its room.
        with patch.object(self.char1, "msg") as msg:
            back.at_traverse(self.char1, self.room1)
            self.assertEqual(follow_lines(msg), [])
            onward.at_traverse(self.char1, third)
        self.assertIs(self.char1.location, third)
        self.assertIs(stuck.location, third)
        self.assertEqual(follow_lines(msg), [])

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_quiet_follow_fires_no_announce_messages(self):
        companion = self._companion("quiet npc")
        with patch.object(companion, "announce_move_to") as announce_to, patch.object(
            companion, "announce_move_from"
        ) as announce_from:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(companion.location, self.room2)
        announce_to.assert_not_called()
        announce_from.assert_not_called()

    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_follow_keeps_the_party_binding_unchanged(self):
        companion = self._companion("bound npc")
        before = party_ids(self.char1)
        self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(party_ids(self.char1), before)
        self.assertEqual(int(companion.db.party_member), int(self.char1.pk))
        self.assertEqual(live_companions(self.char1), [companion])

    def test_follow_hook_never_raises_for_a_failed_companion_move(self):
        companion = self._companion("exploding npc")

        def _explode(*args, **kwargs):
            raise RuntimeError("injected follow failure")

        with patch.object(companion, "move_to", side_effect=_explode), patch.object(
            self.char1, "msg"
        ) as msg:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(companion.location, self.room1)
        expected = FOLLOW_LOST_MESSAGE.format(names="exploding npc")
        self.assertEqual(follow_lines(msg), [expected])

    def test_corrupt_party_entry_never_raises_and_does_not_block_others(self):
        from world.rules.party import live_companions

        survivor = self._companion("survivor")
        # A non-numeric dbid (corrupt stored party) must be skipped silently
        # by the resolver and never reach the traversal hook.
        self.char1.db.party = ["not-an-int", survivor.pk]
        with patch.object(self.char1, "msg") as msg:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(survivor.location, self.room2)
        self.assertEqual(follow_lines(msg), [])
        self.assertEqual([npc.pk for npc in live_companions(self.char1)], [survivor.pk])

    def test_corrupt_co_location_read_never_raises_or_blocks_others(self):
        from world.rules.party import _companion_co_located

        stuck = self._companion("corrupt")
        follower = self._companion("follower")

        def _failing_co_located(npc, source_location, wilderness_source_coordinates):
            if getattr(npc, "key", None) == "corrupt":
                raise RuntimeError("injected co-location failure")
            return _companion_co_located(
                npc, source_location, wilderness_source_coordinates
            )

        with patch(
            "world.rules.party._companion_co_located", side_effect=_failing_co_located
        ), patch.object(self.char1, "msg") as msg:
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(follower.location, self.room2)
        self.assertIs(stuck.location, self.room1)
        self.assertEqual(follow_lines(msg), [])

    def test_failed_notification_never_raises_from_the_hook(self):
        self._companion("quiet npc")
        real_msg = self.char1.msg

        def _failing_msg(text=None, *args, **kwargs):
            if text is not None and "跟丟了" in str(text):
                raise RuntimeError("injected notify failure")
            return real_msg(text, *args, **kwargs)

        with patch.object(self.char1, "msg", side_effect=_failing_msg):
            self.door.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)


class WildernessFollowTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        sync_all()
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]
        self.char1.location = self.north_gate
        self.char1.race = "human"
        self.char1.apply_race_baseline()

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.north_gate)
        join_party(npc, self.char1)
        return npc

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    def _tick(self):
        return get_world_clock().tick

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_gate_entry_follows_companions_through_the_provider_api(self):
        first = self._companion("第一")
        second = self._companion("第二")
        before = self._tick()
        self.gate.at_traverse(self.char1, self.north_gate)
        from typeclasses.rooms import TerrainRoom

        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertIsInstance(first.location, TerrainRoom)
        self.assertEqual(first.location.coordinates, ENTRY_XY)
        self.assertIsInstance(second.location, TerrainRoom)
        self.assertEqual(second.location.coordinates, ENTRY_XY)
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)

    @covers_requirement("wilderness-gateway::every-successful-wildernessreturnexit-traversal-advances-the-clock-not-only-the-registered-return-branch")
    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_ordinary_step_follows_companions_without_extra_clock(self):
        companion = self._companion("step npc")
        self.gate.at_traverse(self.char1, self.north_gate)
        before = self._tick()
        self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.coordinates, (61, 103))
        self.assertEqual(companion.location.coordinates, (61, 103))
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)

    @covers_requirement("wilderness-gateway::leaving-the-wilderness-through-wildernessreturnexit-triggers-ordinary-cleanup")
    @covers_requirement("party-system::companions-follow-the-player-through-every-exit-traversal")
    def test_return_follows_companions_to_the_grid_room(self):
        companion = self._companion("return npc")
        self.gate.at_traverse(self.char1, self.north_gate)
        self._exit("east").at_traverse(self.char1, self.char1.location)
        self._exit("west").at_traverse(self.char1, self.char1.location)
        before = self._tick()
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertIs(companion.location, self.north_gate)
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)

    def test_return_clears_the_wilderness_registration(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        companion = self._companion("leak npc")
        self.gate.at_traverse(self.char1, self.north_gate)
        self._exit("south").at_traverse(self.char1, self.char1.location)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertNotIn(companion, script.db.itemcoordinates)
        self.assertIs(companion.location, self.north_gate)

    def test_ordinary_step_does_not_double_announce(self):
        companion = self._companion("quiet step npc")
        with patch.object(companion, "announce_move_to") as announce_to, patch.object(
            companion, "announce_move_from"
        ) as announce_from:
            self.gate.at_traverse(self.char1, self.north_gate)
            self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(companion.location.coordinates, (61, 103))
        announce_to.assert_not_called()
        announce_from.assert_not_called()

    def test_wilderness_failed_follow_notifies_without_blocking_others(self):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        real_enter = enter_wilderness
        rejected = []

        def _failing_enter(obj, coordinates=(0, 0), name="default"):
            if getattr(obj, "key", None) == "stuck":
                rejected.append(obj)
                return False
            return real_enter(obj, coordinates=coordinates, name=name)

        stuck = self._companion("stuck")
        follower = self._companion("follower")
        with patch.object(self.char1, "msg") as msg, patch(
            "evennia.contrib.grid.wilderness.wilderness.enter_wilderness",
            side_effect=_failing_enter,
        ):
            self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIs(follower.location, self.char1.location)
        self.assertIs(stuck.location, self.north_gate)
        self.assertEqual(rejected, [stuck])
        expected = FOLLOW_LOST_MESSAGE.format(names="stuck")
        self.assertEqual(follow_lines(msg), [expected])
