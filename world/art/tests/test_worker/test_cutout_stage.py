"""Slice of ``test_worker``: CutoutStageTests.
"""
from contextlib import contextmanager
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from django.test import override_settings

from PIL import Image
from evennia.utils.test_resources import EvenniaTest

from world.art.fake_sd_client import DEFAULT_PNG, FakeSDWebUIClient
from world.art.fake_cutout import FakeCutoutBackend
from world.art.cutout import CutoutError
from world.art import gallery as gallery_api
from world.art.gallery import DEFAULT_FACE_RECT
from world.art.queue import (
    claim,
    ensure,
    enqueue_gallery_job,
    gallery_record_key,
    record_key,
    reclaim_expired_leases,
    requeue,
    settle,
    settle_generated,
)
from world.art.sd_worker import GeneratedImage, SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _lease_timeout,
    _run_and_settle_batch,
    _write_temp,
    drain,
    drain_synchronous,
    expected_output_identity,
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

from ._support import (
    WorkerStoreIsolation,
    _OpaqueClient,
    _opaque_portrait_png,
)

class CutoutStageTests(WorkerStoreIsolation):  # noqa: E501

    """The enabled stage stores cutouts; the skipped paths are byte-identical."""

    def setUp(self):
        super().setUp()
        self.client = _OpaqueClient()

    @contextmanager
    def _cutout(self, fake):
        """Enable the stage with ``fake`` as the injected backend instance."""
        with override_settings(
            ART_REMBG_ENABLED=True,
            ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend",
        ):
            with patch(
                "world.art.fake_cutout.FakeCutoutBackend", return_value=fake
            ):
                yield

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_a_character_portrait_is_stored_transparent(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        self._record(subject)
        with self._client(self.client):
            drain_synchronous(10)
        target = self.root / "portrait" / "character" / "42.png"
        disabled_bytes = target.read_bytes()
        requeue(subject)
        fake = FakeCutoutBackend()
        with self._cutout(fake):
            with self._client(self.client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(len(fake.calls), 1)
        self._assert_region_transparent(target)
        self.assertNotEqual(target.read_bytes(), disabled_bytes)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_a_monster_portrait_is_stored_transparent(self):
        subject = self._subject("low", ArtSubjectKind.MONSTER)
        self._record(subject)
        with self._client(self.client):
            drain_synchronous(10)
        target = self.root / "portrait" / "monster" / "low.png"
        disabled_bytes = target.read_bytes()
        requeue(subject)
        fake = FakeCutoutBackend()
        with self._cutout(fake):
            with self._client(self.client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self._assert_region_transparent(target)
        self.assertNotEqual(target.read_bytes(), disabled_bytes)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_gallery_portrait_jobs_are_cut_out_on_the_same_terms(self):
        monster = self._subject("low", ArtSubjectKind.MONSTER)
        character_image_id = "aaaaaaaa-1111-4111-8111-111111111111"
        monster_image_id = "bbbbbbbb-2222-4222-8222-222222222222"
        character_job = enqueue_gallery_job(
            self._subject("42", ArtSubjectKind.CHARACTER),
            "desc",
            image_id=character_image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        monster_job = enqueue_gallery_job(
            monster,
            "desc",
            image_id=monster_image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        fake = FakeCutoutBackend()
        with self._cutout(fake):
            with self._client(self.client):
                drain_synchronous(10)
        self.assertEqual(len(fake.calls), 2)
        self._assert_region_transparent(
            self.root / "gallery" / "character" / "42" / f"{character_image_id}.png"
        )
        self._assert_region_transparent(
            self.root / "gallery" / "monster" / "low" / f"{monster_image_id}.png"
        )
        self.assertEqual(len(gallery_api.cards_for(self._subject("42", ArtSubjectKind.CHARACTER))), 1)
        self.assertEqual(len(gallery_api.cards_for(monster)), 1)
        self.assertIsNone(self._gallery_job_key(character_job))
        self.assertIsNone(self._gallery_job_key(monster_job))

    def _gallery_job_key(self, job):
        return ArtAssetRecord.objects.filter(db_key=job.db_key).first()

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_scene_art_never_reaches_the_backend(self):
        subject = self._subject()
        self._record(subject)
        with self._client(self.client):
            drain_synchronous(10)
        target = self.root / "scene" / "t_synth_forest.png"
        disabled_bytes = target.read_bytes()
        requeue(subject)
        fake = FakeCutoutBackend()
        with self._cutout(fake):
            with self._client(self.client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(fake.calls, [])
        self.assertEqual(target.read_bytes(), disabled_bytes)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_the_disabled_stage_records_zero_calls_for_every_kind(self):
        fake = FakeCutoutBackend()
        self._record(self._subject())
        self._record(self._subject("42", ArtSubjectKind.CHARACTER))
        self._record(self._subject("low", ArtSubjectKind.MONSTER))
        with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
            with self._client(self.client):
                drain_synchronous(10)
        self.assertEqual(fake.calls, [])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::the-background-removal-backend-is-an-injectable-cpu-only-seam")
    def test_the_stage_runs_between_generation_and_encoding(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        self._record(subject)
        real_encode = __import__("world.art.formats", fromlist=["encode"]).encode
        captured: dict = {}

        def _spy_encode(png_bytes, **kwargs):
            captured["bytes"] = png_bytes
            return real_encode(png_bytes, **kwargs)

        fake = FakeCutoutBackend()
        with self._cutout(fake):
            with patch("world.art.worker.encode", side_effect=_spy_encode):
                with self._client(self.client):
                    drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(len(self.client.calls), 1, "the generation is never re-issued")
        self.assertEqual(len(fake.calls), 1)
        # encode received the BACKEND's bytes, not the client's: the received
        # bytes decode RGBA with the fake's zeroed region.
        self.assertNotEqual(captured["bytes"], _opaque_portrait_png())
        with Image.open(io.BytesIO(captured["bytes"])) as image:
            self.assertEqual(image.mode, "RGBA")
            self.assertEqual(image.load()[0, 0][3], 0)
        listing = sorted(p.name for p in (self.root / "portrait" / "character").iterdir())
        self.assertEqual(listing, ["42.png"], "exactly one artifact is published")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_the_disabled_stage_keeps_todays_lease_bound(self):
        from world.art.worker import _CONVERSION_ALLOWANCE_SECONDS, _LEASE_MARGIN_SECONDS

        with override_settings(
            ART_SD_TIMEOUT_SECONDS=1,
            ART_SCHEDULER_LIMIT=2,
            ART_REMBG_ENABLED=False,
        ):
            expected = 2 * (1 + _CONVERSION_ALLOWANCE_SECONDS) + _LEASE_MARGIN_SECONDS
            self.assertEqual(_lease_timeout(), expected)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::character-and-monster-portraits-are-stored-with-their-background-removed")
    def test_the_enabled_stage_widens_the_bound_by_the_cutout_allowance(self):
        from django.conf import settings as django_settings

        from world.art.worker import _CONVERSION_ALLOWANCE_SECONDS, _LEASE_MARGIN_SECONDS

        with override_settings(
            ART_SD_TIMEOUT_SECONDS=1,
            ART_SCHEDULER_LIMIT=2,
            ART_REMBG_ENABLED=True,
        ):
            expected = 2 * (
                1
                + _CONVERSION_ALLOWANCE_SECONDS
                + int(django_settings.ART_REMBG_ALLOWANCE_SECONDS)
            ) + _LEASE_MARGIN_SECONDS
            self.assertEqual(_lease_timeout(), expected)
