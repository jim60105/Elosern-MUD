"""Tests for the staff-only ``@art`` command family."""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.art import (
    CmdArtRequeue,
    CmdArtRetry,
    CmdArtRun,
    CmdArtStatus,
)
from world.art.queue import claim, ensure, requeue, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_staff_can_list_scene_records_without_persona_or_paths(self):
        ensure(_scene("forest_path"), "desc")
        claim(10)
        settle(
            _scene("forest_path"),
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        output = self.call(CmdArtStatus(), "scene")
        self.assertIn("scene:forest_path", output)
        self.assertIn("[done]", output)
        self.assertNotIn("/app", output)
        self.assertNotIn(".art", output)
        self.assertNotIn("persona", output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_portrait_filter_lists_portrait_records(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, "low")
        ensure(subject, "desc")
        output = self.call(CmdArtStatus(), "portrait")
        self.assertIn("portrait:monster:low", output)
        scene_output = self.call(CmdArtStatus(), "scene")
        self.assertNotIn("portrait:monster:low", scene_output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    @covers_requirement("art-staff-commands::players-have-no-access-to-any-art-control")
    def test_non_staff_is_denied_every_subcommand(self):
        ensure(_scene(), "desc")
        for cmd, args in (
            (CmdArtStatus(), ""),
            (CmdArtRun(), "--limit 1"),
            (CmdArtRetry(), ""),
            (CmdArtRequeue(), "scene:forest_path"),
        ):
            with self.subTest(cmd=cmd.key):
                output = self.call(cmd, args, caller=self.char2)
                self.assertIn("沒有權限", output)

    @covers_requirement("art-staff-commands::art-run-drains-the-shared-queue-now-with-an-optional-limit")
    def test_bounded_drain_dispatches_pending_jobs(self):
        ensure(_scene("forest_path"), "a")
        ensure(_scene("tavern_interior"), "b")
        ensure(_scene("city_street"), "c")
        with patch("world.art.worker.drain", return_value=2) as drain:
            output = self.call(CmdArtRun(), "--limit 2")
        drain.assert_called_once_with(2)
        self.assertIn("2", output)

    @covers_requirement("art-staff-commands::art-retry-re-enqueues-failed-records")
    def test_retry_reenqueues_failed_records(self):
        subject = _scene("forest_path")
        ensure(subject, "desc")
        claim(10)
        settle(subject, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        with patch("world.art.worker.drain"):
            output = self.call(CmdArtRetry(), "")
        record = ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").first()
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertIn("1", output)

    @covers_requirement("art-staff-commands::art-requeue-accepts-one-validated-full-subject-key-and-forces-regeneration-under-the-lock")
    def test_requeue_valid_key_forces_regeneration_preserving_prior_output(self):
        subject = _scene("forest_path")
        ensure(subject, "desc")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        output = self.call(CmdArtRequeue(), "scene:forest_path")
        record = ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").first()
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(record.db.prior_output_identity, "scene/forest_path.png")
        self.assertIn("scene:forest_path", output)

    @covers_requirement("art-staff-commands::art-requeue-accepts-one-validated-full-subject-key-and-forces-regeneration-under-the-lock")
    def test_requeue_invalid_key_is_rejected_with_no_record_change(self):
        ensure(_scene("forest_path"), "desc")
        before = ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").first()
        before_status = before.db.status
        output = self.call(CmdArtRequeue(), "not_a_subject")
        self.assertIn("無效", output)
        after = ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").first()
        self.assertEqual(after.db.status, before_status)
        self.assertEqual(ArtAssetRecord.objects.count(), 1)

    @covers_requirement("art-staff-commands::art-requeue-accepts-one-validated-full-subject-key-and-forces-regeneration-under-the-lock")
    def test_requeue_unregistered_scene_key_is_rejected_with_no_record_change(self):
        output = self.call(CmdArtRequeue(), "scene:not_registered")
        self.assertIn("無效", output)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key="art:scene:not_registered").count(), 0
        )

    @covers_requirement("art-staff-commands::art-requeue-accepts-one-validated-full-subject-key-and-forces-regeneration-under-the-lock")
    @covers_requirement("adult-portrait-gate::the-gate-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_requeue_underage_character_is_rejected_with_no_record_change(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="underage-for-requeue")
        player.db.age = 17
        player.db.apparent_age = 22
        player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(player.pk),
        }
        output = self.call(
            CmdArtRequeue(), f"portrait:character:{player.pk}"
        )
        self.assertIn("無法重新排入", output)
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{player.pk}"
            ).count(),
            0,
        )

    @covers_requirement("adult-portrait-gate::the-gate-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_retry_skips_an_underage_character_portrait(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter
        from world.art.queue import source_hash

        player = create_object(PlayerCharacter, key="underage-retry")
        player.db.age = 17
        player.db.apparent_age = 22
        player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(player.pk),
        }
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        ensure(subject, "desc")
        claim(10)
        settle(subject, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("0", output)
        record = ArtAssetRecord.objects.filter(
            db_key=f"art:portrait:character:{player.pk}"
        ).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)


if __name__ == "__main__":
    import unittest

    unittest.main()
