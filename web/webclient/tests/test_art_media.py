"""Tests for the same-origin art media route (art-assets D8)."""

from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTestCase

from world.art.queue import ensure, settle
from world.art.store import ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtMediaViewTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()
        super().tearDown()

    def _done_identity(self, identity, key="forest_path"):
        subject = _scene(key)
        ensure(subject, "desc")
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("asset", encoding="utf-8")
        from world.art.queue import claim

        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )
        return subject

    def _get(self, identity):
        from django.test import Client

        with override_settings(ART_STORE_ROOT=str(self.root)):
            return Client().get(f"/art/{identity}")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_valid_done_record_identity_is_served_same_origin(self):
        self._done_identity("scene/forest_path.png")
        response = self._get("scene/forest_path.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_every_store_extension_is_served_with_its_exact_media_type(self):
        cases = {
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".avif": "image/avif",
        }
        for extension, media_type in cases.items():
            identity = f"scene/mixed_store_{extension[1:]}{extension}"
            with self.subTest(extension=extension):
                self._done_identity(identity, key=f"mixed_store_{extension[1:]}")
                response = self._get(identity)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], media_type)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_mixed_store_serves_a_png_record_under_another_formats_config(self):
        # The route never consults the configured format: a done record with
        # a .png identity is served even when the store's active format is
        # avif (a store mid-way through a format switch).
        self._done_identity("scene/forest_path.png")
        with override_settings(ART_SD_OUTPUT_FORMAT="avif", ART_SD_OUTPUT_EXTENSION=".avif"):
            response = self._get("scene/forest_path.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_unlisted_extension_and_extensionless_identity_return_404(self):
        for identity in ("scene/forest_path.jxl", "scene/forest_path"):
            with self.subTest(identity=identity):
                response = self._get(identity)
                self.assertEqual(response.status_code, 404)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_out_of_root_traversal_and_symlink_identities_return_404(self):
        self._done_identity("scene/forest_path.png")
        (self.root / "scene" / "inner.png").write_text("inner", encoding="utf-8")
        (self.root / "scene" / "inroot_symlink.png").symlink_to(
            self.root / "scene" / "inner.png"
        )
        outside_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside_dir, ignore_errors=True)
        (self.root / "scene" / "outroot_symlink.png").symlink_to(
            outside_dir / "x.png"
        )
        for identity in (
            "../outside.png",
            "scene/../outside.png",
            "absolute",
            "unknown.png",
            "scene/wrong.txt",
            "scene/inroot_symlink.png",
            "scene/outroot_symlink.png",
            "portrait/character/../scene/forest_path.png",
        ):
            with self.subTest(identity=identity):
                response = self._get(identity)
                self.assertEqual(response.status_code, 404)

    def test_unreferenced_identity_returns_404_even_if_the_file_exists(self):
        target = self.root / "scene" / "orphan.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("orphan", encoding="utf-8")
        response = self._get("scene/orphan.png")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
