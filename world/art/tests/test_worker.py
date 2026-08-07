"""Tests for the internal sd-webui worker boundary and store-path confinement.

Every test is deterministic and socket-free: the client seam is injected as
``FakeSDWebUIClient`` (via the ``ART_SD_CLIENT`` setting and a patched
``resolve_sd_client``), replaying fixed PNG fixtures and scripted failures.
"""

from contextlib import contextmanager
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTest

from world.art.fake_sd_client import DEFAULT_PNG, FakeSDWebUIClient
from world.art.queue import (
    claim,
    ensure,
    record_key,
    reclaim_expired_leases,
    requeue,
    settle,
    settle_generated,
)
from world.art.sd_worker import SDError
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _lease_timeout,
    _run_and_settle_batch,
    _write_temp,
    drain,
    drain_synchronous,
    expected_output_identity,
)

from tools.spec_traceability import covers_requirement

class _MixedOutcomeClient:
    """A deterministic client whose outcome is scripted per description.

    ``None`` means a valid generation; any other value is raised verbatim, so
    tests can script named ``SDError``s and unexpected internal errors in one
    batch. Records every call like the fake client.
    """

    def __init__(self):
        self.calls: list[tuple[ArtSubject, str]] = []
        self.outcomes: dict[str, Exception | None] = {}

    def generate(self, subject: ArtSubject, description: str) -> bytes:
        self.calls.append((subject, description))
        error = self.outcomes.get(description)
        if error is not None:
            raise error
        return DEFAULT_PNG


