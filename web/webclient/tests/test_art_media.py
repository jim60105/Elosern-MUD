"""Tests for the same-origin art media route (art-assets D8)."""

import io
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid
from unittest.mock import patch

from django.test import override_settings
from PIL import Image

from evennia.utils.test_resources import EvenniaTestCase

from world.art import official
from world.art.gallery import append_card
from world.art.queue import ensure, settle
from world.art.store import ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="t_synth_bazaar"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _encoded(format_name: str, size=(2, 2)) -> bytes:
    """Real, decodable image bytes in one of the closed store formats."""
    buffer = io.BytesIO()
    Image.new("L", size).save(buffer, format=format_name)
    return buffer.getvalue()


def _tree_bytes(root: Path) -> dict[str, bytes]:
    """Every regular file under ``root`` keyed by relative path (byte snapshot)."""
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ArtMediaViewTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()
        super().tearDown()

    def _done_identity(self, identity, key="t_synth_bazaar"):
        subject = _scene(key)
        ensure(subject, "desc")
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("asset", encoding="utf-8")
        from world.art.queue import claim

        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
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
        self._done_identity("scene/t_synth_bazaar.png")
        response = self._get("scene/t_synth_bazaar.png")
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
        self._done_identity("scene/t_synth_bazaar.png")
        with override_settings(ART_SD_OUTPUT_FORMAT="avif", ART_SD_OUTPUT_EXTENSION=".avif"):
            response = self._get("scene/t_synth_bazaar.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_unlisted_extension_and_extensionless_identity_return_404(self):
        for identity in ("scene/t_synth_bazaar.jxl", "scene/t_synth_bazaar"):
            with self.subTest(identity=identity):
                response = self._get(identity)
                self.assertEqual(response.status_code, 404)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_out_of_root_traversal_and_symlink_identities_return_404(self):
        self._done_identity("scene/t_synth_bazaar.png")
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
            "portrait/character/../scene/t_synth_bazaar.png",
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
        self.assertNotIn(str(self.root), repr(response))


class GalleryIdentityServingTests(EvenniaTestCase):
    """The gallery branch: served only via the addressed record (task 5.6)."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _subject(self, kind=ArtSubjectKind.CHARACTER, key="gallery-owner"):
        return ArtSubject(kind, key)

    def _card(self, subject, extension=".png", image_id=None, identity=None):
        image_id = image_id or str(uuid.uuid4())
        kind_dir = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        identity = identity or f"gallery/{kind_dir}/{subject.key}/{image_id}{extension}"
        append_card(
            subject,
            **{
                "image_id": image_id,
                "stored_identity": identity,
                "prompt": {"positive": "a hero", "negative": "blur"},
                "seed": 1,
                "checkpoint": "realVision.safetensors",
                "requested_fields": ["appearance"],
                "binding": None,
                "source": "generated",
                "image_size": {"width": 1000, "height": 1000},
            },
        )
        return identity

    def _write(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        return target

    def _get(self, identity):
        from django.test import Client

        return Client().get(f"/art/{identity}")

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_a_card_referenced_gallery_identity_is_served_with_its_type(self):
        media_types = {
            ".png": "image/png",
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".avif": "image/avif",
        }
        for index, (extension, media_type) in enumerate(media_types.items()):
            subject = self._subject(key=f"gallery-owner-{index}")
            identity = self._card(subject, extension=extension)
            self._write(identity)
            response = self._get(identity)
            with self.subTest(extension=extension):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], media_type)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_unreferenced_gallery_identity_returns_404(self):
        subject = self._subject(key="gallery-unref")
        stray = f"gallery/character/{subject.key}/{uuid.uuid4()}.png"
        self._write(stray)
        self.assertEqual(self._get(stray).status_code, 404)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_mis_addressed_gallery_identity_returns_404(self):
        # A card of one subject whose stored identity addresses ANOTHER
        # subject's path: the addressed record holds no such card -> 404.
        from world.art.gallery import record_for

        thief = self._subject(key="gallery-thief")
        identity = self._card(thief)
        self._write(identity)
        self.assertEqual(self._get(identity).status_code, 200)
        # Corrupt the card's stored identity to address a different subject
        # (the write API itself refuses this).
        victim_identity = f"gallery/character/gallery-victim/{uuid.uuid4()}.png"
        self._write(victim_identity)
        record = record_for(thief)
        poisoned = dict(record.db.cards[0])
        poisoned["stored_identity"] = victim_identity
        record.db.cards = [poisoned]
        self.assertEqual(self._get(victim_identity).status_code, 404)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_traversal_unexpected_directory_and_extension_404(self):
        subject = self._subject(key="gallery-rules")
        for bad in (
            f"gallery/character/{subject.key}/../../etc/passwd.png",
            "gallery/npc/gallery-rules/x.png",
            f"gallery/character/{subject.key}/{uuid.uuid4()}.jxl",
        ):
            with self.subTest(bad=bad):
                self.assertEqual(self._get(bad).status_code, 404)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_symlinked_gallery_file_returns_404_and_leaves_the_target_alive(self):
        subject = self._subject(key="gallery-symlink")
        identity = self._card(subject)
        target = self._write(identity)
        external = Path(self.tempdir.name).parent / "media-precious.png"
        external.write_bytes(b"do not serve")
        target.unlink()
        target.symlink_to(external)
        self.assertEqual(self._get(identity).status_code, 404)
        self.assertTrue(external.exists())


class DefaultsServingTests(EvenniaTestCase):
    """The built-in fallback branch serves from one fixed in-repo directory."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.defaults = Path(self.tempdir.name) / "art" / "defaults"
        self.defaults.mkdir(parents=True)
        self.store_temp = tempfile.TemporaryDirectory()
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.store_temp.name).resolve()),
            STATICFILES_DIRS=[str(Path(self.tempdir.name))],
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        self.store_temp.cleanup()
        super().tearDown()

    def _get(self, identity):
        from django.test import Client

        return Client().get(f"/art/{identity}")

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_a_defaults_identity_is_served_from_the_defaults_directory(self):
        # Closed vocabulary (gallery-builtin-fallbacks): only a committed key
        # is served; an out-of-vocabulary stem 404s even when the file exists.
        (self.defaults / "man.webp").write_bytes(b"fallback")
        (self.defaults / "stray.png").write_bytes(b"fallback")
        response = self._get("defaults/man.webp")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(self._get("defaults/stray.png").status_code, 404)
        # The committed set is exactly ``<key>.webp``: an alternate extension
        # for a valid stem is not a committed identity (duck MAJOR).
        for extension in ("png", "jpg", "avif"):
            (self.defaults / f"man.{extension}").write_bytes(b"fallback")
            with self.subTest(extension=extension):
                self.assertEqual(
                    self._get(f"defaults/man.{extension}").status_code, 404
                )

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_missing_escaping_or_symlinked_defaults_identities_404(self):
        outside = Path(self.tempdir.name) / "outside.png"
        outside.write_bytes(b"x")
        # Missing file
        self.assertEqual(self._get("defaults/man.webp").status_code, 404)
        # Unexpected sub-path
        nested = self.defaults / "nested"
        nested.mkdir()
        (nested / "hidden.png").write_bytes(b"x")
        self.assertEqual(self._get("defaults/nested/hidden.png").status_code, 404)
        # An identity whose segments escape the defaults directory
        escaping = self.defaults.parent.parent / "escape.png"
        escaping.write_bytes(b"x")
        self.assertEqual(self._get("defaults/../escape.png").status_code, 404)
        # Symlink escaping the defaults directory (vocabulary stem so only the
        # containment check can be what rejects it)
        link = self.defaults / "man.webp"
        link.symlink_to(outside)
        self.assertEqual(self._get("defaults/man.webp").status_code, 404)
        # The store root is never consulted for a defaults identity
        store_defaults = Path(self.store_temp.name) / "defaults"
        store_defaults.mkdir()
        (store_defaults / "sneaky.png").write_bytes(b"x")
        self.assertEqual(self._get("defaults/sneaky.png").status_code, 404)


