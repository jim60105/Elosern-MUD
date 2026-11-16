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
    enqueue_gallery_job,
    gallery_record_key,
    reclaim_expired_leases,
)
from world.art.sd_worker import GeneratedImage, SDError
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _run_and_settle_batch,
    drain,
    drain_synchronous,
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

from ._support import (
    WorkerStoreIsolation,
    _SYNTH_MONSTER,
    _OpaqueClient,
)


class CutoutFailureTests(WorkerStoreIsolation):
    """A cutout failure is a bounded, terminal, non-degrading job failure."""

    def setUp(self):
        super().setUp()
        self.client = _OpaqueClient()

    def _publish_prior(self, subject: ArtSubject) -> tuple[Path, bytes]:
        """Publish one valid prior card, then return its file and bytes."""
        job = self._record(subject, "prior")
        target = self.root / output_identity_for(job)
        with self._client(self.client):
            drain_synchronous(10)
        self.assertTrue(target.is_file())
        return target, target.read_bytes()

    def _cutout(self, **overrides):
        return override_settings(ART_REMBG_ENABLED=True, **overrides)

    def test_an_unresolvable_backend_settles_art_cutout_unavailable(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        target, prior = self._publish_prior(subject)
        job = self._record(subject, "failing")
        image_id = job.db.gallery_image_id
        with self._cutout(ART_REMBG_BACKEND="no.such.module.Backend"):
            with self._client(self.client):
                drain_synchronous(10)
        states = gallery_api.erroring_subjects()
        self.assertEqual([state.error_code for state in states], ["art_cutout_unavailable"])
        self.assertEqual(target.read_bytes(), prior)
        self.assertEqual(len(gallery_api.cards_for(subject)), 1)
        self.assertEqual(len(self.client.calls), 2, "one failing generation, never re-issued twice")
        self.assertIsNone(self._job_for(job))

    def test_a_scripted_failure_settles_art_cutout_error(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        target, prior = self._publish_prior(subject)
        job = self._record(subject, "failing")
        image_id = job.db.gallery_image_id
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "scripted"))
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                with self._client(self.client):
                    drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["art_cutout_error"],
        )
        self.assertEqual(target.read_bytes(), prior)
        self.assertEqual(len(gallery_api.cards_for(subject)), 1)
        self.assertFalse(
            (self.root / "gallery" / "character" / "42" / f"{image_id}.tmp").exists()
        )
        self.assertIsNone(self._job_for(job))

    def test_an_arbitrary_exception_is_still_bounded(self):
        subject = self._subject(_SYNTH_MONSTER, ArtSubjectKind.MONSTER)
        job = self._record(subject)
        with override_settings(
            ART_REMBG_ENABLED=True,
            ART_REMBG_BACKEND="world.art.tests.test_worker._support._ExplodingBackend",
        ):
            with self._client(self.client):
                drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["art_cutout_error"],
        )
        self.assertEqual(gallery_api.cards_for(subject), [])
        self.assertIsNone(self._job_for(job))

    @covers_requirement("art-portrait-cutout::gallery-cutout-failure-preserves-existing-cards")
    def test_a_failing_gallery_cutout_appends_no_card(self):
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
        self.assertIsNone(self._job_for(job))

    def test_one_failing_portrait_does_not_fail_its_batch(self):
        scene = self._subject()
        failing = self._subject("42", ArtSubjectKind.CHARACTER)
        succeeding = self._subject(_SYNTH_MONSTER, ArtSubjectKind.MONSTER)
        scene_job = self._record(scene, "scene")
        failing_job = self._record(failing, "failing")
        succeeding_job = self._record(succeeding, "succeeding")
        scene_identity = output_identity_for(scene_job)
        failing_identity = output_identity_for(failing_job)
        succeeding_identity = output_identity_for(succeeding_job)
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
        self.assertEqual(len(gallery_api.cards_for(scene)), 1)
        self.assertEqual(gallery_api.cards_for(failing), [])
        self.assertEqual(len(gallery_api.cards_for(succeeding)), 1)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["art_cutout_error"],
        )
        for job in (scene_job, failing_job, succeeding_job):
            self.assertIsNone(self._job_for(job))
        self.assertEqual(GalleryJobRecord.objects.count(), 0)
        self._assert_region_transparent(
            self.root / succeeding_identity
        )
        self.assertFalse(
            (self.root / failing_identity).exists()
        )

    def test_a_stale_cutout_failure_never_steals_a_reclaimed_claim(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        job = self._record(subject)
        held = claim(10)[0]
        token_a = str(held.db.generation_token)
        # The job is reclaimed to pending and re-claimed under a NEW token
        # while the obsolete worker (token A) is still holding its batch.
        reclaim_expired_leases(0.0)
        fresh = claim(10)[0]
        token_b = str(fresh.db.generation_token)
        self.assertNotEqual(token_a, token_b)
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "obsolete worker"))
        with self._cutout(ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend"):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                settled = _run_and_settle_batch(
                    [(held, subject, token_a, str(held.db_key))]
                )
        self.assertEqual(settled, [])
        current = self._job_for(job)
        self.assertEqual(current.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(current.db.generation_token, token_b)
        self.assertIsNone(current.db.last_error_code)
        self.assertEqual(gallery_api.cards_for(subject), [])
