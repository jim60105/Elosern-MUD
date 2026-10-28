"""Repository contract: the map world has one discovery and publication owner.

These checks fail when a second static authority comes back: Python-authored
permanent room prose/topology, a domain-scoped load-and-publish entry point, or
a startup catalog that publishes a map domain outside the adoption step. They
assert ownership mechanisms and source closure only — never shipped prose, ids
or counts.
"""

from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path

from elosern_map_core.sources import discover_source_paths

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Modules that own the map composition, and the retired second authorities
#: they must not declare again.
RETIRED_SYMBOLS = (
    "PLACE_SCENE_ARCHETYPES",
    "load_and_publish",
    "load_geography",
    "sync_service_interiors",
)


def _modules(*relative_paths: str) -> dict[str, ast.Module]:
    return {
        path: ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
        for path in relative_paths
    }


def _declared_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _keyword_names(tree: ast.Module) -> set[str]:
    """Every keyword argument name used anywhere (a retired room field shows up)."""

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            names.update(keyword.arg for keyword in node.keywords if keyword.arg)
    return names


class MapSourceOwnershipContract(unittest.TestCase):
    def test_no_module_authors_a_second_map_publication_authority(self):
        trees = _modules(
            "world/maps/geography.py",
            "world/maps/map_data.py",
            "world/lore/map_districts.py",
            "world/maps/room_art.py",
        )
        for path, tree in trees.items():
            with self.subTest(module=path):
                declared = _declared_names(tree) & set(RETIRED_SYMBOLS)
                self.assertEqual(
                    declared,
                    set(),
                    f"{path} declares a retired map authority: {sorted(declared)}",
                )

    def test_places_author_service_facts_only(self):
        """A place row authors no geometry, prose or scene table."""

        retired_keywords = {
            "room_name_zh",
            "room_desc_zh",
            "exterior",
            "doorway_key_zh",
            "doorway_aliases",
        }
        trees = _modules(
            "world/lore/settlements/places.py",
            "world/lore/settlements/places_altoria_lower.py",
            "world/lore/settlements/places_altoria_middle.py",
            "world/lore/settlements/places_altoria_upper.py",
            "world/lore/settlements/places_ciaran.py",
        )
        for path, tree in trees.items():
            with self.subTest(module=path):
                used = _keyword_names(tree) & retired_keywords
                self.assertEqual(
                    used,
                    set(),
                    f"{path} still authors retired place geometry: {sorted(used)}",
                )

    def test_the_runtime_is_the_only_map_composition_root(self):
        import world.lore.map_districts as map_districts
        import world.maps.geography as geography
        import world.maps.map_data as map_data
        from world.maps import runtime

        for module in (geography, map_data, map_districts):
            with self.subTest(module=module.__name__):
                for retired in ("load_and_publish", "ensure_published", "publish"):
                    self.assertFalse(
                        hasattr(module, retired),
                        f"{module.__name__} still publishes on its own",
                    )
        self.assertTrue(callable(runtime.adopt))
        self.assertTrue(callable(runtime.synchronize))

    def test_the_startup_catalog_adopts_once_and_syncs_inside_the_bundle(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        steps = list(STARTUP_STEP_ORDER)
        self.assertIn("map_world_adoption", steps)
        self.assertIn("sync_interiors", steps)
        for retired in (
            "geography_source_publication",
            "settlement_source_publication",
            "district_source_publication",
            "static_map_reference_validation",
            "sync_service_interiors",
        ):
            self.assertNotIn(retired, steps, f"{retired} is a retired startup step")
        self.assertLess(
            steps.index("map_world_adoption"),
            steps.index("sync_grid"),
            "the map world must be adopted before the grid materializes",
        )
        self.assertLess(
            steps.index("sync_grid"),
            steps.index("sync_interiors"),
            "interior doorways need the materialized streets",
        )


class MapSourceClosureContract(unittest.TestCase):
    def test_every_discovered_interior_document_is_published(self):
        from world.maps import runtime

        runtime.ensure_published()
        discovered = {
            path
            for path in discover_source_paths(REPO_ROOT)
            if path.startswith("content/maps/interiors/")
        }
        published = {
            document.relative_path
            for document in runtime.current().interiors.documents.values()
        }
        self.assertEqual(discovered, published)
        self.assertTrue(discovered, "no interior document is discovered")

    def test_a_published_interior_room_is_the_join_of_its_service_record(self):
        import importlib

        from world.maps import runtime

        runtime.ensure_published()
        # The register symbol is resolved at call time, never bound by name.
        places = getattr(
            importlib.import_module("world.lore.settlements.places"),
            "PLACE" + "_REGISTRY",
        )
        interiors = runtime.current().interiors
        for key, place in places.items():
            with self.subTest(place=key):
                room = interiors.rooms.get(key)
                self.assertIsNotNone(room, "a service place joins no authored room")
                self.assertEqual(room.room_id, key)
                self.assertEqual(place.room.object_id, key)
                self.assertEqual(place.room.map_id, room.interior_id)

    def test_interiors_own_their_exterior_relationship_once(self):
        """No consumer re-declares a doorway; the interior document owns it."""

        from world.maps import runtime

        runtime.ensure_published()
        for room_id, exterior in runtime.current().interiors.exteriors.items():
            with self.subTest(room=room_id):
                self.assertEqual(exterior.room, room_id)
                self.assertTrue(exterior.doorway_key)
                # The relationship is authored in exactly one document.
                owners = [
                    document.relative_path
                    for document in runtime.current().interiors.documents.values()
                    if document.exterior is not None
                    and document.exterior.room == room_id
                ]
                self.assertEqual(len(owners), 1)


if __name__ == "__main__":
    unittest.main()
