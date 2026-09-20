"""Slice of ``test_service``: GalleryPruneTests.
"""
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
from world.art.gallery_prompt import (
    CUSTOM_PROMPT_MAX,
    GalleryPromptError,
)
from world.art.sd_worker import SDError
from world.art.service import requeue_gallery_subject
from world.art.service import prune_gallery_orphans
from world.art.subjects import (
    ArtSubjectError,
    monster_description,
    monster_subject_for,
    scene_subject_for,
)
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    request_gallery_image,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_ITEMS,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

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
