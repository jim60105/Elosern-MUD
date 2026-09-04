"""Tests for the localized starting room (Limbo) identity and its bridge
(localize-limbo-zhtw: limbo-room capability)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.localized.general import CmdHome
from server.conf.at_server_startstop import at_server_start
from typeclasses.characters import Character, PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, LimboRoom, Room
from world.maps.bootstrap import sync_grid, sync_limbo
from world.maps.city_gates import CITY_GATE_REGISTRY
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.tests.combat_fixtures import BattlefieldIsolation

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")


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

    def _south_gate(self):
        return GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()

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
    def test_at_server_start_calls_sync_limbo_before_sync_grid(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_limbo"),
            STARTUP_STEP_ORDER.index("sync_grid"),
        )

    @covers_requirement("limbo-room::sync-limbo-converges-the-starting-room-idempotently-at-server-start")
    def test_at_server_start_renames_legacy_room_and_bridges_it(self):
        legacy = create_object(Room, key=LIMBO_LEGACY_KEY, location=None)
        at_server_start()

        room = self._limbo()
        self.assertEqual(room.id, legacy.id)
        self.assertEqual(room.key, LIMBO_KEY)
        bridge = [exit_obj for exit_obj in room.exits if exit_obj.destination.xyz == SOUTH_GATE_XYZ]
        self.assertEqual([exit_obj.key for exit_obj in bridge], ["南門"])

    @covers_requirement("limbo-room::the-bridge-to-the-capital-presents-zh-tw-exit-names-and-aliases-reconciled-in-place")
    def test_bridge_exits_carry_zh_tw_keys_and_aliases_only(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        limbo = self._limbo()
        south_gate = self._south_gate()
        to_city = [e for e in limbo.exits if e.destination == south_gate]
        self.assertEqual([e.key for e in to_city], ["南門"])
        # One-way: no exit leads back into the starting room.
        self.assertEqual([e for e in south_gate.exits if e.destination == limbo], [])
        for exit_obj in to_city:
            aliases = set(exit_obj.aliases.all())
            self.assertEqual(aliases, set(CITY_GATE_REGISTRY["capital_altoria"].exit_aliases))
            self.assertTrue(all(not alias.isascii() for alias in aliases))

    @covers_requirement("limbo-room::the-bridge-to-the-capital-presents-zh-tw-exit-names-and-aliases-reconciled-in-place")
    def test_pre_existing_english_bridge_aliases_are_reconciled_in_place(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        limbo = self._limbo()
        south_gate = self._south_gate()
        to_city = [e for e in limbo.exits if e.destination == south_gate][0]
        to_city.aliases.clear()
        to_city.aliases.add("south gate", "altoria")
        to_city_id = to_city.id
        # A legacy reverse exit seeded as an existing database has it.
        reverse = create_object(
            Exit, key="離開王都", aliases=["回虛境"], location=south_gate, destination=limbo
        )

        sync_grid()

        to_city = [e for e in limbo.exits if e.destination == south_gate]
        self.assertEqual(len(to_city), 1)
        self.assertEqual(to_city[0].id, to_city_id)
        self.assertEqual(to_city[0].key, "南門")
        self.assertNotIn("south gate", to_city[0].aliases.all())
        self.assertNotIn("altoria", to_city[0].aliases.all())
        self.assertEqual(
            set(to_city[0].aliases.all()), set(CITY_GATE_REGISTRY["capital_altoria"].exit_aliases)
        )
        # The reverse exit converges away (deleted object, gone from db).
        self.assertEqual(
            ObjectDB.objects.filter(id=reverse.id).exists(),
            False,
        )

    @covers_requirement("limbo-room::the-bridge-to-the-capital-presents-zh-tw-exit-names-and-aliases-reconciled-in-place")
    def test_resync_keeps_bridge_zh_tw_without_duplicates(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_grid()

        limbo = self._limbo()
        south_gate = self._south_gate()
        self.assertEqual(len([e for e in limbo.exits if e.destination == south_gate]), 1)
        self.assertEqual(len([e for e in south_gate.exits if e.destination == limbo]), 0)


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


class GateHomePolicyTests(
    BattlefieldIsolation, RegistryIsolationMixin, EvenniaCommandTestMixin, EvenniaTest
):
    """First-gate-traversal home re-anchor (D7) and the full one-way flow."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_limbo()
        sync_grid()
        self.limbo = search_object(LIMBO_KEY, exact=True)[0]
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.gate_exit = [e for e in self.limbo.exits if e.destination == self.south_gate][0]
        # Birth state: the character was created in 虛境 with a 虛境 home
        # (no DEFAULT_HOME override), via direct placement as the creation
        # pipeline performs it.
        self.char1.location = self.limbo
        self.char1.home = self.limbo

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_first_gate_traversal_reanchors_home(self):
        self.gate_exit.at_traverse(self.char1, self.south_gate)

        self.assertIs(self.char1.location, self.south_gate)
        self.assertIs(self.char1.home, self.south_gate)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_second_gate_traversal_never_overwrites_home(self):
        self.gate_exit.at_traverse(self.char1, self.south_gate)
        home_id = self.char1.home.id
        self.assertIsNotNone(home_id)

        # Re-crossing the same gate later (e.g. placed back for a resync test)
        # must not touch the now-city home.
        self.char1.location = self.limbo
        self.gate_exit.at_traverse(self.char1, self.south_gate)

        self.assertEqual(self.char1.home.id, home_id)
        self.assertIs(self.char1.home, self.south_gate)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_preexisting_non_limbo_home_survives_first_traversal(self):
        self.char1.home = self.room2

        self.gate_exit.at_traverse(self.char1, self.south_gate)

        self.assertIs(self.char1.location, self.south_gate)
        self.assertIs(self.char1.home, self.room2)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_failed_settlement_leaves_home_at_limbo(self):
        with patch(
            "world.rules.movement.charge_movement", side_effect=RuntimeError("clock boom")
        ):
            with self.assertRaises(RuntimeError):
                self.gate_exit.at_traverse(self.char1, self.south_gate)

        self.assertIs(self.char1.location, self.limbo)
        self.assertIs(self.char1.home, self.limbo)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_settlement_failure_after_the_home_write_restores_live_home(self):
        # The writer logs AFTER the durable write; failing that log raises
        # inside the settlement transaction with home already written, so the
        # outer rollback plus compensation must reconcile the LIVE object back
        # to the rolled-back row — not just the database.
        with patch("world.rules.city_gates.log_info", side_effect=RuntimeError("log boom")):
            with self.assertRaises(RuntimeError):
                self.gate_exit.at_traverse(self.char1, self.south_gate)

        self.assertIs(self.char1.location, self.limbo)
        self.assertIs(self.char1.home, self.limbo)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    def test_non_player_traversal_changes_no_home(self):
        traveler = create_object(NPC, key="旅人", location=self.limbo, home=self.limbo)

        self.gate_exit.at_traverse(traveler, self.south_gate)

        self.assertIs(traveler.location, self.south_gate)
        self.assertIs(traveler.home, self.limbo)

    @covers_requirement("limbo-one-way-gates::the-first-city-gate-traversal-re-anchors-a-虛境-home-to-the-arrival-gate-room")
    @covers_requirement("limbo-one-way-gates::虛境-admits-no-character-by-any-path")
    def test_home_command_after_reanchor_delivers_to_gate_never_limbo(self):
        # Full one-way flow: birth in 虛境 → cross 「南門」 → wander → home.
        self.gate_exit.at_traverse(self.char1, self.south_gate)
        self.char1.location = self.room1  # wander away through any later path

        output = self.call(CmdHome(), "", caller=self.char1, cmdstring="回家")

        self.assertIn("還是家最溫暖", output)
        self.assertIs(self.char1.location, self.south_gate)
        self.assertIsNot(self.char1.location, self.limbo)
