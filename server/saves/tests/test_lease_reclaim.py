"""Art jobs captured ``in_progress`` by a save are requeued after restoration."""

from __future__ import annotations

import time

from evennia.utils.test_resources import EvenniaTestCase

from world.art.queue import claim, ensure, record_key, reclaim_expired_leases
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import _lease_timeout
from tools.spec_traceability import covers_requirement


class RestoredLeaseReclaimTests(EvenniaTestCase):
    @covers_requirement("gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_a_job_claimed_when_the_save_was_taken_returns_to_pending(self):
        subject = ArtSubject(ArtSubjectKind.SCENE, "t_synth_saved_claim")
        ensure(subject, "desc")
        claim(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        # The restored database still carries the claim time from the moment
        # the save was taken; the worker that held it no longer exists.
        record.db.claimed_at = time.time() - _lease_timeout() - 1
        self.assertEqual(reclaim_expired_leases(_lease_timeout()), 1)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertIsNone(record.db.claimed_at)
