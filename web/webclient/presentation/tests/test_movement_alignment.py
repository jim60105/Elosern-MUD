"""Committed movement alignment: authoritative identity and checkpoints.

Focused behaviour tests for the movement slice of the incremental
synchronization design:

- the authoritative area/instance identity reader: grid map keys, the
  registered wilderness map (pooled rooms and bare coordinates are not
  identities), coordinate-free interior components, instance components with
  their spawn root and ``scene_identity``, and the conservative ``None`` for
  anything untrustworthy;
- the committed checkpoint fact of a real relocation through the text command
  path and the ``explore.move`` graphical path, its absence for refused,
  rolled-back, compensated and same-area moves, and the single emission of the
  settlement owner even though the player's own move hooks also run;
- the watcher outcome: one freshly rendered complete snapshot per lawful
  watcher instead of the settlement delta, a deliberately stale panel repaired
  by the checkpoint, an old epoch publishing nothing, Telnet receiving no
  graphical state, and an unopened on-demand map presenter never running.

Each test that establishes a clause of a requirement carries the requirement's
canonical ``capability::requirement`` id from ``tools.spec_traceability``.
"""

from types import SimpleNamespace
from unittest import mock
import unittest

from evennia.contrib.grid.xyzgrid.xyzroom import (
    MAP_X_TAG_CATEGORY,
    MAP_Y_TAG_CATEGORY,
    MAP_Z_TAG_CATEGORY,
)
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.actions.node_ids import node_id_for_location
from web.webclient.presentation import alignment
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.ingress import (
    build_presentation_context,
    build_production_registry,
)
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from web.webclient.presentation.watchers import (
    clear_watchers,
    register_watcher,
)
from world.maps.area_identity import (
    is_alignment_boundary,
    read_alignment_identity,
    room_component,
)
from world.maps.map_data import KNOWN_GRID_MAP_KEYS
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.movement_settlement import settle_relocation
from world.rules.presentation_events import (
    AlignmentIdentity,
    clear_alignment_observers,
    register_alignment_observer,
)

from .test_publication_settlements import FakeSession, QueuedScheduler, _coordinator
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


def _actor(location):
    """A minimal actor: the identity reader only reads ``location``."""
    return SimpleNamespace(pk=1, key="actor", location=location)


def _grid_room(key, coordinates, map_key):
    """One synthetic grid room carrying the xyzgrid coordinate tags."""
    room = create_object(GridRoom, key=key, location=None)
    x, y = coordinates
    room.tags.add(str(x), category=MAP_X_TAG_CATEGORY)
    room.tags.add(str(y), category=MAP_Y_TAG_CATEGORY)
    room.tags.add(str(map_key), category=MAP_Z_TAG_CATEGORY)
    return room


def _terrain_room(key, coordinates, wilderness_name=WILDERNESS_NAME):
    """One synthetic pooled terrain room bound to a wilderness script."""
    room = create_object(TerrainRoom, key=key, location=None)
    room.ndb.wildernessscript = (
        SimpleNamespace(key=wilderness_name) if wilderness_name else None
    )
    room.ndb.active_coordinates = coordinates
    return room


def _instance_room(key, origin, scene_identity):
    room = create_object(InstanceRoom, key=key, location=None)
    room.db.origin_room = origin
    room.scene_identity = scene_identity
    return room


def _join(source, destination, key="passage"):
    return create_object(Exit, key=key, location=source, destination=destination)


class _FactRecorder:
    """Collect every committed alignment fact the producers emit."""

    def __init__(self):
        self.facts = []

    def __call__(self, fact):
        self.facts.append(fact)


# ---------------------------------------------------------------------------
# Authoritative identity.
# ---------------------------------------------------------------------------


