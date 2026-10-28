"""Mechanism tests for the authored permanent-interior source domain.

The interior documents are the sole authority for a permanent room's identity,
prose, scene/art facts and connections, and for the one exterior entrance
relationship it owns. These tests build synthetic documents only — no shipped
prose is pinned — and establish the composition and rejection rules the game
adapter depends on.
"""

from __future__ import annotations

import unittest

from elosern_map_core.codec import document_from_data
from elosern_map_core.references import interior_room_ref

from world.maps.interiors import (
    InteriorError,
    build_interiors,
)


def _document(
    interior_id: str,
    rooms: dict,
    *,
    exterior: dict | None = None,
    connections: tuple = (),
    interior_links: tuple = (),
):
    data = {
        "version": 1,
        "kind": "interior",
        "id": interior_id,
        "rooms": rooms,
        "connections": list(connections),
        "interior_links": list(interior_links),
        "exterior": exterior,
    }
    path = f"content/maps/interiors/{interior_id}.yaml"
    return document_from_data(path, data)


def _room(name: str = "合成房間", *, art_key: str | None = None) -> dict:
    return {
        "name_zh": name,
        "desc_zh": "Synthetic interior prose.",
        "scene_archetype": "t_synth_scene",
        "art_key": art_key,
    }


def _exterior(node: str, room: str, doorway: str, **extra) -> dict:
    return {
        "settlement": "t_map",
        "node": node,
        "room": room,
        "doorway_key": doorway,
        "doorway_aliases": [],
        **extra,
    }


class InteriorSourceTests(unittest.TestCase):
    def test_every_room_is_composed_with_its_own_authored_facts(self):
        documents = {
            "t_shop": _document(
                "t_shop",
                {"t_shop_room": _room("合成商店", art_key="t_shop_art")},
                exterior=_exterior("t_street", "t_shop_room", "合成店門"),
            ),
            "t_standalone": _document(
                "t_standalone",
                {"t_standalone_room": _room("合成空屋")},
            ),
        }

        snapshot = build_interiors(documents)

        room = snapshot.room("t_shop_room")
        self.assertEqual(room.interior_id, "t_shop")
        self.assertEqual(room.name_zh, "合成商店")
        self.assertEqual(room.scene_archetype, "t_synth_scene")
        self.assertEqual(room.art_key, "t_shop_art")
        self.assertEqual(snapshot.room_art_keys, {"t_shop_room": "t_shop_art"})
        # A document-level identity distinct from its rooms is the supported
        # shape: a future multi-room interior adds rooms without renaming the
        # document its layout file is keyed by.
        self.assertEqual(room.ref, interior_room_ref("t_shop", "t_shop_room"))
        self.assertEqual(
            snapshot.exteriors["t_shop_room"].doorway_key, "合成店門"
        )
        # A standalone interior needs no service record and no exterior.
        self.assertNotIn("t_standalone_room", snapshot.exteriors)
        self.assertEqual(snapshot.room("t_standalone_room").art_key, None)

    def test_a_multi_room_document_binds_one_entrance_and_internal_connections(self):
        documents = {
            "t_house": _document(
                "t_house",
                {
                    "t_house_hall": _room("合成前廳"),
                    "t_house_inner": _room("合成內室"),
                },
                connections=(
                    {"source": "t_house_hall", "destination": "t_house_inner", "label": "往內"},
                    {"source": "t_house_inner", "destination": "t_house_hall", "label": "往外"},
                ),
                exterior=_exterior("t_street", "t_house_hall", "合成宅門"),
            ),
            "t_neighbour": _document(
                "t_neighbour",
                {"t_neighbour_room": _room("合成鄰居")},
                interior_links=(
                    {
                        "source_room": "t_neighbour_room",
                        "target_interior": "t_house",
                        "target_room": "t_house_inner",
                        "label": "敲門",
                        "return_label": "回鄰居",
                    },
                ),
            ),
        }

        snapshot = build_interiors(documents)

        self.assertEqual(
            [connection.label for connection in snapshot.connections["t_house"]],
            ["往內", "往外"],
        )
        self.assertEqual(snapshot.exteriors["t_house_hall"].room, "t_house_hall")
        self.assertEqual(len(snapshot.interior_links), 1)
        self.assertEqual(snapshot.room("t_house_inner").interior_id, "t_house")

    def test_a_room_identity_is_globally_unique(self):
        documents = {
            "t_first": _document("t_first", {"t_shared": _room("合成甲")}),
            "t_second": _document("t_second", {"t_shared": _room("合成乙")}),
        }

        with self.assertRaises(InteriorError) as caught:
            build_interiors(documents)
        self.assertIn("t_shared", str(caught.exception))

    def test_an_exterior_must_open_into_a_room_of_its_own_document(self):
        documents = {
            "t_shop": _document(
                "t_shop",
                {"t_shop_room": _room()},
                exterior=_exterior("t_street", "t_other_room", "合成店門"),
            )
        }

        with self.assertRaises(InteriorError) as caught:
            build_interiors(documents)
        self.assertIn("t_other_room", str(caught.exception))

    def test_two_interiors_sharing_an_exterior_need_distinct_doorways(self):
        shared = {"node": "t_street"}
        documents = {
            "t_first": _document(
                "t_first",
                {"t_first_room": _room()},
                exterior=_exterior("t_street", "t_first_room", "合成甲門"),
            ),
            "t_second": _document(
                "t_second",
                {"t_second_room": _room()},
                exterior=_exterior("t_street", "t_second_room", "合成甲門"),
            ),
        }

        with self.assertRaises(InteriorError) as caught:
            build_interiors(documents)
        message = str(caught.exception)
        self.assertIn("t_first", message)
        self.assertIn("t_second", message)

        documents["t_second"] = _document(
            "t_second",
            {"t_second_room": _room()},
            exterior=_exterior("t_street", "t_second_room", "合成乙門"),
        )
        snapshot = build_interiors(documents)
        self.assertEqual(
            sorted(
                (exterior.doorway_key for exterior in snapshot.exteriors.values())
            ),
            ["合成乙門", "合成甲門"],
        )

    def test_an_interior_link_must_name_an_authored_target(self):
        documents = {
            "t_house": _document(
                "t_house",
                {"t_house_room": _room()},
                interior_links=(
                    {
                        "source_room": "t_house_room",
                        "target_interior": "t_absent",
                        "target_room": "t_absent_room",
                        "label": "敲門",
                        "return_label": None,
                    },
                ),
            )
        }

        with self.assertRaises(InteriorError) as caught:
            build_interiors(documents)
        self.assertIn("t_absent", str(caught.exception))

    def test_two_synthetic_worlds_have_distinct_identities(self):
        """A composed world's identity covers the documents it actually holds."""

        from world.tests.interior_fixture import build_synthetic_interiors

        first = build_synthetic_interiors(
            _document("t_first_world", {"t_first_room": _room()})
        )
        second = build_synthetic_interiors(
            _document("t_second_world", {"t_second_room": _room()})
        )
        self.assertNotEqual(first.identity, second.identity)

    def test_no_interior_reads_the_service_registry(self):
        """The interior domain is independent of service records."""

        import ast
        import inspect

        import world.maps.interiors as module

        tree = ast.parse(inspect.getsource(module))
        imported = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertFalse(
            [name for name in imported if name.startswith("world.lore.settlements")],
            "the interior domain must not import the service registry",
        )
        used = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        }
        self.assertNotIn("PLACE_REGISTRY", used)


if __name__ == "__main__":
    unittest.main()