class WorkerStoreIsolation(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        super().tearDown()

    @contextmanager
    def _client(self, client):
        """Run a drain block with ``client`` injected through the seam."""
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    def _subject(self, key="forest_path", kind=ArtSubjectKind.SCENE):
        return ArtSubject(kind, key)

    def _record(self, subject, description="desc"):
        return ensure(subject, description)

    def _record_for(self, subject):
        return ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()


class WorkerStoreIsolationTests(WorkerStoreIsolation):
    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
        "internal-art-worker::the-client-is-injectable-and-tests-never-open-a-socket",
    )
    def test_successful_generation_completes_a_scene_job(self):
        subject = self._subject()
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/forest_path.png")
        target = self.root / "scene" / "forest_path.png"
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_bytes(), DEFAULT_PNG)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_portrait_subject_writes_the_exact_portrait_identity(self):
        subject = self._subject("low", ArtSubjectKind.MONSTER)
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "portrait/monster/low.png")
        self.assertTrue((self.root / "portrait" / "monster" / "low.png").is_file())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_atomic_write_never_leaves_a_temporary_file_behind(self):
        subject = self._subject()
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        leftovers = [
            path for path in (self.root / "scene").iterdir() if path.name != "forest_path.png"
        ]
        self.assertEqual(leftovers, [])

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
    )
    def test_unreachable_server_settles_failed_and_keeps_the_placeholder(self):
        subject = self._subject()
        self._record(subject)
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(fake):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        from world.art.presenter import resolve_subject

        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "missing")
        self.assertIsNone(payload["url"])

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
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
            self._record(subject)
            fake = FakeSDWebUIClient()
            fake.fail_every_call(SDError(code, "scripted"))
            with self._client(fake):
                drain_synchronous(10)
            record = self._record_for(subject)
            with self.subTest(code=code):
                self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
                self.assertEqual(record.db.last_error_code, code)
                self.assertFalse((self.root / "scene" / f"{key}.png").exists())

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
    )
    def test_prompt_library_failure_settles_sd_prompt_error(self):
        from world.art.sd_worker import SDWebUIClient

        subject = self._subject()
        self._record(subject)
        from world.prompts.loader import PromptUnavailableError

        render_error = PromptUnavailableError("art.yaml", "art.scene_prompt", "broken")
        client = SDWebUIClient(transport=lambda request: {"images": ["cA=="]})
        with patch("world.art.sd_worker.render_prompt", side_effect=render_error):
            with self._client(client):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_prompt_error")

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
    )
    def test_unresolvable_client_settles_sd_client_config_error(self):
        subject = self._subject()
        self._record(subject)
        with override_settings(
            ART_SD_CLIENT="world.art.no_such_module.NoSuchClient"
        ):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_client_config_error")

    @covers_requirement(
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
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
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_internal_error")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_out_of_root_store_directory_is_rejected(self):
        subject = self._subject("mountain_path")
        self._record(subject)
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "scene").symlink_to(outside, target_is_directory=True)
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
            record = self._record_for(subject)
            self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
            self.assertEqual(record.db.last_error_code, "worker_output_out_of_root")
            self.assertFalse((Path(outside) / "mountain_path.png").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_atomic_write_removes_the_temp_file_when_publish_fails(self):
        subject = self._subject()
        self._record(subject)
        claimed = claim(10)
        target = self.root / "scene" / "forest_path.png"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"prior")
        tmp_path = _write_temp("scene/forest_path.png", DEFAULT_PNG)
        with patch("world.art.queue.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                settle_generated(
                    subject,
                    generation_token=claimed[0].db.generation_token,
                    output_identity="scene/forest_path.png",
                    tmp_path=tmp_path,
                )
        self.assertEqual(target.read_bytes(), b"prior")
        self.assertFalse(Path(tmp_path).exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_stale_claim_never_publishes_its_output_after_a_requeue(self):
        subject = self._subject("forest_path")
        self._record(subject)
        claimed = claim(10)
        # A staff requeue lands while the generation is still in flight.
        requeue(subject)
        target = self.root / "scene" / "forest_path.png"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"prior")
        tmp_path = _write_temp("scene/forest_path.png", DEFAULT_PNG)
        committed = settle_generated(
            subject,
            generation_token=claimed[0].db.generation_token,
            output_identity="scene/forest_path.png",
            tmp_path=tmp_path,
        )
        self.assertIsNone(committed)
        self.assertFalse(Path(tmp_path).exists())
        self.assertEqual(target.read_bytes(), b"prior")
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertFalse(record.db.output_identity)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_stale_claimed_record_is_skipped_by_the_batch_settler(self):
        subject = self._subject("tavern_interior")
        self._record(subject)
        claimed = claim(10)
        requeue(subject)
        with self._client(FakeSDWebUIClient()):
            settled = _run_and_settle_batch([claimed[0]])
        self.assertEqual(settled, [])
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertFalse((self.root / "scene" / "tavern_interior.png").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_failed_regeneration_never_corrupts_the_prior_output(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/dungeon_interior.png",
            error=None,
        )
        target = self.root / "scene" / "dungeon_interior.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"prior-image")
        requeue(subject)
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_timeout", "regeneration stalled"))
        with self._client(fake):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_timeout")
        self.assertEqual(record.db.prior_output_identity, "scene/dungeon_interior.png")
        self.assertEqual(target.read_bytes(), b"prior-image")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_slow_batch_is_not_reclaimed_before_n_times_timeout_plus_margin(self):
        with override_settings(ART_SD_TIMEOUT_SECONDS=1, ART_SCHEDULER_LIMIT=2):
            subjects = [self._subject("forest_path"), self._subject("tavern_interior")]
            for subject in subjects:
                self._record(subject)
            claimed = claim(2)
            self.assertEqual(len(claimed), 2)
            now = time.time()
            for record in claimed:
                record.db.claimed_at = now - (_lease_timeout() - 0.5)
                record.save()
            # A drain's reclaim uses the worst-case batch bound (2 x 1s + 5s
            # margin = 7s): 6.5s in is still inside the lease, so the batch is
            # not reclaimed and no generation is attempted.
            dispatched = drain_synchronous(10)
            self.assertEqual(dispatched, 0)
            for subject in subjects:
                record = self._record_for(subject)
                self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
            # A flat per-item bound (1s + 5s margin) would already have
            # reclaimed the batch, proving the sizing is worst-case not flat.
            self.assertEqual(reclaim_expired_leases(6.0), 2)

    @covers_requirement(
        "art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root",
        "internal-art-worker::art-generation-failures-degrade-to-bounded-named-error-codes",
    )
    def test_mixed_batch_settles_every_job_with_none_left_in_progress(self):
        client = _MixedOutcomeClient()
        client.outcomes["boom"] = SDError("sd_http_error", "scripted")
        client.outcomes["crash"] = RuntimeError("unexpected")
        subjects = [
            self._subject("forest_path"),
            self._subject("tavern_interior", ArtSubjectKind.MONSTER),
            self._subject("city_street"),
        ]
        for subject, description in zip(subjects, ("ok", "boom", "crash")):
            self._record(subject, description)
        with self._client(client):
            drain_synchronous(10)
        statuses = {}
        for subject in subjects:
            record = self._record_for(subject)
            statuses[subject.key] = (record.db.status, record.db.last_error_code)
        self.assertEqual(statuses["forest_path"], (ArtAssetStatus.DONE, None))
        self.assertEqual(
            statuses["tavern_interior"], (ArtAssetStatus.FAILED, "sd_http_error")
        )
        self.assertEqual(
            statuses["city_street"], (ArtAssetStatus.FAILED, "sd_internal_error")
        )
        in_progress = [
            record
            for record in ArtAssetRecord.objects.all()
            if record.db.status == ArtAssetStatus.IN_PROGRESS
        ]
        self.assertEqual(in_progress, [])

    @covers_requirement("art-queue-worker::scenes-and-portraits-share-one-serialization-lock-and-one-worker-concurrency-slot")
    def test_only_one_worker_runs_at_a_time(self):
        subject = self._subject("forest_path")
        self._record(subject)
        from world.art.worker import _try_acquire_worker_slot, _release_worker_slot

        self.assertTrue(_try_acquire_worker_slot())
        try:
            # A drain attempted while another worker is in flight claims nothing.
            with self._client(FakeSDWebUIClient()):
                self.assertEqual(drain_synchronous(10), 0)
        finally:
            _release_worker_slot()
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-queue-worker::scenes-and-portraits-share-one-serialization-lock-and-one-worker-concurrency-slot")
    def test_slot_is_released_after_a_synchronous_drain(self):
        subject = self._subject("tavern_interior")
        self._record(subject)
        from world.art.worker import _try_acquire_worker_slot, _release_worker_slot

        with self._client(FakeSDWebUIClient()):
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        self.assertTrue(_try_acquire_worker_slot())
        _release_worker_slot()

    @covers_requirement("internal-art-worker::the-internal-sd-webui-client-generates-images-through-txt2img-with-bounded-validation")
    def test_drain_dispatches_generation_through_the_background_thread_seam(self):
        subject = self._subject("forest_path")
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
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_expected_output_identity_is_exact_per_kind(self):
        self.assertEqual(
            expected_output_identity(ArtSubject(ArtSubjectKind.SCENE, "x")),
            "scene/x.png",
        )
        self.assertEqual(
            expected_output_identity(ArtSubject(ArtSubjectKind.MONSTER, "x")),
            "portrait/monster/x.png",
        )
        self.assertEqual(
            expected_output_identity(ArtSubject(ArtSubjectKind.CHARACTER, "x")),
            "portrait/character/x.png",
        )


if __name__ == "__main__":
    unittest.main()
