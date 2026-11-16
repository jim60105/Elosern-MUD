"""Art jobs captured ``in_progress`` by a save are requeued after restoration."""

from __future__ import annotations

import time
import uuid

from evennia.utils.test_resources import EvenniaTestCase

from world.art.queue import (
    claim,
    enqueue_gallery_job,
    gallery_record_key,
    reclaim_expired_leases,
)
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import _lease_timeout
from tools.spec_traceability import covers_requirement


class RestoredLeaseReclaimTests(EvenniaTestCase):
    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_a_job_claimed_when_the_save_was_taken_returns_to_pending(self):
        subject = ArtSubject(ArtSubjectKind.SCENE, "t_synth_saved_claim")
        image_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, subject.full()))
        enqueue_gallery_job(
            subject,
            "desc",
            image_id=image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        claim(10)
        job = GalleryJobRecord.objects.filter(
            db_key=gallery_record_key(subject, image_id)
        ).first()
        self.assertEqual(job.db.status, ArtAssetStatus.IN_PROGRESS)
        # The restored database still carries the claim time from the moment
        # the save was taken; the worker that held it no longer exists.
        job.db.claimed_at = time.time() - _lease_timeout() - 1
        self.assertEqual(reclaim_expired_leases(_lease_timeout()), 1)
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        self.assertIsNone(job.db.claimed_at)
