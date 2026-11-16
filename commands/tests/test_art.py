"""Tests for the staff-only ``@art`` command family."""

import tempfile
import uuid
from unittest.mock import patch

from django.test import override_settings
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
from world.art import gallery as gallery_api
from world.art.connectivity import ProbeResult
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.queue import claim, enqueue_gallery_job
from world.art.sd_worker import SDError
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    monster_subject_for,
)
from world.lore.scene_archetypes import SceneArchetype
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

# Scope every class over the synthetic scene-archetype and monster-species
# catalogs: the art layer keys subjects through those registries, so the
# suite drives real validation against kit rows only. A third locally
# authored archetype covers the three-scene queue case.
_EXTRA_ARCHETYPE = SceneArchetype(
    "t_synth_ridge",
    "苔脊小徑",
    "合成的小徑沿著長滿苔蘚的岩脊攀升，燈籠光在霧裡暈開。",
)
_ART_SCOPE = synthetic_registries(
    "archetypes",
    "monster_species",
    extra={"archetypes": {_EXTRA_ARCHETYPE.key: _EXTRA_ARCHETYPE}},
)
_SCENE_KEY = next(iter(SYNTH_ARCHETYPES))
_ALT_SCENE_KEY = "t_synth_ridge"
# Monster art membership is a registered VISUAL species key, never a threat
# tier; the retired tier below belongs only to the refusal assertions.
_MONSTER_KEY = next(iter(SYNTH_MONSTER_SPECIES))
_RETIRED_TIER = next(iter(SYNTH_MONSTER_TIERS))

from tools.spec_traceability import covers_requirement


def _sync_defer_to_thread(inline_callback, *args, **kwargs):
    """Run the threaded work synchronously and return a settled Deferred."""
    deferred = Deferred()
    try:
        deferred.callback(inline_callback(*args, **kwargs))
    except Exception:  # noqa: BLE001 - mirror real dispatch semantics
        deferred.errback(Failure())
    return deferred


def _scene(key=_SCENE_KEY):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _fallback_text() -> str:
    return "已重新請求 0 次圖庫生成"


