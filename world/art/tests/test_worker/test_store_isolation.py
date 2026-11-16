"""Slice of ``test_worker``: WorkerStoreIsolationTests.
"""
import base64
from contextlib import contextmanager
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from django.test import override_settings

from PIL import Image
from evennia.utils.test_resources import EvenniaTest

from world.art.fake_sd_client import DEFAULT_PNG, FakeSDWebUIClient
from world.art.fake_cutout import FakeCutoutBackend
from world.art.cutout import CutoutError
from world.art import gallery as gallery_api
from world.art.gallery import DEFAULT_FACE_RECT
from world.art.queue import (
    claim,
    enqueue_gallery_job,
    gallery_record_key,
    reclaim_expired_leases,
    settle_gallery_generated,
)
from world.art.sd_worker import GeneratedImage, SDError, SDWebUIClient
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _lease_timeout,
    _run_and_settle_batch,
    _write_temp,
    drain,
    drain_synchronous,
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

from ._support import (
    WorkerStoreIsolation,
    _SYNTH_MONSTER,
    _MixedOutcomeClient,
)


class WorkerStoreIsolationTests(WorkerStoreIsolation):
    def _image_id_for(self, subject, image_id):
        return self.root / (
            f"gallery/{subject.kind.value.split(':')[-1]}/{subject.key}/{image_id}.png"
        )

    @covers_requirement(
        "internal-art-worker::the-client-is-injectable-and-tests-never-open-a-socket",
    )
    def test_successful_generation_completes_a_scene_job(self):
        subject = self._subject()
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        with self._client(FakeSDWebUIClient()):
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(
            cards[0]["stored_identity"],
            f"gallery/scene/t_synth_forest/{image_id}.png",
        )
        target = self.root / cards[0]["stored_identity"]
        self.assertTrue(target.is_file())
        # The png path re-encodes through the local converter: the container
        # bytes may differ, the decoded pixels must not.
        with Image.open(io.BytesIO(DEFAULT_PNG)) as before_img, Image.open(target) as after_img:
            before = before_img.convert("RGBA")
            after = after_img.convert("RGBA")
        self.assertEqual(list(before.getdata()), list(after.getdata()))
        self.assertIsNone(self._job_for(job))

    @covers_requirement(
        "internal-art-worker::server-side-generated-image-retention-is-request-scoped-and-configurable"
    )
    def test_successful_generation_with_disabled_retention_persists_normally(self):
        subject = self._subject()
        self._record(subject)
        captured = {}
        def transport(request):
            captured["request"] = request
            return {"images": [base64.b64encode(DEFAULT_PNG).decode("ascii")]}
        with override_settings(ART_SD_SERVER_RETAIN_IMAGES=False):
            with self._client(SDWebUIClient(transport=transport)):
                dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        self.assertIs(captured["request"]["save_images"], False)
        self.assertIs(captured["request"]["do_not_save_samples"], True)
        self.assertIs(captured["request"]["do_not_save_grid"], True)
        self.assertEqual(len(gallery_api.cards_for(subject)), 1)

    def test_portrait_subject_writes_the_exact_gallery_identity(self):
        subject = self._subject(_SYNTH_MONSTER, ArtSubjectKind.MONSTER)
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(
            cards[0]["stored_identity"],
            f"gallery/monster/{_SYNTH_MONSTER}/{image_id}.png",
        )
        self.assertTrue((self.root / cards[0]["stored_identity"]).is_file())

    def test_atomic_write_never_leaves_a_temporary_file_behind(self):
        subject = self._subject()
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        directory = self.root / "gallery" / "scene" / "t_synth_forest"
        leftovers = [path for path in directory.iterdir() if path.name != f"{image_id}.png"]
        self.assertEqual(leftovers, [])

    def test_server_reported_seed_is_persisted_on_publish(self):
        subject = self._subject()
        self._record(subject)
        fake = FakeSDWebUIClient()
        fake.seed = 42
        with self._client(fake):
            drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["seed"], 42)

    def test_seedless_regeneration_stores_a_new_seedless_card(self):
        # A seedless regeneration must never keep advertising the old image's
        # seed: the new card carries the new (absent) seed.
        subject = self._subject()
        self._record(subject)
        seeded = FakeSDWebUIClient()
        seeded.seed = 42
        with self._client(seeded):
            drain_synchronous(10)
        self.assertEqual(gallery_api.cards_for(subject)[0]["seed"], 42)
        self._record(subject, "second")
        seedless = FakeSDWebUIClient()
        seedless.seed = None
        with self._client(seedless):
            drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertIsNone(cards[0]["seed"])

    def test_failed_regeneration_retains_prior_card_and_seed(self):
        subject = self._subject()
        self._record(subject)
        seeded = FakeSDWebUIClient()
        seeded.seed = 7
        with self._client(seeded):
            drain_synchronous(10)
        prior = gallery_api.cards_for(subject)
        self.assertEqual(len(prior), 1)
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        self._record(subject, "failing")
        with self._client(failing):
            drain_synchronous(10)
        self.assertEqual(gallery_api.cards_for(subject), prior)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_connection_error"],
        )

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_unreachable_server_settles_failed_and_keeps_the_placeholder(self):
        subject = self._subject()
        self._record(subject)
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(fake):
            drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_connection_error"],
        )
        from world.art import descriptors
        from world.art.presenter import describe_scene
        from world.art import subjects as art_subjects
        from world.rules.art_view import SceneTarget

        with patch.object(
            art_subjects,
            "SCENE_ARCHETYPE_REGISTRY",
            {subject.key: None},
        ):
            descriptor = describe_scene(
                SceneTarget(
                    identity="place:t_synth_store_isolation",
                    trusted_identity=True,
                    archetype=subject.key,
                    room_art_key=None,
                    room_binding_invalid=False,
                )
            )
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        generated = [
            attempt
            for attempt in descriptor["attempts"]
            if attempt["rank"] == descriptors.SCENE_RANK_GENERATED
        ]
        self.assertEqual(
            [attempt["reason"] for attempt in generated],
            [descriptors.REASON_GENERATION_FAILED],
        )

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_every_named_sd_error_settles_its_bounded_code(self):
        codes = (
            "sd_connection_error",
            "sd_timeout",
            "sd_http_error",
            "sd_malformed_response",
            "sd_no_image",
            "sd_decode_error",
            "sd_not_png",
            "sd_response_too_large",
            "sd_image_dimensions_too_large",
        )
        for index, code in enumerate(codes):
            key = f"subject_{index}"
            subject = self._subject(key)
            job = self._record(subject)
            fake = FakeSDWebUIClient()
            fake.fail_every_call(SDError(code, "scripted"))
            with self._client(fake):
                drain_synchronous(10)
            with self.subTest(code=code):
                states = {
                    state.subject.full(): state.error_code
                    for state in gallery_api.erroring_subjects()
                }
                self.assertEqual(
                    states.get(subject.full()),
                    code,
                )
                self.assertEqual(gallery_api.cards_for(subject), [])
                self.assertIsNone(self._job_for(job))

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_prompt_library_failure_settles_sd_prompt_error(self):
        subject = self._subject()
        self._record(subject)
        from world.prompts.loader import PromptUnavailableError

        render_error = PromptUnavailableError("art.yaml", "art.scene_prompt", "broken")
        client = SDWebUIClient(transport=lambda request: {"images": ["cA=="]})
        with patch("world.art.sd_worker.render_prompt", side_effect=render_error):
            with self._client(client):
                drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_prompt_error"],
        )

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_unresolvable_client_settles_sd_client_config_error(self):
        subject = self._subject()
        self._record(subject)
        with override_settings(
            ART_SD_CLIENT="world.art.no_such_module.NoSuchClient"
        ):
            drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_client_config_error"],
        )

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_unexpected_internal_error_settles_sd_internal_error(self):
        subject = self._subject()
        self._record(subject)
        fake = FakeSDWebUIClient()
        fake.add_failure(
            lambda subj, desc: True, RuntimeError("unexpected client bug")
        )
        with self._client(fake):
            drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_internal_error"],
        )

    @covers_requirement(
        "art-queue-worker::gallery-workers-publish-confined-immutable-image-outputs"
    )
    def test_out_of_root_store_directory_is_rejected(self):
        subject = self._subject("t_synth_mountain")
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "gallery").mkdir(exist_ok=True)
            (self.root / "gallery" / "scene").symlink_to(outside, target_is_directory=True)
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
            self.assertEqual(
                [state.error_code for state in gallery_api.erroring_subjects()],
                ["worker_output_out_of_root"],
            )
            self.assertFalse((Path(outside) / image_id).exists())
        self.assertEqual(gallery_api.cards_for(subject), [])

    def test_atomic_write_removes_the_temp_file_when_publish_fails(self):
        subject = self._subject()
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        identity = output_identity_for(job)
        claimed = claim(10)
        tmp_path = _write_temp(identity, DEFAULT_PNG)
        with patch("world.art.queue.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                settle_gallery_generated(
                    claimed[0].db_key,
                    generation_token=claimed[0].db.generation_token,
                    output_identity=identity,
                    tmp_path=tmp_path,
                    prompt={"positive": "p", "negative": "n"},
                    seed=None,
                    checkpoint=None,
                )
        self.assertFalse(Path(tmp_path).exists())
        self.assertEqual(gallery_api.cards_for(subject), [])
        self.assertTrue(
            (self.root / "gallery" / "scene" / subject.key).is_dir()
        )

    def test_stale_claim_never_publishes_its_output_after_reclaim(self):
        subject = self._subject("t_synth_forest")
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        identity = output_identity_for(job)
        claimed = claim(10)
        # A lease reclaim lands while the generation is still in flight.
        reclaim_expired_leases(0.0)
        tmp_path = _write_temp(identity, DEFAULT_PNG)
        committed = settle_gallery_generated(
            claimed[0].db_key,
            generation_token=claimed[0].db.generation_token,
            output_identity=identity,
            tmp_path=tmp_path,
            prompt={"positive": "p", "negative": "n"},
            seed=None,
            checkpoint=None,
        )
        self.assertIsNone(committed)
        self.assertFalse(Path(tmp_path).exists())
        self.assertEqual(gallery_api.cards_for(subject), [])
        current = self._job_for(job)
        self.assertEqual(current.db.status, ArtAssetStatus.PENDING)
        self.assertFalse(
            self._image_id_for(subject, image_id).exists()
        )

    def test_stale_claimed_job_is_skipped_by_the_batch_settler(self):
        subject = self._subject("t_synth_tavern")
        job = self._record(subject)
        claimed = claim(10)
        reclaim_expired_leases(0.0)
        with self._client(FakeSDWebUIClient()):
            settled = _run_and_settle_batch(
                [
                    (
                        claimed[0],
                        subject,
                        str(claimed[0].db.generation_token),
                        str(claimed[0].db_key),
                    )
                ]
            )
        self.assertEqual(settled, [])
        self.assertEqual(self._job_for(job).db.status, ArtAssetStatus.PENDING)
        self.assertEqual(gallery_api.cards_for(subject), [])

    def test_failed_regeneration_never_corrupts_the_prior_card(self):
        subject = self._subject("t_synth_dungeon")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        prior = gallery_api.cards_for(subject)
        prior_bytes = (self.root / prior[0]["stored_identity"]).read_bytes()
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_timeout", "regeneration stalled"))
        self._record(subject, "failing")
        with self._client(fake):
            drain_synchronous(10)
        self.assertEqual(gallery_api.cards_for(subject), prior)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_timeout"],
        )
        self.assertEqual((self.root / prior[0]["stored_identity"]).read_bytes(), prior_bytes)

    def test_slow_batch_is_not_reclaimed_before_n_times_timeout_plus_margin(self):
        with override_settings(ART_SD_TIMEOUT_SECONDS=1, ART_SCHEDULER_LIMIT=2):
            subjects = [self._subject("t_synth_forest"), self._subject("t_synth_tavern")]
            jobs = [self._record(subject) for subject in subjects]
            claimed = claim(2)
            self.assertEqual(len(claimed), 2)
            now = time.time()
            for job in claimed:
                job.db.claimed_at = now - (_lease_timeout() - 0.5)
                job.save()
            # A drain's reclaim uses the worst-case batch bound
            # (2 x (timeout + 60s conversion allowance) + 5s margin): a moment
            # inside the lease keeps the batch unreclaimed, so no generation
            # is attempted.
            dispatched = drain_synchronous(10)
            self.assertEqual(dispatched, 0)
            for job in jobs:
                self.assertEqual(self._job_for(job).db.status, ArtAssetStatus.IN_PROGRESS)
            # A flat per-item bound (timeout + margin) would already have
            # reclaimed the batch, proving the sizing is worst-case not flat.
            self.assertEqual(reclaim_expired_leases(6.0), 2)

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_mixed_batch_settles_every_job_with_none_left_in_progress(self):
        client = _MixedOutcomeClient()
        client.outcomes["boom"] = SDError("sd_http_error", "scripted")
        client.outcomes["crash"] = RuntimeError("unexpected")
        subjects = [
            self._subject("t_synth_forest"),
            self._subject(_SYNTH_MONSTER, ArtSubjectKind.MONSTER),
            self._subject("t_synth_city"),
        ]
        jobs = [
            self._record(subject, description)
            for subject, description in zip(subjects, ("ok", "boom", "crash"))
        ]
        with self._client(client):
            drain_synchronous(10)
        self.assertEqual(len(gallery_api.cards_for(subjects[0])), 1)
        self.assertEqual(gallery_api.cards_for(subjects[1]), [])
        self.assertEqual(gallery_api.cards_for(subjects[2]), [])
        errors = {state.subject.full(): state.error_code for state in gallery_api.erroring_subjects()}
        self.assertEqual(errors.get(subjects[1].full()), "sd_http_error")
        self.assertEqual(errors.get(subjects[2].full()), "sd_internal_error")
        self.assertEqual(
            [
                job
                for job in GalleryJobRecord.objects.all()
                if job.db.status == ArtAssetStatus.IN_PROGRESS
            ],
            [],
        )
        for job in jobs:
            self.assertIsNone(self._job_for(job))

    @covers_requirement("art-queue-worker::gallery-jobs-share-one-lock-and-worker-slot")
    def test_only_one_worker_runs_at_a_time(self):
        subject = self._subject("t_synth_forest")
        job = self._record(subject)
        from world.art.worker import _try_acquire_worker_slot, _release_worker_slot

        self.assertTrue(_try_acquire_worker_slot())
        try:
            # A drain attempted while another worker is in flight claims nothing.
            with self._client(FakeSDWebUIClient()):
                self.assertEqual(drain_synchronous(10), 0)
        finally:
            _release_worker_slot()
        self.assertEqual(self._job_for(job).db.status, ArtAssetStatus.PENDING)

    def test_slot_is_released_after_a_synchronous_drain(self):
        subject = self._subject("t_synth_tavern")
        self._record(subject)
        from world.art.worker import _try_acquire_worker_slot, _release_worker_slot

        with self._client(FakeSDWebUIClient()):
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        self.assertTrue(_try_acquire_worker_slot())
        _release_worker_slot()

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_drain_dispatches_generation_through_the_background_thread_seam(self):
        subject = self._subject("t_synth_forest")
        self._record(subject)
        from twisted.internet import defer

        dispatched_to_thread = []

        def _sync_defer_to_thread(fn, *args):
            dispatched_to_thread.append(fn.__name__)
            deferred = defer.Deferred()
            deferred.callback(fn(*args))
            return deferred

        with patch(
            "world.art.worker.threads.deferToThread", side_effect=_sync_defer_to_thread
        ):
            with self._client(FakeSDWebUIClient()):
                dispatched = drain(10)
        self.assertEqual(dispatched, 1)
        self.assertEqual(dispatched_to_thread, ["_run_and_release_slot"])
        self.assertEqual(len(gallery_api.cards_for(subject)), 1)

    def test_output_identity_is_exact_per_kind(self):
        for subject, directory in (
            (ArtSubject(ArtSubjectKind.SCENE, "x"), "scene"),
            (ArtSubject(ArtSubjectKind.MONSTER, _SYNTH_MONSTER), "monster"),
            (ArtSubject(ArtSubjectKind.CHARACTER, "x"), "character"),
        ):
            job = enqueue_gallery_job(
                subject,
                "desc",
                image_id="aaaaaaaa-1111-4111-8111-111111111111",
                binding=None,
                face_rect=None,
                requested_fields=[],
            )
            self.assertEqual(
                output_identity_for(job),
                f"gallery/{directory}/{subject.key}/aaaaaaaa-1111-4111-8111-111111111111.png",
            )
            job.delete()