class AreaIdentityTests(EvenniaTest):
    """Identity comes from committed map/instance facts, never labels."""

    def setUp(self):
        super().setUp()
        self.room1.key = "同名房間"
        self.room1.save()
        self.room2.key = "同名房間"
        self.room2.save()

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_grid_identity_is_the_map_key_not_the_label_or_coordinates(self):
        first = _grid_room("同名房間", (10, 20), "map_a")
        same_map = _grid_room("同名房間", (11, 20), "map_a")
        other_map = _grid_room("同名房間", (10, 20), "map_b")

        a = read_alignment_identity(_actor(first))
        self.assertEqual(a, AlignmentIdentity(layer="grid", area_key="map_a"))
        self.assertEqual(read_alignment_identity(_actor(same_map)), a)
        self.assertFalse(is_alignment_boundary(a, read_alignment_identity(_actor(same_map))))
        self.assertTrue(
            is_alignment_boundary(a, read_alignment_identity(_actor(other_map))),
            "the same display label on another map is another area",
        )

    def test_a_grid_room_without_a_map_key_has_no_identity(self):
        room = create_object(GridRoom, key="同名房間", location=None)

        self.assertIsNone(read_alignment_identity(_actor(room)))
        self.assertTrue(is_alignment_boundary(None, None), "unknown is conservative")

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_pooled_wilderness_reuse_and_object_identity_are_not_boundaries(self):
        room = _terrain_room("荒野", (3, 4))
        other = _terrain_room("荒野", (90, 91))

        captured = read_alignment_identity(_actor(room))
        self.assertEqual(
            captured, AlignmentIdentity(layer="wilderness", area_key=WILDERNESS_NAME)
        )
        self.assertEqual(read_alignment_identity(_actor(other)), captured)
        # The same pooled room object now serves another cell; the captured
        # value is a copy, so neither the coordinate change nor the reused
        # object changes the area it belongs to.
        room.ndb.active_coordinates = (5, 6)
        self.assertEqual(read_alignment_identity(_actor(room)), captured)
        self.assertEqual(captured, read_alignment_identity(_actor(room)))

    def test_a_terrain_room_without_its_wilderness_map_has_no_identity(self):
        room = _terrain_room("荒野", (3, 4), wilderness_name=None)

        self.assertIsNone(read_alignment_identity(_actor(room)))

    def test_connected_interior_rooms_are_one_component(self):
        connected = read_alignment_identity(_actor(self.room2))
        self.assertEqual(connected, read_alignment_identity(_actor(self.room1)))
        self.assertEqual(connected.layer, "interior")
        detached = create_object(Room, key="同名房間", location=None)
        self.assertNotEqual(read_alignment_identity(_actor(detached)), connected)
        rooms, exits = room_component(self.room1, lambda room: isinstance(room, Room))
        self.assertEqual(set(rooms), {int(self.room1.pk), int(self.room2.pk)})
        self.assertEqual([int(item.pk) for item in exits], [int(self.exit.pk)])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_instance_identity_uses_the_component_root_and_scene_identity(self):
        first = _instance_room("洞窟", self.room1, "instance:first")
        replacement = _instance_room("洞窟", self.room1, "instance:second")

        a = read_alignment_identity(_actor(first))
        b = read_alignment_identity(_actor(replacement))
        self.assertEqual(a.layer, "instance")
        self.assertEqual(a.area_key, f"instance:{int(first.pk)}")
        self.assertEqual(a.instance_key, (int(first.pk), "instance:first"))
        self.assertNotEqual(a, b, "an equal-looking replacement is another scene")

    def test_instance_component_of_one_origin_is_one_identity(self):
        root = _instance_room("洞窟", self.room1, "instance:root")
        inner = _instance_room("洞窟", self.room1, "instance:root")
        _join(root, inner)

        self.assertEqual(
            read_alignment_identity(_actor(inner)),
            read_alignment_identity(_actor(root)),
        )

    def test_connected_instance_rooms_of_different_origins_are_untrustworthy(self):
        first = _instance_room("洞窟", self.room1, "instance:first")
        second = _instance_room("洞窟", self.room2, "instance:second")
        _join(first, second)

        self.assertIsNone(
            read_alignment_identity(_actor(first)),
            "connectivity alone never establishes one instance",
        )
        self.assertIsNone(read_alignment_identity(_actor(second)))

    def test_one_origin_with_different_scene_identities_is_untrustworthy(self):
        first = _instance_room("洞窟", self.room1, "instance:first")
        second = _instance_room("洞窟", self.room1, "instance:second")
        _join(first, second)

        # The same origin can spawn several instances, so its identity alone
        # never joins two scenes: the component has no comparable identity and
        # must never inherit the root's.
        self.assertIsNone(read_alignment_identity(_actor(first)))
        self.assertIsNone(read_alignment_identity(_actor(second)))

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_an_unknown_position_has_no_identity(self):
        self.assertIsNone(read_alignment_identity(_actor(None)))
        self.assertIsNone(read_alignment_identity(_actor(SimpleNamespace())))

    @covers_requirement(
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner"
    )
    def test_identity_never_runs_a_map_presenter(self):
        with mock.patch(
            "web.webclient.presentation.area_map.area_map_presenter"
        ) as presenter:
            read_alignment_identity(_actor(self.room1))
            read_alignment_identity(_actor(_grid_room("同名房間", (1, 1), "map_a")))
        presenter.assert_not_called()


