"""Slice of ``test_worker``: CutoutFailureTests.
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

class CutoutFailureTests(WorkerStoreIsolation):
    """A cutout failure is a bounded, terminal, non-degrading job failure."""

    def setUp(self):
        super().setUp()
        self.client = _OpaqueClient()

    def _prior_output(self, subject: ArtSubject) -> tuple[Path, bytes]:
        """Generate a valid prior output once, then requeue for the failure."""
        with self._client(self.client):
            drain_synchronous(10)
        target = self.root / expected_output_identity(subject)
        self.assertTrue(target.is_file())
        prior = target.read_bytes()
        requeue(subject)
        return target, prior

    def _cutout(self, **overrides):
        return override_settings(ART_REMBG_ENABLED=True, **overrides)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_an_unresolvable_backend_settles_art_cutout_unavailable(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        self._record(subject)
        target, prior = self._prior_output(subject)
        with self._cutout(ART_REMBG_BACKEND="no.such.module.Backend"):
            with self._client(self.client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "art_cutout_unavailable")
        self.assertEqual(target.read_bytes(), prior)
        self.assertEqual(len(self.client.calls), 2, "one failing generation, never re-issued twice")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_scripted_failure_settles_art_cutout_error(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        self._record(subject)
        target, prior = self._prior_output(subject)
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "scripted"))
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                with self._client(self.client):
                    drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "art_cutout_error")
        self.assertEqual(target.read_bytes(), prior)
        self.assertFalse((self.root / "portrait" / "character" / "42.tmp").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_an_arbitrary_exception_is_still_bounded(self):
        subject = self._subject("low", ArtSubjectKind.MONSTER)
        self._record(subject)
        with override_settings(
            ART_REMBG_ENABLED=True,
            ART_REMBG_BACKEND="world.art.tests.test_worker._support._ExplodingBackend",
        ):
            with self._client(self.client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "art_cutout_error")
        self.assertIsNone(record.db.output_identity)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_failing_gallery_cutout_appends_no_card(self):
        from world.art.queue import enqueue_gallery_job

        character = self._subject("42", ArtSubjectKind.CHARACTER)
        image_id = "cccccccc-3333-4333-8333-333333333333"
        job = enqueue_gallery_job(
            character,
            "desc",
            image_id=image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_unavailable", "model missing"))
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                with self._client(self.client):
                    drain_synchronous(10)
        record = gallery_api.record_for(character)
        self.assertEqual(record.db.last_error_code, "art_cutout_unavailable")
        self.assertEqual(gallery_api.cards_for(character), [])
        self.assertFalse(
            (self.root / "gallery" / "character" / "42" / f"{image_id}.png").exists()
        )
        self.assertIsNone(
            ArtAssetRecord.objects.filter(db_key=job.db_key).first()
        )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_one_failing_portrait_does_not_fail_its_batch(self):
        scene = self._subject()
        failing = self._subject("42", ArtSubjectKind.CHARACTER)
        succeeding = self._subject("low", ArtSubjectKind.MONSTER)
        for subject in (scene, failing, succeeding):
            self._record(subject)
        fake = FakeCutoutBackend()
        seen: list[bytes] = []

        def _fail_first_portrait(payload: bytes) -> bool:
            seen.append(payload)
            return len(seen) == 1

        fake.add_failure(
            _fail_first_portrait,
            CutoutError("art_cutout_error", "first portrait only"),
        )
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                with self._client(self.client):
                    drain_synchronous(10)
        scene_record = self._record_for(scene)
        failing_record = self._record_for(failing)
        succeeding_record = self._record_for(succeeding)
        self.assertEqual(scene_record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(failing_record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(failing_record.db.last_error_code, "art_cutout_error")
        self.assertEqual(succeeding_record.db.status, ArtAssetStatus.DONE)
        self._assert_not_in_progress({scene_record, failing_record, succeeding_record})
        self._assert_region_transparent(
            self.root / "portrait" / "monster" / "low.png"
        )
        self.assertFalse((self.root / "portrait" / "character" / "42.png").exists())

    def _assert_not_in_progress(self, records) -> None:
        from world.art.store import ArtAssetStatus as Status

        for record in records:
            self.assertIn(
                record.db.status,
                {Status.DONE, Status.FAILED},
                "no claimed job is left in_progress",
            )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    @covers_requirement("art-portrait-cutout::a-background-removal-failure-is-a-bounded-terminal-non-degrading-job-failure")
    def test_a_stale_cutout_failure_never_steals_a_reclaimed_claim(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        self._record(subject)
        held = claim(10)[0]
        token_a = str(held.db.generation_token)
        # The record is reclaimed to pending and re-claimed under a NEW token
        # while the obsolete worker (token A) is still holding its batch.
        requeue(subject)
        fresh = claim(10)[0]
        token_b = str(fresh.db.generation_token)
        self.assertNotEqual(token_a, token_b)
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "obsolete worker"))
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                settled = _run_and_settle_batch([(held, subject, token_a)])
        self.assertEqual(settled, [])
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(record.db.generation_token, token_b)
        self.assertIsNone(record.db.last_error_code)
        self.assertIsNone(record.db.output_identity)
        self.assertFalse((self.root / "portrait" / "character" / "42.png").exists())
