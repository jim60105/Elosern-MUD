"""Observability boundary events for the sd-webui worker (art deltas).

Asserts per-record ``sd_job_claim``/``sd_job_settled`` cardinality (no fake
settles for stale records, per-record reason codes on batch-config failure),
the claim-failure diagnostic, and the swallowed-code chain events. All
deterministic and socket-free through the injected client seam.
"""

from contextlib import contextmanager
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTest

from world.art.fake_cutout import FakeCutoutBackend
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.fake_translate import FakeTranslator
from world.art.queue import ensure, record_key, requeue
from evennia.utils.create import create_object
from typeclasses.characters import PlayerCharacter
from world.art.service import request_gallery_image

from tools.spec_traceability import covers_requirement
from world.art.sd_worker import SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.translate import TranslateError
import world.art.translate_ct2 as translate_ct2
from world.art.worker import drain_synchronous


# File-local synthetic scene identity: the queue treats a scene key as opaque
# identity (no registry validation on the worker path), so the event-cardinality
# mechanics under test never depend on shipped archetype keys.
_SCENE_KEY = "t_synth_scene"


def _subject(key=_SCENE_KEY):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _events(mock, name):
    return [
        call
        for call in mock.call_args_list
        if call.args and call.args[0] == name
    ]


class ArtWorkerObservabilityTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.tempdir.name)),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @covers_requirement('art-queue-worker::worker-claim-and-settle-emit-boundary-events')
    def test_success_emits_exactly_one_claim_and_settle_pair(self):
        subject = _subject()
        ensure(subject, "desc")
        with self._client(FakeSDWebUIClient()):
            with patch("world.art.worker.log_info") as info:
                drain_synchronous(10)
        claims = _events(info, "sd_job_claim")
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(claims), 1, claims)
        self.assertEqual(len(settles), 1, settles)
        claim_ctx = claims[0].kwargs["context"]
        settle_ctx = settles[0].kwargs["context"]
        self.assertEqual(claim_ctx["job"], record_key(subject))
        self.assertEqual(settle_ctx["job"], claim_ctx["job"])
        self.assertEqual(settle_ctx["subject"], subject.full())
        self.assertEqual(settle_ctx["status"], ArtAssetStatus.DONE)
        self.assertEqual(settle_ctx["reason"], "generated")

    def test_client_config_failure_settles_every_record_with_reason(self):
        subjects = [_subject(f"path_{n}") for n in range(3)]
        for subject in subjects:
            ensure(subject, "desc")
        with patch(
            "world.art.worker.resolve_sd_client",
            side_effect=ImportError("no module named nope"),
        ):
            with patch("world.art.worker.log_info") as info:
                with patch("world.art.worker.log_error") as error:
                    drain_synchronous(10)
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(settles), 3, settles)
        reasons = {call.kwargs["context"]["reason"] for call in settles}
        self.assertEqual(reasons, {"sd_client_config_error"})
        jobs = {call.kwargs["context"]["job"] for call in settles}
        self.assertEqual(jobs, {record_key(s) for s in subjects})
        config_events = _events(error, "sd_client_config_failed")
        self.assertEqual(len(config_events), 1, config_events)
        self.assertIn("endpoint", config_events[0].kwargs["context"])
        self.assertIsNotNone(config_events[0].kwargs["exc"])

    def test_stale_record_produces_no_fake_settle_event(self):
        subject = _subject()
        ensure(subject, "desc")
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(failing):
            # The record was reclaimed/requeued mid-flight: settle is a no-op.
            with patch("world.art.worker.settle", return_value=None):
                with patch("world.art.worker.log_info") as info:
                    drain_synchronous(10)
        self.assertEqual(len(_events(info, "sd_job_claim")), 1)
        self.assertEqual(_events(info, "sd_job_settled"), [])

    def test_claim_failure_events_slot_release_and_no_settles(self):
        with patch("world.art.worker.claim", side_effect=RuntimeError("db down")):
            with patch("world.art.worker.log_error") as error:
                with patch("world.art.worker.log_info") as info:
                    with self.assertRaises(RuntimeError):
                        drain_synchronous(10)
        claims = _events(error, "sd_job_claim_failed")
        self.assertEqual(len(claims), 1, claims)
        self.assertIsNotNone(claims[0].kwargs["exc"])
        self.assertEqual(_events(info, "sd_job_settled"), [])
        # The slot was released despite the failure: the next drain proceeds.
        with self._client(FakeSDWebUIClient()):
            self.assertEqual(drain_synchronous(10), 0)

    @covers_requirement('internal-art-worker::named-degradation-codes-carry-the-swallowed-exception-in-the-log')
    def test_internal_error_keeps_code_and_adds_chain_event(self):
        subject = _subject()
        ensure(subject, "desc")
        failing = FakeSDWebUIClient()
        failing.fail_every_call(RuntimeError("encoder exploded"))
        with self._client(failing):
            with patch("world.art.worker.log_warn") as warn:
                with patch("world.art.worker.log_info") as info:
                    drain_synchronous(10)
        events = _events(warn, "sd_generation_error")
        self.assertEqual(len(events), 1, events)
        context = events[0].kwargs["context"]
        self.assertEqual(context["code"], "sd_internal_error")
        self.assertIn("endpoint", context)
        self.assertIsNotNone(events[0].kwargs["exc"])
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(settles), 1, settles)
        self.assertEqual(settles[0].kwargs["context"]["reason"], "sd_internal_error")
        from world.art.store import ArtAssetRecord

        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.last_error_code, "sd_internal_error")
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)

    def test_publication_failure_still_reaches_terminal_settle(self):
        # A claimed record whose atomic publication raises must not escape
        # the batch loop: it settles FAILED with one sd_job_settled, and the
        # worker slot is released (rubber-duck P3 MAJOR).
        subject = _subject()
        ensure(subject, "desc")
        with self._client(FakeSDWebUIClient()):
            with patch(
                "world.art.worker.settle_generated",
                side_effect=OSError("filesystem went away"),
            ):
                with patch("world.art.worker.log_warn") as warn:
                    with patch("world.art.worker.log_info") as info:
                        drain_synchronous(10)
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(settles), 1, settles)
        self.assertEqual(settles[0].kwargs["context"]["status"], ArtAssetStatus.FAILED)
        self.assertEqual(settles[0].kwargs["context"]["reason"], "sd_internal_error")
        events = _events(warn, "sd_generation_error")
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["stage"], "publication")
        self.assertIsNotNone(events[0].kwargs["exc"])
        from world.art.store import ArtAssetRecord

        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        # The slot was released: a following drain proceeds normally.
        with self._client(FakeSDWebUIClient()):
            self.assertEqual(drain_synchronous(10), 0)


