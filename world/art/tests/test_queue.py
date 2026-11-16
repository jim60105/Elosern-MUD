"""Tests for the per-image gallery job queue and its lock discipline."""

from unittest.mock import patch
import unittest

from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTestCase

from world.art import gallery as gallery_api
from world.art import gallery_kinds
from world.art.gallery import GalleryRecordError
from world.art.queue import (
    claim,
    enqueue_gallery_job,
    failed_keys,
    gallery_record_key,
    is_gallery_job,
    queue_lock,
    reclaim_expired_leases,
    record_key,
    source_hash,
)
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="t_synth_forest"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _character(key="42"):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _enqueue_gallery(subject, image_id="11111111-1111-4111-8111-111111111111", **fields):
    return enqueue_gallery_job(
        subject,
        "desc",
        image_id=image_id,
        binding=fields.get("binding"),
        face_rect=fields.get("face_rect"),
        requested_fields=fields.get("requested_fields", []),
    )


def _job_count() -> int:
    return GalleryJobRecord.objects.all().count()


class GalleryJobQueueTests(EvenniaTestCase):
    """Per-image gallery jobs share the queue machinery and carry request state."""

    @covers_requirement("art-queue-worker::gallery-image-requests-own-independent-queue-jobs")
    def test_two_requests_for_one_subject_produce_two_independent_jobs(self):
        subject = _character("42")
        first = _enqueue_gallery(subject, "11111111-1111-4111-8111-111111111111")
        second = _enqueue_gallery(subject, "22222222-2222-4222-8222-222222222222")
        self.assertNotEqual(first.db_key, second.db_key)
        self.assertEqual(
            first.db_key,
            gallery_record_key(subject, "11111111-1111-4111-8111-111111111111"),
        )
        self.assertTrue(first.db_key.startswith(f"art:{subject.full()}:gen:"))
        self.assertEqual(first.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(second.db.status, ArtAssetStatus.PENDING)
        self.assertTrue(is_gallery_job(first) and is_gallery_job(second))
        self.assertEqual(_job_count(), 2)

    @covers_requirement("art-queue-worker::gallery-jobs-carry-transient-request-state-only")
    def test_a_gallery_job_carries_the_card_metadata_and_no_output_identity(self):
        subject = _character("42")
        binding = {
            "mask": ["weapon_main"],
            "snapshot": {"weapon_main": "longsword"},
        }
        rect = {"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.4}
        job = _enqueue_gallery(
            subject,
            "33333333-3333-4333-8333-333333333333",
            binding=binding,
            face_rect=rect,
            requested_fields=["eyes"],
        )
        self.assertEqual(dict(job.db.gallery_binding), binding)
        self.assertEqual(dict(job.db.gallery_face_rect), rect)
        self.assertEqual(list(job.db.gallery_requested_fields), ["eyes"])
        self.assertEqual(job.db.source_hash, source_hash("desc"))
        self.assertTrue(job.db.prompt_digest)
        self.assertEqual(job.db.aspect_ratio, "3:4")
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        for forbidden in (
            "output_identity",
            "prior_output_identity",
            "published_generation_token",
            "hash_changed",
            "seed",
        ):
            self.assertNotIn(forbidden, GalleryJobRecord.__dict__, forbidden)
        # No lease was taken: a reclaim pass never disturbs a pending job.
        self.assertEqual(reclaim_expired_leases(0.001), 0)

    def test_enqueue_refuses_a_kind_with_no_gallery_declaration(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, "nogoblin")
        no_gallery = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.MONSTER.value
        ].with_values(has_gallery=False, store_directory=None)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.MONSTER.value: no_gallery},
        ):
            with self.assertRaises(GalleryRecordError):
                _enqueue_gallery(subject)
        self.assertEqual(_job_count(), 0)

    def test_claim_makes_in_progress_with_a_lease_and_increments_attempts(self):
        _enqueue_gallery(_scene("t_synth_mountain"))
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        job = claimed[0]
        self.assertEqual(job.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertIsNotNone(job.db.claimed_at)
        self.assertEqual(int(job.db.attempt_count), 1)
        self.assertEqual(job.db.aspect_ratio, "16:9")
        self.assertTrue(job.db.generation_token)

    def test_expired_lease_is_reclaimed_to_pending(self):
        _enqueue_gallery(_scene("t_synth_coast"))
        claim(10)
        job = GalleryJobRecord.objects.first()
        self.assertEqual(job.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(reclaim_expired_leases(0.001), 1)
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        self.assertIsNone(job.db.claimed_at)

    def test_failed_keys_represent_recorded_gallery_errors(self):
        good = _scene("t_synth_forest")
        bad = _scene("t_synth_cave")
        _enqueue_gallery(good, "11111111-1111-4111-8111-111111111111")
        _enqueue_gallery(bad, "22222222-2222-4222-8222-222222222222")
        claimed = {job.db_key: job for job in claim(10)}
        bad_job = claimed[gallery_record_key(bad, "22222222-2222-4222-8222-222222222222")]
        from world.art.queue import settle_gallery_failed

        self.assertEqual(
            gallery_api.erroring_subjects(),
            [],
        )
        self.assertIsNotNone(
            settle_gallery_failed(
                str(bad_job.db_key),
                generation_token=str(bad_job.db.generation_token),
                error="boom",
            )
        )
        self.assertEqual(failed_keys(), ["scene:t_synth_cave"])
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=bad_job.db_key).exists())

    @covers_requirement("art-queue-worker::gallery-jobs-share-one-lock-and-worker-slot")
    def test_concurrent_drains_serialize_and_never_hold_the_lock_across_a_worker_wait(self):
        from world.art.queue import settle_gallery_failed

        for key, image_id in (
            ("t_synth_forest", "11111111-1111-4111-8111-111111111111"),
            ("t_synth_tavern", "22222222-2222-4222-8222-222222222222"),
            ("t_synth_city", "33333333-3333-4333-8333-333333333333"),
        ):
            _enqueue_gallery(_scene(key), image_id)
        lock_free_during_worker_wait = []
        first_batch = claim(2)
        self.assertEqual(len(first_batch), 2)
        lock_free_during_worker_wait.append(not queue_lock.locked())
        for job in first_batch:
            settle_gallery_failed(
                str(job.db_key),
                generation_token=str(job.db.generation_token),
                error="fixture",
            )
        second_batch = claim(2)
        lock_free_during_worker_wait.append(not queue_lock.locked())
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(
            {job.db.subject_key for job in second_batch}, {"t_synth_city"}
        )
        self.assertTrue(all(lock_free_during_worker_wait))
        self.assertEqual(GalleryJobRecord.objects.count(), 1)

    def test_a_stale_token_failure_settle_is_a_noop(self):
        from world.art.queue import settle_gallery_failed

        job = _enqueue_gallery(_scene("t_synth_dungeon"))
        held = claim(10)[0]
        token_a = str(held.db.generation_token)
        # Reclaim and re-claim under a fresh token.
        reclaim_expired_leases(0.0)
        fresh = claim(10)[0]
        token_b = str(fresh.db.generation_token)
        self.assertNotEqual(token_a, token_b)
        self.assertIsNone(
            settle_gallery_failed(
                str(job.db_key),
                generation_token=token_a,
                error="art_cutout_error",
            )
        )
        current = GalleryJobRecord.objects.get(db_key=job.db_key)
        self.assertEqual(current.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(current.db.generation_token, token_b)
        self.assertIsNone(current.db.last_error_code)

    def test_the_current_token_failure_settle_applies(self):
        from world.art.queue import settle_gallery_failed

        job = _enqueue_gallery(_scene("t_synth_coast"))
        claimed = claim(10)[0]
        subject = settle_gallery_failed(
            str(job.db_key),
            generation_token=str(claimed.db.generation_token),
            error="art_cutout_error",
        )
        self.assertEqual(subject.full(), "scene:t_synth_coast")
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=job.db_key).exists())
        states = {state.subject.full(): state for state in gallery_api.gallery_states()}
        self.assertEqual(states["scene:t_synth_coast"].error_code, "art_cutout_error")

    def test_is_gallery_job_rejects_a_malformed_record(self):
        malformed = create_script(
            GalleryJobRecord, key="art:t_synth_bad", persistent=True, interval=0
        )
        malformed.db.kind = ArtSubjectKind.SCENE.value
        malformed.db.subject_key = "t_synth_bad"
        malformed.db.gallery_image_id = "t_image"
        self.assertFalse(is_gallery_job(malformed))
        well_formed = create_script(
            GalleryJobRecord,
            key="art:t_synth_ok:gen:t_image",
            persistent=True,
            interval=0,
        )
        well_formed.db.kind = ArtSubjectKind.SCENE.value
        well_formed.db.subject_key = "t_synth_ok"
        well_formed.db.gallery_image_id = "t_image"
        self.assertTrue(is_gallery_job(well_formed))
        self.assertEqual(record_key(_scene("t_synth_ok")), "art:scene:t_synth_ok")


if __name__ == "__main__":
    unittest.main()
