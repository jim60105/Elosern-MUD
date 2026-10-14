"""Tests for the read-only official-artwork catalog (official-artwork-catalog).

``EvenniaTestCase`` classes run :func:`world.art.official.load_catalog` against
synthetic artwork trees under a temporary ``ART_OFFICIAL_ROOT`` and prove: the
sorted snapshot indexes the closed ``monster``/``preset``/``npc``/``scene``/
``room`` layout with root-relative identities and deterministic ordering;
admission refuses
symlinked, out-of-root, unsupported, undecodable, oversized, nested, and
non-regular entries per entry without blocking unrelated valid artwork; the
optional per-content manifest supplies a default/rectangle/stage and degrades
whole (one bounded diagnostic) or per image (fitted rectangle) as the contract
requires; the per-file content fingerprint is computed exactly once at load and
never during resolution; an absent/empty/unreadable root is a supported no-art
configuration that acquires nothing; and load emits exactly one boundary event
plus budgeted per-entry diagnostics carrying no absolute root. The boot-step
registration is pinned against the real startup catalog.

``unified-scene-catalog`` added the two operator-only ``scene``/``room`` kinds;
their registry membership (the authored scene-art and room-art vocabularies),
the layout/reference vocabulary distinction and the bundled scene collection's
independent publish are pinned here too.

``unified-art-source-faults`` added the retained root-health fact: every
configuration of ``ART_OFFICIAL_ROOT`` (a default absence, an empty root, an
explicitly configured missing root, an unreadable root, a refused symlink or an
existing non-directory) starts normally and keeps its own bounded state and
fault flag. The per-source fault facts (a declared default, rejected identity,
malformed metadata, per-entry refusal reason) live in
``world.art.tests.test_art_source_faults``.
"""

import base64
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from world.art import official
from world.art.gallery import GalleryRecord, default_face_rect, identity_stage
from world.art.official import (
    OFFICIAL_CATALOG_EVENT,
    OFFICIAL_CONTENT_KINDS,
    OFFICIAL_LAYOUT_KINDS,
    OFFICIAL_MANIFEST_FILENAME,
    current_catalog,
    fingerprint_for,
    load_catalog,
    reset_catalog,
)
from world.art.scene_definitions import (
    BUNDLED_SCENE_CATALOG_EVENT,
    current_bundled_scenes,
    reset_bundled_scenes,
)
from world.art.store import ArtAssetRecord
from tools.spec_traceability import covers_requirement

# Deterministic valid PNG transport bytes: 1x1 and 1x2, so a fitted default
# rectangle and a per-image rectangle applicability differ measurably.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_TALL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAIAAAAW4yFwAAAAEElEQVR4nGPg5GBn"
    "YmBgAAAAogAb5lwhpwAAAABJRU5ErkJggg=="
)

# File-local synthetic content keys: the catalog owns the INDEXING mechanics,
# never shipped content, so no registry key of the game appears here.
_PRESET_KEY = "t_synth_preset"
_NPC_KEY = "t_synth_profile"
_MONSTER_KEY = "t_synth_species"
_SCENE_KEY = "t_synth_scene"
_ROOM_KEY = "t_synth_room"


def _real_png(width: int, height: int) -> bytes:
    """A real, decodable PNG of the given pixel size (the bounded-limit probe)."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class _CatalogCase(EvenniaTestCase):
    """A temporary official root plus a synthetic preset registry and sinks."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve() / "art-official"
        # The fixture's root is a settings override, never an environment
        # binding, so the import-time configuration provenance is pinned False
        # here: the module's cases stay environment-independent, and a
        # configured-root case opts in with its own nested override.
        self._settings = override_settings(
            ART_OFFICIAL_ROOT=str(self.root), ART_OFFICIAL_ROOT_EXPLICIT=False
        )
        self._settings.enable()
        reset_catalog()
        self.addCleanup(reset_catalog)
        reset_bundled_scenes()
        self.addCleanup(reset_bundled_scenes)
        registry = patch.object(
            official,
            "_registered_preset_keys",
            return_value=frozenset({_PRESET_KEY}),
        )
        self.registry = registry.start()
        self.addCleanup(registry.stop)
        info = patch.object(official, "log_info")
        self.info = info.start()
        self.addCleanup(info.stop)
        warn = patch.object(official, "log_warn")
        self.warn = warn.start()
        self.addCleanup(warn.stop)

    def tearDown(self):
        self._settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    # -- tree builders ----------------------------------------------------
    def image(self, kind, key, name, content=_TINY_PNG) -> Path:
        folder = self.root / kind / key
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(content)
        return path

    def manifest(self, kind, key, payload) -> Path:
        folder = self.root / kind / key
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / OFFICIAL_MANIFEST_FILENAME
        path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload),
            encoding="utf-8",
        )
        return path

    def load(self) -> dict:
        return load_catalog()

    def fresh_root(self, name: str):
        """Point both the tree builder and the setting at a brand-new root."""
        self.root = (Path(self.tempdir.name) / name).resolve()
        return override_settings(ART_OFFICIAL_ROOT=str(self.root))

    # -- event assertions -------------------------------------------------
    def contexts(self, mock) -> list[dict]:
        return [call.kwargs["context"] for call in mock.call_args_list]

    def reasons(self, mock) -> list[str]:
        return sorted(context.get("reason") for context in self.contexts(mock))

    def boundary(self) -> dict:
        self.assertEqual(
            len(self.info.call_args_list),
            1,
            msg=f"expected exactly one boundary event: {self.info.call_args_list}",
        )
        context = self.contexts(self.info)[0]
        self.assertEqual(context["phase"], "loaded")
        return context


class IndexingTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_valid_synthetic_content_indexes_with_root_relative_identities(self):
        self.image("monster", _MONSTER_KEY, "a.png")
        self.image("preset", _PRESET_KEY, "b.png")
        self.image("npc", _NPC_KEY, "c.png")
        # The layout's license notice is a plain root file, not content.
        (self.root / "LICENSE").write_text("notice", encoding="utf-8")
        summary = self.load()
        catalog = current_catalog()
        self.assertEqual(summary["images"], 3)
        self.assertEqual(summary["contents"], 3)
        self.assertEqual(summary["refused"], 0)
        identities = catalog.identities()
        self.assertEqual(
            identities,
            (
                f"monster/{_MONSTER_KEY}/a.png",
                f"npc/{_NPC_KEY}/c.png",
                f"preset/{_PRESET_KEY}/b.png",
            ),
        )
        entry = catalog.entry(f"preset/{_PRESET_KEY}/b.png")
        self.assertEqual(entry.kind, "preset")
        self.assertEqual(entry.key, _PRESET_KEY)
        self.assertEqual(entry.image_size, {"width": 1, "height": 1})
        self.assertEqual(entry.face_rect, default_face_rect({"width": 1, "height": 1}))
        self.assertEqual(entry.stage, identity_stage())
        self.assertEqual(entry.fingerprint, fingerprint_for(entry.identity))
        self.assertEqual(
            catalog.url_for(entry.identity),
            f"/art/official/{entry.fingerprint}/{entry.identity}",
        )
        self.assertIsNone(catalog.url_for("preset/t_synth_absent/x.png"))
        self.assertTrue(catalog.admits(entry.identity, entry.fingerprint))
        self.assertFalse(catalog.admits(entry.identity, "0" * 64))
        self.assertFalse(catalog.admits("preset/t_synth_absent/x.png", entry.fingerprint))
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_the_default_image_is_the_first_valid_filename_in_order(self):
        self.image("preset", _PRESET_KEY, "z.png")
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("preset", _PRESET_KEY, "m.png")
        # An undecodable first candidate is never the default: it is refused.
        self.image("preset", _PRESET_KEY, "0_broken.png", content=b"not an image")
        self.load()
        content = current_catalog().content("preset", _PRESET_KEY)
        self.assertEqual(
            content.images,
            tuple(f"preset/{_PRESET_KEY}/{name}" for name in ("a.png", "m.png", "z.png")),
        )
        self.assertEqual(content.default_identity, f"preset/{_PRESET_KEY}/a.png")

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_unsupported_kind_directories_are_skipped_with_a_diagnostic(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("weapons", "t_synth_weapon", "b.png")
        (self.root / "notes.txt").write_text("x", encoding="utf-8")
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertIn("unknown_kind_directory_skipped", self.reasons(self.warn))
        self.assertIsNone(current_catalog().content("weapons", "t_synth_weapon"))

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_an_unknown_registry_reference_is_skipped_not_fatal(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("preset", "t_synth_ghost", "b.png")
        summary = self.load()
        self.assertEqual(
            [context["key"] for context in self.contexts(self.warn)],
            ["t_synth_ghost"],
        )
        self.assertIn("unknown_registry_reference", self.reasons(self.warn))
        self.assertEqual(summary["images"], 1)
        self.assertIsNone(current_catalog().content("preset", "t_synth_ghost"))
        self.assertIsNotNone(current_catalog().content("preset", _PRESET_KEY))

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_a_content_key_outside_the_stable_key_contract_is_skipped(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("npc", "bad:key", "b.png")
        self.image("npc", "k" * 65, "c.png")
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(
            self.reasons(self.warn),
            ["invalid_content_key_skipped", "invalid_content_key_skipped"],
        )

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_resolution_answers_from_the_snapshot_without_re_walking_the_root(self):
        identity = f"preset/{_PRESET_KEY}/a.png"
        self.image("preset", _PRESET_KEY, "a.png")
        self.load()
        catalog = current_catalog()
        fingerprint = catalog.fingerprint_for(identity)
        # The snapshot is the only source: the tree is gone, the answers remain.
        for path in sorted(self.root.rglob("*"), reverse=True):
            if path.is_dir():
                path.rmdir()
            else:
                path.unlink()
        for _ in range(10):
            self.assertEqual(catalog.fingerprint_for(identity), fingerprint)
            self.assertEqual(catalog.entry(identity).identity, identity)
            self.assertTrue(catalog.admits(identity, fingerprint))
            self.assertEqual(
                catalog.url_for(identity), f"/art/official/{fingerprint}/{identity}"
            )


class AdmissionRefusalTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_an_out_of_root_symlink_is_refused_while_siblings_index(self):
        self.image("preset", _PRESET_KEY, "ok.png")
        outside = Path(self.tempdir.name) / "precious.png"
        outside.write_bytes(_TINY_PNG)
        (self.root / "preset" / _PRESET_KEY / "linked.png").symlink_to(outside)
        (self.root / "preset" / "t_synth_linked").symlink_to(outside.parent)
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(
            self.reasons(self.warn),
            sorted(["symlink_skipped", "symlinked_content_directory_skipped"]),
        )
        self.assertIsNone(current_catalog().entry(f"preset/{_PRESET_KEY}/linked.png"))
        self.assertIsNotNone(current_catalog().entry(f"preset/{_PRESET_KEY}/ok.png"))
        self.assertTrue(outside.exists())

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_unsupported_and_nested_and_non_regular_entries_are_refused(self):
        self.image("preset", _PRESET_KEY, "ok.png")
        folder = self.root / "preset" / _PRESET_KEY
        (folder / "unsupported.jxl").write_bytes(_TINY_PNG)
        (folder / "uppercase.PNG").write_bytes(_TINY_PNG)
        (folder / "nested").mkdir()
        os.mkfifo(folder / "pipe")
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(
            self.reasons(self.warn),
            sorted([
                "nested_directory_skipped",
                "non_regular_entry_skipped",
                "unsupported_extension_skipped",
                "unsupported_extension_skipped",
            ]),
        )

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_an_undecodable_image_is_refused_while_siblings_index(self):
        self.image("preset", _PRESET_KEY, "ok.png")
        self.image("preset", _PRESET_KEY, "broken.png", content=b"definitely not an image")
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(self.reasons(self.warn), ["image_undecodable"])

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_an_image_over_the_dimension_limit_is_refused(self):
        self.image("preset", _PRESET_KEY, "ok.png")
        self.image("preset", _PRESET_KEY, "wide.png", content=_real_png(4, 4))
        with override_settings(
            ART_SD_MAX_IMAGE_DIMENSIONS=2, ART_SD_MAX_IMAGE_PIXELS=1024
        ):
            summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(summary["refused"], 1)
        self.assertEqual(self.reasons(self.warn), ["image_too_large"])
        self.assertIsNotNone(current_catalog().entry(f"preset/{_PRESET_KEY}/ok.png"))
        self.assertIsNone(current_catalog().entry(f"preset/{_PRESET_KEY}/wide.png"))

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_an_image_over_the_pixel_limit_is_refused(self):
        self.image("preset", _PRESET_KEY, "ok.png")
        self.image("preset", _PRESET_KEY, "dense.png", content=_real_png(2, 2))
        with override_settings(
            ART_SD_MAX_IMAGE_DIMENSIONS=64, ART_SD_MAX_IMAGE_PIXELS=3
        ):
            summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(summary["refused"], 1)
        self.assertEqual(self.reasons(self.warn), ["image_too_large"])

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_a_refused_entry_never_blocks_unrelated_artwork(self):
        self.image("monster", _MONSTER_KEY, "ok.png")
        self.image("preset", _PRESET_KEY, "ok.png")
        self.image("npc", _NPC_KEY, "ok.png")
        self.image("preset", _PRESET_KEY, "bad.jxl", content=b"x")
        self.image("npc", _NPC_KEY, "bad.png", content=b"x")
        summary = self.load()
        self.assertEqual(summary["images"], 3)
        self.assertEqual(summary["contents"], 3)
        self.assertEqual(summary["refused"], 2)
        catalog = current_catalog()
        for kind, key in (
            ("monster", _MONSTER_KEY),
            ("preset", _PRESET_KEY),
            ("npc", _NPC_KEY),
        ):
            self.assertIsNotNone(catalog.entry(f"{kind}/{key}/ok.png"))


class SceneAndRoomKindTests(_CatalogCase):
    """The two operator-only content kinds this change adds to the index.

    The synthetic registry patches mirror the preset seam: the catalog owns
    the indexing mechanics, so these cases never name shipped content. The
    authored vocabularies themselves are exercised in
    :class:`AuthoredKeyAdmissionTests` below.
    """

    def setUp(self):
        super().setUp()
        scene_registry = patch.object(
            official, "_registered_scene_keys", return_value=frozenset({_SCENE_KEY})
        )
        self.addCleanup(scene_registry.stop)
        scene_registry.start()
        room_registry = patch.object(
            official, "_registered_room_art_keys", return_value=frozenset({_ROOM_KEY})
        )
        self.addCleanup(room_registry.stop)
        room_registry.start()

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_scene_and_room_content_index_with_root_relative_identities(self):
        scene_path = self.image("scene", _SCENE_KEY, "a.png")
        room_path = self.image("room", _ROOM_KEY, "b.png")
        summary = self.load()
        self.assertEqual(summary["contents"], 2)
        self.assertEqual(summary["images"], 2)
        catalog = current_catalog()
        for kind, key, path in (
            ("scene", _SCENE_KEY, scene_path),
            ("room", _ROOM_KEY, room_path),
        ):
            with self.subTest(kind=kind):
                identity = f"{kind}/{key}/{path.name}"
                entry = catalog.entry(identity)
                self.assertIsNotNone(entry)
                self.assertEqual(entry.kind, kind)
                self.assertEqual(entry.key, key)
                self.assertEqual(
                    entry.fingerprint, hashlib.sha256(path.read_bytes()).hexdigest()
                )
                self.assertEqual(catalog.content(kind, key).default_identity, identity)
                self.assertIsNotNone(catalog.url_for(identity))

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_an_unknown_scene_or_room_key_is_skipped_not_fatal(self):
        self.image("scene", _SCENE_KEY, "a.png")
        self.image("scene", "t_synth_ghost", "b.png")
        self.image("room", _ROOM_KEY, "a.png")
        self.image("room", "t_synth_ghost", "b.png")
        summary = self.load()
        self.assertEqual(summary["contents"], 2)
        self.assertEqual(summary["images"], 2)
        unknown = [
            context
            for context in self.contexts(self.warn)
            if context["reason"] == "unknown_registry_reference"
        ]
        self.assertEqual(sorted(context["kind"] for context in unknown), ["room", "scene"])
        for context in unknown:
            self.assertEqual(context["key"], "t_synth_ghost")

    @covers_requirement(
        "official-artwork-catalog::admission-admits-only-valid-images-confined-to-the-configured-root"
    )
    def test_a_scene_directory_refuses_bad_entries_per_entry(self):
        self.image("scene", _SCENE_KEY, "ok.png")
        folder = self.root / "scene" / _SCENE_KEY
        (folder / "broken.png").write_bytes(b"definitely not an image")
        (folder / "unsupported.jxl").write_bytes(_TINY_PNG)
        outside = Path(self.tempdir.name) / "precious.png"
        outside.write_bytes(_TINY_PNG)
        (folder / "link.png").symlink_to(outside)
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertEqual(summary["refused"], 3)
        self.assertIsNotNone(
            current_catalog().entry(f"scene/{_SCENE_KEY}/ok.png")
        )
        self.assertTrue(outside.exists())

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_scene_directory_uses_filename_order_or_its_manifest_default(self):
        self.image("scene", _SCENE_KEY, "z.png")
        self.image("scene", _SCENE_KEY, "a.png")
        self.load()
        self.assertEqual(
            current_catalog().content("scene", _SCENE_KEY).default_identity,
            f"scene/{_SCENE_KEY}/a.png",
        )
        self.manifest("scene", _SCENE_KEY, {"default": "z.png"})
        self.load()
        self.assertEqual(
            current_catalog().content("scene", _SCENE_KEY).default_identity,
            f"scene/{_SCENE_KEY}/z.png",
        )

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_a_bundled_identity_directory_is_never_an_operator_content_kind(self):
        """The bundled namespace can never be mounted into the operator root."""
        self.image("scene", _SCENE_KEY, "a.png")
        bundled = self.root / "bundled-scene" / _SCENE_KEY
        bundled.mkdir(parents=True)
        (bundled / "a.png").write_bytes(_TINY_PNG)
        summary = self.load()
        self.assertEqual(summary["images"], 1)
        self.assertIsNone(current_catalog().entry(f"bundled-scene/{_SCENE_KEY}/a.png"))
        skipped = [
            context
            for context in self.contexts(self.warn)
            if context["reason"] == "unknown_kind_directory_skipped"
        ]
        self.assertEqual([context["entry"] for context in skipped], ["bundled-scene"])


class AuthoredKeyAdmissionTests(_CatalogCase):
    """Registry membership as the running game declares it (no patched seam)."""

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_a_declared_scene_key_and_a_declared_room_key_index(self):
        from world.art import scene_definitions

        scene_key = scene_definitions.SCENE_ART_KEYS[0]
        room_key = scene_definitions.ROOM_ART_KEYS[0]
        self.image("scene", scene_key, "a.png")
        self.image("room", room_key, "a.png")
        self.image("scene", "t_synth_ghost", "a.png")
        summary = self.load()
        self.assertEqual(summary["images"], 2)
        self.assertIsNotNone(current_catalog().entry(f"scene/{scene_key}/a.png"))
        self.assertIsNotNone(current_catalog().entry(f"room/{room_key}/a.png"))
        self.assertIsNone(current_catalog().entry("scene/t_synth_ghost/a.png"))


class ManifestTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_missing_manifest_is_silent_with_fitted_defaults(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.load()
        entry = current_catalog().entry(f"preset/{_PRESET_KEY}/a.png")
        self.assertEqual(entry.face_rect, default_face_rect({"width": 1, "height": 1}))
        self.assertEqual(entry.stage, identity_stage())
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_valid_manifest_supplies_default_rectangle_and_stage(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("preset", _PRESET_KEY, "b.png")
        rect = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
        stage = {"scale": 1.5, "x": 0.25, "y": -0.25}
        self.manifest(
            "preset",
            _PRESET_KEY,
            {"default": "b.png", "face_rect": rect, "stage": stage},
        )
        self.load()
        catalog = current_catalog()
        self.assertEqual(
            catalog.content("preset", _PRESET_KEY).default_identity,
            f"preset/{_PRESET_KEY}/b.png",
        )
        for name in ("a.png", "b.png"):
            entry = catalog.entry(f"preset/{_PRESET_KEY}/{name}")
            self.assertEqual(entry.face_rect, rect)
            self.assertEqual(entry.stage, stage)
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_invalid_manifest_degrades_whole_with_one_diagnostic(self):
        cases = {
            "{not json": "manifest_unreadable",
            "[]": "manifest_not_a_valid_object",
            '{"default": "a.png", "package_id": "x"}': "manifest_not_a_valid_object",
            '{"stage": {"scale": 9}}': "manifest_invalid_stage",
            '{"face_rect": {"x": "bad", "y": 0.1, "w": 0.5, "h": 0.5}}': (
                "manifest_invalid_face_rect"
            ),
            '{"default": "missing.png"}': "manifest_default_not_an_admitted_file",
            '{"default": "broken.png"}': "manifest_default_not_an_admitted_file",
        }
        for index, (payload, expected) in enumerate(cases.items()):
            with self.subTest(payload=payload):
                self.warn.reset_mock()
                reset_catalog()
                with self.fresh_root(f"case-{index}"):
                    self.image("preset", _PRESET_KEY, "a.png")
                    self.image("preset", _PRESET_KEY, "broken.png", content=b"x")
                    self.manifest("preset", _PRESET_KEY, payload)
                    self.load()
                manifest_reasons = [
                    reason
                    for reason in self.reasons(self.warn)
                    if reason.startswith("manifest_")
                ]
                self.assertEqual(
                    manifest_reasons,
                    [expected],
                    msg=f"exactly one manifest diagnostic for {payload!r}",
                )
                content = current_catalog().content("preset", _PRESET_KEY)
                self.assertEqual(
                    content.default_identity, f"preset/{_PRESET_KEY}/a.png"
                )
                entry = current_catalog().entry(f"preset/{_PRESET_KEY}/a.png")
                self.assertEqual(
                    entry.face_rect, default_face_rect({"width": 1, "height": 1})
                )
                self.assertEqual(entry.stage, identity_stage())

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_a_rectangle_invalid_for_one_image_is_fitted_for_that_image_only(self):
        self.image("preset", _PRESET_KEY, "square.png")
        self.image("preset", _PRESET_KEY, "tall.png", content=_TALL_PNG)
        # Pixel-square on 1x1 (0.5 x 0.9 -> 0.5 vs 0.9) but not on 1x2
        # (0.5 vs 1.8, more than the one-pixel tolerance).
        rect = {"x": 0.1, "y": 0.05, "w": 0.5, "h": 0.9}
        stage = {"scale": 1.2, "x": 0.1, "y": 0.1}
        self.manifest("preset", _PRESET_KEY, {"face_rect": rect, "stage": stage})
        self.load()
        catalog = current_catalog()
        square = catalog.entry(f"preset/{_PRESET_KEY}/square.png")
        tall = catalog.entry(f"preset/{_PRESET_KEY}/tall.png")
        self.assertEqual(square.face_rect, rect)
        self.assertEqual(tall.face_rect, default_face_rect({"width": 1, "height": 2}))
        self.assertEqual(self.reasons(self.warn), ["manifest_face_rect_inapplicable"])
        # The declared stage is independent of the rectangle and survives.
        self.assertEqual(square.stage, stage)
        self.assertEqual(tall.stage, stage)

    @covers_requirement(
        "official-artwork-catalog::the-optional-per-content-manifest-follows-the-seed-metadata-convention"
    )
    def test_an_unreadable_manifest_degrades_with_one_diagnostic(self):
        self.image("preset", _PRESET_KEY, "a.png")
        folder = self.root / "preset" / _PRESET_KEY
        (folder / OFFICIAL_MANIFEST_FILENAME).mkdir()
        self.load()
        self.assertEqual(self.reasons(self.warn), ["manifest_unreadable"])
        entry = current_catalog().entry(f"preset/{_PRESET_KEY}/a.png")
        self.assertEqual(entry.face_rect, default_face_rect({"width": 1, "height": 1}))


class FingerprintTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::each-indexed-image-carries-a-startup-computed-content-fingerprint"
    )
    def test_replacing_bytes_changes_the_fingerprint_after_a_reload(self):
        identity = f"preset/{_PRESET_KEY}/a.png"
        path = self.image("preset", _PRESET_KEY, "a.png")
        self.load()
        first = current_catalog().fingerprint_for(identity)
        path.write_bytes(_TALL_PNG)
        self.load()
        second = current_catalog().fingerprint_for(identity)
        self.assertNotEqual(second, first)
        self.assertFalse(current_catalog().admits(identity, first))
        self.assertTrue(current_catalog().admits(identity, second))
        self.assertEqual(
            current_catalog().entry(identity).image_size, {"width": 1, "height": 2}
        )

    @covers_requirement(
        "official-artwork-catalog::each-indexed-image-carries-a-startup-computed-content-fingerprint"
    )
    def test_hashing_happens_once_at_load_and_never_during_resolution(self):
        identity = f"preset/{_PRESET_KEY}/a.png"
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("npc", _NPC_KEY, "b.png")
        real = official._content_fingerprint
        with patch.object(official, "_content_fingerprint", side_effect=real) as spy:
            self.load()
            self.assertEqual(spy.call_count, 2)
            catalog = current_catalog()
            fingerprint = catalog.fingerprint_for(identity)
            for _ in range(100):
                catalog.entry(identity)
                catalog.fingerprint_for(identity)
                catalog.admits(identity, fingerprint)
                catalog.url_for(identity)
                catalog.content("preset", _PRESET_KEY)
            self.assertEqual(spy.call_count, 2)


class StartupConfigurationTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_absent_root_is_a_supported_no_art_configuration(self):
        self.root = Path(self.tempdir.name) / "absent"
        with patch("socket.socket", side_effect=AssertionError("no acquisition")):
            with override_settings(ART_OFFICIAL_ROOT=str(self.root)):
                summary = self.load()
        self.assertEqual(len(current_catalog()), 0)
        self.assertTrue(summary["skipped"])
        self.assertFalse(self.root.exists())
        self.warn.assert_not_called()
        context = self.boundary()
        self.assertEqual(context["reason"], "official_root_absent")
        self.assertEqual(context["images"], 0)
        self.assertEqual(context["refused"], 0)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_empty_root_reports_the_empty_condition(self):
        self.root.mkdir(parents=True)
        summary = self.load()
        self.assertEqual(len(current_catalog()), 0)
        self.assertTrue(summary["skipped"])
        self.warn.assert_not_called()
        self.assertEqual(self.boundary()["reason"], "official_root_empty")

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_unset_setting_and_an_unreadable_root_report_their_condition(self):
        with override_settings(ART_OFFICIAL_ROOT=""):
            self.load()
        self.assertEqual(self.boundary()["reason"], "official_root_unset")
        self.warn.reset_mock()
        self.info.reset_mock()
        reset_catalog()
        self.root.mkdir(parents=True)
        with patch.object(official, "open_dir_fd", side_effect=OSError("denied")):
            self.load()
        self.assertEqual(self.boundary()["reason"], "official_root_unreadable")
        self.assertEqual(len(current_catalog()), 0)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_symlinked_root_is_refused_with_one_bounded_event(self):
        target = Path(self.tempdir.name) / "real-root"
        (target / "preset" / _PRESET_KEY).mkdir(parents=True)
        (target / "preset" / _PRESET_KEY / "a.png").write_bytes(_TINY_PNG)
        self.root.symlink_to(target)
        summary = self.load()
        self.assertTrue(summary["skipped"])
        self.assertEqual(self.boundary()["reason"], "official_root_symlink")
        self.assertEqual(len(current_catalog()), 0)

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_default_absent_root_retains_no_availability_fault(self):
        """An absent DEFAULT optional root is normal, never a retained failure.

        The provenance is what separates the two absences: the same missing path
        is the documented no-art configuration without an explicit binding and a
        retained availability failure with one.
        """
        absent = Path(self.tempdir.name) / "absent"
        with override_settings(
            ART_OFFICIAL_ROOT=str(absent), ART_OFFICIAL_ROOT_EXPLICIT=False
        ):
            summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual(
            (health.state, health.configured, health.fault),
            ("absent_default", False, False),
        )
        self.assertEqual(health.reason, "official_root_absent")
        self.assertEqual(summary["root_state"], "absent_default")
        self.assertFalse(summary["root_fault"])
        self.assertEqual(len(current_catalog()), 0)
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_configured_missing_root_retains_an_unavailable_fault(self):
        """A configured root that is missing survives the empty index as a fault."""
        absent = Path(self.tempdir.name) / "absent"
        with override_settings(
            ART_OFFICIAL_ROOT=str(absent), ART_OFFICIAL_ROOT_EXPLICIT=True
        ):
            summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual(
            (health.state, health.configured, health.fault),
            ("unavailable", True, True),
        )
        self.assertEqual(health.reason, "official_root_absent")
        self.assertEqual(summary["root_state"], "unavailable")
        self.assertTrue(summary["root_fault"])
        self.assertEqual(len(current_catalog()), 0)
        # The retained failure is observable: exactly one bounded diagnostic
        # naming the failure category, with no absolute root in its context.
        self.assertEqual(self.reasons(self.warn), ["source_unavailable"])
        event = self.contexts(self.warn)[0]
        self.assertEqual(event["root_state"], "unavailable")
        self.assertTrue(event["configured"])
        self.assertNotIn(str(absent), str(event))

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_empty_root_retains_the_healthy_empty_state(self):
        """A readable root that holds nothing is healthy, not a failure."""
        self.root.mkdir(parents=True)
        summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual(
            (health.state, health.configured, health.fault),
            ("empty", False, False),
        )
        self.assertEqual(summary["root_state"], "empty")
        self.assertFalse(summary["root_fault"])
        self.warn.assert_not_called()

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_an_unreadable_root_retains_an_unavailable_fault_either_way(self):
        """An I/O failure is a retained fault at inspection and at open time."""
        self.root.mkdir(parents=True)
        # Inspection: the root itself cannot even be stat'ed (an unsearchable
        # parent). Patched narrowly, because the load returns on its first call.
        with patch("world.art.official.os.lstat", side_effect=PermissionError("denied")):
            self.load()
        health = current_catalog().root_health()
        self.assertEqual(
            (health.state, health.configured, health.fault),
            ("unavailable", False, True),
        )
        self.assertEqual(health.reason, "official_root_unreadable")
        self.assertEqual(self.reasons(self.warn), ["source_unavailable"])
        self.warn.reset_mock()
        self.info.reset_mock()
        reset_catalog()
        # Open: the directory entry exists but cannot be opened.
        with patch.object(official, "open_dir_fd", side_effect=OSError("denied")):
            self.load()
        self.assertEqual(current_catalog().root_health().fault, True)
        self.assertEqual(self.boundary()["reason"], "official_root_unreadable")
        self.assertEqual(self.reasons(self.warn), ["source_unavailable"])

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_a_refused_or_unusable_root_retains_an_unavailable_fault(self):
        """A refused symlink and an existing non-directory are never "absent"."""
        target = Path(self.tempdir.name) / "real-root"
        target.mkdir(parents=True)
        self.root.symlink_to(target)
        self.load()
        self.assertEqual(
            current_catalog().root_health().state,
            "unavailable",
        )
        self.assertTrue(current_catalog().root_health().fault)
        self.warn.reset_mock()
        self.info.reset_mock()
        reset_catalog()
        # An existing regular file at the configured root: the walk can never
        # read it, so it is a retained failure rather than a normal absence.
        plain = Path(self.tempdir.name) / "not-a-directory"
        plain.write_text("not artwork", encoding="utf-8")
        with override_settings(
            ART_OFFICIAL_ROOT=str(plain), ART_OFFICIAL_ROOT_EXPLICIT=False
        ):
            summary = self.load()
        health = current_catalog().root_health()
        self.assertEqual(health.reason, "official_root_not_a_directory")
        self.assertEqual(health.state, "unavailable")
        self.assertTrue(health.fault)
        self.assertTrue(summary["root_fault"])
        self.assertEqual(self.boundary()["reason"], "official_root_not_a_directory")


class ObservabilityTests(_CatalogCase):
    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_one_boundary_event_reports_counts_and_budgeted_refusals(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("npc", _NPC_KEY, "b.png")
        self.image("preset", _PRESET_KEY, "bad.jpg", content=b"x")
        self.image("npc", _NPC_KEY, "bad.jxl")
        self.load()
        context = self.boundary()
        self.assertEqual(context["reason"], "official_root_indexed")
        self.assertEqual(context["contents"], 2)
        self.assertEqual(context["images"], 2)
        self.assertEqual(context["refused"], 2)
        self.assertEqual(context["diagnostics"], 2)
        self.assertEqual(context["suppressed_diagnostics"], 0)
        self.assertEqual(len(self.warn.call_args_list), 2)
        for event in self.contexts(self.warn):
            self.assertEqual(event["phase"], "diagnostic")
            self.assertIn("kind", event)
            self.assertIn("key", event)
            self.assertIn("entry", event)

    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_refusals_stay_within_the_budget_and_report_the_suppressed_count(self):
        excess = 5
        for index in range(official._MAX_DIAGNOSTICS + excess):
            self.image("preset", _PRESET_KEY, f"bad{index:03d}.jxl")
        self.load()
        self.assertEqual(len(self.warn.call_args_list), official._MAX_DIAGNOSTICS)
        context = self.boundary()
        self.assertEqual(context["diagnostics"], official._MAX_DIAGNOSTICS)
        self.assertEqual(context["suppressed_diagnostics"], excess)
        self.assertEqual(context["refused"], official._MAX_DIAGNOSTICS + excess)

    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_no_event_context_carries_an_absolute_filesystem_root(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.image("preset", "t_synth_ghost", "b.png")
        self.image("npc", _NPC_KEY, "bad.jxl")
        self.manifest("preset", _PRESET_KEY, "{not json")
        self.load()
        absolute = str(self.root)
        for mock in (self.info, self.warn):
            for context in self.contexts(mock):
                for key, value in context.items():
                    with self.subTest(key=key, value=value):
                        self.assertNotIn(absolute, str(value))
                        self.assertNotIn(str(self.tempdir.name), str(value))

    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_catalog_load_writes_no_game_state_and_leaves_the_root_untouched(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.manifest("preset", _PRESET_KEY, {"default": "a.png"})
        before = {
            path: path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }
        self.load()
        after = {
            path: path.read_bytes()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }
        self.assertEqual(before, after)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)
        self.assertEqual(GalleryRecord.objects.count(), 0)

    @covers_requirement(
        "official-artwork-catalog::catalog-load-and-refusals-are-observable-through-the-facade"
    )
    def test_the_event_id_is_the_documented_boundary(self):
        self.image("preset", _PRESET_KEY, "a.png")
        self.load()
        self.assertEqual(OFFICIAL_CATALOG_EVENT, "official_art_catalog_loaded")
        self.assertEqual(self.info.call_args.args[0], OFFICIAL_CATALOG_EVENT)
        for call in self.warn.call_args_list:
            self.assertEqual(call.args[0], OFFICIAL_CATALOG_EVENT)


class BundledCollectionPublishTests(_CatalogCase):
    """The bundled scene collection is published by the same startup step.

    Its publish is independent of the operator root: it runs on every exit
    path (including the no-operator-art configuration bundled art exists for),
    it never touches this catalog's counts, snapshot or single boundary event,
    and the two identity families stay disjoint.
    """

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_load_publishes_the_bundled_collection_beside_the_operator_snapshot(self):
        from world.art import scene_definitions

        self.image("preset", _PRESET_KEY, "a.png")
        with patch.object(scene_definitions, "log_info") as bundled_info:
            summary = self.load()
        self.assertEqual(summary["images"], 1)
        context = self.boundary()
        self.assertEqual(context["reason"], "official_root_indexed")
        self.assertEqual(len(current_bundled_scenes()), 11)
        self.assertEqual(bundled_info.call_args.args[0], BUNDLED_SCENE_CATALOG_EVENT)
        self.assertEqual(bundled_info.call_args.kwargs["context"]["images"], 11)
        for identity in current_catalog().identities():
            self.assertFalse(identity.startswith("bundled-scene/"))
        for identity in current_bundled_scenes().identities():
            self.assertTrue(identity.startswith("bundled-scene/"))
            self.assertIsNone(current_catalog().entry(identity))

    @covers_requirement(
        "official-artwork-catalog::a-missing-or-empty-official-root-is-a-valid-no-art-configuration"
    )
    def test_the_bundled_collection_is_published_without_an_operator_root(self):
        self.root = Path(self.tempdir.name) / "absent"
        with override_settings(ART_OFFICIAL_ROOT=str(self.root)):
            summary = self.load()
        self.assertTrue(summary["skipped"])
        self.assertEqual(len(current_catalog()), 0)
        self.assertEqual(len(current_bundled_scenes()), 11)


class StartupWiringTests(unittest.TestCase):
    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_the_boot_step_sits_between_the_seed_mirror_and_the_art_sync(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertIn("art_official_catalog", STARTUP_STEP_ORDER)
        self.assertLess(
            STARTUP_STEP_ORDER.index("art_seed_sync"),
            STARTUP_STEP_ORDER.index("art_official_catalog"),
        )
        self.assertLess(
            STARTUP_STEP_ORDER.index("art_official_catalog"),
            STARTUP_STEP_ORDER.index("art_sync_all"),
        )


class OfficialReferenceContractTests(unittest.TestCase):
    """The single origin of the content vocabulary and the key grammar.

    ``world.art.official`` owns the closed content-kind vocabulary and the
    admission key contract; ``world.art.official_refs`` (the
    ``official-content-provenance`` capability) duplicates the vocabulary as
    literals BY DESIGN so its leaf module need not import this one's Pillow /
    Django / no-follow chain, and delegates the key grammar to the one shared
    predicate. These two assertions are what make those borrowings safe: the
    tuples cannot diverge, and there is exactly one grammar implementation.
    """

    def test_the_kind_vocabulary_has_exactly_one_origin(self):
        from world.art import official_refs

        self.assertEqual(official_refs.OFFICIAL_CONTENT_KINDS, official.OFFICIAL_CONTENT_KINDS)

    def test_the_layout_vocabulary_adds_exactly_the_two_operator_content_kinds(self):
        """The index vocabulary and the entity-reference vocabulary differ by design.

        ``OFFICIAL_CONTENT_KINDS`` is the ENTITY-REFERENCE vocabulary
        ``world.art.official_refs`` mirrors (``official-content-provenance``),
        where every kind must have a provenance attribute the resolver can map;
        ``OFFICIAL_LAYOUT_KINDS`` is the closed vocabulary of the startup walk,
        which ``unified-scene-catalog`` extended with the operator-only
        ``scene`` and ``room`` content. Growing the reference vocabulary would
        change that resolver's contract, so it is pinned unchanged here.
        """
        from world.art import official_refs

        self.assertEqual(OFFICIAL_CONTENT_KINDS, ("monster", "preset", "npc"))
        self.assertEqual(
            OFFICIAL_LAYOUT_KINDS, OFFICIAL_CONTENT_KINDS + ("scene", "room")
        )
        self.assertEqual(official_refs.OFFICIAL_CONTENT_KINDS, OFFICIAL_CONTENT_KINDS)

    def test_the_key_grammar_has_exactly_one_implementation(self):
        from world.art import official_refs
        from world.art.subjects import is_valid_subject_key

        self.assertIs(official.is_valid_subject_key, is_valid_subject_key)
        self.assertIs(official_refs.is_valid_subject_key, is_valid_subject_key)
        # The boundary battery either side of the contract, so the shared
        # predicate's behavior at every documented edge is pinned here.
        over_long = "x" * 65
        over_bytes = "\U0001d54f" * 51  # 51 code points, 204 UTF-8 bytes
        valid = ("t_synth_preset", "a" * 64, "é" * 64, "a b", "a#b")
        invalid = (
            "",
            None,
            7,
            "a/b",
            "a:b",
            "a|b",
            "a{b",
            "a}b",
            "a\x00b",
            "a\x7fb",
            "a\u00a0b",
            "a\u200bb",
            over_long,
            over_bytes,
        )
        for key in valid:
            with self.subTest(key=repr(key)):
                self.assertTrue(is_valid_subject_key(key))
        for key in invalid:
            with self.subTest(key=repr(key)):
                self.assertFalse(is_valid_subject_key(key))


if __name__ == "__main__":
    unittest.main()
