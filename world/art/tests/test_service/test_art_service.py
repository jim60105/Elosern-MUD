"""Slice of ``test_service``: ArtServiceTests.
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

from ._support import (
    open_synthetic_scope,
    _SYNTH_SCENE,
    _scene,
)

class ArtServiceTests(EvenniaTestCase):
    def setUp(self):
        # The startup-sync coverage tests below assert over the REGISTERED
        # subject set, which is exactly what startup synchronization reads:
        # run the whole class against the kit catalogs so the loops iterate
        # SYNTH_* rows instead of shipped content.
        open_synthetic_scope(self, "archetypes", "monster_tiers")
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
        for archetype in SYNTH_ARCHETYPES:
            self.assertIn(f"art:scene:{archetype}", records)
            self.assertIn(
                records[f"art:scene:{archetype}"].db.status,
                (ArtAssetStatus.MISSING, ArtAssetStatus.PENDING),
            )
        # ``gallery-monster-autogen``: a monster tier gets a gallery request,
        # never a classic fixed-identity record.
        for tier in SYNTH_MONSTER_TIERS:
            self.assertNotIn(f"art:portrait:monster:{tier}", records)
        classic = {
            key: record
            for key, record in records.items()
            if not str(record.db.gallery_image_id or "")
        }
        self.assertEqual(
            sorted(classic),
            sorted(f"art:scene:{archetype}" for archetype in SYNTH_ARCHETYPES),
        )
        monster_jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
            and record.db_key.startswith("art:portrait:monster:")
        ]
        self.assertEqual(len(monster_jobs), len(SYNTH_MONSTER_TIERS))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_leaves_pending_in_progress_and_done_records_untouched(self):
        subject = _scene(_SYNTH_SCENE)
        ensure(subject, "desc")
        art_sync_all()
        # Only classic records remain counted: monster tiers hold gallery jobs
        # (per-image records that drain away), never fixed-identity records.
        classic = [
            key
            for key, record in self._records().items()
            if not str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(classic), len(SYNTH_ARCHETYPES))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_consolidates_duplicate_records(self):
        from world.art.queue import _create_record

        subject = _scene(_SYNTH_SCENE)
        first = _create_record(subject)
        second = _create_record(subject)
        second.db.status = ArtAssetStatus.DONE
        second.db.output_identity = f"scene/{_SYNTH_SCENE}.png"
        art_sync_all()
        records = ArtAssetRecord.objects.filter(db_key=record_key(subject))
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.DONE)

    @covers_requirement("art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_recovery_requests_a_gallery_job_for_a_missing_named_policy(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        art_sync_all()
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
            and record.db_key.startswith(f"art:portrait:character:{self.player.pk}:gen:")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{self.player.pk}:gen:")
        )
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)
        # The retrofit: no classic fixed-identity record is ever created.
        self.assertNotIn(f"art:portrait:character:{self.player.pk}", self._records())

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
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_schedule_portrait_ensure_runs_the_gate_and_enqueues_one_gallery_job(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        key = f"art:portrait:character:{self.player.pk}"
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{key}:gen:"))
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)
        self.assertNotIn(key, self._records())

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
                "world.art.service._ensure_gallery_subject",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(self.player.creation_pending is not None)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_creates_or_leaves_a_record_for_a_validated_archetype(self):
        ensure_scene_asset(_SYNTH_SCENE)
        self.assertIn(f"art:scene:{_SYNTH_SCENE}", self._records())
        ensure_scene_asset(_SYNTH_SCENE)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=f"art:scene:{_SYNTH_SCENE}").count(), 1
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
            ensure_scene_asset(_SYNTH_SCENE)
        self.assertEqual(self._records(), {})
