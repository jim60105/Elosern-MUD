"""Integration tests for the whole party following a possessed traversal.

Pins the ``party-follow-under-possession`` delta: the follow function resolves
the commander from the traverser, so a possessed puppet brings the owner's
unpuppeted body and every other effective companion along. The owner body
passes the destination receive gate explicitly but moves hook-free (one map
knowledge record, no player-arrival presentation), a refused member is named
once in the acting session's 跟丟了 notice, and the movement settlement
compensates the body together with the companions.
"""

from copy import deepcopy
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    enter_wilderness,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.lore.sync import sync_all
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.map_knowledge import parse_knowledge, record_arrival
from world.rules.party import FOLLOW_LOST_MESSAGE, follow_companions, join_party, party_ids
from world.rules.possession import enter_possession, release_possession
from world.quests.room_observation import observe_room_entry

MOVE = CLOCK_YAML["command_defaults"]["move"]
WILDERNESS_MOVE = CLOCK_YAML["command_defaults"]["wilderness_move"]


def _east_gate_probe():
    """The capital's east gate room + approach cell from the live registry."""
    import importlib

    entries = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    ).values()
    entry = next(entry for entry in entries if entry.gate_for("w") is not None)
    gate = entry.gate_for("w")
    return (*gate.grid_xy, gate.z_map_key), entry.approach_cell(gate)


EAST_GATE_XYZ, ENTRY_XY = _east_gate_probe()


def follow_lines(msg):
    """The session messages that are follow notifications (跟丟了 lines)."""
    return [
        str(call.args[0])
        for call in msg.call_args_list
        if call.args and "跟丟了" in str(call.args[0])
    ]


class SelectiveRejectingRoom(Room):
    """Refuse arrival to members whose key is listed in ``rejected_keys``."""

    rejected_keys: tuple[str, ...] = ()

    def at_pre_object_receive(self, moved_obj, source_location, **kwargs):
        if getattr(moved_obj, "key", None) in self.rejected_keys:
            return False
        return True


