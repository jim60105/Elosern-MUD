"""Adoption and persistent synchronization of the permanent map world.

The publish/reject side: one complete validated bundle, interiors owned
independently of services, and reuse on repeated synchronization.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from elosern_map_core.partition_codec import PARTITION_ALGORITHM_VERSION, PartitionFreshness
from elosern_map_core.references import interior_room_ref

from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from world.maps import bootstrap, runtime
from world.maps.static_references import binding_signature

from world.maps.tests._runtime_adoption_fixtures import (
    REPOSITORY_ROOT,
    _MapWorldAdoptionCase,
    _copy_map_sources,
    _extra_interior_document,
    _frozen,
    _npcs_state,
    _places,
    _stale_freshness,
)


class MapWorldAdoptionTests(_MapWorldAdoptionCase):
    """Bundle publication, interior independence, sync reuse and rejection."""

    # -- one complete bundle ---------------------------------------------------

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
    def test_adoption_publishes_one_complete_validated_bundle(self):
        bundle = runtime.current()

        self.assertTrue(runtime.is_published())
        self.assertIsNotNone(bundle.snapshot)
        self.assertTrue(bundle.partition.current, "the committed artifact is stale")
        self.assertTrue(bundle.settlements.graphs)
        self.assertTrue(bundle.interiors.rooms)
        self.assertTrue(bundle.districts.districts)
        # The core snapshot binds the same source set the views were composed from.
        self.assertEqual(bundle.snapshot.fingerprint, bundle.snapshot.fingerprint)
        self.assertEqual(
            set(bundle.snapshot.settlements), set(bundle.settlements.graphs)
        )
        self.assertEqual(set(bundle.snapshot.interiors), set(bundle.interiors.documents))

        # Every domain view reads the one published pointer, not a second copy.
        from world.lore import map_districts
        from world.maps import geography, interiors, map_data

        self.assertIs(geography.current(), bundle.geography)
        self.assertIs(map_data.current(), bundle.settlements)
        self.assertIs(map_districts.current(), bundle.districts)
        self.assertIs(interiors.current(), bundle.interiors)

        # Every service join lands on an authored room of the candidate.
        places = _places()
        for key, place in places.items():
            with self.subTest(place=key):
                self.assertEqual(place.room.domain, "interior_room")
                self.assertEqual(place.room.object_id, key)
                self.assertIn(key, bundle.interiors.rooms)

    @covers_requirement(
        "map-runtime-adoption::permanent-interiors-are-map-owned-independently-of-services"
    )
    def test_interior_synchronization_needs_no_service_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = _copy_map_sources(Path(directory))
            extra = root / "content/maps/interiors/t_adoption_study.yaml"
            extra.write_text(_extra_interior_document(), encoding="utf-8")
            with patch.object(
                runtime,
                "partition_freshness_for",
                side_effect=lambda world: PartitionFreshness(
                    algorithm_version=PARTITION_ALGORITHM_VERSION,
                    input_signature=world.partition_signature,
                    current=True,
                ),
            ):
                runtime.adopt(root)

            bootstrap.sync_interiors()

            rooms = [
                obj
                for obj in ObjectDB.objects.filter(db_key="合成書房")
                if isinstance(obj, Room)
            ]
            self.assertEqual(len(rooms), 1, "a standalone interior must exist once")
            study = rooms[0]
            self.assertTrue(study.tags.has("t_adoption_study"))
            self.assertIsNone(study.db.expire_tick)
            # Its authored doorway opens from the documented exterior, and the
            # room leads back — one owning declaration, both directions.
            out = [exit_obj for exit_obj in study.exits if exit_obj.key == "外"]
            self.assertEqual(len(out), 1)
            frontage = out[0].destination
            doorways = [
                exit_obj
                for exit_obj in frontage.exits
                if exit_obj.destination is study
            ]
            self.assertEqual(len(doorways), 1)
            self.assertEqual(doorways[0].key, "合成書房門")

    # -- repeated synchronization ---------------------------------------------

    def test_repeated_sync_reuses_the_same_rooms_and_exits(self):

        def snapshot():
            return {
                room.room_id: (
                    [
                        obj.pk
                        for obj in ObjectDB.objects.filter(db_key=room.name_zh)
                        if isinstance(obj, Room)
                    ],
                    sorted(
                        (exit_obj.key, exit_obj.destination.pk)
                        for obj in ObjectDB.objects.filter(db_key=room.name_zh)
                        if isinstance(obj, Room)
                        for exit_obj in obj.exits
                    ),
                )
                for room in runtime.current().interiors.rooms.values()
            }

        first = snapshot()
        room_count = Room.objects.all_family().count()
        host_state = _npcs_state()

        # Re-adopting the unchanged sources and synchronizing again must not
        # recreate anything either.
        runtime.adopt()
        bootstrap.sync_interiors()
        bootstrap.sync_interiors()

        self.assertEqual(snapshot(), first)
        self.assertEqual(Room.objects.all_family().count(), room_count)
        self.assertEqual(_npcs_state(), host_state, "a repeat sync reset live host state")
        joined = next(iter(_places().values()))
        self.assertTrue(joined.room_name_zh)

    # -- rejected candidates ---------------------------------------------------

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
    def test_a_bad_service_target_publishes_nothing(self):
        places = _places()

        baseline = runtime.current()
        baseline_signature = binding_signature()
        rooms_before = Room.objects.all_family().count()

        # A service record joining a room no interior document authors is
        # exactly the "invalid service target" the adoption must refuse.
        shipped = next(iter(places.values()))
        broken = replace(
            shipped, key="t_absent_room", room=interior_room_ref(
                "t_absent_interior", "t_absent_room"
            )
        )
        with patch.dict(places, {broken.key: broken}, clear=False):
            with self.assertRaises(runtime.MapWorldError) as caught:
                runtime.adopt()

        self.assertIn("t_absent_room", str(caught.exception))
        self.assertIs(runtime.current(), baseline)
        self.assertEqual(binding_signature(), baseline_signature)
        self.assertEqual(Room.objects.all_family().count(), rooms_before)