@_ART_SCOPE
class ArtCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    def test_staff_can_list_gallery_holdings_without_persona_or_paths(self):
        gallery_api.record_error(_scene(_SCENE_KEY), "sd_connection_error")
        output = self.call(CmdArtStatus(), "scene")
        self.assertIn(f"scene:{_SCENE_KEY}", output)
        self.assertIn("圖庫狀態:", output)
        self.assertNotIn("/app", output)
        self.assertNotIn(".art", output)
        self.assertNotIn("persona", output)

    def test_portrait_filter_lists_gallery_holdings(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, _MONSTER_KEY)
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtStatus(), "portrait")
        self.assertIn(f"portrait:monster:{_MONSTER_KEY}", output)
        scene_output = self.call(CmdArtStatus(), "scene")
        self.assertNotIn(f"portrait:monster:{_MONSTER_KEY}", scene_output)

    @covers_requirement("art-staff-commands::players-have-no-access-to-any-art-control")
    def test_non_staff_is_denied_every_subcommand(self):
        gallery_api.record_error(_scene(), "sd_connection_error")
        for cmd, args in (
            (CmdArtStatus(), ""),
            (CmdArtRun(), "--limit 1"),
            (CmdArtRetry(), ""),
            (CmdArtRequeue(), f"scene:{_SCENE_KEY}"),
        ):
            with self.subTest(cmd=cmd.key):
                output = self.call(cmd, args, caller=self.char2)
                self.assertIn("沒有權限", output)

    @covers_requirement("art-staff-commands::art-run-drains-the-shared-queue-now-with-an-optional-limit")
    def test_bounded_drain_dispatches_pending_jobs(self):
        for key in (_SCENE_KEY, "t_synth_lodge", _ALT_SCENE_KEY):
            enqueue_gallery_job(
                _scene(key),
                "desc",
                image_id=str(uuid.uuid4()),
                binding=None,
                face_rect=None,
                requested_fields=[],
            )
        with patch("world.art.worker.drain", return_value=2) as drain:
            output = self.call(CmdArtRun(), "--limit 2")
        drain.assert_called_once_with(2)
        self.assertIn("2", output)

    def test_retry_requests_a_scene_gallery_failure(self):
        subject = _scene(_SCENE_KEY)
        gallery_api.record_error(subject, "sd_connection_error")
        with patch("world.art.worker.drain"):
            output = self.call(CmdArtRetry(), "")
        self.assertEqual(GalleryJobRecord.objects.count(), 1)
        job = GalleryJobRecord.objects.first()
        self.assertEqual(job.db.kind, ArtSubjectKind.SCENE.value)
        self.assertEqual(job.db.subject_key, _SCENE_KEY)
        self.assertIn("重新請求 1 次圖庫生成", output)

    def test_requeue_scene_key_requests_a_gallery_job_and_keeps_the_card(self):
        subject = _scene(_SCENE_KEY)
        held = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=held,
            stored_identity=f"gallery/scene/{_SCENE_KEY}/{held}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
            image_size={"width": 16, "height": 9},
        )
        output = self.call(CmdArtRequeue(), f"scene:{_SCENE_KEY}")
        self.assertEqual(
            [card["image_id"] for card in gallery_api.cards_for(subject)], [held]
        )
        jobs = list(GalleryJobRecord.objects.all())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].db.kind, ArtSubjectKind.SCENE.value)
        self.assertEqual(jobs[0].db.subject_key, _SCENE_KEY)
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)
        self.assertIn(f"scene:{_SCENE_KEY}", output)

    def test_requeue_invalid_key_is_rejected_with_no_record_change(self):
        enqueue_gallery_job(
            _scene(_SCENE_KEY),
            "desc",
            image_id=str(uuid.uuid4()),
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        before = GalleryJobRecord.objects.count()
        output = self.call(CmdArtRequeue(), "not_a_subject")
        self.assertIn("無效", output)
        self.assertEqual(GalleryJobRecord.objects.count(), before)

    def test_requeue_unregistered_scene_key_is_rejected_with_no_record_change(self):
        output = self.call(CmdArtRequeue(), "scene:not_registered")
        self.assertIn("無法重新排入", output)
        self.assertIn("not_registered", output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)

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
        output = self.call(CmdArtRequeue(), f"portrait:character:{player.pk}")
        self.assertIn("無法重新排入", output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)

    def test_requeue_character_requests_a_gallery_job_without_touching_cards(self):
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        player = create_object(PlayerCharacter, key="requeue-character")
        player.db.age = 30
        player.db.apparent_age = 30
        player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(player.pk),
        }
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
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
            image_size={"width": 1000, "height": 1000},
        )
        cards_before = gallery_api.cards_for(subject)
        output = self.call(CmdArtRequeue(), f"portrait:character:{player.pk}")
        self.assertIn("已將", output)
        jobs = list(GalleryJobRecord.objects.all())
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{player.pk}:gen:")
        )
        self.assertEqual(gallery_api.cards_for(subject), cards_before)
        self.assertEqual(seeded["image_id"], cards_before[0]["image_id"])

    def test_retry_skips_a_character_portrait_with_a_non_integer_age(self):
        player = self._portrait_player("non-int-age-retry", age="twenty")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn(_fallback_text(), output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)
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

    def test_requeue_monster_requests_a_gallery_job_without_touching_cards(self):
        key = _MONSTER_KEY
        subject = monster_subject_for(key)
        with patch("world.art.service.log_info"):
            output = self.call(CmdArtRequeue(), f"portrait:monster:{key}")
        self.assertIn("已將", output)
        jobs = list(GalleryJobRecord.objects.all())
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"art:portrait:monster:{key}:gen:"))
        self.assertEqual(gallery_api.cards_for(subject), [])

    def test_requeue_monster_settles_one_card_under_the_declared_cap(self):
        key = _MONSTER_KEY
        subject = monster_subject_for(key)
        kept = str(uuid.uuid4())
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        with override_settings(
            ART_STORE_ROOT=tempdir.name,
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        ):
            gallery_api.append_card(
                subject,
                image_id=kept,
                stored_identity=f"gallery/monster/{key}/{kept}.png",
                prompt=None,
                seed=None,
                checkpoint=None,
                requested_fields=[],
                binding=None,
                source="seed",
                image_size={"width": 1000, "height": 1000},
            )
            with patch("world.art.service.log_info"):
                output = self.call(CmdArtRequeue(), f"portrait:monster:{key}")
            self.assertIn("已將", output)
            from world.art.worker import drain_synchronous

            with patch(
                "world.art.worker.resolve_sd_client",
                return_value=FakeSDWebUIClient(),
            ):
                drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertNotEqual(cards[0]["image_id"], kept)
        self.assertEqual(
            gallery_api.record_for(subject).db.default_image_id,
            cards[0]["image_id"],
        )

    def test_requeue_unregistered_monster_key_is_rejected_with_no_record_change(self):
        with self.assertRaises(ArtSubjectError):
            monster_subject_for(_RETIRED_TIER)
        output = self.call(CmdArtRequeue(), f"portrait:monster:{_RETIRED_TIER}")
        self.assertIn("無法重新排入", output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)

    @covers_requirement("art-gallery-generation::one-validated-service-seam-requests-every-gallery-image")
    def test_retry_re_requests_an_erroring_monster_subject(self):
        key = _MONSTER_KEY
        subject = monster_subject_for(key)
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 1 次圖庫生成", output)
        jobs = list(GalleryJobRecord.objects.all())
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"art:portrait:monster:{key}:gen:"))

    def test_retry_clears_a_moot_error_on_a_carded_monster_subject(self):
        key = _MONSTER_KEY
        subject = monster_subject_for(key)
        gallery_api.record_error(subject, "sd_connection_error")
        image_id = str(uuid.uuid4())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/monster/{key}/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
            image_size={"width": 1000, "height": 1000},
        )
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 0 次圖庫生成", output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)
        self.assertEqual(gallery_api.erroring_subjects(), [])

    def test_retry_re_requests_an_erroring_character_exactly_once(self):
        player = self._portrait_player("retry-gallery-ok")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 1 次圖庫生成", output)
        jobs = list(GalleryJobRecord.objects.all())
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{player.pk}:gen:")
        )

    def test_retry_skips_an_ineligible_erroring_subject_without_aborting(self):
        ghost = ArtSubject(ArtSubjectKind.CHARACTER, "999999")
        gallery_api.record_error(ghost, "sd_connection_error")
        output = self.call(CmdArtRetry(), "")
        self.assertIn(_fallback_text(), output)
        self.assertEqual(
            [state.subject for state in gallery_api.erroring_subjects()], [ghost]
        )
        self.assertEqual(GalleryJobRecord.objects.count(), 0)

    def test_retry_clears_a_moot_error_on_a_subject_that_now_has_art(self):
        player = self._portrait_player("retry-gallery-moot")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(player.pk))
        gallery_api.record_error(subject, "sd_connection_error")
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
            image_size={"width": 1000, "height": 1000},
        )
        output = self.call(CmdArtRetry(), "")
        self.assertIn("重新請求 0 次圖庫生成", output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)
        self.assertEqual(gallery_api.erroring_subjects(), [])
        status_output = self.call(CmdArtStatus(), "")
        self.assertNotIn("sd_connection_error", status_output)

    def test_retry_requests_nothing_when_no_gallery_record_errors(self):
        output = self.call(CmdArtRetry(), "")
        self.assertIn(_fallback_text(), output)
        self.assertEqual(GalleryJobRecord.objects.count(), 0)


