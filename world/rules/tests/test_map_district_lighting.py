"""Read-only district lighting from visited map knowledge (map-districts).

Synthetic districts and knowledge records only: lighting is exact landmark
node identity in the visited record, never proximity, and reading it writes
nothing.
"""

import copy
import unittest

from tools.spec_traceability import covers_requirement
from elosern_map_core.documents import DistrictDeclaration
from elosern_map_core.references import wilderness_cell_ref
from world.lore.map_districts import landmark_node_ids
from world.rules.map_district_lighting import lit_district_keys, lit_district_keys_from_visits
from world.rules.map_knowledge import KNOWLEDGE_ATTR, KnowledgeError, NodeVisit


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
    # One region district spanning two claims, lit only at its single heart.
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


class _Character:
    def __init__(self, visited):
        record = None
        if visited is not None:
            record = {
                "schema_version": 1,
                "visited": {
                    node: {"first_seen_tick": 3, "last_seen_tick": 9} for node in visited
                },
            }
        self.attributes = _SpyAttributes({} if record is None else {KNOWLEDGE_ATTR: record})


class DistrictLightingTests(unittest.TestCase):
    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_nearby_travel_never_lights_a_district(self):
        near_misses = [
            "wild:elosern:301:600",
            "wild:elosern:300:601",
            "wild:elosern:299:599",
            "wild:elosern:30:600",
            "wild:elosern:300:60",  # a string prefix of the landmark
            "room:300",
            # Both nominal halves of the region, but never its heart.
            "wild:elosern:400:2400",
            "wild:elosern:600:2400",
            "wild:elosern:500:2399",
        ]
        character = _Character(near_misses)
        self.assertEqual(lit_district_keys(character, _DISTRICTS), frozenset())

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_exact_landmark_lights_only_its_district(self):
        character = _Character(["wild:elosern:300:600", "wild:elosern:701:900"])
        self.assertEqual(lit_district_keys(character, _DISTRICTS), frozenset({"dune"}))

        heart = _Character(["wild:elosern:500:2400"])
        # The region district lights as one identity, whichever claim it spans.
        self.assertEqual(lit_district_keys(heart, _DISTRICTS), frozenset({"mire"}))

        everything = _Character(landmark_node_ids(_DISTRICTS).values())
        self.assertEqual(lit_district_keys(everything, _DISTRICTS), frozenset(_DISTRICTS))

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_reading_lighting_writes_nothing(self):
        character = _Character(["wild:elosern:300:600", "wild:elosern:500:2400"])
        before = copy.deepcopy(character.attributes.stored)
        lit_district_keys(character, _DISTRICTS)
        lit_district_keys(character, _DISTRICTS)
        self.assertEqual(character.attributes.writes, [])
        self.assertEqual(character.attributes.stored, before)
        # No discovery attribute or district data is attached to the record.
        self.assertEqual(set(before), {KNOWLEDGE_ATTR})
        self.assertEqual(set(before[KNOWLEDGE_ATTR]), {"schema_version", "visited"})

    @covers_requirement("map-districts::district-lighting-is-derived-from-visited-landmark-identity")
    def test_missing_record_lights_nothing_and_corrupt_record_raises(self):
        fresh = _Character(None)
        self.assertEqual(lit_district_keys(fresh, _DISTRICTS), frozenset())
        self.assertEqual(fresh.attributes.writes, [])

        corrupt = _Character([])
        corrupt.attributes.stored[KNOWLEDGE_ATTR] = {"schema_version": 99, "visited": {}}
        before = copy.deepcopy(corrupt.attributes.stored)
        with self.assertRaises(KnowledgeError):
            lit_district_keys(corrupt, _DISTRICTS)
        self.assertEqual(corrupt.attributes.stored, before)
        self.assertEqual(corrupt.attributes.writes, [])

    def test_visit_ticks_do_not_affect_lighting(self):
        visits = [NodeVisit("wild:elosern:700:900", 0, 0)]
        self.assertEqual(lit_district_keys_from_visits(visits, _DISTRICTS), frozenset({"vale"}))
        self.assertEqual(lit_district_keys_from_visits([], _DISTRICTS), frozenset())
