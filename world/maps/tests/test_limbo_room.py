"""Tests for the localized starting room (Limbo) identity and its bridge
(localize-limbo-zhtw: limbo-room capability)."""

from tools.spec_traceability import covers_requirement

import inspect
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.rooms import GridRoom, Room
from world.maps.bootstrap import sync_grid, sync_limbo
from world.maps.limbo import (
    LIMBO_ALIAS,
    LIMBO_DESC,
    LIMBO_KEY,
    LIMBO_LEGACY_KEY,
)

SOUTH_GATE_XYZ = (2, 0, "capital_altoria")


class LimboRoomTests(EvenniaTest):
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
        source = inspect.getsource(at_server_start)
        self.assertLess(source.index("sync_limbo()"), source.index("sync_grid()"))

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
        to_limbo = [e for e in south_gate.exits if e.destination == limbo]
        self.assertEqual([e.key for e in to_city], ["南門"])
        self.assertEqual([e.key for e in to_limbo], ["離開王都"])
        for exit_obj in to_city + to_limbo:
            aliases = set(exit_obj.aliases.all())
            self.assertFalse(any(alias in aliases for alias in ("south gate", "altoria", "leave", "limbo")))
            self.assertTrue(all(not alias.isascii() for alias in aliases))

    @covers_requirement("limbo-room::the-bridge-to-the-capital-presents-zh-tw-exit-names-and-aliases-reconciled-in-place")
    def test_pre_existing_english_bridge_aliases_are_reconciled_in_place(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()

        limbo = self._limbo()
        south_gate = self._south_gate()
        to_city = [e for e in limbo.exits if e.destination == south_gate][0]
        to_limbo = [e for e in south_gate.exits if e.destination == limbo][0]
        to_city.aliases.clear()
        to_city.aliases.add("south gate", "altoria")
        to_limbo.aliases.clear()
        to_limbo.aliases.add("leave", "limbo")
        to_city_id = to_city.id
        to_limbo_id = to_limbo.id

        sync_grid()

        to_city = [e for e in limbo.exits if e.destination == south_gate]
        to_limbo = [e for e in south_gate.exits if e.destination == limbo]
        self.assertEqual(len(to_city), 1)
        self.assertEqual(len(to_limbo), 1)
        self.assertEqual(to_city[0].id, to_city_id)
        self.assertEqual(to_limbo[0].id, to_limbo_id)
        self.assertEqual(to_city[0].key, "南門")
        self.assertEqual(to_limbo[0].key, "離開王都")
        self.assertNotIn("south gate", to_city[0].aliases.all())
        self.assertNotIn("leave", to_limbo[0].aliases.all())
        self.assertNotIn("limbo", to_limbo[0].aliases.all())

    @covers_requirement("limbo-room::the-bridge-to-the-capital-presents-zh-tw-exit-names-and-aliases-reconciled-in-place")
    def test_resync_keeps_bridge_zh_tw_without_duplicates(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_grid()
        sync_grid()

        limbo = self._limbo()
        south_gate = self._south_gate()
        self.assertEqual(len([e for e in limbo.exits if e.destination == south_gate]), 1)
        self.assertEqual(len([e for e in south_gate.exits if e.destination == limbo]), 1)
