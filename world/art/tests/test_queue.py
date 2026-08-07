"""Tests for the idempotent subject-keyed art queue and its lock discipline."""

from unittest.mock import patch
import unittest

from evennia.utils.test_resources import EvenniaTest

from world.art.queue import (
    claim,
    ensure,
    failed_keys,
    queue_lock,
    reclaim_expired_leases,
    record_key,
    requeue,
    settle,
    source_hash,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtQueueTests(EvenniaTest):
    @covers_requirement("art-queue-worker::the-queue-is-keyed-by-subject-identity-and-enqueue-is-idempotent")
    def test_reensuring_pending_in_progress_or_done_is_a_noop(self):
        subject = _scene()
        first = ensure(subject, "desc-a")
        self.assertEqual(first.db.status, ArtAssetStatus.PENDING)
        second = ensure(subject, "desc-b")
        self.assertEqual(second.pk, first.pk)
        self.assertEqual(second.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(second.db.source_hash, source_hash("desc-a"))
        self.assertEqual(len(ArtAssetRecord.objects.all()), 1)

        claimed = claim(10)
        self.assertEqual(claimed[0].db.status, ArtAssetStatus.IN_PROGRESS)
        ensure(subject, "desc-c")
        self.assertEqual(claimed[0].db.status, ArtAssetStatus.IN_PROGRESS)

        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        ensure(subject, "desc-d")
        done = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(done.db.status, ArtAssetStatus.DONE)
        self.assertEqual(done.db.output_identity, "scene/forest_path.png")

    @covers_requirement("art-queue-worker::the-queue-is-keyed-by-subject-identity-and-enqueue-is-idempotent")
    def test_missing_and_failed_records_become_pending(self):
        subject = _scene("tavern_interior")
        created = ensure(subject, "desc")
        self.assertEqual(created.db.status, ArtAssetStatus.PENDING)

        claim(10)
        settle(subject, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        failed = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(failed.db.status, ArtAssetStatus.FAILED)
        retried = ensure(subject, "desc")
        self.assertEqual(retried.db.status, ArtAssetStatus.PENDING)
        # attempt_count: claim incremented it once, the failed->pending ensure
        # increments it again.
        self.assertEqual(int(retried.db.attempt_count), 2)

    @covers_requirement("art-queue-worker::the-queue-is-keyed-by-subject-identity-and-enqueue-is-idempotent")
    def test_forced_regeneration_resets_and_preserves_the_prior_output(self):
        subject = _scene("dungeon_interior")
        ensure(subject, "desc")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/dungeon_interior.png",
            error=None,
        )
        requeue(subject)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(record.db.prior_output_identity, "scene/dungeon_interior.png")
        claim(10)
        settle(subject, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.prior_output_identity, "scene/dungeon_interior.png")

    @covers_requirement("art-queue-worker::the-queue-is-keyed-by-subject-identity-and-enqueue-is-idempotent")
    def test_stale_settle_for_a_requeued_record_is_a_noop(self):
        subject = _scene("dungeon_interior")
        ensure(subject, "desc")
        claim(10)
        requeue(subject)
        stale = settle(
            subject, status=ArtAssetStatus.DONE,
            output_identity="scene/dungeon_interior.png", error=None,
        )
        self.assertIsNone(stale)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-queue-worker::a-changed-source-description-hash-is-reported-never-silently-applied")
    def test_changed_hash_is_staff_noted_without_replacing_the_image(self):
        subject = _scene("city_street")
        ensure(subject, "original description")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/city_street.png",
            error=None,
        )
        ensure(subject, "changed description")
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/city_street.png")
        self.assertTrue(record.db.hash_changed)

    @covers_requirement("art-queue-worker::a-changed-source-description-hash-is-reported-never-silently-applied")
    def test_changed_prompt_digest_is_staff_noted_without_replacing_the_image(self):
        subject = _scene("city_street")
        ensure(subject, "same description")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/city_street.png",
            error=None,
        )
        # Simulate an admin edit of art.scene_prompt: the stored digest no
        # longer matches the current rendering while the source hash is
        # untouched.
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        record.db.prompt_digest = "stale-digest"
        record.save()
        ensure(subject, "same description")
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/city_street.png")
        self.assertTrue(record.db.hash_changed)
        self.assertEqual(record.db.source_hash, source_hash("same description"))

    def test_ensure_stores_the_rendered_prompt_digest(self):
        subject = _scene("forest_path")
        record = ensure(subject, "desc")
        self.assertTrue(record.db.prompt_digest)
        self.assertNotEqual(record.db.prompt_digest, source_hash("desc"))
        again = ensure(subject, "desc")
        self.assertEqual(again.db.prompt_digest, record.db.prompt_digest)
        self.assertEqual(again.db.status, ArtAssetStatus.PENDING)

    def test_requeue_recomputes_the_rendered_prompt_digest(self):
        subject = _scene("dungeon_interior")
        ensure(subject, "desc")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/dungeon_interior.png",
            error=None,
        )
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        record.db.prompt_digest = "stale-digest"
        record.save()
        requeue(subject)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertNotEqual(record.db.prompt_digest, "stale-digest")
        self.assertTrue(record.db.prompt_digest)

    @covers_requirement("art-queue-worker::asset-records-carry-the-full-contract-and-never-a-live-object-reference")
    def test_claim_makes_in_progress_with_a_lease_and_increments_attempts(self):
        subject = _scene("mountain_path")
        ensure(subject, "desc")
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        record = claimed[0]
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertIsNotNone(record.db.claimed_at)
        self.assertEqual(int(record.db.attempt_count), 1)
        self.assertEqual(record.db.aspect_ratio, "16:9")

    @covers_requirement("art-queue-worker::asset-records-carry-the-full-contract-and-never-a-live-object-reference")
    def test_expired_lease_is_reclaimed_to_pending(self):
        subject = _scene("coastal_path")
        ensure(subject, "desc")
        claim(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        reclaimed = reclaim_expired_leases(0.001)
        self.assertEqual(reclaimed, 1)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertIsNone(record.db.claimed_at)

    def test_failed_keys_lists_failed_subjects(self):
        good = _scene("forest_path")
        bad = _scene("cave_interior")
        ensure(good, "g")
        ensure(bad, "b")
        claim(10)
        settle(good, status=ArtAssetStatus.DONE,
               output_identity="scene/forest_path.png", error=None)
        settle(bad, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        self.assertEqual(failed_keys(), ["scene:cave_interior"])

    def test_duplicate_records_are_consolidated_keeping_the_most_advanced(self):
        subject = _scene("ruin_interior")
        from world.art.queue import _create_record, record_key

        first = _create_record(subject)
        second = _create_record(subject)
        second.db.status = ArtAssetStatus.DONE
        second.db.output_identity = "scene/ruin_interior.png"
        ensure(subject, "desc")
        records = ArtAssetRecord.objects.filter(db_key=record_key(subject))
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.DONE)

    @covers_requirement("art-queue-worker::scenes-and-portraits-share-one-serialization-lock-and-one-worker-concurrency-slot")
    def test_concurrent_drains_serialize_and_never_hold_the_lock_across_a_worker_wait(self):
        for key in ("forest_path", "tavern_interior", "city_street"):
            ensure(_scene(key), f"desc-{key}")
        # A drain is claim -> worker run -> settle. The worker run must never
        # execute while the queue lock is held: after claim() returns the lock
        # must already be released, so the simulated worker wait and the second
        # drain both observe a free lock and unmutated records.
        lock_free_during_worker_wait = []
        first_batch = claim(2)
        self.assertEqual(len(first_batch), 2)
        lock_free_during_worker_wait.append(not queue_lock.locked())
        for record in first_batch:
            settle(
                _scene(record.db.subject_key),
                status=ArtAssetStatus.FAILED,
                output_identity=None,
                error="fixture",
            )
        second_batch = claim(2)
        lock_free_during_worker_wait.append(not queue_lock.locked())
        self.assertEqual(len(second_batch), 1)
        self.assertEqual(
            {record.db.subject_key for record in second_batch}, {"city_street"}
        )
        self.assertTrue(all(lock_free_during_worker_wait))
        pending = [
            record
            for record in ArtAssetRecord.objects.all()
            if record.db.status == ArtAssetStatus.PENDING
        ]
        self.assertEqual(len(pending), 0)


if __name__ == "__main__":
    unittest.main()
