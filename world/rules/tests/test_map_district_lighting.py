"""Read-only district lighting from the landmark rite record (map-districts).

Synthetic districts, knowledge records and rite records only: a district is lit
exactly when a completed rite for it is recorded and the registry declares it.
A visited landmark lights nothing, and reading lighting writes nothing.
"""

import copy
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement
from elosern_map_core.documents import DistrictDeclaration
from elosern_map_core.references import wilderness_cell_ref
from world.lore.map_districts import landmark_node_ids
from world.rules.landmark_rite_record import (
    RECORD_ATTR,
    LandmarkRiteRecordError,
    empty_record,
    with_completion,
)
from world.rules.map_district_lighting import (
    lit_district_keys,
    readable_lit_district_keys,
)
from world.rules.map_knowledge import CHUNK_CELLS, KNOWLEDGE_ATTR, decode_node
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()


def _district(key, name, landmark_name, cell, kind="voronoi", region_key=None):
    return DistrictDeclaration(
        district_id=key,
        district_name_zh=name,
        landmark_name_zh=landmark_name,
        landmark=wilderness_cell_ref(cell),
        kind=kind,
        region_key=region_key,
    )


_DISTRICTS = {
    "mire": _district("mire", "霧沼區", "霧沼心", (500, 2400), "region", "mire_region"),
    "dune": _district("dune", "沙丘區", "沙丘石", (300, 600)),
    "vale": _district("vale", "溪谷區", "溪谷橋", (700, 900)),
}


class _SpyAttributes:
    """An attribute handler that records every write attempt."""

    def __init__(self, stored):
        self.stored = stored
        self.writes = []

    def get(self, key, default=None):
        return self.stored.get(key, default)

    def add(self, *args, **kwargs):
        self.writes.append(("add", args, kwargs))

    def remove(self, *args, **kwargs):
        self.writes.append(("remove", args, kwargs))


def _knowledge(visited):
    """A schema-2 map-knowledge record holding exactly ``visited``."""
    visited_map = {}
    wild_chunks = {}
    for node in visited:
        decoded = decode_node(node)
        if decoded["prefix"] in ("grid", "room"):
            visited_map[node] = {"first_seen_tick": 3, "last_seen_tick": 9}
        elif decoded["prefix"] == "wild":
            x, y = decoded["x"], decoded["y"]
            chunk_key = f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}"
            offset = str((y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS))
            wild_chunks.setdefault(chunk_key, {})[offset] = {
                "first_seen_tick": 3,
                "last_seen_tick": 9,
                "sight": 0,
            }
    return {
        "schema_version": 2,
        "visited": visited_map,
        "wilderness": {WILDERNESS_NAME: wild_chunks} if wild_chunks else {},
    }


def _rites(*district_keys):
    record = empty_record()
    for key in district_keys:
        record = with_completion(record, key, "t_option", 4)
    return record


class _Character:
    def __init__(self, *, visited=None, rites=None):
        stored = {}
        if visited is not None:
            stored[KNOWLEDGE_ATTR] = _knowledge(visited)
        if rites is not None:
            stored[RECORD_ATTR] = rites
        self.pk = 7
        self.attributes = _SpyAttributes(stored)


class DistrictLightingTests(unittest.TestCase):
    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_a_visited_landmark_lights_nothing(self):
        # Every exact landmark node is visited, yet no rite is recorded.
        character = _Character(visited=landmark_node_ids(_DISTRICTS).values())
        self.assertEqual(lit_district_keys(character, _DISTRICTS), frozenset())
        self.assertEqual(readable_lit_district_keys(character, _DISTRICTS), frozenset())

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_a_completed_rite_lights_only_its_declared_district(self):
        character = _Character(rites=_rites("dune", "t_retired"))
        self.assertEqual(lit_district_keys(character, _DISTRICTS), frozenset({"dune"}))

        # The region district lights as one identity, whichever claim it spans.
        region = _Character(rites=_rites("mire"))
        self.assertEqual(lit_district_keys(region, _DISTRICTS), frozenset({"mire"}))

        everything = _Character(rites=_rites(*_DISTRICTS))
        self.assertEqual(lit_district_keys(everything, _DISTRICTS), frozenset(_DISTRICTS))

    def test_the_default_registry_is_the_published_district_world(self):
        character = _Character(rites=_rites("dune", "t_retired"))
        with patch(
            "world.lore.map_districts.current",
            new=lambda: type("Snapshot", (), {"districts": _DISTRICTS})(),
        ):
            self.assertEqual(lit_district_keys(character), frozenset({"dune"}))

    def test_no_completion_reads_no_registry(self):
        character = _Character(visited=["wild:elosern:300:600"])
        with patch(
            "world.lore.map_districts.current",
            side_effect=AssertionError("the district registry was read"),
        ):
            self.assertEqual(lit_district_keys(character), frozenset())

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_reading_lighting_writes_nothing(self):
        character = _Character(visited=["wild:elosern:300:600"], rites=_rites("dune"))
        before = copy.deepcopy(character.attributes.stored)
        lit_district_keys(character, _DISTRICTS)
        readable_lit_district_keys(character, _DISTRICTS)
        self.assertEqual(character.attributes.writes, [])
        self.assertEqual(character.attributes.stored, before)

        fresh = _Character()
        self.assertEqual(lit_district_keys(fresh, _DISTRICTS), frozenset())
        self.assertEqual(readable_lit_district_keys(fresh, _DISTRICTS), frozenset())
        # No record, discovery or lighting attribute is created by reading.
        self.assertEqual(fresh.attributes.stored, {})
        self.assertEqual(fresh.attributes.writes, [])

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_a_corrupt_record_raises_strictly_and_degrades_with_one_warning(self):
        corrupt_record = {"schema_version": 2, "completed": {}}
        corrupt = _Character(rites=corrupt_record)
        before = copy.deepcopy(corrupt.attributes.stored)
        with self.assertRaises(LandmarkRiteRecordError):
            lit_district_keys(corrupt, _DISTRICTS)

        with patch("world.rules.map_district_lighting.log_warn") as warning:
            self.assertEqual(readable_lit_district_keys(corrupt, _DISTRICTS), frozenset())
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(warning.call_args.args[0], "landmark_rite_record_corrupt")
        self.assertIsInstance(warning.call_args.kwargs["exc"], LandmarkRiteRecordError)
        self.assertEqual(warning.call_args.kwargs["context"], {"char": 7, "district": ""})
        self.assertEqual(corrupt.attributes.stored, before)
        self.assertEqual(corrupt.attributes.writes, [])

    def test_a_corrupt_record_raises_even_with_no_readable_completion(self):
        # The empty-record shortcut never hides an envelope violation.
        corrupt = _Character(rites={"schema_version": 1, "completed": {"dune": "x"}})
        with patch(
            "world.lore.map_districts.current",
            side_effect=AssertionError("the district registry was read"),
        ):
            with self.assertRaises(LandmarkRiteRecordError):
                lit_district_keys(corrupt)
