"""Tests for the external worker boundary and store-path confinement."""

from contextlib import ExitStack, contextmanager
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from django.test import override_settings

from evennia.utils.test_resources import EvenniaTest

from world.art.queue import ensure, record_key
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    WorkerProtocolError,
    _run_and_settle_batch,
    _valid_result,
    drain_synchronous,
    expected_output_identity,
)

from tools.spec_traceability import covers_requirement


FIXTURE_CMD = [
    "python",
    str(Path(__file__).parent / "fixtures" / "fixture_worker.py"),
]


class WorkerStoreIsolation(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.tempdir.cleanup()
        super().tearDown()

    def _cmd(self, env_overrides=None, settings_overrides=None):
        """Return a context that points the worker at the fixture."""
        env = {
            "ART_FIXTURE_STORE_ROOT": str(self.root),
        }
        env.update(env_overrides or {})
        settings = {
            "ART_WORKER_CMD": FIXTURE_CMD,
            "ART_STORE_ROOT": str(self.root),
        }
        settings.update(settings_overrides or {})

        @contextmanager
        def _combined():
            with ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, env))
                stack.enter_context(override_settings(**settings))
                yield

        return _combined()

    def _subject(self, key="forest_path"):
        return ArtSubject(ArtSubjectKind.SCENE, key)

    def _record(self, subject, description="desc"):
        return ensure(subject, description)


class WorkerValidationTests(unittest.TestCase):
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

    def test_result_requires_matching_key(self):
        job = {"kind": "scene", "key": "scene:a", "out_path": "scene/a.png"}
        status, identity, error = _valid_result(job, {
            "key": "scene:b", "status": "success",
            "output_identity": "scene/a.png",
        })
        self.assertEqual(status, ArtAssetStatus.FAILED)
        self.assertEqual(error, "worker_result_key_mismatch")

    def test_result_requires_valid_status(self):
        job = {"kind": "scene", "key": "scene:a", "out_path": "scene/a.png"}
        status, identity, error = _valid_result(job, {
            "key": "scene:a", "status": "weird", "output_identity": "scene/a.png",
        })
        self.assertEqual(status, ArtAssetStatus.FAILED)
        self.assertEqual(error, "worker_result_invalid_status")

    def test_result_requires_exact_expected_identity(self):
        job = {"kind": "scene", "key": "scene:a", "out_path": "scene/a.png"}
        status, identity, error = _valid_result(job, {
            "key": "scene:a", "status": "success", "output_identity": "scene/other.png",
        })
        self.assertEqual(status, ArtAssetStatus.FAILED)
        self.assertEqual(error, "worker_output_identity_mismatch")


class WorkerStoreIsolationTests(WorkerStoreIsolation):
    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_successful_fixture_run_completes_a_scene_job(self):
        subject = self._subject()
        self._record(subject)
        with self._cmd():
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/forest_path.png")
        self.assertTrue((self.root / "scene" / "forest_path.png").is_file())

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_a_failed_marker_job_settles_failed(self):
        subject = self._subject()
        self._record(subject)
        with self._cmd(env_overrides={"ART_FIXTURE_FAIL": "scene:forest_path"}):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "fixture_fail")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_mismatched_key_result_is_rejected_with_prior_output_retained(self):
        subject = self._subject("tavern_interior")
        self._record(subject)
        (self.root / "scene" / "tavern_interior.png").write_text("prior", encoding="utf-8")
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        record.db.prior_output_identity = "scene/tavern_interior.png"
        with self._cmd(env_overrides={"ART_FIXTURE_WRONG_KEY": "scene:tavern_interior"}):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_result_key_mismatch")
        self.assertEqual(record.db.prior_output_identity, "scene/tavern_interior.png")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_wrong_identity_result_is_rejected(self):
        subject = self._subject("city_street")
        self._record(subject)
        with self._cmd(env_overrides={"ART_FIXTURE_WRONG_IDENTITY": "1"}):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_output_identity_mismatch")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_out_of_root_symlinked_output_is_rejected(self):
        subject = self._subject("mountain_path")
        self._record(subject)
        outside_dir = tempfile.TemporaryDirectory()
        try:
            outside = Path(outside_dir.name) / "outside.png"
            outside.write_text("outside", encoding="utf-8")
            (self.root / "scene").mkdir(parents=True, exist_ok=True)
            (self.root / "scene" / "mountain_path.png").symlink_to(outside)
            with self._cmd():
                drain_synchronous(10)
        finally:
            outside_dir.cleanup()
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_output_out_of_root")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_timeout_produces_a_bounded_failure(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._cmd(
            env_overrides={"ART_FIXTURE_SLEEP": "3"},
            settings_overrides={"ART_WORKER_TIMEOUT_SECONDS": 1},
        ):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_timeout")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_crash_truncated_batch_leaves_no_job_stuck(self):
        for key in ("forest_path", "tavern_interior"):
            self._record(self._subject(key), f"desc-{key}")
        with self._cmd(env_overrides={"ART_FIXTURE_EMIT_NONE": "1"}):
            drain_synchronous(10)
        for key in ("forest_path", "tavern_interior"):
            subject = self._subject(key)
            record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
            self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
            self.assertEqual(record.db.last_error_code, "worker_batch_protocol_error")

    def test_unparseable_batch_fails_unfinished_jobs(self):
        subject = self._subject("cave_interior")
        self._record(subject)
        with self._cmd(env_overrides={"ART_FIXTURE_MALFORMED": "1"}):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_protocol_error")

    @covers_requirement("art-queue-worker::the-external-worker-contract-validates-every-output-against-its-input-and-confines-paths-to-the-store-root")
    def test_non_object_json_result_leaves_no_job_stuck(self):
        subject = self._subject("cave_interior")
        self._record(subject)
        with self._cmd(env_overrides={"ART_FIXTURE_NON_OBJECT": "1"}):
            drain_synchronous(10)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "worker_protocol_error")


    @covers_requirement("art-queue-worker::scenes-and-portraits-share-one-serialization-lock-and-one-worker-concurrency-slot")
    def test_only_one_worker_runs_at_a_time(self):
        subject = self._subject("forest_path")
        self._record(subject)
        from world.art.worker import _try_acquire_worker_slot, _release_worker_slot

        self.assertTrue(_try_acquire_worker_slot())
        try:
            # A drain attempted while another worker is in flight claims nothing.
            with self._cmd():
                self.assertEqual(drain_synchronous(10), 0)
        finally:
            _release_worker_slot()
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-queue-worker::scenes-and-portraits-share-one-serialization-lock-and-one-worker-concurrency-slot")
    def test_slot_is_released_after_a_synchronous_drain(self):
        subject = self._subject("tavern_interior")
        self._record(subject)
        from world.art.worker import _try_acquire_worker_slot

        with self._cmd():
            dispatched = drain_synchronous(10)
        self.assertEqual(dispatched, 1)
        self.assertTrue(_try_acquire_worker_slot())
        from world.art.worker import _release_worker_slot

        _release_worker_slot()


if __name__ == "__main__":
    unittest.main()
