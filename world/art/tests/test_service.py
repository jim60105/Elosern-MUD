"""Tests for the sole-writer art service and its deterministic seams."""

from unittest.mock import patch
import unittest

from contextlib import contextmanager
import tempfile
from pathlib import Path

from django.db import transaction
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.art.queue import ensure, record_key, source_hash
from world.art import gallery as gallery_api
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.sd_worker import SDError
from world.art.service import prune_gallery_orphans
from world.art.subjects import ArtSubjectError
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    request_gallery_image,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

from tools.spec_traceability import covers_requirement


def _scene(key):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _valid_binding():
    return {"mask": ["armor"], "snapshot": {"armor": "leather_armor"}}


class ArtServiceTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="service-player")
        self.player.age = 22
        self.player.apparent_age = 22

    def _records(self):
        return {record.db_key: record for record in ArtAssetRecord.objects.all()}

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_ensures_every_registered_subject_on_a_fresh_db(self):
        art_sync_all()
        records = self._records()
        for archetype in SCENE_ARCHETYPE_REGISTRY:
            self.assertIn(f"art:scene:{archetype}", records)
            self.assertIn(
                records[f"art:scene:{archetype}"].db.status,
                (ArtAssetStatus.MISSING, ArtAssetStatus.PENDING),
            )
        for tier in MONSTER_TIER_REGISTRY:
            self.assertIn(f"art:portrait:monster:{tier}", records)
        self.assertEqual(len(records), len(SCENE_ARCHETYPE_REGISTRY) + len(MONSTER_TIER_REGISTRY))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_leaves_pending_in_progress_and_done_records_untouched(self):
        subject = _scene("forest_path")
        ensure(subject, "desc")
        art_sync_all()
        self.assertEqual(len(self._records()), len(SCENE_ARCHETYPE_REGISTRY) + len(MONSTER_TIER_REGISTRY))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_consolidates_duplicate_records(self):
        from world.art.queue import _create_record

        subject = _scene("forest_path")
        first = _create_record(subject)
        second = _create_record(subject)
        second.db.status = ArtAssetStatus.DONE
        second.db.output_identity = "scene/forest_path.png"
        art_sync_all()
        records = ArtAssetRecord.objects.filter(db_key=record_key(subject))
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.DONE)

    @covers_requirement("art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies")
    def test_recovery_creates_a_missing_named_policy_record(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        art_sync_all()
        key = f"art:portrait:character:{self.player.pk}"
        self.assertIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies")
    @covers_requirement("art-asset-lifecycle::the-age-check-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_recovery_skips_an_ineligible_subject_deterministically(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.attributes.remove("age")
        art_sync_all()
        key = f"art:portrait:character:{self.player.pk}"
        self.assertNotIn(key, self._records())
        art_sync_all()
        self.assertNotIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    def test_schedule_portrait_ensure_runs_the_gate_and_writes_one_record(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        key = f"art:portrait:character:{self.player.pk}"
        records = ArtAssetRecord.objects.filter(db_key=key)
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-asset-lifecycle::portrait-character-enqueue-validates-canonical-age-attributes-immediately-before-enqueue")
    def test_rejected_portrait_produces_no_record_and_no_worker_call(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.attributes.remove("age")
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch("world.art.worker._run_and_settle_batch") as worker,
        ):
            schedule_portrait_ensure(self.player)
        # The missing canonical age rejects at schedule time: no on_commit
        # callback is even registered, and no record or worker call is
        # produced.
        self.assertEqual(len(callbacks), 0)
        worker.assert_not_called()
        key = f"art:portrait:character:{self.player.pk}"
        self.assertNotIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_an_art_callback_exception_never_propagates_to_the_owning_workflow(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch(
                "world.art.service._ensure_character_portrait",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(self.player.creation_pending is not None)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_creates_or_leaves_a_record_for_a_validated_archetype(self):
        ensure_scene_asset("forest_path")
        self.assertIn("art:scene:forest_path", self._records())
        ensure_scene_asset("forest_path")
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").count(), 1
        )

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_is_a_noop_for_none_or_unresolvable_archetype(self):
        ensure_scene_asset(None)
        ensure_scene_asset("not_a_scene")
        self.assertEqual(self._records(), {})

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_scene_asset_failure_is_bounded_and_never_blocks_the_move(self):
        with patch(
            "world.art.service.queue_ensure",
            side_effect=RuntimeError("art boom"),
        ):
            ensure_scene_asset("forest_path")
        self.assertEqual(self._records(), {})


class GalleryRequestSeamTests(EvenniaTestCase):
    """request_gallery_image validates before any write and never gates."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="gallery-player")
        self.player.age = 30
        self.player.apparent_age = 25
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.player.pk))

    def _gallery_jobs(self):
        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_a_valid_request_queues_exactly_one_job_with_the_supplied_metadata(self):
        rect = {"x": 0.2, "y": 0.1, "w": 0.5, "h": 0.5}
        with patch("world.art.service.log_info") as info:
            image_id = request_gallery_image(
                self.player, binding=_valid_binding(), face_rect=rect
            )
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.db_key, f"art:{self.subject.full()}:gen:{image_id}")
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(dict(job.db.gallery_binding), _valid_binding())
        self.assertEqual(dict(job.db.gallery_face_rect), rect)
        self.assertEqual(gallery_api.cards_for(self.subject), [])
        generates = [
            call for call in info.call_args_list if call.args and call.args[0] == "gallery_generate"
        ]
        self.assertEqual(len(generates), 1)
        self.assertEqual(
            generates[0].kwargs["context"],
            {"subject": self.subject.full(), "image_id": image_id, "kind": self.subject.kind.value},
        )

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_invalid_binding_or_rect_never_reaches_the_queue(self):
        with patch("world.art.queue._prompt_digest_or_empty") as digest:
            with self.assertRaises(gallery_api.GalleryRecordError):
                request_gallery_image(self.player, binding={"mask": []})
            with self.assertRaises(gallery_api.GalleryRecordError):
                request_gallery_image(
                    self.player, face_rect={"x": 0.8, "y": 0.8, "w": 0.5, "h": 0.5}
                )
        self.assertEqual(self._gallery_jobs(), [])
        digest.assert_not_called()

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_ineligible_subject_is_rejected_deterministically(self):
        self.player.attributes.remove("age")
        with patch("world.art.sd_worker.render_prompt_pair") as render:
            with self.assertRaises(ArtSubjectError):
                request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])
        render.assert_not_called()

        self.player.age = 30
        self.player.attributes.remove("apparent_age")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])

        self.player.apparent_age = 25
        self.player.age = "not-an-integer"
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])

        plain = create_object(NPC, key="gallery-no-policy")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(plain)
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-generation::generation-while-the-image-server-is-unreachable-is-a-reported-failure-never-a-gate"
    )
    def test_an_offline_request_settles_failed_with_the_named_code_and_no_card(self):
        request_gallery_image(self.player)
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(fake):
            from world.art.worker import drain_synchronous

            drain_synchronous(10)
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(gallery_api.cards_for(self.subject), [])
        record = gallery_api.record_for(self.subject)
        self.assertIsNotNone(record)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        self.assertIsNotNone(record.db.last_error_at)


class GalleryPruneTests(EvenniaTestCase):
    """The startup prune reclaims orphan files and spent job records only."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "9001")

    def _write(self, identity: str) -> Path:
        path = self.root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"img")
        return path

    def _card(self, image_id: str, identity: str):
        gallery_api.append_card(
            self.subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_an_orphan_gallery_file_is_reclaimed_and_referenced_files_survive(self):
        referenced = self._write("gallery/character/9001/11111111-1111-4111-8111-111111111111.png")
        self._card(
            "11111111-1111-4111-8111-111111111111",
            "gallery/character/9001/11111111-1111-4111-8111-111111111111.png",
        )
        outside_gallery = self._write("portrait/character/legacy.png")
        orphan = self._write("gallery/character/9001/deadbeef-1111-4111-8111-111111111111.png")
        result = prune_gallery_orphans()
        self.assertFalse(orphan.exists())
        self.assertTrue(referenced.exists())
        self.assertTrue(outside_gallery.exists())
        self.assertEqual(result["files"], 1)
        # Idempotent: a second pass deletes nothing.
        self.assertEqual(prune_gallery_orphans(), {"files": 0, "records": 0})

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_a_missing_or_unreadable_gallery_tree_never_raises(self):
        # No gallery/ directory at all.
        prune_gallery_orphans()
        tree = self._write("gallery/character/9001/x.png").parent
        with patch("pathlib.Path.rglob", side_effect=OSError("unreadable tree")):
            prune_gallery_orphans()
        self.assertTrue(tree.is_dir())

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_a_failing_deletion_is_bounded_and_a_failed_reference_read_deletes_nothing(self):
        orphan = self._write("gallery/character/9001/deadbeef-1111-4111-8111-111111111111.png")
        # One deletion raising never aborts the sweep and never raises out.
        with patch("pathlib.Path.unlink", side_effect=OSError("busy")):
            result = prune_gallery_orphans()
        self.assertEqual(result["files"], 0)
        self.assertTrue(orphan.exists())
        # Without a readable reference set NOTHING may be deleted — not even
        # orphans: a prune must never delete a file a card references.
        with patch(
            "world.art.gallery.referenced_stored_identities",
            side_effect=RuntimeError("db down"),
        ):
            result = prune_gallery_orphans()
        self.assertEqual(result["files"], 0)
        self.assertTrue(orphan.exists())

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_unclaimable_job_records_are_pruned_while_claimable_jobs_survive(self):
        from world.art.queue import enqueue_gallery_job
        import time

        # A claimable pending job and a lease-expired in_progress job survive.
        pending = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000001",
            binding=None, face_rect=None, requested_fields=[],
        )
        in_flight = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000002",
            binding=None, face_rect=None, requested_fields=[],
        )
        in_flight.db.status = ArtAssetStatus.IN_PROGRESS
        in_flight.db.claimed_at = time.time()
        # An unresolvable-subject job and a terminal-status job never publish.
        broken = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000003",
            binding=None, face_rect=None, requested_fields=[],
        )
        broken.db.subject_key = "bad|key"
        dead = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000004",
            binding=None, face_rect=None, requested_fields=[],
        )
        dead.db.status = ArtAssetStatus.FAILED
        result = prune_gallery_orphans()
        self.assertEqual(result["records"], 2)
        keys = {record.db_key for record in ArtAssetRecord.objects.all()}
        self.assertIn(pending.db_key, keys)
        # A live in-progress job (lease unexpired) is never pruned.
        self.assertIn(in_flight.db_key, keys)
        self.assertEqual(in_flight.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertNotIn(broken.db_key, keys)
        self.assertNotIn(dead.db_key, keys)

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_an_in_progress_job_past_its_lease_is_retained_for_reclaim(self):
        from world.art.queue import claim

        job = self._job("bbbb0000-0000-4000-8000-000000000001")
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        # Force the lease far past its expiry WITHOUT reclaiming.
        claimed[0].db.claimed_at = 0.0
        claimed[0].save()
        result = prune_gallery_orphans()
        self.assertEqual(result["records"], 0)
        self.assertEqual(job.db.status, ArtAssetStatus.IN_PROGRESS)
        # The shared reclaim (not the prune) returns it to pending.
        from world.art.queue import reclaim_expired_leases

        self.assertEqual(reclaim_expired_leases(0.001), 1)

    def _job(self, image_id):
        from world.art.queue import enqueue_gallery_job

        return enqueue_gallery_job(
            self.subject, "d", image_id=image_id,
            binding=None, face_rect=None, requested_fields=[],
        )


if __name__ == "__main__":
    unittest.main()