@_ART_SCOPE
class ArtOptionsCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """``@art options`` with the thread dispatch replaced by a sync seam."""

    def _options(self, result):
        with patch(
            "twisted.internet.threads.deferToThread",
            side_effect=_sync_defer_to_thread,
        ) as dispatch:
            if isinstance(result, Exception):
                with patch(
                    "world.art.sd_worker.list_models", side_effect=result
                ):
                    output = self.call(CmdArtOptions(), "models")
            else:
                with patch(
                    "world.art.sd_worker.list_models", return_value=result
                ):
                    output = self.call(CmdArtOptions(), "models")
        return output, dispatch

    @covers_requirement("art-staff-commands::art-options-lists-the-live-server-s-selectable-option-names")
    def test_models_are_listed(self):
        output, dispatch = self._options(["model-b", "model-a"])
        dispatch.assert_called_once()
        self.assertIn("model-a", output)
        self.assertIn("model-b", output)

    def test_backend_error_is_reported_without_transport_noise(self):
        output, _ = self._options(SDError("sd_timeout", "scripted"))
        self.assertIn("sd_timeout", output)
        self.assertNotIn("Basic ", output)


@_ART_SCOPE
class ArtStatusGalleryTests(EvenniaCommandTestMixin, EvenniaTest):
    def test_gallery_job_records_are_invisible_to_the_status_listing(self):
        gallery_api.record_error(_scene(_SCENE_KEY), "sd_connection_error")
        enqueue_gallery_job(
            ArtSubject(ArtSubjectKind.CHARACTER, "42"),
            "desc",
            image_id="99999999-9999-4999-8999-999999999999",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn(f"scene:{_SCENE_KEY}", output)
        self.assertNotIn(":gen:", output)
        portrait_output = self.call(CmdArtStatus(), "portrait")
        self.assertNotIn(":gen:", portrait_output)

    def test_a_failed_gallery_generation_is_visible_with_its_bounded_code(self):
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertIn("portrait:character:42", output)
        self.assertIn("sd_connection_error", output)
        self.assertNotIn("persona", output)
        self.assertNotIn("prompt", output)
        self.assertNotIn("stored_identity", output)
        self.assertNotIn("/app", output)
        scene_output = self.call(CmdArtStatus(), "scene")
        self.assertNotIn("portrait:character:42", scene_output)
        self.assertNotIn("圖庫狀態:", scene_output)
        gallery_api.record_error(_scene(_SCENE_KEY), "sd_internal_error")
        scene_output = self.call(CmdArtStatus(), "scene")
        self.assertIn("圖庫狀態:", scene_output)
        self.assertIn(f"scene:{_SCENE_KEY}", scene_output)
        self.assertNotIn("portrait:character:42", scene_output)
        portrait_output = self.call(CmdArtStatus(), "portrait")
        self.assertIn("portrait:character:42", portrait_output)
        self.assertNotIn(f"scene:{_SCENE_KEY}", portrait_output)

    def test_a_healthy_gallery_line_shows_cards_and_default_with_no_error(self):
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
            image_size={"width": 1000, "height": 1000},
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertIn("portrait:character:42 卡片:1 預設:是", output)
        self.assertNotIn("錯誤:", output.split("圖庫狀態:")[1])

    def test_a_gallery_only_store_still_shows_the_gallery_section(self):
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
            image_size={"width": 1000, "height": 1000},
        )
        output = self.call(CmdArtStatus(), "")
        self.assertIn("圖庫狀態:", output)
        self.assertNotIn("沒有符合的美術資產記錄。", output)

    def test_both_surfaces_empty_keeps_the_empty_message(self):
        output = self.call(CmdArtStatus(), "")
        self.assertIn("沒有符合的美術資產記錄。", output)

    def test_the_broad_portrait_filter_lists_gallery_rows(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, _MONSTER_KEY)
        gallery_api.record_error(subject, "sd_connection_error")
        output = self.call(CmdArtStatus(), "portrait")
        self.assertIn(f"portrait:monster:{_MONSTER_KEY}", output)