# ---------------------------------------------------------------------------
# Committed facts through the deterministic owner.
# ---------------------------------------------------------------------------


class CommittedMovementFactTests(EvenniaTest):
    """The settlement owner publishes one committed fact per boundary."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room
    exit_typeclass = Exit

    def setUp(self):
        super().setUp()
        self.room1.key = "同名房間"
        self.room1.save()
        self.room2.key = "同名房間"
        self.room2.save()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        clear_alignment_observers()
        self.recorder = _FactRecorder()
        register_alignment_observer(self.recorder)
        self.addCleanup(clear_alignment_observers)
        from world.rules.clock import get_world_clock

        get_world_clock()

    def _instance_destination(self, key="洞窟"):
        destination = _instance_room(key, self.room1, "instance:test-destination")
        return destination, create_object(
            Exit, key="door", location=self.room1, destination=destination
        )

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_text_traversal_into_an_instance_emits_one_boundary_fact(self):
        destination, exit_obj = self._instance_destination()

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)

        self.assertIs(self.char1.location, destination)
        self.assertEqual(len(self.recorder.facts), 1, "the settlement emits exactly once")
        fact = self.recorder.facts[0]
        self.assertEqual(fact.cause, "movement_boundary")
        self.assertEqual(fact.actor_id, int(self.char1.pk))
        self.assertEqual(len(fact.group_id), 32)
        self.assertEqual(fact.source.layer, "interior")
        self.assertEqual(fact.destination.layer, "instance")

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_same_area_text_move_emits_no_fact(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(self.exit.key, session=self.session)

        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_refused_traversal_emits_no_fact(self):
        destination, exit_obj = self._instance_destination()
        with mock.patch(
            "world.rules.combat_session.is_in_active_session", return_value=True
        ):
            with self.captureOnCommitCallbacks(execute=True):
                self.char1.execute_cmd(exit_obj.key, session=self.session)

        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_rolled_back_settlement_emits_no_fact(self):
        destination, exit_obj = self._instance_destination()
        with mock.patch(
            "world.rules.party.follow_companions",
            side_effect=RuntimeError("post-move step failed"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    exit_obj.at_traverse(self.char1, destination)

        self.assertIs(self.char1.location, self.room1, "the relocation compensated")
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_an_unreadable_destination_identity_still_aligns(self):
        destination, exit_obj = self._instance_destination()
        # A missing scene identity makes the destination untrustworthy.
        destination.scene_identity = None

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)

        self.assertEqual(len(self.recorder.facts), 1)
        self.assertIsNone(self.recorder.facts[0].destination)

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_mixed_instance_component_aligns_conservatively(self):
        destination, exit_obj = self._instance_destination()
        # A connected sibling spawned from the same origin with another scene
        # identity makes the whole component non-comparable.
        _join(destination, _instance_room("洞窟", self.room1, "instance:sibling"))

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)

        self.assertIs(self.char1.location, destination)
        self.assertEqual(len(self.recorder.facts), 1)
        self.assertIsNone(self.recorder.facts[0].destination)

    @covers_requirement(
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner"
    )
    def test_the_settlement_owner_does_not_duplicate_the_player_hook_fact(self):
        destination, exit_obj = self._instance_destination()
        from world.rules import movement_settlement

        with mock.patch.object(
            movement_settlement,
            "note_direct_move_start",
            wraps=movement_settlement.note_direct_move_start,
        ) as start:
            with self.captureOnCommitCallbacks(execute=True):
                self.char1.execute_cmd(exit_obj.key, session=self.session)

        self.assertEqual(len(self.recorder.facts), 1)
        self.assertTrue(start.called, "the hook runs and stands down")
        self.assertIs(self.char1.location, destination)

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_direct_player_move_publishes_its_own_boundary(self):
        destination = _instance_room("洞窟", self.room2, "instance:direct")

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.move_to(destination)

        self.assertIs(self.char1.location, destination)
        self.assertEqual(len(self.recorder.facts), 1)
        fact = self.recorder.facts[0]
        self.assertEqual(fact.source.layer, "interior")
        self.assertEqual(fact.destination.layer, "instance")

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_an_npc_move_uses_the_settlement_owner(self):
        npc = create_object(NPC, key="同伴", location=self.room1)
        destination = create_object(Room, key="洞窟", location=None)

        with self.captureOnCommitCallbacks(execute=True):
            npc.move_to(destination)

        self.assertIs(npc.location, destination)
        self.assertEqual([fact.actor_id for fact in self.recorder.facts], [int(npc.pk)])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_console_relocation_between_interiors_is_a_boundary(self):
        destination = create_object(Room, key="同名房間", location=None)
        with self.captureOnCommitCallbacks(execute=True):
            settle_relocation(self.char1, destination)

        self.assertIs(self.char1.location, destination)
        self.assertEqual(len(self.recorder.facts), 1)
        self.assertNotEqual(
            self.recorder.facts[0].source, self.recorder.facts[0].destination
        )


# ---------------------------------------------------------------------------
# Watcher outcome: one fresh complete snapshot instead of the delta.
# ---------------------------------------------------------------------------


class WatcherAlignmentTests(EvenniaTest):
    """Every lawful watcher receives one fresh snapshot for the checkpoint."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room
    exit_typeclass = Exit

    def setUp(self):
        super().setUp()
        import evennia

        self.room1.key = "同名房間"
        self.room1.save()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        clear_alignment_observers()
        clear_watchers()
        alignment.connect_alignment_observer()
        self.addCleanup(clear_alignment_observers)
        self.addCleanup(clear_watchers)
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.registry = build_production_registry()
        self.sessions = []
        self.schedulers = []
        for index in (0, 1):
            session = FakeSession(sessid=50 + index)
            session.puppet = self.char1
            scheduler = QueuedScheduler()
            _coordinator(session, self.registry, scheduler=scheduler)
            self.sessions.append(session)
            self.schedulers.append(scheduler)
        self.telnet = FakeSession(sessid=59)
        self.telnet.protocol_key = "telnet"
        self.telnet.puppet = self.char1
        _coordinator(self.telnet, self.registry, scheduler=QueuedScheduler())
        self.sessionhandler = mock.patch.object(
            evennia.SESSION_HANDLER,
            "get_sessions",
            return_value=[*self.sessions, self.telnet],
        )
        self.sessionhandler.start()
        self.addCleanup(self.sessionhandler.stop)

    def _prime(self):
        for session, scheduler in zip(self.sessions, self.schedulers):
            coordinator = session.ndb.elosern_coordinator
            coordinator.full_snapshot(build_presentation_context(session, self.char1))
            register_watcher(session)
            scheduler.run()
            session.sent.clear()
        register_watcher(self.telnet)
        self.telnet.sent.clear()

    def _drain(self):
        for scheduler in self.schedulers:
            scheduler.run()

    def _move_envelope(self, exit_obj):
        coordinator = self.sessions[0].ndb.elosern_coordinator
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "req-move",
            "base_revision": coordinator.revision,
            "action_id": "explore.move",
            "payload": {
                "exit_ref": str(int(exit_obj.pk)),
                "current_node": node_id_for_location(self.char1.location),
            },
        }

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment",
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner",
    )
    def test_text_boundary_move_publishes_one_snapshot_and_no_delta(self):
        self._prime()
        destination = _instance_room("同名房間", self.room1, "instance:watcher")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=destination
        )
        before = [
            session.ndb.elosern_coordinator.revision for session in self.sessions
        ]

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)
        self._drain()

        for session, previous in zip(self.sessions, before):
            self.assertEqual(session.names(), ["ui_snapshot"])
            self.assertEqual(session.frames("ui_update"), [])
            self.assertEqual(
                session.frames("ui_snapshot")[0]["revision"], previous + 1
            )
        self.assertEqual(self.telnet.sent, [], "Telnet receives no graphical state")

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment",
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner",
    )
    def test_graphical_boundary_move_publishes_one_snapshot_then_its_result(self):
        self._prime()
        # Two registered grid maps: the same display label on another map key
        # is the authoritative boundary a coordinate or label cannot express.
        maps = sorted(KNOWN_GRID_MAP_KEYS)
        self.assertGreaterEqual(len(maps), 2, "two registered settlement maps")
        source = _grid_room("同名房間", (0, 0), maps[0])
        destination = _grid_room("同名房間", (0, 0), maps[1])
        self.char1.location = source
        exit_obj = create_object(
            Exit, key="north", location=source, destination=destination
        )
        for session, scheduler in zip(self.sessions, self.schedulers):
            coordinator = session.ndb.elosern_coordinator
            coordinator.full_snapshot(
                build_presentation_context(session, self.char1)
            )
            scheduler.run()
            session.sent.clear()

        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                self.sessions[0],
                self.char1,
                self._move_envelope(exit_obj),
                build_production_action_registry(),
                self.registry,
            )
        self._drain()

        self.assertIs(self.char1.location, destination)
        session = self.sessions[0]
        self.assertEqual(session.names(), ["ui_snapshot", "ui_action_result"])
        snapshot = session.frames("ui_snapshot")[0]
        result = session.frames("ui_action_result")[0]
        self.assertEqual(result["presentation_revision"], snapshot["revision"])
        self.assertEqual(session.frames("ui_update"), [])

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_same_area_graphical_move_stays_incremental(self):
        self._prime()
        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                self.sessions[0],
                self.char1,
                self._move_envelope(self.exit),
                build_production_action_registry(),
                self.registry,
            )
        self._drain()

        self.assertIs(self.char1.location, self.room2)
        session = self.sessions[0]
        self.assertNotIn("ui_snapshot", session.names())
        self.assertIn("ui_action_result", session.names())

    @covers_requirement(
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner"
    )
    def test_a_companion_cleanup_push_coalesces_with_the_checkpoint(self):
        from world.rules.party import join_party

        companion = create_object(NPC, key="同伴", location=self.room1)
        companion.traits.add("hp", trait_type="gauge", base=500, min=0, rate=0)
        join_party(companion, self.char1)
        self._prime()
        destination = _instance_room("同名房間", self.room1, "instance:companion")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=destination
        )

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)
        self._drain()

        self.assertIs(self.char1.location, destination)
        self.assertIs(companion.location, destination, "the companion followed")
        for session in self.sessions:
            # The follower's dialogue-availability cleanup push and the
            # movement checkpoint share one group: one final snapshot, never a
            # preceding settlement delta.
            self.assertEqual(session.names(), ["ui_snapshot"])
            self.assertEqual(session.frames("ui_update"), [])

    @covers_requirement(
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner"
    )
    def test_a_retired_epoch_checkpoint_publishes_nothing(self):
        self._prime()
        destination = _instance_room("同名房間", self.room1, "instance:retired")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=destination
        )

        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)
        for session in self.sessions:
            # A puppet replacement retires the pending sequence before the
            # reactor's next turn, so the queued checkpoint never publishes.
            session.ndb.elosern_coordinator.reset()
        self._drain()

        for session in self.sessions:
            self.assertEqual(session.sent, [])


