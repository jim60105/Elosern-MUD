"""Tests for the staff-only ``@art`` command family."""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

from commands.art import (
    CmdArtHealth,
    CmdArtOptions,
    CmdArtRequeue,
    CmdArtRetry,
    CmdArtRun,
    CmdArtStatus,
)
from world.art.connectivity import ProbeResult
from world.art.queue import claim, ensure, requeue, settle
from world.art.queue import enqueue_gallery_job, is_gallery_job
from world.art.sd_worker import SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _sync_defer_to_thread(inline_callback, *args, **kwargs):
    """Run the threaded work synchronously and return a settled Deferred.

    Replaces ``twisted.internet.threads.deferToThread`` so command tests never
    spawn a thread: a success resolves the deferred with the value, a failure
    errbacks it with a ``Failure`` exactly like the real dispatch.
    """
    deferred = Deferred()
    try:
        deferred.callback(inline_callback(*args, **kwargs))
    except Exception:  # noqa: BLE001 - mirror real dispatch semantics
        deferred.errback(Failure())
    return deferred


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
    @covers_requirement("art-asset-lifecycle::the-age-check-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_requeue_character_with_missing_canonical_age_is_rejected_with_no_record_change(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="missing-age-for-requeue")
        player.db.age = None
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

    @covers_requirement("art-staff-commands::art-requeue-accepts-one-validated-full-subject-key-and-forces-regeneration-under-the-lock")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_requeue_character_requests_a_gallery_job_with_no_classic_record(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter
        from world.art import gallery as gallery_api

        player = create_object(PlayerCharacter, key="requeue-character")
        player.db.age = 30
        player.db.apparent_age = 30
        player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(player.pk),
        }
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        # An occupied gallery: requeue is the force path and still requests.
        seeded = gallery_api.append_card(
            subject,
            image_id="a1b2c3d4-0000-4000-8000-000000000009",
            stored_identity=(
                "gallery/character/"
                f"{player.pk}/a1b2c3d4-0000-4000-8000-000000000009.png"
            ),
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        cards_before = gallery_api.cards_for(subject)
        output = self.call(CmdArtRequeue(), f"portrait:character:{player.pk}")
        self.assertIn("已將", output)
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{player.pk}:gen:")
        )
        # No classic fixed-identity record, and the existing card is untouched
        # until the new card is appended.
        self.assertFalse(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{player.pk}"
            ).exists()
        )
        self.assertEqual(gallery_api.cards_for(subject), cards_before)
        self.assertEqual(seeded["image_id"], cards_before[0]["image_id"])

    @covers_requirement("art-asset-lifecycle::the-age-check-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_retry_skips_a_character_portrait_with_a_non_integer_age(self):
        # Rewritten (task 6.7) against the gallery arm: the age check now
        # rejects through the request seam, deterministically, with the
        # recorded error kept and no job produced — the classic record the
        # old test manufactured via ``queue.ensure`` is a state production
        # can no longer produce for a character.
        from world.art import gallery as gallery_api

        player = self._portrait_player("non-int-age-retry", age="twenty")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("已重新排入 0 個失敗記錄，並重新請求 0 次圖庫生成", output)
        # Deterministic rejection: no job, no classic record, error retained.
        self.assertFalse(
            any(
                is_gallery_job(record)
                for record in ArtAssetRecord.objects.all()
            )
        )
        self.assertFalse(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{player.pk}"
            ).exists()
        )
        self.assertEqual(
            [state.subject for state in gallery_api.erroring_subjects()], [subject]
        )

    def _portrait_player(self, key, *, age=30, apparent=30):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key=key)
        player.db.age = age
        player.db.apparent_age = apparent
        player.db.portrait_policy = {"mode": "named", "stable_key": str(player.pk)}
        return player

    @covers_requirement("art-staff-commands::art-retry-re-enqueues-failed-records")
    def test_retry_re_requests_an_erroring_character_exactly_once(self):
        from world.art import gallery as gallery_api

        player = self._portrait_player("retry-gallery-ok")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 1 次圖庫生成", output)
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if is_gallery_job(record)
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{player.pk}:gen:")
        )
        # The classic re-enqueue count is honestly zero.
        self.assertIn("已重新排入 0 個失敗記錄", output)

    @covers_requirement("art-staff-commands::art-retry-re-enqueues-failed-records")
    def test_retry_skips_an_ineligible_erroring_subject_without_aborting(self):
        from world.art import gallery as gallery_api

        # An erroring subject whose entity no longer exists: typed rejection,
        # error kept, no record change — and a healthy scene record in the
        # same store still re-enqueues.
        ghost = ArtSubject(ArtSubjectKind.CHARACTER, "999999")
        gallery_api.record_error(ghost, "sd_connection_error")
        scene = _scene("forest_path")
        ensure(scene, "desc")
        claim(10)
        settle(scene, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("已重新排入 1 個失敗記錄，並重新請求 0 次圖庫生成", output)
        # The ghost keeps its recorded error (typed rejection keeps it).
        self.assertEqual(
            [state.subject for state in gallery_api.erroring_subjects()], [ghost]
        )
        self.assertIsNone(
            ArtAssetRecord.objects.filter(
                db_key__startswith="art:portrait:character:999999:gen:"
            ).first()
        )

    @covers_requirement("art-staff-commands::art-retry-re-enqueues-failed-records")
    def test_retry_clears_a_moot_error_on_a_subject_that_now_has_art(self):
        import uuid

        from world.art import gallery as gallery_api

        player = self._portrait_player("retry-gallery-moot")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
        # A card arrived since the failure: the automatic guard will suppress
        # every future request, so the error is moot.
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/character/{player.pk}/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 0 次圖庫生成", output)
        # No job was requested, the error is cleared, and the subject is gone
        # from the erroring surface.
        self.assertFalse(
            any(
                is_gallery_job(record)
                for record in ArtAssetRecord.objects.all()
            )
        )
        self.assertEqual(gallery_api.erroring_subjects(), [])
        status_output = self.call(CmdArtStatus(), "")
        self.assertNotIn("sd_connection_error", status_output)

    @covers_requirement("art-staff-commands::art-retry-re-enqueues-failed-records")
    def test_retry_requests_nothing_when_no_gallery_record_errors(self):
        output = self.call(CmdArtRetry(), "")
        self.assertIn("已重新排入 0 個失敗記錄，並重新請求 0 次圖庫生成", output)
        self.assertFalse(
            any(is_gallery_job(record) for record in ArtAssetRecord.objects.all())
        )


class ArtOptionsCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """``@art options`` with the thread dispatch replaced by a sync seam."""

    def _options(self, args, names=None, error=None, caller=None):
        def work():
            if error is not None:
                raise error
            return names

        with patch(
            "twisted.internet.threads.deferToThread",
            side_effect=_sync_defer_to_thread,
        ) as dispatch:
            with patch("world.art.sd_worker.list_models", side_effect=work):
                with patch("world.art.sd_worker.list_samplers", side_effect=work):
                    with patch("world.art.sd_worker.list_styles", side_effect=work):
                        output = self.call(CmdArtOptions(), args, caller=caller)
        return output, dispatch

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_lists_names_under_a_kind_and_count_header(self):
        output, dispatch = self._options("samplers", names=["Euler a", "ER SDE"])
        dispatch.assert_called_once()
        self.assertIn("2 項", output)
        self.assertIn("1. Euler a", output)
        self.assertIn("2. ER SDE", output)
        # Zero writes: the enumeration never creates or mutates a record.
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_display_names_are_clamped_to_256_code_points(self):
        output, _ = self._options("samplers", names=["x" * 300])
        self.assertIn("x" * 256, output)
        self.assertNotIn("x" * 257, output)

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_failure_prints_the_named_code_and_no_partial_list(self):
        output, _ = self._options(
            "models", error=SDError("sd_connection_error", "offline")
        )
        self.assertIn("sd_connection_error", output)
        self.assertNotIn("1.", output)

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_invalid_argument_is_rejected_without_any_request(self):
        for args in ("", "nope", "models extra"):
            with self.subTest(args=args):
                output, dispatch = self._options(args, names=[])
                self.assertIn("用法：art options", output)
                dispatch.assert_not_called()

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    @covers_requirement("art-staff-commands::players-have-no-access-to-any-art-control")
    def test_non_staff_is_denied_with_no_request(self):
        output, dispatch = self._options("models", names=[], caller=self.char2)
        self.assertIn("沒有權限", output)
        dispatch.assert_not_called()

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_output_never_leaks_credentials_or_authorization_material(self):
        output, _ = self._options("styles", names=["cinematic"])
        self.assertNotIn("Authorization", output)
        self.assertNotIn("Basic ", output)


class ArtStatusSeedColumnTests(EvenniaCommandTestMixin, EvenniaTest):
    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_done_record_shows_its_persisted_seed(self):
        ensure(_scene("forest_path"), "desc")
        claim(10)
        settle(
            _scene("forest_path"),
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        record = ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").first()
        record.db.seed = 42
        output = self.call(CmdArtStatus(), "")
        self.assertIn(" seed=42", output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_seedless_record_shows_no_seed_field(self):
        ensure(_scene("forest_path"), "desc")
        output = self.call(CmdArtStatus(), "")
        self.assertIn("scene:forest_path", output)
        self.assertNotIn("seed=", output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_gallery_job_records_are_invisible_to_the_status_listing(self):
        ensure(_scene("forest_path"), "desc")
        enqueue_gallery_job(
            ArtSubject(ArtSubjectKind.CHARACTER, "42"),
            "desc",
            image_id="99999999-9999-4999-8999-999999999999",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn("scene:forest_path", output)
        self.assertNotIn(":gen:", output)
        portrait_output = self.call(CmdArtStatus(), "portrait")
        self.assertNotIn(":gen:", portrait_output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_a_failed_gallery_generation_is_visible_with_its_bounded_code(self):
        from world.art import gallery as gallery_api

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertIn("portrait:character:42", output)
        self.assertIn("sd_connection_error", output)
        # The section obeys the non-leakage rule.
        self.assertNotIn("persona", output)
        self.assertNotIn("prompt", output)
        self.assertNotIn("stored_identity", output)
        self.assertNotIn("/app", output)
        # A scene filter yields no gallery rows (gallery kinds are portraits).
        scene_output = self.call(CmdArtStatus(), "scene")
        self.assertNotIn("portrait:character:42", scene_output)
        self.assertNotIn("圖庫狀態:", scene_output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_a_healthy_gallery_line_shows_cards_and_default_with_no_error(self):
        import uuid

        from world.art import gallery as gallery_api

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/character/42/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertIn("portrait:character:42 卡片:1 預設:是", output)
        self.assertNotIn("錯誤:", output.split("圖庫狀態:")[1])

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_a_gallery_only_store_still_shows_the_gallery_section(self):
        # The classic listing is empty; the healthy gallery must still appear
        # (the gallery-only case, not the both-empty message).
        import uuid

        from world.art import gallery as gallery_api

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/character/42/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertNotIn("沒有符合的美術資產記錄。", output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_both_surfaces_empty_keeps_the_empty_message(self):
        output = self.call(CmdArtStatus(), "")
        self.assertIn("沒有符合的美術資產記錄。", output)

    @covers_requirement("art-staff-commands::art-status-lists-and-filters-records-without-leaking-sensitive-data")
    def test_the_broad_portrait_filter_keeps_the_pre_existing_classic_behaviour(self):
        # A bare ``portrait``-prefixed classic record matches the startswith
        # filter — the pre-existing classic behaviour this change must not
        # alter.
        subject = ArtSubject(ArtSubjectKind.MONSTER, "low")
        ensure(subject, "desc")
        output = self.call(CmdArtStatus(), "portrait")
        self.assertIn("portrait:monster:low", output)


class ArtHealthCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """``@art health`` with the thread dispatch replaced by a sync seam."""

    def _health(self, result, caller=None):
        from world.art import connectivity

        with patch(
            "twisted.internet.threads.deferToThread",
            side_effect=_sync_defer_to_thread,
        ) as dispatch:
            with patch.object(connectivity, "probe", return_value=result) as probe:
                output = self.call(CmdArtHealth(), "", caller=caller)
        return output, dispatch, probe

    @staticmethod
    def _verdict(ok=True, code=None, from_cache=False, age=0.0):
        return ProbeResult(
            ok=ok,
            code=code,
            host="sd.internal",
            checked_at=0.0,
            age_seconds=age,
            from_cache=from_cache,
        )

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_reachable_dashboard_shows_all_five_sections(self):
        ensure(_scene("forest_path"), "desc")
        claim(10)
        settle(
            _scene("forest_path"),
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        ensure(_scene("old_ruins"), "desc")
        claim(10)
        settle(
            _scene("old_ruins"),
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="sd_connection_error",
        )
        output, dispatch, _ = self._health(self._verdict())
        dispatch.assert_called_once()
        lines = output.splitlines()
        self.assertEqual(lines[0], "server: reachable (checked just now)")
        self.assertEqual(lines[1], "scheduler: enabled interval=30s limit=4")
        self.assertEqual(lines[2], "queue: pending=0 in_progress=0 failed=1 done=1")
        self.assertEqual(lines[3], "gallery: records=0 cards=0 erroring=0")
        self.assertEqual(lines[4], "output: png q=80 metadata=on")

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_the_gallery_line_counts_records_cards_and_erroring_subjects(self):
        import uuid

        from world.art import gallery as gallery_api

        one = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            one,
            image_id=image_id,
            stored_identity=f"gallery/character/42/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        gallery_api.record_error(one, "sd_connection_error")
        two = ArtSubject(ArtSubjectKind.CHARACTER, "43")
        gallery_api.record_error(two, "sd_timeout")
        output, _, _ = self._health(self._verdict())
        self.assertIn("gallery: records=2 cards=1 erroring=2", output)

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_unreachable_line_keeps_remaining_sections(self):
        output, _, probe = self._health(
            self._verdict(ok=False, code="sd_connection_error")
        )
        self.assertIn(
            "server: unreachable — sd_connection_error (checked just now)", output
        )
        self.assertIn("scheduler: ", output)
        self.assertIn("queue: pending=0 in_progress=0 failed=0 done=0", output)
        self.assertIn("output: ", output)
        probe.assert_called_once_with(force=True)

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_queue_counts_exclude_gallery_job_records(self):
        ensure(_scene("forest_path"), "desc")
        enqueue_gallery_job(
            ArtSubject(ArtSubjectKind.CHARACTER, "42"),
            "desc",
            image_id="88888888-8888-4888-8888-888888888888",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        output, _, _ = self._health(self._verdict())
        # The lone pending scene record counts; the pending gallery job does not.
        self.assertIn("queue: pending=1 in_progress=0 failed=0 done=0", output)

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_health_mutates_nothing(self):
        import uuid

        from world.art import gallery as gallery_api

        ensure(_scene("forest_path"), "desc")
        claim(1)
        # Gallery state must survive untouched too: one card, one error.
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/character/42/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        gallery_api.record_error(subject, "sd_timeout")
        gallery_before = [(s.subject.full(), s.card_count, s.has_default, s.error_code) for s in gallery_api.gallery_states()]
        before = [
            (r.db_key, r.db.status, r.db.attempt_count, r.db.output_identity)
            for r in ArtAssetRecord.objects.all()
        ]
        self._health(self._verdict())
        after = [
            (r.db_key, r.db.status, r.db.attempt_count, r.db.output_identity)
            for r in ArtAssetRecord.objects.all()
        ]
        self.assertEqual(before, after)
        gallery_after = [(s.subject.full(), s.card_count, s.has_default, s.error_code) for s in gallery_api.gallery_states()]
        self.assertEqual(gallery_before, gallery_after)

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_output_leaks_no_credentials_userinfo_or_paths(self):
        from django.test import override_settings

        with override_settings(
            ART_SD_USERNAME="operator",
            ART_SD_PASSWORD="sup3r-s3cret",
            ART_SD_BASE_URL="http://user:password@sd.internal:7860",
        ):
            output, _, _ = self._health(self._verdict())
        for forbidden in ("operator", "sup3r-s3cret", "user", "password", "@", "Basic ", "/app", "server/"):
            self.assertNotIn(forbidden, output)

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    @covers_requirement("art-staff-commands::players-have-no-access-to-any-art-control")
    def test_non_staff_denied_without_any_probe(self):
        output, dispatch, probe = self._health(self._verdict(), caller=self.char2)
        self.assertIn("沒有權限", output)
        dispatch.assert_not_called()
        probe.assert_not_called()

    @covers_requirement(
        "art-staff-commands::art-health-reports-server-reachability-scheduler-state-queue-counts-and-output-policy"
    )
    def test_cached_verdict_line_shows_its_age(self):
        output, _, _ = self._health(
            self._verdict(ok=False, code="sd_timeout", from_cache=True, age=12.34)
        )
        self.assertIn(
            "server: unreachable — sd_timeout (checked 12.3s ago)", output
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
