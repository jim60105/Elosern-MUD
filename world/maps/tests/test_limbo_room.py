"""Tests for the localized starting room (Limbo): its identity, its hard
entry gate and the rule that it owns no exits (limbo-room and
limbo-one-way-gates capabilities)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit
from typeclasses.rooms import LimboRoom, Room
from world.maps.bootstrap import sync_limbo
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import (
    publish_shipped_geography,
    selected_startup_settlements,
)


publish_shipped_geography()


class LimboRoomTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _limbo(self):
        found = search_object(LIMBO_KEY, exact=True)
        return found[0] if found else None

    @covers_requirement("limbo-room::the-starting-room-presents-a-localized-zh-tw-identity")
    def test_sync_limbo_authors_zh_tw_identity(self):
        legacy = create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        sync_limbo()

        room = self._limbo()
        self.assertIsNotNone(room)
        self.assertEqual(room, legacy)
        self.assertEqual(room.key, LIMBO_KEY)
        self.assertIn(LIMBO_ALIAS, room.aliases.all())
        self.assertEqual(room.db.desc, LIMBO_DESC)
        self.assertNotIn("evennia.com", room.db.desc)
        self.assertNotIn("Welcome to", room.db.desc)

    @covers_requirement("limbo-room::the-starting-room-presents-a-localized-zh-tw-identity")
    def test_legacy_english_key_is_gone_and_alias_resolves(self):
        create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        sync_limbo()

        self.assertFalse(Room.objects.filter(db_key=LIMBO_LEGACY_KEY).exists())
        by_alias = search_object(LIMBO_ALIAS)
        self.assertTrue(by_alias)
        self.assertEqual(by_alias[0].key, LIMBO_KEY)

    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_repeated_runs_are_idempotent(self):
        create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        sync_limbo()
        first = self._limbo()
        first_id = first.id

        sync_limbo()
        second = self._limbo()
        self.assertEqual(second.id, first_id)
        self.assertEqual(len(search_object(LIMBO_KEY, exact=True)), 1)
        self.assertEqual(second.db.desc, LIMBO_DESC)

    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_dual_room_database_converges_on_canonical(self):
        canonical = create_object(Room, key=LIMBO_KEY, location=None)
        legacy = create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        legacy_desc = "untouched legacy description"
        legacy.db.desc = legacy_desc

        with patch("world.maps.bootstrap.log_warn") as warn:
            sync_limbo()

        room = self._limbo()
        self.assertEqual(room.id, canonical.id)
        self.assertEqual(room.db.desc, LIMBO_DESC)
        self.assertEqual(legacy.key, LIMBO_LEGACY_KEY)
        self.assertEqual(legacy.db.desc, legacy_desc)
        self.assertTrue(any(LIMBO_LEGACY_KEY in str(call) for call in warn.call_args_list))

    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_missing_room_degrades_without_raising(self):
        with patch("world.maps.bootstrap.log_warn") as warn:
            sync_limbo()
        self.assertIsNone(self._limbo())
        self.assertTrue(any(LIMBO_KEY in str(call) for call in warn.call_args_list))

    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_at_server_start_renames_legacy_room_and_leaves_it_without_exits(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        legacy = create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        # Full startup also synchronizes service hosts in every settlement, so
        # the declaration must cover every spawned host room.
        # The ambient monster population is not part of this declaration: the
        # contract under test is the legacy room's rename and that the
        # settlement grid joins no exit to it.
        with selected_startup_settlements(
            tuple(
                sorted(
                    {
                        gate.destination.map_id
                        for entry in WILDERNESS_ENTRY_REGISTRY.values()
                        for gate in entry.gates
                    }
                )
            ),
            zone_keys=(),
        ):
            at_server_start()

        room = self._limbo()
        self.assertEqual(room.id, legacy.id)
        self.assertEqual(room.key, LIMBO_KEY)
        self.assertEqual(room.exits, [])
        self.assertFalse(ObjectDB.objects.filter(db_destination=room.id).exists())


class LimboHardGateTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """Layer-2 one-way gate: 虛境 admits no non-superuser character (D4)."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_limbo()

    def _limbo(self):
        return search_object(LIMBO_KEY, exact=True)[0]

    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    def test_sync_limbo_converges_the_hard_gate_typeclass(self):
        self.assertIsInstance(self._limbo(), LimboRoom)

    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    def test_character_traversal_into_limbo_is_refused(self):
        limbo = self._limbo()
        reverse = create_object(Exit, key="回程", location=self.room1, destination=limbo)
        self.char1.location = self.room1

        with patch.object(self.char1, "msg") as msg:
            result = reverse.at_traverse(self.char1, limbo)

        self.assertFalse(result)
        self.assertIs(self.char1.location, self.room1)
        sent = [call.args[0] for call in msg.call_args_list if call.args]
        self.assertIn(LimboRoom.LIMBO_REFUSAL_MSG, sent)
        # The stock English failure line is suppressed for this refusal.
        self.assertFalse(any("You cannot go there" in line for line in sent))

    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    def test_forced_teleport_style_move_into_limbo_is_refused(self):
        limbo = self._limbo()
        self.char1.location = self.room1

        with patch.object(self.char1, "msg") as msg:
            result = self.char1.move_to(limbo, quiet=True, move_type="teleport")

        self.assertFalse(result)
        self.assertIs(self.char1.location, self.room1)
        sent = [call.args[0] for call in msg.call_args_list if call.args]
        self.assertIn(LimboRoom.LIMBO_REFUSAL_MSG, sent)

    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    def test_superuser_governed_character_may_enter(self):
        # Superuser-governed means governed by a superuser ACCOUNT (the repo's
        # admin convention reads the governing account, typeclasses/exits.py).
        self.account.is_superuser = True
        self.account.save()
        limbo = self._limbo()
        self.char1.location = self.room1

        result = self.char1.move_to(limbo, move_type="teleport")

        self.assertTrue(result)
        self.assertIs(self.char1.location, limbo)

    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_double_sync_limbo_does_not_swap_twice(self):
        with patch("typeclasses.rooms.LimboRoom.swap_typeclass") as swap:
            sync_limbo()
        swap.assert_not_called()

        room = self._limbo()
        self.assertIsInstance(room, LimboRoom)
        self.assertEqual(room.key, LIMBO_KEY)
        self.assertIn(LIMBO_ALIAS, room.aliases.all())
        self.assertEqual(room.db.desc, LIMBO_DESC)


class LimboExitPruneTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaTest):
    """``sync_limbo()`` deletes every exit that touches 虛境 (retire-limbo-city-gates D1)."""

    def setUp(self):
        super().setUp()
        self.limbo = create_object(Room, key=LIMBO_KEY, location=None)

    @staticmethod
    def _pruned_events(log_info):
        return [
            call
            for call in log_info.call_args_list
            if call.args and call.args[0] == "bootstrap_limbo_exit_pruned"
        ]

    def test_leftover_forward_exit_is_removed_and_logged(self):
        forward = create_object(
            Exit, key="t_離境小徑", location=self.limbo, destination=self.room1
        )
        forward_id = forward.id
        forward_dbref = forward.dbref

        with patch("world.maps.bootstrap.log_info") as log_info:
            sync_limbo()

        self.assertFalse(ObjectDB.objects.filter(id=forward_id).exists())
        events = self._pruned_events(log_info)
        self.assertEqual(len(events), 1)
        context = events[0].kwargs["context"]
        self.assertEqual(context["exit_dbref"], forward_dbref)
        self.assertEqual(context["exit_key"], "t_離境小徑")
        self.assertEqual(context["side"], "location")

    def test_reverse_exit_is_removed_and_logged(self):
        reverse = create_object(
            Exit, key="t_回境小徑", location=self.room1, destination=self.limbo
        )
        reverse_id = reverse.id
        reverse_dbref = reverse.dbref

        with patch("world.maps.bootstrap.log_info") as log_info:
            sync_limbo()

        self.assertFalse(ObjectDB.objects.filter(id=reverse_id).exists())
        events = self._pruned_events(log_info)
        self.assertEqual(len(events), 1)
        context = events[0].kwargs["context"]
        self.assertEqual(context["exit_dbref"], reverse_dbref)
        self.assertEqual(context["side"], "destination")

    def test_self_loop_exit_is_removed_once(self):
        loop = create_object(Exit, key="t_迴圈小徑", location=self.limbo, destination=self.limbo)
        loop_id = loop.id

        with patch("world.maps.bootstrap.log_info") as log_info:
            sync_limbo()

        self.assertFalse(ObjectDB.objects.filter(id=loop_id).exists())
        events = self._pruned_events(log_info)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["side"], "location")

    def test_converged_room_is_left_alone_on_a_second_run(self):
        create_object(Exit, key="t_離境小徑", location=self.limbo, destination=self.room1)
        create_object(Exit, key="t_回境小徑", location=self.room1, destination=self.limbo)
        sync_limbo()
        object_ids = set(ObjectDB.objects.values_list("id", flat=True))

        with patch("world.maps.bootstrap.log_info") as log_info:
            sync_limbo()

        self.assertEqual(self._pruned_events(log_info), [])
        self.assertEqual(set(ObjectDB.objects.values_list("id", flat=True)), object_ids)

    def test_non_exit_objects_touching_the_room_survive(self):
        # An item that merely carries a destination, and a non-exit object
        # held in the room (as a creation-pending shell is), are not exits.
        marker = create_object(
            "typeclasses.objects.Object",
            key="t_指路石",
            location=self.room1,
            destination=self.limbo,
        )
        held = create_object("typeclasses.objects.Object", key="t_寄存物", location=self.limbo)

        with patch("world.maps.bootstrap.log_info") as log_info:
            sync_limbo()

        self.assertTrue(ObjectDB.objects.filter(id=marker.id).exists())
        self.assertTrue(ObjectDB.objects.filter(id=held.id).exists())
        self.assertEqual(self._pruned_events(log_info), [])
