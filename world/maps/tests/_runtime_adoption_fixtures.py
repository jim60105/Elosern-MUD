"""Shared candidate case and source helpers for the map-world adoption suites."""

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


class _MapWorldAdoptionCase(EvenniaTestCase):
    @classmethod
    def setUpTestData(cls):
        # This case intentionally adopts and materializes the complete
        # candidate; it is an explicit full-candidate contract case, so the
        # world is built once per class. Each method's writes still roll back
        # with its own transaction, and the bundle is republished per test.
        super().setUpTestData()
        create_object(Room, key="虛境", location=None)
        cls.baseline = runtime.adopt()
        from world.tests.geography_fixture import sync_test_settlements

        sync_test_settlements(tuple(cls.baseline.settlements.graphs))
        bootstrap.sync_interiors()
        # Startup settles the adoption once the persistent world converged.
        runtime.commit_adoption()

    def setUp(self):
        super().setUp()
        self.baseline = type(self).baseline

    def tearDown(self):
        runtime.publish(type(self).baseline)
        super().tearDown()


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