class OfficialIdentityServingTests(EvenniaTestCase):
    """The official branch: a catalog lookup alone (official-artwork-catalog).

    ``npc/`` content is used because its keys carry no registry membership
    check (the authored npc/profile provenance lands with its own change), so
    this module never touches a shipped registry.
    """

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.official_root = Path(self.tempdir.name).resolve() / "art-official"
        self.store_temp = tempfile.TemporaryDirectory()
        self.store_root = Path(self.store_temp.name).resolve() / "store"
        self.art_settings = override_settings(
            ART_OFFICIAL_ROOT=str(self.official_root),
            ART_STORE_ROOT=str(self.store_root),
        )
        self.art_settings.enable()
        official.reset_catalog()
        self.addCleanup(official.reset_catalog)

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        self.store_temp.cleanup()
        super().tearDown()

    def _image(self, name="a.png", content=None, key="t_synth_profile") -> Path:
        folder = self.official_root / "npc" / key
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(content if content is not None else _encoded("PNG"))
        return path

    def _url(self, identity: str) -> str:
        """The same-origin URL the catalog builds for an admitted identity."""
        url = official.current_catalog().url_for(identity)
        self.assertIsNotNone(url, msg=f"{identity} is not admitted")
        return url

    def _get(self, target: str):
        from django.test import Client

        return Client().get(target if target.startswith("/art/") else f"/art/{target}")

    @staticmethod
    def _body(response) -> bytes:
        return b"".join(response.streaming_content)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_a_catalog_admitted_identity_is_served_with_its_exact_bytes(self):
        cases = (
            ("a.png", "PNG", "image/png"),
            ("b.jpg", "JPEG", "image/jpeg"),
            ("c.webp", "WEBP", "image/webp"),
        )
        for name, format_name, media_type in cases:
            with self.subTest(name=name):
                path = self._image(name=name, content=_encoded(format_name))
                official.load_catalog()
                identity = f"npc/t_synth_profile/{name}"
                response = self._get(self._url(identity))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], media_type)
                self.assertEqual(self._body(response), path.read_bytes())

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_a_stale_fingerprint_404s_while_the_refreshed_one_serves(self):
        identity = "npc/t_synth_profile/a.png"
        path = self._image()
        official.load_catalog()
        stale = self._url(identity)
        self.assertEqual(self._get(stale).status_code, 200)
        # A maintenance restart replaces the bytes at the same path.
        path.write_bytes(_encoded("PNG", size=(3, 3)))
        official.load_catalog()
        self.assertEqual(self._get(stale).status_code, 404)
        response = self._get(self._url(identity))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._body(response), path.read_bytes())
        self.assertNotEqual(self._url(identity), stale)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_unindexed_paths_and_bogus_fingerprints_404_without_acquiring(self):
        identity = "npc/t_synth_profile/a.png"
        self._image()
        official.load_catalog()
        fingerprint = official.current_catalog().fingerprint_for(identity)
        self._image(key="t_synth_late")
        targets = (
            f"official/{'0' * 64}/{identity}",
            f"official/{fingerprint}/npc/t_synth_profile/absent.png",
            f"official/{fingerprint}/npc/t_synth_late/a.png",
            f"official/{fingerprint}/monster/t_synth_species/a.png",
        )
        with patch("socket.socket", side_effect=AssertionError("no acquisition")):
            for target in targets:
                with self.subTest(target=target):
                    self.assertEqual(self._get(target).status_code, 404)
        # The unindexed-but-present file was never touched or copied.
        self.assertTrue(
            (self.official_root / "npc" / "t_synth_late" / "a.png").is_file()
        )

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_escaping_and_post_load_swapped_symlinks_404(self):
        identity = "npc/t_synth_profile/a.png"
        path = self._image()
        official.load_catalog()
        fingerprint = official.current_catalog().fingerprint_for(identity)
        self.assertEqual(self._get(self._url(identity)).status_code, 200)
        outside = Path(self.tempdir.name).parent / "media-precious.png"
        outside.write_bytes(b"do not serve")
        # The file admitted at load is swapped for a symlink afterwards: the
        # confinement re-check refuses it rather than serving the target.
        path.unlink()
        path.symlink_to(outside)
        self.assertEqual(self._get(self._url(identity)).status_code, 404)
        self.assertTrue(outside.exists())
        for target in (
            f"official/{fingerprint}/npc/../../etc/passwd.png",
            f"official/{fingerprint}/..%2Fnpc/t_synth_profile/a.png",
            f"official/{fingerprint}/npc/t_synth_profile/a.txt",
            f"official//npc/t_synth_profile/a.png",
            f"official/{fingerprint}/",
        ):
            with self.subTest(target=target):
                self.assertEqual(self._get(target).status_code, 404)

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_serving_copies_nothing_into_the_runtime_store(self):
        identity = "npc/t_synth_profile/a.png"
        self._image()
        official.load_catalog()
        store_before = _tree_bytes(self.store_root)
        official_before = _tree_bytes(self.official_root)
        response = self._get(self._url(identity))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self._body(response))
        self.assertEqual(_tree_bytes(self.store_root), store_before)
        self.assertEqual(_tree_bytes(self.official_root), official_before)
        self.assertEqual(_tree_bytes(self.store_root), {})

    @covers_requirement(
        "art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root"
    )
    def test_an_unloaded_catalog_serves_no_official_identity(self):
        identity = "npc/t_synth_profile/a.png"
        self._image()
        official.reset_catalog()
        self.assertEqual(self._get(f"official/{'a' * 64}/{identity}").status_code, 404)
        self.assertEqual(self._get(identity).status_code, 404)


if __name__ == "__main__":
    unittest.main()
