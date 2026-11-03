"""A synchronization failure restores the prior map bundle and world."""

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


class MapWorldSynchronizationRollbackTests(_MapWorldAdoptionCase):
    """A synchronization failure restores the prior bundle and persistent world."""

    def test_a_second_adoption_keeps_the_last_synchronized_rollback_baseline(self):
        baseline = runtime.current()
        baseline_signature = binding_signature()

        with tempfile.TemporaryDirectory() as directory:
            root = _copy_map_sources(Path(directory))
            (root / "content/maps/interiors/t_adoption_study.yaml").write_text(
                _extra_interior_document(), encoding="utf-8"
            )
            (root / "content/maps/interiors/t_adoption_study_two.yaml").write_text(
                _extra_interior_document()
                .replace("t_adoption_study", "t_adoption_study_two")
                .replace("合成書房門", "合成第二書房門"),
                encoding="utf-8",
            )
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
                runtime.adopt()
            self.assertIsNot(runtime.current(), baseline)

            calls = {"count": 0}
            real = bootstrap._ensure_owned_exit

            def fail_after_writes(*args, **kwargs):
                calls["count"] += 1
                created = real(*args, **kwargs)
                if calls["count"] > 2:
                    raise RuntimeError("injected interior edge failure")
                return created

            with patch.object(
                bootstrap, "_ensure_owned_exit", side_effect=fail_after_writes
            ):
                with self.assertRaises(RuntimeError):
                    runtime.synchronize()

        # The failed synchronization restores the last SYNCHRONIZED world, not
        # the intermediate unsynchronized adoption.
        self.assertIs(runtime.current(), baseline)
        self.assertEqual(binding_signature(), baseline_signature)

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
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

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
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