@_ART_SCOPE
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

    def test_reachable_dashboard_shows_all_five_sections(self):
        enqueue_gallery_job(
            _scene(_SCENE_KEY),
            "desc",
            image_id="11111111-1111-4111-8111-111111111111",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        output, dispatch, _ = self._health(self._verdict())
        dispatch.assert_called_once()
        lines = output.splitlines()
        self.assertEqual(lines[0], "server: reachable (checked just now)")
        self.assertEqual(lines[1], "scheduler: enabled interval=30s limit=4")
        self.assertEqual(lines[2], "queue: pending=1 in_progress=0")
        self.assertEqual(lines[3], "gallery: records=0 cards=0 erroring=0")
        self.assertEqual(lines[4], "output: png q=80 metadata=on")

    def test_the_gallery_line_counts_records_cards_and_erroring_subjects(self):
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
            image_size={"width": 1000, "height": 1000},
        )
        gallery_api.record_error(one, "sd_connection_error")
        two = ArtSubject(ArtSubjectKind.CHARACTER, "43")
        gallery_api.record_error(two, "sd_timeout")
        output, _, _ = self._health(self._verdict())
        self.assertIn("gallery: records=2 cards=1 erroring=2", output)

    def test_a_claimed_job_is_reported_in_progress(self):
        enqueue_gallery_job(
            _scene(_SCENE_KEY),
            "desc",
            image_id="22222222-2222-4222-8222-222222222222",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        claim(1)
        output, _, _ = self._health(self._verdict())
        self.assertIn("queue: pending=0 in_progress=1", output)

    def test_unreachable_line_keeps_remaining_sections(self):
        output, _, probe = self._health(
            self._verdict(ok=False, code="sd_connection_error")
        )
        self.assertIn(
            "server: unreachable — sd_connection_error (checked just now)", output
        )
        self.assertIn("scheduler: ", output)
        self.assertIn("queue: pending=0 in_progress=0", output)
        self.assertIn("output: ", output)
        probe.assert_called_once_with(force=True)

    def test_health_mutates_nothing(self):
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
            image_size={"width": 1000, "height": 1000},
        )
        gallery_api.record_error(subject, "sd_timeout")
        gallery_before = [
            (s.subject.full(), s.card_count, s.has_default, s.error_code)
            for s in gallery_api.gallery_states()
        ]
        job = enqueue_gallery_job(
            _scene(_SCENE_KEY),
            "desc",
            image_id="33333333-3333-4333-8333-333333333333",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        before = [
            (r.db_key, r.db.status, r.db.attempt_count, r.db.gallery_image_id)
            for r in GalleryJobRecord.objects.all()
        ]
        self._health(self._verdict())
        after = [
            (r.db_key, r.db.status, r.db.attempt_count, r.db.gallery_image_id)
            for r in GalleryJobRecord.objects.all()
        ]
        self.assertEqual(before, after)
        gallery_after = [
            (s.subject.full(), s.card_count, s.has_default, s.error_code)
            for s in gallery_api.gallery_states()
        ]
        self.assertEqual(gallery_before, gallery_after)

    def test_output_leaks_no_credentials_userinfo_or_paths(self):
        with override_settings(
            ART_SD_USERNAME="operator",
            ART_SD_PASSWORD="sup3r-s3cret",
            ART_SD_BASE_URL="http://user:password@sd.internal:7860",
        ):
            output, _, _ = self._health(self._verdict())
        for forbidden in ("operator", "sup3r-s3cret", "user", "password", "@", "Basic ", "/app", "server/"):
            self.assertNotIn(forbidden, output)

    @covers_requirement("art-staff-commands::players-have-no-access-to-any-art-control")
    def test_non_staff_denied_without_any_probe(self):
        output, dispatch, probe = self._health(self._verdict(), caller=self.char2)
        self.assertIn("沒有權限", output)
        dispatch.assert_not_called()
        probe.assert_not_called()

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
