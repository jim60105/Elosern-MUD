"""Tests for the sole-writer art service and its deterministic seams."""

from unittest.mock import patch
import unittest

from django.db import transaction
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.art.adult import ADULT_MINIMUM, PortraitRejected
from world.art.queue import ensure, record_key, source_hash
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

from tools.spec_traceability import covers_requirement


def _scene(key):
    return ArtSubject(ArtSubjectKind.SCENE, key)


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
    @covers_requirement("adult-portrait-gate::the-gate-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_recovery_skips_an_ineligible_subject_deterministically(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.age = ADULT_MINIMUM - 1
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

    @covers_requirement("adult-portrait-gate::every-character-portrait-enqueue-re-checks-both-adult-age-fields-immediately-before-enqueue")
    def test_rejected_portrait_produces_no_record_and_no_worker_call(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.age = ADULT_MINIMUM - 1
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch("world.art.worker._run_and_settle_batch") as worker,
        ):
            schedule_portrait_ensure(self.player)
        # The gate rejects at schedule time: no on_commit callback is even
        # registered, and no record or worker call is produced.
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


if __name__ == "__main__":
    unittest.main()
