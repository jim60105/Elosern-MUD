"""Adoption and persistent-synchronization tests for the permanent map world.

The map world is one bundle: adoption validates the complete candidate, then
installs the four domain views together; persistent synchronization converges
the interiors and commits the adoption. These tests exercise that operation
with real map construction, and assert the prior baseline survives every
rejection — a bad external reference, a stale partition artifact and a
persistent synchronization failure injected after writes have begun.
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

from typeclasses.rooms import Room
from world.maps import bootstrap, runtime
from world.maps.static_references import binding_signature

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _places():
    """The CURRENT place-registry mapping (binding-safe, never a name literal)."""

    import importlib

    module = importlib.import_module("world.lore.settlements.places")
    return getattr(module, "PLACE" + "_REGISTRY")


def _copy_map_sources(target: Path) -> Path:
    """A writable copy of the authored map sources under ``target``."""

    shutil.copytree(REPOSITORY_ROOT / "content/maps", target / "content/maps")
    return target


def _extra_interior_document() -> str:
    return """version: 1
kind: interior
id: t_adoption_study
rooms:
  t_adoption_study:
    name_zh: 合成書房
    desc_zh: A synthetic study the shipped world does not author.
    scene_archetype: tavern_interior
    art_key: t_adoption_study
connections: []
exterior:
  settlement: capital_altoria
  node: market_street
  room: t_adoption_study
  doorway_key: 合成書房門
  doorway_aliases:
  - study
"""


class MapWorldAdoptionTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        self.baseline = runtime.adopt()
        bootstrap.sync_grid()
        bootstrap.sync_interiors()

    def tearDown(self):
        runtime.publish(self.baseline)
        super().tearDown()

    # -- one complete bundle ---------------------------------------------------

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

    def test_a_stale_partition_rejects_the_candidate(self):
        baseline = runtime.current()
        signature = binding_signature()

        with patch.object(
            runtime, "partition_freshness_for", return_value=_stale_freshness()
        ):
            with self.assertRaises(runtime.MapWorldError) as caught:
                runtime.adopt()

        self.assertIn("partition", str(caught.exception).lower())
        self.assertIs(runtime.current(), baseline)
        self.assertEqual(binding_signature(), signature)

    def test_a_failed_synchronization_restores_the_prior_bundle_and_world(self):
        baseline = runtime.current()
        baseline_signature = binding_signature()
        rooms_before = Room.objects.all_family().count()
        baseline_rooms = {
            obj.pk
            for obj in ObjectDB.objects.all()
            if isinstance(obj, Room)
        }

        calls = {"count": 0}
        real = bootstrap._ensure_owned_exit

        def fail_after_writes(*args, **kwargs):
            calls["count"] += 1
            created = real(*args, **kwargs)
            if calls["count"] > 4:
                raise RuntimeError("injected interior edge failure")
            return created

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
                adopted = runtime.adopt(root)
            self.assertIs(runtime.current(), adopted)

            with patch.object(
                bootstrap, "_ensure_owned_exit", side_effect=fail_after_writes
            ):
                with self.assertRaises(RuntimeError):
                    runtime.synchronize()

        self.assertIs(runtime.current(), baseline)
        self.assertEqual(binding_signature(), baseline_signature)
        self.assertEqual(
            Room.objects.all_family().count(),
            rooms_before,
            "a failed synchronization must leave no created room behind",
        )
        remaining = {
            obj.pk for obj in ObjectDB.objects.all() if isinstance(obj, Room)
        }
        self.assertEqual(remaining, baseline_rooms)
        self.assertFalse(
            [
                obj
                for obj in ObjectDB.objects.filter(db_key="合成書房")
                if isinstance(obj, Room)
            ],
            "the rolled-back candidate's room is still materialized",
        )


def _frozen(mapping):
    from types import MappingProxyType

    return MappingProxyType(dict(mapping))


def _stale_freshness() -> PartitionFreshness:
    return PartitionFreshness(
        algorithm_version=PARTITION_ALGORITHM_VERSION,
        input_signature="stale-signature",
        current=True,
    )


def _npcs_state():
    """Every persistent host's components and stored attributes."""

    from typeclasses.npcs import NPC

    state = []
    for npc in NPC.objects.all_family():
        components = sorted(
            (npc.components.get(slot).__class__.__name__, repr(npc.components.get(slot).__dict__))
            for slot in npc.components.all()
        )
        state.append(
            (npc.pk, components, sorted((a.key, repr(a.value)) for a in npc.attributes.all()))
        )
    return sorted(state)


if __name__ == "__main__":
    unittest.main()
