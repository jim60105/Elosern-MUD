"""Data-contract test: bundled scene-art registry, collection and media identity contract

The ``unified-scene-catalog`` change declares the closed eleven-key scene-art
registry (``world/art/scene_definitions.py``) over the ACTUAL committed
collection under ``web/static/art/scenes``, which four prerequisite artwork
packs delivered. This module is that registry's data contract: it proves the
declarations cover the registered archetypes plus the explicit dream scene, the
declared terminal table is the approved one, the committed directory holds
exactly the eleven declared illustrations (each decoding, bounded, full-bleed
16:9 and distinct, with a provenance sidecar whose checksum is the shipped
bytes), and the STARTUP ADMISSION publishes exactly those declared keys under
``bundled-scene/<key>/<sha256>.webp`` identities from the fixed repository root.

Nothing here regenerates, downloads or re-encodes artwork, and nothing here
echoes a registry value as its own proof: a planted defect (a missing
declaration, an unregistered definition key, an invalid or unregistered
terminal reference, a missing/corrupt/oversized/non-landscape/symlinked image)
must be reported BY SCENE KEY, and a redirected root must admit only the
declarations it actually holds.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from world.art import scene_definitions
from world.art.scene_definitions import (
    BUNDLED_SCENE_CATALOG_EVENT,
    BUNDLED_SCENE_EXTENSION,
    BUNDLED_SCENE_MAX_FILE_BYTES,
    BUNDLED_SCENE_MEDIA_PREFIX,
    DREAM_SCENE_KEY,
    ROOM_ART_KEYS,
    SCENE_ART_DEFINITIONS,
    SCENE_ART_KEYS,
    SceneArtDefinition,
    bundled_asset_filename,
    bundled_identity,
    bundled_scene_root,
    current_bundled_scenes,
    is_registered_room_art_key,
    is_registered_scene_key,
    load_bundled_scene_catalog,
    reset_bundled_scenes,
    scene_art_collection_problems,
)
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENES_DIRECTORY = REPO_ROOT / "web/static/art/scenes"

# The approved design's §6.2 terminal table, pinned key by key: the terminal
# image a scene falls back to is authored data, never derived at runtime.
DECLARED_TERMINALS = {
    "forest_path": "forest_path",
    "tavern_interior": "city_street",
    "dungeon_interior": "forest_path",
    "city_street": "city_street",
    "wilderness_path": "forest_path",
    "mountain_path": "forest_path",
    "ruin_interior": "forest_path",
    "coastal_path": "forest_path",
    "cave_interior": "forest_path",
    "shrine_interior": "city_street",
    DREAM_SCENE_KEY: "city_street",
}

# Synthetic declarations for the defect plants: never a shipped key shape, so a
# planted failure cannot be confused with the authored collection.
_PLANTED_KEY = "t_synth_scene"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _planted(**overrides) -> dict[str, SceneArtDefinition]:
    """A copy of the authored declarations with synthetic replacements."""
    definitions = dict(SCENE_ART_DEFINITIONS)
    definitions.update(overrides)
    return definitions


@contextmanager
def _planted_scene_directory(files: dict[str, bytes]):
    """A temporary scene directory holding exactly the planted files."""
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        for key, payload in files.items():
            (root / bundled_asset_filename(key)).write_bytes(payload)
        yield root


class AuthoredRegistryTests(unittest.TestCase):
    """The declarations themselves, against the registries they must cover."""

    def test_every_registered_archetype_and_the_dream_scene_are_declared(self):
        """A registered archetype without a declaration is a contract hole."""
        from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

        registered = tuple(SCENE_ARCHETYPE_REGISTRY)
        self.assertEqual(SCENE_ART_KEYS, registered + (DREAM_SCENE_KEY,))
        self.assertNotIn(DREAM_SCENE_KEY, registered)
        self.assertEqual(len(SCENE_ART_KEYS), 11)
        self.assertEqual(
            len(set(SCENE_ART_KEYS)), 11, "a declaration may not repeat a scene key"
        )

    def test_the_declared_terminal_map_is_the_approved_table(self):
        """The terminal fallback is authored per scene, never inferred."""
        self.assertEqual(
            {key: definition.terminal_key for key, definition in SCENE_ART_DEFINITIONS.items()},
            DECLARED_TERMINALS,
        )
        self.assertEqual(scene_definitions.TERMINAL_SCENE_KEYS, ("city_street", "forest_path"))

    def test_the_registry_is_frozen_and_keyed_by_its_own_keys(self):
        """Consumers read declarations; nothing may extend or replace them."""
        self.assertEqual(
            {key: definition.key for key, definition in SCENE_ART_DEFINITIONS.items()},
            {key: key for key in SCENE_ART_KEYS},
        )
        for key in SCENE_ART_KEYS:
            with self.subTest(key=key):
                self.assertTrue(is_registered_scene_key(key))
        for key in ("", None, 7, _PLANTED_KEY, "forest_path/../city_street"):
            with self.subTest(key=repr(key)):
                self.assertFalse(is_registered_scene_key(key))

    def test_the_room_art_vocabulary_is_the_authored_place_projection(self):
        """Room-art keys are authored content, never ids or display names."""
        from world.lore.settlements.places import PLACE_REGISTRY

        self.assertEqual(ROOM_ART_KEYS, tuple(sorted(PLACE_REGISTRY)))
        self.assertTrue(ROOM_ART_KEYS, "the authored room-art vocabulary is empty")
        for key in ROOM_ART_KEYS:
            with self.subTest(key=key):
                self.assertTrue(is_registered_room_art_key(key))
        for key in ("", None, 7, _PLANTED_KEY, "t_synth:key"):
            with self.subTest(key=repr(key)):
                self.assertFalse(is_registered_room_art_key(key))

    def test_the_production_root_is_the_committed_scene_directory(self):
        """The trusted bundled root is the in-repo collection, never a mount."""
        self.assertEqual(bundled_scene_root(), SCENES_DIRECTORY)


class CommittedCollectionTests(unittest.TestCase):
    """The ACTUAL shipped eleven files, their sidecars and their uniqueness."""

    def test_the_collection_is_complete_and_valid(self):
        """The complete-collection contract passes with no problem at all."""
        self.assertEqual(scene_art_collection_problems(), ())

    @covers_requirement(
        "official-artwork-catalog::official-artwork-lives-outside-git-behind-one-directory-root-setting"
    )
    def test_the_directory_holds_exactly_the_declared_collection(self):
        """No missing declaration, no stray file, no undeclared key.

        The complete-collection gate the tracked-art exception defers to the
        scene catalog: the committed ``web/static/art/scenes/`` directory holds
        exactly the eleven declared illustrations and their sidecars — the
        closed set the exception names — and nothing else.
        """
        names = sorted(path.name for path in SCENES_DIRECTORY.iterdir())
        expected = sorted(
            [bundled_asset_filename(key) for key in SCENE_ART_KEYS]
            + [f"{key}.provenance.json" for key in SCENE_ART_KEYS]
        )
        self.assertEqual(names, expected)

    def test_every_required_image_is_bounded_full_bleed_and_distinct(self):
        """Eleven distinct committed illustrations, none over the file bound."""
        from PIL import Image

        digests: dict[str, str] = {}
        for key in SCENE_ART_KEYS:
            with self.subTest(key=key):
                path = SCENES_DIRECTORY / bundled_asset_filename(key)
                payload = path.read_bytes()
                self.assertLess(len(payload), BUNDLED_SCENE_MAX_FILE_BYTES)
                digests[key] = hashlib.sha256(payload).hexdigest()
                with Image.open(path) as image:
                    width, height = image.size
                self.assertGreater(width, 0)
                self.assertEqual(
                    width * 9,
                    height * 16,
                    f"{key}: the bundled scene must be a full-bleed 16:9 landscape",
                )
        self.assertEqual(
            len(set(digests.values())),
            len(SCENE_ART_KEYS),
            "the eleven bundled scenes must be eleven distinct images, never one "
            "file committed under several names",
        )

    def test_every_sidecar_records_the_shipped_bytes(self):
        """Each provenance record's checksum and size are the committed file."""
        for key in SCENE_ART_KEYS:
            with self.subTest(key=key):
                path = SCENES_DIRECTORY / bundled_asset_filename(key)
                payload = path.read_bytes()
                record = json.loads(
                    (SCENES_DIRECTORY / f"{key}.provenance.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(record["key"], key)
                self.assertEqual(
                    record["file"]["sha256"], hashlib.sha256(payload).hexdigest()
                )
                self.assertEqual(record["file"]["bytes"], len(payload))
                self.assertEqual(record["license"]["distribution"], "permitted")


class BrokenCoverageTests(unittest.TestCase):
    """Every defect the delta names is reported, and names its scene key."""

    def test_a_missing_declaration_names_the_archetype(self):
        definitions = _planted()
        del definitions["tavern_interior"]
        problems = scene_art_collection_problems(
            definitions=definitions, root=SCENES_DIRECTORY
        )
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("tavern_interior:"), problems)

    def test_an_unregistered_definition_key_names_its_key(self):
        definitions = _planted(
            **{_PLANTED_KEY: SceneArtDefinition(_PLANTED_KEY, "forest_path")}
        )
        problems = scene_art_collection_problems(
            definitions=definitions, root=SCENES_DIRECTORY
        )
        # The planted key is unregistered AND has no committed image; the
        # registry defect must still be reported, naming the key.
        self.assertIn(f"{_PLANTED_KEY}: unregistered scene-art key", problems)

    def test_an_invalid_terminal_names_its_key(self):
        definitions = _planted(
            forest_path=SceneArtDefinition("forest_path", _PLANTED_KEY)
        )
        problems = scene_art_collection_problems(
            definitions=definitions, root=SCENES_DIRECTORY
        )
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("forest_path:"), problems)
        self.assertIn(_PLANTED_KEY, problems[0])

    def test_a_terminal_without_a_required_image_names_its_key(self):
        definitions = _planted()
        del definitions["city_street"]
        definitions["tavern_interior"] = SceneArtDefinition(
            "tavern_interior", "city_street"
        )
        problems = scene_art_collection_problems(
            definitions=definitions, root=SCENES_DIRECTORY
        )
        # Every scene whose declared terminal is the removed key is reported
        # alongside the removed declaration itself.
        self.assertIn("city_street: no scene-art definition", problems)
        for key in ("tavern_interior", "shrine_interior", DREAM_SCENE_KEY):
            with self.subTest(key=key):
                self.assertIn(
                    f"{key}: terminal 'city_street' has no required image", problems
                )

    def test_a_missing_required_image_names_its_key(self):
        with tempfile.TemporaryDirectory() as scratch:
            problems = scene_art_collection_problems(root=Path(scratch))
        self.assertEqual(len(problems), len(SCENE_ART_KEYS), problems)
        for problem in problems:
            self.assertIn(problem.split(":", 1)[0], SCENE_ART_KEYS)
            self.assertIn("missing", problem)

    def test_a_corrupt_required_image_names_its_key(self):
        with _planted_scene_directory(files={"forest_path": b"not a webp at all"}) as root:
            problems = scene_art_collection_problems(root=root)
        self.assertTrue(
            any(
                problem.startswith("forest_path:") and "does not decode" in problem
                for problem in problems
            ),
            problems,
        )

    def test_a_truncated_required_image_names_its_key(self):
        payload = (SCENES_DIRECTORY / bundled_asset_filename("city_street")).read_bytes()
        with _planted_scene_directory(files={"city_street": payload[: len(payload) // 2]}) as root:
            problems = scene_art_collection_problems(root=root)
        self.assertTrue(
            any(
                problem.startswith("city_street:") and "does not decode" in problem
                for problem in problems
            ),
            problems,
        )

    def test_an_oversized_required_image_names_its_key(self):
        oversized = b"x" * (BUNDLED_SCENE_MAX_FILE_BYTES + 1)
        with _planted_scene_directory(files={"forest_path": oversized}) as root:
            problems = scene_art_collection_problems(root=root)
        self.assertTrue(
            any(
                problem.startswith("forest_path:")
                and "plain bounded regular file" in problem
                for problem in problems
            ),
            problems,
        )

    def test_a_non_landscape_required_image_names_its_key(self):
        import io

        from PIL import Image

        buffer = io.BytesIO()
        Image.new("L", (4, 4)).save(buffer, format="WEBP")
        with _planted_scene_directory(files={"forest_path": buffer.getvalue()}) as root:
            problems = scene_art_collection_problems(root=root)
        self.assertTrue(
            any(
                problem.startswith("forest_path:")
                and "full-bleed 16:9 landscape" in problem
                for problem in problems
            ),
            problems,
        )

    def test_a_symlinked_required_image_names_its_key(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            for key in SCENE_ART_KEYS:
                (root / bundled_asset_filename(key)).write_bytes(
                    (SCENES_DIRECTORY / bundled_asset_filename(key)).read_bytes()
                )
            target = root / bundled_asset_filename("forest_path")
            target.unlink()
            target.symlink_to(SCENES_DIRECTORY / bundled_asset_filename("city_street"))
            problems = scene_art_collection_problems(root=root)
        self.assertTrue(
            any(
                problem.startswith("forest_path:")
                and "unreadable" in problem
                for problem in problems
            ),
            problems,
        )


class BundledAdmissionTests(unittest.TestCase):
    """Startup admission of the committed collection and its snapshot."""

    def setUp(self):
        reset_bundled_scenes()
        self.addCleanup(reset_bundled_scenes)

    def test_the_admission_publishes_every_declaration_with_its_own_fingerprint(self):
        with patch.object(scene_definitions, "log_info") as logged:
            summary = load_bundled_scene_catalog()
        snapshot = current_bundled_scenes()
        self.assertEqual(summary["definitions"], 11)
        self.assertEqual(summary["images"], 11)
        self.assertEqual(summary["refused"], 0)
        self.assertEqual(summary["reason"], "bundled_root_indexed")
        self.assertFalse(summary["skipped"])
        self.assertEqual(len(snapshot), 11)
        self.assertEqual(
            logged.call_args.args[0], BUNDLED_SCENE_CATALOG_EVENT
        )
        self.assertEqual(logged.call_args.kwargs["context"]["images"], 11)
        for key in SCENE_ART_KEYS:
            with self.subTest(key=key):
                payload = (SCENES_DIRECTORY / bundled_asset_filename(key)).read_bytes()
                fingerprint = hashlib.sha256(payload).hexdigest()
                entry = snapshot.entry(key)
                self.assertIsNotNone(entry)
                self.assertEqual(entry.fingerprint, fingerprint)
                self.assertEqual(entry.identity, bundled_identity(key, fingerprint))
                self.assertEqual(
                    entry.identity, f"bundled-scene/{key}/{fingerprint}{BUNDLED_SCENE_EXTENSION}"
                )
                self.assertTrue(snapshot.admits(key, fingerprint))
                self.assertEqual(
                    snapshot.url_for(key),
                    f"{BUNDLED_SCENE_MEDIA_PREFIX}{key}/{fingerprint}{BUNDLED_SCENE_EXTENSION}",
                )
        self.assertEqual(
            len(snapshot.identities()), 11, "identities are unique per scene key"
        )

    def test_only_declared_keys_are_ever_admitted(self):
        """The closed allowlist is the declaration registry itself."""
        load_bundled_scene_catalog()
        snapshot = current_bundled_scenes()
        for key in (_PLANTED_KEY, "", "../forest_path", "Forest_Path"):
            with self.subTest(key=repr(key)):
                self.assertIsNone(snapshot.entry(key))
                self.assertFalse(snapshot.admits(key, "0" * 64))
                self.assertIsNone(snapshot.url_for(key))
        self.assertFalse(snapshot.admits("forest_path", "0" * 64))

    def test_a_redirected_root_admits_only_what_it_holds(self):
        """One planted illustration admits; its absent siblings are refused."""
        with tempfile.TemporaryDirectory() as scratch:
            scenes = Path(scratch) / "art" / "scenes"
            scenes.mkdir(parents=True)
            planted = scenes / bundled_asset_filename("forest_path")
            planted.write_bytes(
                (SCENES_DIRECTORY / bundled_asset_filename("forest_path")).read_bytes()
            )
            with override_settings(STATICFILES_DIRS=[scratch]):
                with patch.object(scene_definitions, "log_warn") as warned:
                    summary = load_bundled_scene_catalog()
                snapshot = current_bundled_scenes()
            self.assertEqual(summary["images"], 1)
            self.assertEqual(summary["refused"], 10)
            self.assertEqual(len(snapshot), 1)
            self.assertTrue(snapshot.admits("forest_path", _digest(planted)))
            self.assertIsNone(snapshot.entry("city_street"))
            reasons = [call.kwargs["context"]["reason"] for call in warned.call_args_list]
            self.assertEqual(reasons, ["image_missing"] * 10)

    def test_a_corrupt_file_is_refused_without_blocking_its_siblings(self):
        with tempfile.TemporaryDirectory() as scratch:
            scenes = Path(scratch) / "art" / "scenes"
            scenes.mkdir(parents=True)
            (scenes / bundled_asset_filename("forest_path")).write_bytes(
                b"definitely not an image"
            )
            (scenes / bundled_asset_filename("city_street")).write_bytes(
                (SCENES_DIRECTORY / bundled_asset_filename("city_street")).read_bytes()
            )
            with override_settings(STATICFILES_DIRS=[scratch]):
                summary = load_bundled_scene_catalog()
            snapshot = current_bundled_scenes()
            self.assertEqual(summary["images"], 1)
            self.assertEqual(summary["refused"], 10)
            self.assertTrue(snapshot.admits("city_street", _digest(
                scenes / bundled_asset_filename("city_street")
            )))
            self.assertIsNone(snapshot.entry("forest_path"))

    def test_an_absent_root_is_a_supported_no_bundled_art_configuration(self):
        with tempfile.TemporaryDirectory() as scratch:
            with override_settings(STATICFILES_DIRS=[scratch]):
                summary = load_bundled_scene_catalog()
            self.assertTrue(summary["skipped"])
            self.assertEqual(summary["reason"], "bundled_root_absent")
            self.assertEqual(summary["images"], 0)
            self.assertEqual(len(current_bundled_scenes()), 0)
            self.assertIsNone(current_bundled_scenes().url_for("forest_path"))

    def test_a_symlinked_root_is_refused(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "art").mkdir()
            (root / "art" / "scenes").symlink_to(SCENES_DIRECTORY, target_is_directory=True)
            with override_settings(STATICFILES_DIRS=[str(root)]):
                summary = load_bundled_scene_catalog()
            self.assertTrue(summary["skipped"])
            self.assertEqual(summary["reason"], "bundled_root_symlink")
            self.assertEqual(len(current_bundled_scenes()), 0)

    def test_the_reset_drops_every_admission(self):
        load_bundled_scene_catalog()
        self.assertEqual(len(current_bundled_scenes()), 11)
        reset_bundled_scenes()
        self.assertEqual(len(current_bundled_scenes()), 0)
        self.assertIsNone(current_bundled_scenes().entry("forest_path"))


if __name__ == "__main__":
    unittest.main()
