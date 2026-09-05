"""Integration tests for the relocation action-options trigger.

The trigger registers through ``transaction.on_commit`` in the player
typeclass's post-move lifecycle (``PlayerCharacter.at_post_move``), so every
successful hooks-enabled relocation — ordinary exit traversal and a direct
``move_to()`` alike — shares one observer, and rollback compensations with
hooks disabled never fire it. These tests pin the contract through the real
movement paths: exactly one fire-and-forget scheduling call with the live
watchers on a committed success, silence for NPC movement, silence for
``move_hooks=False`` moves (the compensation surface), silence on a failed or
rolled-back settlement, and an unchanged movement result.
``captureOnCommitCallbacks`` executes the registered callback immediately,
mirroring a committed outer transaction.
"""

from unittest.mock import patch

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock

from server import option_proposal_service as service
from web.webclient.presentation import watchers
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry

MOVE = CLOCK_YAML["command_defaults"]["move"]


def _make_session(sessionhandler, sessid, puppet):
    session = ServerSession()
    session.init_session("webclient/websocket", ("localhost", 9999), sessionhandler)
    session.sessid = sessid
    session.protocol_key = "webclient/websocket"
    session.puppet = puppet
    session.logged_in = True
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = str(getattr(puppet, "pk", ""))
    sessionhandler[session.sessid] = session
    puppet.sessions.add(session)
    return session


class RoomEntryTriggerTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        watchers.clear_watchers()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        get_world_clock()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def _puppeted_watcher(self, sessid=41):
        session = _make_session(self.sessionhandler, sessid, self.char1)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        return session

    def _traverse(self, exit_obj, traverser=None):
        """Traverse through the settlement boundary, then run the registered
        on_commit trigger as a committed transaction would."""
        traverser = traverser or self.char1
        with self.captureOnCommitCallbacks(execute=True):
            exit_obj.at_traverse(traverser, self.room2)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_possessed_npc_traversal_schedules_a_generation(self):
        """Scenario: A possessed NPC traversal schedules a generation."""
        npc = create_object(NPC, key="附身NPC", location=self.room1)
        npc.db.possessed_by = self.char1.pk
        session = _make_session(self.sessionhandler, 43, npc)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch.object(service, "schedule_action_options") as schedule:
            self._traverse(exit_obj, traverser=npc)
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], npc)
        self.assertIs(npc.location, self.room2)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_successful_plain_exit_schedules_exactly_one_call_with_live_watchers(self):
        session = self._puppeted_watcher()
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch.object(service, "schedule_action_options") as schedule:
            before = get_world_clock().tick
            self._traverse(exit_obj)
            self.assertEqual(schedule.call_count, 1)
            call = schedule.call_args
            self.assertIs(call.kwargs["watchers"][0][0], session)
            self.assertEqual(
                call.kwargs["watchers"],
                watchers.watchers_for(self.char1),
                "the hook passes the registry's live watchers untouched",
            )
            self.assertIs(call.args[0], self.char1)
            self.assertIsNone(call.kwargs.get("client"))
            self.assertIs(self.char1.location, self.room2)
            self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("action-options-trigger-hooks::every-trigger-is-fire-and-forget-non-raising-and-non-mutating")
    def test_scheduling_call_keeps_the_movement_result_unchanged(self):
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)

        def _scheduling_raises(*args, **kwargs):
            raise RuntimeError("transport unavailable")

        with patch.object(service, "schedule_action_options", side_effect=_scheduling_raises):
            before = get_world_clock().tick
            self._traverse(exit_obj)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_failed_clock_charge_schedules_nothing(self):
        def _failing_advance(clock, *args, **kwargs):
            raise RuntimeError("clock advance failed")

        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            with patch.object(service, "schedule_action_options") as schedule:
                with self.assertRaises(RuntimeError):
                    self._traverse(exit_obj)
                schedule.assert_not_called()
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_failed_clock_charge_on_possessed_npc_compensates_location_and_clock(self):
        """When clock advance fails for a possessed NPC, rollback compensates location and clock."""
        def _failing_advance(clock, *args, **kwargs):
            raise RuntimeError("clock advance failed")

        npc = create_object(NPC, key="附身NPC_fail", location=self.room1)
        npc.db.possessed_by = self.char1.pk
        session = _make_session(self.sessionhandler, 44, npc)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            with patch.object(service, "schedule_action_options") as schedule:
                with self.assertRaises(RuntimeError):
                    self._traverse(exit_obj, traverser=npc)
                schedule.assert_not_called()
        self.assertIs(npc.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_outer_transaction_rollback_never_fires_the_trigger(self):
        """The trigger is registered through on_commit: an outer transaction
        that rolls back after a successful traversal must never schedule."""
        from django.db import transaction

        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch.object(service, "schedule_action_options") as schedule:
            with transaction.atomic():
                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    exit_obj.at_traverse(self.char1, self.room2)
                self.assertNotEqual(
                    callbacks, [], "a successful move registers the trigger"
                )
                transaction.set_rollback(True)
            schedule.assert_not_called()
        self.assertIs(self.char1.location, self.room2)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_npc_traversal_schedules_nothing(self):
        npc = create_object(NPC, key="路人", location=self.room1)
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch.object(service, "schedule_action_options") as schedule:
            self._traverse(exit_obj, traverser=npc)
            schedule.assert_not_called()
        self.assertIs(npc.location, self.room2)

    @covers_requirement("action-options-trigger-hooks::room-entry-triggers-a-proposal-on-deterministic-movement-success")
    def test_unpuppeted_player_schedules_nothing(self):
        session = _make_session(self.sessionhandler, 42, self.char1)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        self.char1.account = None
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch.object(service, "schedule_action_options") as schedule:
            before = get_world_clock().tick
            self._traverse(exit_obj)
            schedule.assert_not_called()
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_direct_move_to_relocation_schedules_exactly_one_call(self):
        """A direct ``move_to()`` (no exit involved) shares the post-move
        lifecycle observer with ordinary traversal: one scheduling call with
        the live watchers after the move commits."""
        session = self._puppeted_watcher()
        with patch.object(service, "schedule_action_options") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                moved = self.char1.move_to(self.room2)
            self.assertTrue(moved)
            self.assertEqual(schedule.call_count, 1)
            call = schedule.call_args
            self.assertIs(call.args[0], self.char1)
            self.assertEqual(
                call.kwargs["watchers"],
                watchers.watchers_for(self.char1),
            )
            self.assertIs(call.kwargs["watchers"][0][0], session)
        self.assertIs(self.char1.location, self.room2)

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_npc_direct_move_to_schedules_nothing(self):
        npc = create_object(NPC, key="路人", location=self.room1)
        with patch.object(service, "schedule_action_options") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                moved = npc.move_to(self.room2)
            self.assertTrue(moved)
            schedule.assert_not_called()
        self.assertIs(npc.location, self.room2)

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_move_hooks_disabled_move_schedules_nothing(self):
        """Rollback compensations move with ``move_hooks=False``; the
        post-move lifecycle never fires there, so compensation stays silent."""
        with patch.object(service, "schedule_action_options") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                moved = self.char1.move_to(self.room2, move_hooks=False)
            self.assertTrue(moved)
            schedule.assert_not_called()
        self.assertIs(self.char1.location, self.room2)

    @covers_requirement("action-options-trigger-service::all-committed-player-relocations-and-terminal-combat-returns-trigger-options")
    def test_creation_pending_relocation_is_a_service_level_no_op(self):
        """An account-owned player still in creation has no exploration
        situation: the relocation trigger fires but the service's exploration
        gate resolves it to a logged no-op, never touching session state."""
        session = self._puppeted_watcher()
        self.char1.creation_pending = True
        with self.captureOnCommitCallbacks(execute=True):
            moved = self.char1.move_to(self.room2)
        self.assertTrue(moved)
        self.assertIs(self.char1.location, self.room2)
        self.assertIsNone(session.ndb.options_state)
