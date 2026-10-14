"""Room-art metadata contract tests (unified-room-art-metadata).

The map layer owns three authored facts per supported room: its registered
scene archetype, its optional registered room-art key, and its bounded logical
scene identity. These tests exercise the real construction paths — grid
bootstrap, permanent-interior sync, pooled wilderness preparation and supported
instance construction — rather than manufactured descriptor inputs, and assert
that startup is idempotent, undeclared dynamic rooms carry no key, and a pooled
object's stale facts never survive reuse.
"""

import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom
from world.art.scene_definitions import (
    ROOM_ART_KEY_SET,
    is_registered_room_art_key,
    is_registered_scene_key,
)
from world.maps.bootstrap import sync_grid, sync_service_interiors
from world.maps.instance import spawn_instance_room
from world.maps.room_art import (
    GRID_NODE_SCENE_ARCHETYPES,
    PLACE_SCENE_ARCHETYPES,
    REGION_SCENE_ARCHETYPES,
    grid_scene_identity,
    instance_scene_identity,
    place_scene_identity,
    wilderness_scene_identity,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)


def _live_places():
    """The CURRENT place-registry mapping (binding-safe, never a name literal)."""
    module = importlib.import_module("world.lore.settlements.places")
    return getattr(module, "PLACE" + "_REGISTRY")


def _registered_room_art_key():
    return sorted(ROOM_ART_KEY_SET)[0]


def _registered_scene_archetype():
    module = importlib.import_module("world.lore.scene_archetypes")
    registry = getattr(module, "SCENE_ARCHETYPE" + "_REGISTRY")
    return next(iter(registry))


def _limbo():
    create_object(Room, key="虛境", location=None)


class GridRoomArtMetadataTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        _limbo()
        sync_grid()

    def _room(self, key):
        map_key, x, y = key
        return GridRoom.objects.filter_xyz((x, y, map_key)).first()

    def test_every_authored_grid_node_carries_registered_metadata(self):
        for key, scene_archetype in GRID_NODE_SCENE_ARCHETYPES.items():
            with self.subTest(node=key):
                room = self._room(key)
                self.assertIsNotNone(room)
                self.assertEqual(room.scene_archetype, scene_archetype)
                self.assertTrue(is_registered_scene_key(room.scene_archetype))
                # An authored grid node declares no room-art key.
                self.assertIsNone(room.room_art_key)
                self.assertEqual(room.scene_identity, grid_scene_identity(*key))

    def test_repeated_startup_converges_drifted_grid_metadata(self):
        key = next(iter(GRID_NODE_SCENE_ARCHETYPES))
        room = self._room(key)
        room.scene_archetype = None
        room.room_art_key = _registered_room_art_key()
        room.scene_identity = "drifted"
        room.save()

        sync_grid()

        room = self._room(key)
        self.assertEqual(room.scene_archetype, GRID_NODE_SCENE_ARCHETYPES[key])
        self.assertIsNone(room.room_art_key)
        self.assertEqual(room.scene_identity, grid_scene_identity(*key))


class PermanentInteriorArtMetadataTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        _limbo()
        sync_grid()

    def test_new_interior_carries_metadata_that_survives_reload(self):
        sync_service_interiors()
        place = next(iter(_live_places().values()))
        interior = search_object_by_tag(place.key)[0]

        self.assertEqual(interior.scene_archetype, PLACE_SCENE_ARCHETYPES[place.key])
        self.assertTrue(is_registered_scene_key(interior.scene_archetype))
        self.assertEqual(interior.room_art_key, place.key)
        self.assertTrue(is_registered_room_art_key(interior.room_art_key))
        self.assertEqual(interior.scene_identity, place_scene_identity(place.key))

        # Reload from the database: the facts are stored, not instance-only.
        reloaded = Room.objects.get(pk=interior.pk)
        self.assertEqual(reloaded.scene_archetype, PLACE_SCENE_ARCHETYPES[place.key])
        self.assertEqual(reloaded.room_art_key, place.key)
        self.assertEqual(reloaded.scene_identity, place_scene_identity(place.key))

    def test_repeated_startup_reapplies_interior_metadata_without_duplicates(self):
        sync_service_interiors()
        count = Room.objects.all_family().count()
        place = next(iter(_live_places().values()))
        interior = search_object_by_tag(place.key)[0]
        interior.scene_archetype = None
        interior.save()

        sync_service_interiors()

        self.assertEqual(Room.objects.all_family().count(), count)
        self.assertEqual(
            search_object_by_tag(place.key)[0].scene_archetype,
            PLACE_SCENE_ARCHETYPES[place.key],
        )


class PooledWildernessRoomArtTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.provider = ElosernWildernessMapProvider()

    def test_pooled_object_clears_a_stale_key_between_coordinates(self):
        room = create_object(TerrainRoom, key="t_pooled")
        place_a = (200, 100)
        place_b = (204, 104)
        # Same region, distinct coordinates: the archetype is equal while the
        # logical identity must still differ.
        self.assertEqual(
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*place_a)],
            REGION_SCENE_ARCHETYPES[region_for_coordinates(*place_b)],
        )

        self.provider.at_prepare_room(place_a, None, room)
        room.room_art_key = _registered_room_art_key()
        identity_a = room.scene_identity

        self.provider.at_prepare_room(place_b, None, room)
        self.assertIsNone(room.room_art_key)
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, *place_b),
        )
        self.assertNotEqual(room.scene_identity, identity_a)
        self.assertTrue(is_registered_scene_key(room.scene_archetype))

    def test_identity_follows_the_attached_wilderness_name(self):
        # The delta requires identity from the CURRENT wilderness; an attached
        # script whose name differs from the configured constant must not
        # collapse two logical places onto one identity.
        room = create_object(TerrainRoom, key="t_named_wilderness")
        stub = SimpleNamespace(key="t_other_wilderness")
        with patch("world.maps.wilderness_population.ensure_population") as ensure:
            with patch.object(TerrainRoom, "wilderness", property(lambda self: stub)):
                self.provider.at_prepare_room((10, 10), None, room)
            ensure.assert_called_once()
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity("t_other_wilderness", 10, 10),
        )


class ReadOnlyResolverBoundaryTests(EvenniaTest):
    def test_resolving_a_plain_room_persists_no_metadata(self):
        # A plain Room that was never given metadata must stay untouched by a
        # read: the descriptors are autocreate=False, so build_art_view can
        # never mint an Attribute just by rendering the room.
        from world.rules.art_view import build_art_view

        room = create_object(Room, key="t_bare_room")
        for key in ("scene_archetype", "room_art_key", "scene_identity"):
            self.assertFalse(room.attributes.has(key), key)
        self.assertIsNone(room.scene_archetype)
        self.char1.location = room

        build_art_view(self.char1)

        for key in ("scene_archetype", "room_art_key", "scene_identity"):
            self.assertFalse(room.attributes.has(key), key)

    def test_resolving_a_bare_instance_room_persists_no_metadata(self):
        origin = create_object(Room, key="t_resolver_origin")
        room = spawn_instance_room(
            origin,
            {"prototype_parent": "instance_room", "key": "t_resolver_room"},
            exit_key="進入",
            return_key="離開",
            ttl_seconds=10,
        )
        # The construction writes the three facts, so delete them and prove a
        # read never re-creates them.
        room.attributes.remove("scene_archetype")
        room.attributes.remove("room_art_key")
        room.attributes.remove("scene_identity")
        self.char1.location = room
        from world.rules.art_view import build_art_view

        build_art_view(self.char1)

        for key in ("scene_archetype", "room_art_key", "scene_identity"):
            self.assertFalse(room.attributes.has(key), key)


class InstanceRoomArtMetadataTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.origin = create_object(Room, key="t_instance_origin")

    def _spawn(self, **kwargs):
        return spawn_instance_room(
            self.origin,
            {"prototype_parent": "instance_room", "key": "t_scene_room"},
            exit_key="進入",
            return_key="離開",
            ttl_seconds=10,
            **kwargs,
        )

    def test_invalid_declared_key_is_rejected_before_construction(self):
        with self.assertRaises(ValueError):
            self._spawn(room_art_key="t_not_a_registered_room")
        # Nothing was spawned or attached.
        self.assertEqual(InstanceRoom.objects.count(), 0)
        self.assertEqual(list(self.origin.exits), [])

    def test_invalid_declared_archetype_is_rejected_before_construction(self):
        with self.assertRaises(ValueError):
            self._spawn(scene_archetype="t_not_a_registered_scene")
        self.assertEqual(InstanceRoom.objects.count(), 0)

    def test_absent_declaration_defaults_to_no_key_with_a_stable_identity(self):
        room = self._spawn()
        self.assertIsNone(room.room_art_key)
        self.assertIsNone(room.scene_archetype)
        self.assertEqual(room.scene_identity, instance_scene_identity(room.pk))

    def test_invalid_explicit_scene_identity_is_rejected_before_construction(self):
        for bad in ("", "x" * 129, 7, b"bytes"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self._spawn(scene_identity=bad)
                self.assertEqual(InstanceRoom.objects.count(), 0)

    def test_boundary_length_scene_identity_is_accepted(self):
        identity = "x" * 128
        room = self._spawn(scene_identity=identity)
        self.assertEqual(room.scene_identity, identity)

    def test_explicit_registered_declaration_survives_a_reload(self):
        room_art_key = _registered_room_art_key()
        scene_archetype = _registered_scene_archetype()
        room = self._spawn(room_art_key=room_art_key, scene_archetype=scene_archetype)

        self.assertEqual(room.room_art_key, room_art_key)
        self.assertEqual(room.scene_archetype, scene_archetype)
        self.assertNotEqual(room.scene_identity, room_art_key)

        reloaded = InstanceRoom.objects.get(pk=room.pk)
        self.assertEqual(reloaded.room_art_key, room_art_key)
        self.assertEqual(reloaded.scene_archetype, scene_archetype)
        self.assertEqual(reloaded.scene_identity, room.scene_identity)

    def test_the_art_resolver_reads_metadata_without_mutation(self):
        from world.rules.art_view import build_art_view

        room = self._spawn(scene_archetype=_registered_scene_archetype())
        self.char1.location = room
        before = (
            room.scene_archetype,
            room.room_art_key,
            room.scene_identity,
        )

        view = build_art_view(self.char1)

        self.assertEqual(view.scene_archetype, room.scene_archetype)
        self.assertEqual(
            (room.scene_archetype, room.room_art_key, room.scene_identity), before
        )


class RoomMetadataSmokeTests(EvenniaTest):
    def test_bootstrap_and_pool_reuse(self):
        """Real map/bootstrap construction and real wilderness reuse.

        A fresh boot yields a registered art-panel archetype on a grid room and
        supported metadata on a permanent interior; one pooled wilderness
        object prepared for two coordinates keeps distinct logical identities
        and clears the stale room-art key.
        """
        _limbo()
        sync_grid()
        sync_service_interiors()

        node = next(iter(GRID_NODE_SCENE_ARCHETYPES))
        map_key, x, y = node
        grid_room = GridRoom.objects.filter_xyz((x, y, map_key)).first()
        self.assertTrue(is_registered_scene_key(grid_room.scene_archetype))

        interior = search_object_by_tag(next(iter(_live_places())))[0]
        self.assertTrue(is_registered_scene_key(interior.scene_archetype))
        self.assertTrue(is_registered_room_art_key(interior.room_art_key))

        provider = ElosernWildernessMapProvider()
        room = create_object(TerrainRoom, key="t_smoke_pooled")
        provider.at_prepare_room((200, 100), None, room)
        first_identity = room.scene_identity
        room.room_art_key = _registered_room_art_key()
        provider.at_prepare_room((201, 101), None, room)
        self.assertIsNone(room.room_art_key)
        self.assertNotEqual(room.scene_identity, first_identity)


if __name__ == "__main__":
    unittest.main()