class PossessedFollowTestCase(EvenniaTest):
    """A possessed companion with the owner body and a second companion."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        self.char1.location = self.room1
        self.npc = self._companion("艾拉")
        self.other = self._companion("卡恩")
        enter_possession(self.char1, self.npc)

    def _companion(self, key):
        npc = create_object(NPC, key=key, location=self.room1)
        join_party(npc, self.char1)
        return npc

    def _tick(self):
        return get_world_clock().tick


class PossessedGridFollowTests(PossessedFollowTestCase):
    def setUp(self):
        super().setUp()
        self.door = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_whole_party_follows_a_possessed_grid_traversal(self):
        party_before = party_ids(self.char1)
        possession_before = deepcopy(self.char1.db.possession)
        entranced = self.char1.get_display_name(self.other)
        before = self._tick()

        self.door.at_traverse(self.npc, self.room2)

        self.assertIs(self.npc.location, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(self.other.location, self.room2)
        self.assertIn(self.char1, self.room2.contents)
        self.assertIn(self.other, self.room2.contents)
        self.assertEqual(self._tick(), before + MOVE)
        self.assertEqual(party_ids(self.char1), party_before)
        self.assertEqual(self.char1.db.possession, possession_before)
        self.assertEqual(
            self.char1.get_display_name(self.other), entranced
        )
        self.assertIs(self.session.puppet, self.npc)

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_owner_body_moves_hook_free_and_records_arrival_once(self):
        with patch.object(
            self.char1, "move_to", wraps=self.char1.move_to
        ) as body_move, patch.object(self.char1, "at_post_move") as post_move, patch.object(
            self.char1, "at_pre_move"
        ) as pre_move, patch(
            "world.rules.map_knowledge.record_arrival", wraps=record_arrival
        ) as record, patch(
            "world.quests.room_observation.observe_arrival_lore"
        ) as lore, patch(
            "world.quests.encounter_dispatch.activate_for_move"
        ) as encounter, patch(
            "world.rules.dialogue.clear_dialogue_session"
        ) as dialogue:
            self.door.at_traverse(self.npc, self.room2)

        body_move.assert_called_once()
        self.assertIs(body_move.call_args.args[0], self.room2)
        self.assertIs(body_move.call_args.kwargs["quiet"], True)
        self.assertIs(body_move.call_args.kwargs["move_hooks"], False)
        post_move.assert_not_called()
        pre_move.assert_not_called()
        dialogue.assert_not_called()
        for call in encounter.call_args_list:
            self.assertIsNot(call.args[0], self.char1)
        for call in lore.call_args_list:
            self.assertIsNot(call.args[0], self.char1)
        body_records = [call for call in record.call_args_list if call.args[0] is self.char1]
        self.assertEqual(len(body_records), 1)
        stored = self.char1.attributes.get("map_knowledge")
        self.assertIn(f"room:{self.room2.pk}", stored["visited"])

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_failed_companion_follow_notifies_the_puppet_session_once(self):
        rejecting = create_object(
            SelectiveRejectingRoom, key="Rejecting", location=None
        )
        rejecting.rejected_keys = ("卡恩",)
        trap = create_object(
            Exit, key="trap", location=self.room1, destination=rejecting
        )
        with patch.object(self.npc, "msg") as npc_msg, patch.object(
            self.char1, "msg"
        ) as body_msg:
            trap.at_traverse(self.npc, rejecting)

        self.assertIs(self.npc.location, rejecting)
        self.assertIs(self.char1.location, rejecting)
        self.assertIs(self.other.location, self.room1)
        expected = FOLLOW_LOST_MESSAGE.format(names="卡恩")
        self.assertEqual(follow_lines(npc_msg), [expected])
        self.assertEqual(follow_lines(body_msg), [])

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_refused_owner_body_is_left_behind_with_the_notice(self):
        rejecting = create_object(
            SelectiveRejectingRoom, key="Rejecting", location=None
        )
        rejecting.rejected_keys = (self.char1.key,)
        trap = create_object(
            Exit, key="trap", location=self.room1, destination=rejecting
        )
        with patch.object(self.npc, "msg") as npc_msg:
            trap.at_traverse(self.npc, rejecting)

        self.assertIs(self.npc.location, rejecting)
        self.assertIs(self.other.location, rejecting)
        self.assertIs(self.char1.location, self.room1)
        self.assertIsNone(self.char1.attributes.get("map_knowledge"))
        expected = FOLLOW_LOST_MESSAGE.format(names=self.char1.key)
        self.assertEqual(follow_lines(npc_msg), [expected])

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_stale_possession_flag_follows_nobody(self):
        self.npc.sessions.remove(self.session)
        self.session.puppet = None
        self.char1.db.possession = None
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))

        with patch("world.rules.party.log_warn") as warn:
            self.door.at_traverse(self.npc, self.room2)

        self.assertIs(self.npc.location, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertIs(self.other.location, self.room1)
        warn.assert_called_once_with(
            "party_follow_commander_unresolved",
            context={"obj": str(self.npc), "possessed": True},
        )

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_player_traversal_keeps_the_ordinary_follow_path(self):
        release_possession(self.char1, npc=self.npc, reason="handback")
        before = self._tick()
        with patch("world.rules.party._reobserve_quest_arrival") as reobserve:
            self.door.at_traverse(self.char1, self.room2)

        self.assertIs(self.char1.location, self.room2)
        self.assertIs(self.npc.location, self.room2)
        self.assertIs(self.other.location, self.room2)
        self.assertEqual(self._tick(), before + MOVE)
        reobserve.assert_called_once()
        self.assertIs(reobserve.call_args.args[0], self.char1)
        self.assertFalse(reobserve.call_args.kwargs["possessed"])

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_body_observes_once_even_when_a_member_waits_at_the_destination(self):
        self.other.move_to(self.room2, quiet=True)
        with patch(
            "world.quests.room_observation.observe_room_entry",
            wraps=observe_room_entry,
        ) as observe:
            self.door.at_traverse(self.npc, self.room2)

        commander_calls = [call for call in observe.call_args_list if call.args[1] is self.char1]
        self.assertEqual(len(commander_calls), 1)
        self.assertIs(commander_calls[0].args[0], self.room2)
        self.assertIs(commander_calls[0].kwargs["observe_lore"], False)


class PossessedWildernessFollowTests(PossessedFollowTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_all()
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]
        self.char1.location = self.east_gate
        for npc in (self.npc, self.other):
            npc.location = self.east_gate

    def _exit(self, direction):
        return [e for e in self.npc.location.exits if e.key == direction][0]

    def _script(self):
        return WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_gate_entry_brings_the_whole_party(self):
        before = self._tick()

        self.gate.at_traverse(self.npc, self.east_gate)

        self.assertEqual(self.npc.location.coordinates, ENTRY_XY)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(self.other.location.coordinates, ENTRY_XY)
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)
        self.assertEqual(self._script().itemcoordinates.get(self.char1), ENTRY_XY)
        visited = self.char1.attributes.get("map_knowledge")["visited"]
        self.assertIn(f"wild:{WILDERNESS_NAME}:{ENTRY_XY[0]}:{ENTRY_XY[1]}", visited)

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_recycled_body_rejoins_through_the_registration_predicate(self):
        self.gate.at_traverse(self.npc, self.east_gate)
        # The contrib recycles a wilderness room once no account remains in it:
        # the unpuppeted body keeps only its registration at the source cell.
        self.char1.location = None
        self.assertIsNone(self.char1.location)
        target = (ENTRY_XY[0] + 1, ENTRY_XY[1])
        before = self._tick()

        self._exit("east").at_traverse(self.npc, self.npc.location)

        self.assertIsNotNone(self.char1.location)
        self.assertEqual(self.char1.location.coordinates, target)
        self.assertIn(self.char1, self.char1.location.contents)
        self.assertEqual(self.other.location.coordinates, target)
        self.assertEqual(self._script().itemcoordinates.get(self.char1), target)
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)

    @covers_requirement(
        "party-system::companions-follow-the-player-through-every-exit-traversal"
    )
    def test_wilderness_return_brings_the_whole_party_to_the_grid(self):
        self.gate.at_traverse(self.npc, self.east_gate)
        self._exit("east").at_traverse(self.npc, self.npc.location)
        self._exit("west").at_traverse(self.npc, self.npc.location)
        before = self._tick()

        self._exit("west").at_traverse(self.npc, self.npc.location)

        self.assertIs(self.npc.location, self.east_gate)
        self.assertIs(self.char1.location, self.east_gate)
        self.assertIs(self.other.location, self.east_gate)
        self.assertEqual(self._tick(), before + WILDERNESS_MOVE)
        itemcoordinates = self._script().itemcoordinates
        for member in (self.npc, self.char1, self.other):
            self.assertNotIn(member, itemcoordinates)

    @covers_requirement(
        "companion-possession-transition::normal-possession-release-preserves-the-"
        "companion-s-room-presence"
    )
    def test_release_keeps_a_refused_body_at_its_registered_coordinates(self):
        self.gate.at_traverse(self.npc, self.east_gate)
        target = (ENTRY_XY[0] + 1, ENTRY_XY[1])
        target_room = self._script()._create_room(target, self.npc)
        with patch.object(
            target_room, "at_pre_object_receive", return_value=False
        ), patch.object(self.npc, "msg") as npc_msg:
            self._exit("east").at_traverse(self.npc, self.npc.location)

        self.assertIsNone(self.char1.location)
        self.assertEqual(self.other.location.coordinates, target)
        expected = FOLLOW_LOST_MESSAGE.format(names=self.char1.key)
        self.assertEqual(follow_lines(npc_msg), [expected])

        release_possession(self.char1, npc=self.npc, reason="handback")

        self.assertIsNotNone(self.char1.location)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(self.npc.location.coordinates, target)
        self.assertIs(self.session.puppet, self.char1)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)


class PossessedSettlementTests(PossessedFollowTestCase):
    def setUp(self):
        super().setUp()
        self.door = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )

    def _failing_advance(self, *args, **kwargs):
        raise RuntimeError("clock advance failed")

    def _assert_whole_party_in_room(self, room):
        for member in (self.npc, self.char1, self.other):
            self.assertIs(member.location, room)
            self.assertIn(member, room.contents)
        other = self.room2 if room is self.room1 else self.room1
        for member in (self.npc, self.char1, self.other):
            self.assertNotIn(member, other.contents)

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-"
        "relocation-and-reconciles-every-evennia-cache-surface"
    )
    def test_clock_failure_before_follow_returns_the_whole_party(self):
        before = self._tick()
        possession_before = deepcopy(self.char1.db.possession)

        with patch.object(WorldClock, "advance", self._failing_advance):
            with self.assertRaises(RuntimeError):
                self.door.at_traverse(self.npc, self.room2)

        self._assert_whole_party_in_room(self.room1)
        self.assertEqual(self._tick(), before)
        self.assertEqual(self.char1.db.possession, possession_before)
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))
        self.assertIsNone(self.char1.attributes.get("map_knowledge"))

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-"
        "relocation-and-reconciles-every-evennia-cache-surface"
    )
    def test_failure_after_follow_returns_the_whole_party_and_its_surfaces(self):
        import world.rules.party as party_module

        real_follow = party_module.follow_companions

        def follow_then_raise(*args, **kwargs):
            real_follow(*args, **kwargs)
            raise RuntimeError("post-follow step failed")

        before = self._tick()
        possession_before = deepcopy(self.char1.db.possession)

        with patch("world.rules.party.follow_companions", side_effect=follow_then_raise):
            with self.assertRaises(RuntimeError):
                self.door.at_traverse(self.npc, self.room2)

        self._assert_whole_party_in_room(self.room1)
        self.assertEqual(self._tick(), before)
        self.assertEqual(self.char1.db.possession, possession_before)
        self.assertEqual(int(self.npc.db.possessed_by), int(self.char1.pk))
        self.assertIsNone(self.char1.attributes.get("map_knowledge"))
        self.assertEqual(self.char1.attributes.get("quest_log"), [])

    @covers_requirement(
        "companion-possession-transition::normal-possession-release-preserves-the-"
        "companion-s-room-presence"
    )
    def test_release_after_a_possessed_walk_leaves_both_in_the_destination(self):
        self.door.at_traverse(self.npc, self.room2)

        release_possession(self.char1, npc=self.npc, reason="handback")

        self.assertIs(self.session.puppet, self.char1)
        self.assertIs(self.char1.location, self.room2)
        self.assertIs(self.npc.location, self.room2)
        self.assertIn(self.char1, self.room2.contents)
        self.assertIn(self.npc, self.room2.contents)
        self.assertIsNone(self.char1.db.possession)
        self.assertIsNone(self.npc.db.possessed_by)
        self.assertFalse(self.npc.attributes.has("prelogout_location"))
        self.assertNotIn("呆立入神", self.char1.get_display_name(self.other))


class PossessedWildernessSettlementTests(PossessedFollowTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_all()
        sync_grid()
        sync_wilderness()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]
        self.char1.location = self.east_gate
        for npc in (self.npc, self.other):
            npc.location = self.east_gate

    def _script(self):
        return WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    def _bookkeeping(self):
        script = self._script()
        return (
            dict(script.db.itemcoordinates or {}),
            dict(script.db.rooms or {}),
            list(script.db.unused_rooms or []),
        )

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-"
        "relocation-and-reconciles-every-evennia-cache-surface"
    )
    def test_falsy_wilderness_return_compensates_the_whole_party(self):
        from world.rules.movement_settlement import settle_movement

        self.gate.at_traverse(self.npc, self.east_gate)
        source_room = self.npc.location
        current = self._script().itemcoordinates[self.npc]
        bookkeeping = self._bookkeeping()
        before = get_world_clock().tick
        possession_before = deepcopy(self.char1.db.possession)

        def traverse():
            self.assertTrue(self.npc.move_to(self.east_gate, quiet=True))
            follow_companions(
                self.npc,
                source_room,
                destination=self.east_gate,
                wilderness_source_coordinates=current,
            )
            return False

        result = settle_movement(
            self.npc,
            source_room,
            destination=self.east_gate,
            wilderness_source_coordinates=current,
            traverse=traverse,
        )

        self.assertFalse(result)
        for member in (self.npc, self.char1, self.other):
            self.assertEqual(member.location.coordinates, current)
        self.assertEqual(self._script().itemcoordinates.get(self.char1), current)
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(self.char1.db.possession, possession_before)
        restored_bookkeeping = self._bookkeeping()
        self.assertEqual(restored_bookkeeping[0], bookkeeping[0])
        self.assertEqual(restored_bookkeeping[1], bookkeeping[1])
        self.assertEqual(restored_bookkeeping[2], bookkeeping[2])
        visited = {visit.node_id for visit in parse_knowledge(self.char1)}
        self.assertIn(f"wild:{WILDERNESS_NAME}:{current[0]}:{current[1]}", visited)

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-"
        "relocation-and-reconciles-every-evennia-cache-surface"
    )
    def test_teleport_to_a_wilderness_room_registers_the_body(self):
        from world.rules.movement_settlement import settle_relocation

        self.gate.at_traverse(self.npc, self.east_gate)
        target = (ENTRY_XY[0] + 2, ENTRY_XY[1])
        target_room = self._script()._create_room(target, self.npc)
        possession_before = deepcopy(self.char1.db.possession)

        settle_relocation(self.npc, target_room)

        self.assertIs(self.npc.location, target_room)
        self.assertEqual(self.char1.location.coordinates, target)
        self.assertEqual(self.other.location.coordinates, target)
        self.assertEqual(self._script().itemcoordinates.get(self.char1), target)
        self.assertEqual(self.char1.db.possession, possession_before)

    @covers_requirement(
        "movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-"
        "relocation-and-reconciles-every-evennia-cache-surface"
    )
    def test_failed_teleport_to_a_wilderness_room_compensates_the_body(self):
        from world.rules.movement_settlement import settle_relocation

        self.gate.at_traverse(self.npc, self.east_gate)
        target = (ENTRY_XY[0] + 2, ENTRY_XY[1])
        target_room = self._script()._create_room(target, self.npc)
        bookkeeping = self._bookkeeping()
        possession_before = deepcopy(self.char1.db.possession)
        import world.rules.party as party_module

        real_follow = party_module.follow_companions

        def follow_then_raise(*args, **kwargs):
            real_follow(*args, **kwargs)
            raise RuntimeError("post-follow step failed")

        with patch("world.rules.party.follow_companions", side_effect=follow_then_raise):
            with self.assertRaises(RuntimeError):
                settle_relocation(self.npc, target_room)

        for member in (self.npc, self.char1, self.other):
            self.assertEqual(member.location.coordinates, ENTRY_XY)
        self.assertEqual(self._script().itemcoordinates.get(self.char1), ENTRY_XY)
        self.assertEqual(self.char1.db.possession, possession_before)
        restored = self._bookkeeping()
        self.assertEqual(restored[0], bookkeeping[0])
        self.assertEqual(restored[1], bookkeeping[1])
        self.assertEqual(restored[2], bookkeeping[2])


if __name__ == "__main__":
    import unittest

    unittest.main()