# ---------------------------------------------------------------------------
# Complete alignment: the checkpoint repairs a deliberately missed panel.
# ---------------------------------------------------------------------------


class CheckpointCompletenessTests(EvenniaTest):
    """A checkpoint renders every eager panel and never loads an unopened map."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room
    exit_typeclass = Exit

    def setUp(self):
        super().setUp()
        import evennia

        self.room1.key = "同名房間"
        self.room1.save()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        clear_alignment_observers()
        clear_watchers()
        alignment.connect_alignment_observer()
        self.addCleanup(clear_alignment_observers)
        self.addCleanup(clear_watchers)
        from world.rules.clock import get_world_clock

        get_world_clock()
        self.state = {"status": 1, "party": "one"}
        self.map_calls = []
        registry = PresentationRegistry("movement-alignment")
        for name in ("status", "party"):
            registry.register(
                PresenterSpec(
                    name=name,
                    schema_version=1,
                    unavailable_reason=("missing_data", "無法讀取"),
                    presenter=(
                        lambda context, _name=name: {
                            "available": True,
                            "value": self.state[_name],
                        }
                    ),
                )
            )
        registry.register(
            PresenterSpec(
                name="area_map",
                schema_version=1,
                unavailable_reason=("missing_data", "無法讀取"),
                presenter=self._unopened_map,
                on_demand=True,
            )
        )
        self.web = FakeSession(sessid=70)
        self.web.puppet = self.char1
        self.scheduler = QueuedScheduler()
        self.coordinator = PresentationCoordinator(
            self.web,
            registry,
            calendar_provider=lambda: SimpleNamespace(
                year=1204,
                season_index=2,
                season_name="仲夏",
                day_in_season=17,
                hour=14,
                minute=30,
                second=5,
            ),
            mode_provider=lambda context: "exploration",
            scheduler=self.scheduler,
        )
        self.web.ndb.elosern_coordinator = self.coordinator
        self.sessionhandler = mock.patch.object(
            evennia.SESSION_HANDLER, "get_sessions", return_value=[self.web]
        )
        self.sessionhandler.start()
        self.addCleanup(self.sessionhandler.stop)
        register_watcher(self.web)

    def _unopened_map(self, context):
        self.map_calls.append(context)
        return {"available": False}

    def _prime(self):
        self.coordinator.full_snapshot(
            build_presentation_context(self.web, self.char1)
        )
        self.scheduler.run()
        self.web.sent.clear()

    @covers_requirement(
        "webclient-event-alignment::"
        "one-serialized-settlement-has-one-final-publication-owner"
    )
    def test_a_checkpoint_restores_a_deliberately_omitted_panel(self):
        self._prime()
        self.state["status"] = 2
        # The client is told only about ``party``; the changed status panel is
        # deliberately left out of that ordinary publication.
        self.coordinator.enqueue_publication(
            lambda: build_presentation_context(self.web, self.char1),
            candidate_panels={"party": {"available": True, "value": "one"}},
        )
        self.scheduler.run()
        self.assertFalse(
            any(
                frame.get("panels", {}).get("status")
                for frame in self.web.frames("ui_update")
            ),
            "the omitted candidate never reaches the client",
        )

        destination = _instance_room("洞窟", self.room1, "instance:repair")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=destination
        )
        self.web.sent.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.char1.execute_cmd(exit_obj.key, session=self.session)
        self.scheduler.run()

        snapshots = self.web.frames("ui_snapshot")
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["panels"]["status"]["value"], 2)
        self.assertEqual(self.web.frames("ui_update"), [])
        self.assertEqual(self.map_calls, [], "an unopened map presenter never runs")

    @covers_requirement(
        "webclient-event-alignment::"
        "committed-area-and-instance-transitions-replace-deltas-with-fresh-alignment"
    )
    def test_a_failed_move_publishes_no_frame(self):
        self._prime()
        destination = _instance_room("洞窟", self.room1, "instance:failed")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=destination
        )
        with mock.patch(
            "world.rules.party.follow_companions",
            side_effect=RuntimeError("post-move step failed"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    exit_obj.at_traverse(self.char1, destination)
        self.scheduler.run()

        self.assertEqual(self.web.sent, [])
        self.assertEqual(self.map_calls, [])


if __name__ == "__main__":
    unittest.main()