class GalleryBoundaryEventTests(EvenniaTest):
    """One generate/settle pair per requested image, carrying the business ids."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.tempdir.name)),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.player = create_object(PlayerCharacter, key="gallery-obs-player")
        self.player.age = 30
        self.player.apparent_age = 30
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.subject_full = f"portrait:character:{self.player.pk}"

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @covers_requirement("art-gallery-generation::gallery-generation-emits-its-boundary-events")
    def test_a_successful_request_logs_one_generate_and_one_done_settle(self):
        with patch("world.art.service.log_info") as service_info:
            image_id = request_gallery_image(self.player)
        generates = _events(service_info, "gallery_generate")
        self.assertEqual(len(generates), 1, generates)
        self.assertEqual(
            generates[0].kwargs["context"],
            {"subject": self.subject_full, "image_id": image_id, "kind": "portrait:character"},
        )
        with self._client(FakeSDWebUIClient()):
            with patch("world.art.worker.log_info") as info:
                drain_synchronous(10)
        settles = _events(info, "gallery_settle")
        self.assertEqual(len(settles), 1, settles)
        self.assertEqual(
            settles[0].kwargs["context"],
            {
                "subject": self.subject_full,
                "image_id": image_id,
                "kind": "portrait:character",
                "status": ArtAssetStatus.DONE,
                "reason": "generated",
            },
        )

    @covers_requirement("art-gallery-generation::gallery-generation-emits-its-boundary-events")
    def test_a_failed_settle_reports_the_bounded_reason(self):
        with patch("world.art.service.log_info"):
            image_id = request_gallery_image(self.player)
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_timeout", "scripted"))
        with self._client(failing):
            with patch("world.art.worker.log_info") as info:
                drain_synchronous(10)
        settles = _events(info, "gallery_settle")
        self.assertEqual(len(settles), 1, settles)
        context = settles[0].kwargs["context"]
        self.assertEqual(context["status"], ArtAssetStatus.FAILED)
        self.assertEqual(context["reason"], "sd_timeout")
        self.assertEqual(context["image_id"], image_id)
        self.assertEqual(context["subject"], self.subject_full)
        self.assertEqual(context["kind"], "portrait:character")


class CutoutEventTests(EvenniaTest):
    """Stage-vs-job event cardinality for the background-removal stage.

    Design D12: exactly one ``art_cutout_*`` event per stage outcome plus the
    existing job events, never a merged job-level event. Patches the caller
    module's binding (``world.art.worker``), never ``world.observability.*``.
    """

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.tempdir.name)),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @contextmanager
    def _cutout(self, fake):
        with override_settings(
            ART_REMBG_ENABLED=True,
            ART_REMBG_BACKEND="world.art.fake_cutout.FakeCutoutBackend",
        ):
            with patch("world.art.fake_cutout.FakeCutoutBackend", return_value=fake):
                yield

    def _opaque_client(self):
        from world.art.tests.test_worker._support import _OpaqueClient

        return _OpaqueClient()

    @covers_requirement("art-queue-worker::worker-claim-and-settle-emit-boundary-events")
    @covers_requirement("art-portrait-cutout::the-background-removal-stage-emits-boundary-events")
    def test_a_successful_cutout_emits_exactly_one_stage_event(self):
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        ensure(subject, "desc")
        with self._cutout(FakeCutoutBackend()):
            with self._client(self._opaque_client()):
                with patch("world.art.worker.log_info") as info:
                    drain_synchronous(10)
        done = _events(info, "art_cutout_done")
        self.assertEqual(len(done), 1)
        context = done[0].kwargs["context"]
        self.assertEqual(context["job"], record_key(subject))
        self.assertEqual(context["subject"], subject.full())
        self.assertEqual(context["image_id"], "")
        self.assertEqual(context["model"], "bria-rmbg")
        self.assertIsInstance(context["duration_ms"], int)
        self.assertEqual(_events(info, "art_cutout_failed"), [])

    @covers_requirement("art-queue-worker::worker-claim-and-settle-emit-boundary-events")
    @covers_requirement("art-portrait-cutout::the-background-removal-stage-emits-boundary-events")
    def test_a_failed_cutout_emits_one_stage_event_and_the_job_pair(self):
        from world.art.cutout import CutoutError

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        ensure(subject, "desc")
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_unavailable", "model missing"))
        with self._cutout(fake):
            with self._client(self._opaque_client()):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        failed = _events(warn, "art_cutout_failed")
        self.assertEqual(len(failed), 1)
        context = failed[0].kwargs["context"]
        self.assertEqual(context["job"], record_key(subject))
        self.assertEqual(context["subject"], subject.full())
        self.assertEqual(context["image_id"], "")
        self.assertEqual(context["model"], "bria-rmbg")
        self.assertEqual(context["code"], "art_cutout_unavailable")
        self.assertIsNotNone(failed[0].kwargs["exc"])
        # The existing job events still fire, exactly once, with the same code.
        generation_errors = _events(warn, "sd_generation_error")
        self.assertEqual(len(generation_errors), 1)
        self.assertEqual(
            generation_errors[0].kwargs["context"]["code"], "art_cutout_unavailable"
        )
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(settles), 1)
        self.assertEqual(settles[0].kwargs["context"]["reason"], "art_cutout_unavailable")
        self.assertEqual(_events(info, "art_cutout_done"), [])

    @covers_requirement("art-queue-worker::worker-claim-and-settle-emit-boundary-events")
    @covers_requirement("art-portrait-cutout::the-background-removal-stage-emits-boundary-events")
    def test_a_failing_gallery_cutout_emits_the_gallery_terminal_event(self):
        from world.art.cutout import CutoutError
        from world.art.queue import enqueue_gallery_job

        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        image_id = "aaaaaaaa-1111-4111-8111-111111111111"
        job = enqueue_gallery_job(
            subject,
            "desc",
            image_id=image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        fake = FakeCutoutBackend()
        fake.fail_every_call(CutoutError("art_cutout_error", "scripted"))
        with self._cutout(fake):
            with self._client(self._opaque_client()):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        failed = _events(warn, "art_cutout_failed")
        self.assertEqual(len(failed), 1)
        # The spent job record is deleted by the settle, so the event context
        # is compared against the REQUESTED image id captured before the drain.
        self.assertEqual(failed[0].kwargs["context"]["image_id"], image_id)
        self.assertEqual(failed[0].kwargs["context"]["code"], "art_cutout_error")
        gallery_settles = _events(info, "gallery_settle")
        self.assertEqual(len(gallery_settles), 1)
        self.assertEqual(
            gallery_settles[0].kwargs["context"]["status"], ArtAssetStatus.FAILED
        )
        # The batch settler's job-level settle event also fires for the spent
        # gallery job record (existing behavior, shared with the config-failure
        # path): exactly one, with the same bounded code.
        job_settles = _events(info, "sd_job_settled")
        self.assertEqual(len(job_settles), 1)
        self.assertEqual(job_settles[0].kwargs["context"]["reason"], "art_cutout_error")

    @covers_requirement("art-portrait-cutout::the-background-removal-stage-emits-boundary-events")
    def test_no_cutout_event_for_a_skipped_or_disabled_run(self):
        scene = ArtSubject(ArtSubjectKind.SCENE, _SCENE_KEY)
        ensure(scene, "desc")
        # Enabled stage, scene subject only: skipped, no cutout event.
        with self._cutout(FakeCutoutBackend()):
            with self._client(self._opaque_client()):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        self.assertEqual(_events(info, "art_cutout_done"), [])
        self.assertEqual(_events(warn, "art_cutout_failed"), [])
        # Fully disabled stage: no event for any kind, backend never built.
        character = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        ensure(character, "desc")
        requeue(scene)
        with patch("world.art.fake_cutout.FakeCutoutBackend") as backend_cls:
            with self._client(self._opaque_client()):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        self.assertEqual(_events(info, "art_cutout_done"), [])
        self.assertEqual(_events(warn, "art_cutout_failed"), [])
        self.assertEqual(backend_cls.call_count, 0)


class TranslationEventTests(EvenniaTest):
    """Stage event cardinality is independent of the art subject kind."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(Path(self.tempdir.name)),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        # The translation download latch is process-global; a worker test
        # that trips it must not leak into later tests, and no engine built
        # for a previous directory may be reused.
        self.addCleanup(self._reset_translate_module_state)

    def _reset_translate_module_state(self):
        translate_ct2._DOWNLOAD_LATCHED = False
        translate_ct2._ENGINES.clear()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @contextmanager
    def _translator(self, fake):
        with override_settings(
            ART_TRANSLATE_ENABLED=True,
            ART_TRANSLATE_BACKEND="world.art.fake_translate.FakeTranslator",
        ):
            with patch(
                "world.art.fake_translate.FakeTranslator", return_value=fake
            ):
                yield

    @covers_requirement(
        "art-prompt-translation::the-stage-emits-exactly-one-boundary-event-per-non-skipped-outcome"
    )
    def test_success_emits_one_done_event_with_the_exact_context_schema(self):
        subject = _subject("t_synth_translate_done")
        ensure(subject, "第一行漢字\nLatin")
        with self._translator(FakeTranslator()):
            with self._client(FakeSDWebUIClient()):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        done = _events(info, "art_translate_done")
        self.assertEqual(len(done), 1)
        self.assertEqual(_events(warn, "art_translate_failed"), [])
        self.assertEqual(
            set(done[0].kwargs["context"]),
            {
                "job",
                "subject",
                "image_id",
                "lines_total",
                "lines_offered",
                "lines_untranslated",
                "duration_ms",
            },
        )
        context = done[0].kwargs["context"]
        self.assertEqual(context["job"], record_key(subject))
        self.assertEqual(context["subject"], subject.full())
        self.assertEqual(context["image_id"], "")
        self.assertEqual(
            (context["lines_total"], context["lines_offered"], context["lines_untranslated"]),
            (2, 1, 0),
        )
        self.assertIsInstance(context["duration_ms"], int)
        self.assertNotIn("exc", done[0].kwargs)

    @covers_requirement(
        "art-prompt-translation::the-stage-emits-exactly-one-boundary-event-per-non-skipped-outcome"
    )
    @covers_requirement(
        "art-prompt-translation::translation-failure-degrades-the-prompt-and-never-costs-the-image"
    )
    def test_forward_default_failure_emits_one_bounded_event_and_still_settles(self):
        # Forward default with no backend override: the shipped
        # CTranslate2Backend resolves, but the model directory is unseeded, so
        # the layout check raises art_translate_unavailable. The run is
        # air-gapped by settings — the explicit DOWNLOAD_ENABLED=False here is
        # belt-and-braces beside the test-settings pin (task 3.4), so the test
        # neither populates server/.translate nor trips the module download
        # latch. The stage boundary maps every failure inside a backend call
        # to art_translate_error (the seam's own contract), the worker emits
        # one bounded event, and the record still settles with the authored
        # prompt.
        subject = _subject("t_synth_translate_forward_default")
        description = "模型尚未種子"
        ensure(subject, description)
        client = FakeSDWebUIClient()
        with override_settings(
            ART_TRANSLATE_ENABLED=True,
            ART_TRANSLATE_DOWNLOAD_ENABLED=False,
        ):
            with self._client(client):
                with patch("world.art.worker.log_info") as info:
                    with patch("world.art.worker.log_warn") as warn:
                        drain_synchronous(10)
        failed = _events(warn, "art_translate_failed")
        self.assertEqual(len(failed), 1)
        self.assertEqual(_events(info, "art_translate_done"), [])
        self.assertEqual(
            set(failed[0].kwargs["context"]),
            {"job", "subject", "image_id", "code"},
        )
        self.assertEqual(
            failed[0].kwargs["context"],
            {
                "job": record_key(subject),
                "subject": subject.full(),
                "image_id": "",
                "code": "art_translate_error",
            },
        )
        self.assertIsInstance(failed[0].kwargs["exc"], TranslateError)
        self.assertEqual(failed[0].kwargs["exc"].code, "art_translate_error")
        cause = failed[0].kwargs["exc"].__cause__
        self.assertIsInstance(cause, TranslateError)
        self.assertEqual(cause.code, "art_translate_unavailable")
        self.assertEqual(client.calls, [(subject, description)])
        self.assertFalse(translate_ct2._DOWNLOAD_LATCHED)

    @covers_requirement(
        "art-prompt-translation::translation-failure-degrades-the-prompt-and-never-costs-the-image"
    )
    def test_download_failure_degrades_the_prompt_and_never_costs_the_image(self):
        # The download track end to end through the worker: a fetch failure is
        # observed as the normal one art_translate_failed warn (never a crash,
        # never a settled failure), the backend's own download-failed warn has
        # fired exactly once, and the record settles done with the authored
        # prompt while the image is still produced.
        subject = _subject("t_synth_translate_download_failure")
        description = "模型下載失敗"
        ensure(subject, description)
        client = FakeSDWebUIClient()
        with override_settings(
            ART_TRANSLATE_ENABLED=True,
            ART_TRANSLATE_DOWNLOAD_ENABLED=True,
            ART_TRANSLATE_MODEL_DIR=str(Path(self.tempdir.name)),
        ):
            with patch(
                "world.art.translate_ct2.urlopen",
                side_effect=OSError("connection refused"),
            ):
                with self._client(client):
                    with patch("world.art.worker.log_info") as info:
                        with patch("world.art.worker.log_warn") as warn:
                            with patch(
                                "world.art.translate_ct2.log_warn"
                            ) as backend_warn:
                                drain_synchronous(10)
        failed = _events(warn, "art_translate_failed")
        self.assertEqual(len(failed), 1)
        self.assertEqual(_events(info, "art_translate_done"), [])
        self.assertEqual(
            failed[0].kwargs["context"]["code"], "art_translate_error"
        )
        self.assertEqual(client.calls, [(subject, description)])
        download_failed = _events(backend_warn, "art_translate_model_download_failed")
        self.assertEqual(len(download_failed), 1)
        self.assertEqual(
            download_failed[0].kwargs["context"]["url"],
            translate_ct2._MODEL_URL,
        )
        # The record settles DONE with the untranslated description (task
        # 2.4's "the job still settles done on the untranslated description").
        record = ArtAssetRecord.objects.filter(
            db_key=record_key(subject)
        ).first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        settles = _events(info, "sd_job_settled")
        self.assertEqual(len(settles), 1)
        self.assertEqual(
            settles[0].kwargs["context"]["status"], ArtAssetStatus.DONE
        )

    @covers_requirement(
        "art-prompt-translation::the-stage-emits-exactly-one-boundary-event-per-non-skipped-outcome"
    )
    def test_unknown_translator_code_is_normalized_before_the_failure_event(self):
        subject = _subject("t_synth_translate_unknown_code")
        description = "未知錯誤碼"
        ensure(subject, description)
        translator = FakeTranslator()
        translator.fail_every_call(TranslateError("unexpected", "scripted"))
        client = FakeSDWebUIClient()
        with self._translator(translator):
            with self._client(client):
                with patch("world.art.worker.log_warn") as warn:
                    drain_synchronous(10)
        failed = _events(warn, "art_translate_failed")
        self.assertEqual(len(failed), 1)
        self.assertEqual(
            failed[0].kwargs["context"]["code"], "art_translate_error"
        )
        self.assertEqual(client.calls, [(subject, description)])

    @covers_requirement(
        "art-prompt-translation::the-stage-emits-exactly-one-boundary-event-per-non-skipped-outcome"
    )
    @covers_requirement(
        "art-prompt-translation::a-per-line-language-gate-skips-text-that-needs-no-translation"
    )
    def test_disabled_and_all_latin_runs_are_silent_and_unresolved(self):
        disabled = _subject("t_synth_translate_disabled")
        latin = _subject("t_synth_translate_latin")
        ensure(disabled, "關閉時不翻譯")
        with patch(
            "world.art.translate.resolve_translate_backend",
            side_effect=AssertionError("skipped stages must not resolve"),
        ) as resolver:
            with self._client(FakeSDWebUIClient()):
                with patch("world.art.worker.log_info") as disabled_info:
                    with patch("world.art.worker.log_warn") as disabled_warn:
                        drain_synchronous(10)
            ensure(latin, "English prompt tags")
            with override_settings(ART_TRANSLATE_ENABLED=True):
                with self._client(FakeSDWebUIClient()):
                    with patch("world.art.worker.log_info") as latin_info:
                        with patch("world.art.worker.log_warn") as latin_warn:
                            drain_synchronous(10)
        self.assertEqual(resolver.call_count, 0)
        self.assertEqual(_events(disabled_info, "art_translate_done"), [])
        self.assertEqual(_events(disabled_warn, "art_translate_failed"), [])
        self.assertEqual(_events(latin_info, "art_translate_done"), [])
        self.assertEqual(_events(latin_warn, "art_translate_failed"), [])


if __name__ == "__main__":
    import unittest

    unittest.main()
