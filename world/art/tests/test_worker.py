"""Tests for the internal sd-webui worker boundary and store-path confinement.

Every test is deterministic and socket-free: the client seam is injected as
``FakeSDWebUIClient`` (via the ``ART_SD_CLIENT`` setting and a patched
``resolve_sd_client``), replaying fixed PNG fixtures and scripted failures.
"""

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
from world.art.queue import (
    claim,
    ensure,
    record_key,
    reclaim_expired_leases,
    requeue,
    settle,
    settle_generated,
)
from world.art.sd_worker import GeneratedImage, SDError
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
    batch. Records every call like the fake client. A valid generation returns
    the default PNG with a scripted seed (default ``None``).
    """

    def __init__(self):
        self.calls: list[tuple[ArtSubject, str]] = []
        self.outcomes: dict[str, Exception | None] = {}
        self.seed: int | None = None

    def generate(self, subject: ArtSubject, description: str) -> GeneratedImage:
        self.calls.append((subject, description))
        error = self.outcomes.get(description)
        if error is not None:
            raise error
        return GeneratedImage(data=DEFAULT_PNG, seed=self.seed)


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
        # The png path re-encodes through the local converter: the container
        # bytes may differ, the decoded pixels must not.
        before = Image.open(io.BytesIO(DEFAULT_PNG)).convert("RGBA")
        after = Image.open(target.open("rb")).convert("RGBA")
        self.assertEqual(list(before.getdata()), list(after.getdata()))

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

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_server_reported_seed_is_persisted_on_publish(self):
        subject = self._subject()
        self._record(subject)
        fake = FakeSDWebUIClient()
        fake.seed = 42
        with self._client(fake):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.seed, 42)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_seedless_regeneration_clears_the_previous_seed(self):
        # A seedless regeneration must never keep advertising the old image's
        # seed: settle_generated assigns the new (absent) seed unconditionally.
        subject = self._subject()
        self._record(subject)
        seeded = FakeSDWebUIClient()
        seeded.seed = 42
        with self._client(seeded):
            drain_synchronous(10)
        self.assertEqual(self._record_for(subject).db.seed, 42)
        requeue(subject)
        seedless = FakeSDWebUIClient()
        seedless.seed = None
        with self._client(seedless):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertIsNone(record.db.seed)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_failed_regeneration_retains_prior_output_and_seed(self):
        subject = self._subject()
        self._record(subject)
        seeded = FakeSDWebUIClient()
        seeded.seed = 7
        with self._client(seeded):
            drain_synchronous(10)
        requeue(subject)
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(failing):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.output_identity, "scene/forest_path.png")
        self.assertEqual(record.db.seed, 7)

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
            # A drain's reclaim uses the worst-case batch bound
            # (2 x (timeout + 60s conversion allowance) + 5s margin): a moment
            # inside the lease keeps the batch unreclaimed, so no generation
            # is attempted.
            dispatched = drain_synchronous(10)
            self.assertEqual(dispatched, 0)
            for subject in subjects:
                record = self._record_for(subject)
                self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
            # A flat per-item bound (timeout + margin) would already have
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


class OutputFormatPipelineTests(WorkerStoreIsolation):
    """The worker-side conversion: extension-aware identity and prior cleanup."""

    def _formats(self, output_format: str, extension: str):
        """Override the format pair together (settings derive one from the other)."""
        return override_settings(
            ART_SD_OUTPUT_FORMAT=output_format,
            ART_SD_OUTPUT_EXTENSION=extension,
        )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_configured_format_drives_the_published_extension(self):
        subject = self._subject()
        self._record(subject)
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/forest_path.webp")
        target = self.root / "scene" / "forest_path.webp"
        self.assertTrue(target.is_file())
        self.assertEqual(Image.open(target.open("rb")).format, "WEBP")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_format_change_replaces_file_and_deletes_prior_after_commit(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "dungeon_interior.png"
        self.assertTrue(png_path.is_file())
        requeue(subject)
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/dungeon_interior.webp")
        self.assertTrue((self.root / "scene" / "dungeon_interior.webp").is_file())
        # The stale png is deleted only after the transition committed; the
        # record never points at the deleted file at any point.
        self.assertFalse(png_path.exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_same_extension_regeneration_deletes_nothing_extra(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        requeue(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        # Same extension: the atomic replace overwrote in place; no cleanup
        # candidate existed, so the directory holds exactly the one file.
        listing = sorted(p.name for p in (self.root / "scene").iterdir())
        self.assertEqual(listing, ["dungeon_interior.png"])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_encode_failure_sets_sd_format_error_and_keeps_prior(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "dungeon_interior.png"
        prior_bytes = png_path.read_bytes()
        requeue(subject)

        class _GarbageClient:
            def generate(self, subject, description):
                return GeneratedImage(data=b"not-an-image", seed=99)

        with self._formats("webp", ".webp"):
            with self._client(_GarbageClient()):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(record.db.last_error_code, "sd_format_error")
        # Prior output retained: record still references it and bytes intact.
        self.assertEqual(record.db.output_identity, "scene/dungeon_interior.png")
        self.assertEqual(png_path.read_bytes(), prior_bytes)
        self.assertFalse((self.root / "scene" / "dungeon_interior.webp").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_reclaimed_record_never_lets_the_stale_claim_publish(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        held = claim(10)[0]
        token_a = str(held.db.generation_token)

        class _ReclaimMidFlightClient:
            """Requeue + fresh claim (token B) DURING the in-flight generation."""

            def __init__(self):
                self.token_b: str | None = None

            def generate(self, subject, description):
                requeue(subject)
                fresh = claim(10)[0]
                self.token_b = str(fresh.db.generation_token)
                return GeneratedImage(data=DEFAULT_PNG, seed=1)

        racing = _ReclaimMidFlightClient()
        from world.art.worker import _settle_one

        outcome = _settle_one(racing, held)
        self.assertIsNone(outcome)
        record = self._record_for(subject)
        # The stale worker (token A) must not publish under the newer claim
        # (token B): the record stays in_progress under B, unpublished.
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(record.db.generation_token, racing.token_b)
        self.assertNotEqual(racing.token_b, token_a)
        self.assertIsNone(record.db.output_identity)
        self.assertFalse((self.root / "scene" / "dungeon_interior.png").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_settle_failure_before_commit_keeps_prior_file_on_disk(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "dungeon_interior.png"
        prior_bytes = png_path.read_bytes()
        requeue(subject)
        with self._formats("webp", ".webp"):
            # Claim the record (fresh token), then requeue mid-flight so the
            # held token goes stale: settle_generated must refuse and the
            # prior file must stay on disk AND keep being referenced.
            claimed = claim(10)
            self.assertEqual(len(claimed), 1)
            held = claimed[0]
            requeue(subject)
            from world.art.worker import _settle_one

            outcome = _settle_one(FakeSDWebUIClient(), held)
            self.assertIsNone(outcome)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(record.db.output_identity, "scene/dungeon_interior.png")
        self.assertEqual(png_path.read_bytes(), prior_bytes)
        self.assertFalse((self.root / "scene" / "dungeon_interior.webp").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_cleanup_deletion_error_logs_and_never_reverts(self):
        subject = self._subject("dungeon_interior")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "dungeon_interior.png"
        requeue(subject)
        with self._formats("webp", ".webp"):
            with patch("pathlib.Path.unlink", side_effect=OSError("read-only")):
                with patch("world.art.worker.log_warn") as warned:
                    with self._client(FakeSDWebUIClient()):
                        drain_synchronous(10)
        record = self._record_for(subject)
        # The DONE transition stays committed; the orphan remains; bounded log.
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/dungeon_interior.webp")
        self.assertTrue(png_path.exists())
        messages = [call.args[0] for call in warned.call_args_list]
        self.assertTrue(any("cleanup_failed" in message for message in messages), messages)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_embedded_provenance_comes_from_the_returned_image(self):
        # The client's image provenance is what gets embedded — patching the
        # prompt library to a DIFFERENT sentinel proves the worker never
        # re-renders the mutable library to fill metadata.
        subject = self._subject()
        self._record(subject)

        class _ProvenanceClient:
            def generate(self, subject, description):
                return GeneratedImage(
                    data=DEFAULT_PNG,
                    seed=777,
                    prompt="CLIENT PROMPT",
                    negative_prompt="CLIENT NEGATIVE",
                    steps=23,
                    cfg_scale=7.5,
                    sampler="DPM++ 2M",
                    scheduler="Karras",
                    width=512,
                    height=768,
                    checkpoint="client-model.safetensors",
                )

        captured = {}
        real_encode = __import__(
            "world.art.formats", fromlist=["encode"]
        ).encode

        def _spy_encode(*args, **kwargs):
            result = real_encode(*args, **kwargs)
            captured["bytes"] = result[0]
            return result

        with patch("world.art.worker.encode", side_effect=_spy_encode):
            with patch(
                "world.art.sd_worker.render_prompt_pair",
                return_value=("LIBRARY PROMPT", "LIBRARY NEGATIVE"),
            ):
                with self._client(_ProvenanceClient()):
                    drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        text = Image.open(io.BytesIO(captured["bytes"])).text["parameters"]
        self.assertIn("CLIENT PROMPT", text)
        self.assertNotIn("LIBRARY PROMPT", text)
        self.assertIn("Negative prompt: CLIENT NEGATIVE", text)
        self.assertIn("Steps: 23", text)
        self.assertIn("Sampler name: DPM++ 2M", text)
        self.assertIn("Scheduler: Karras", text)
        self.assertIn("CFG scale: 7.5", text)
        self.assertIn("Seed: 777", text)
        self.assertIn("Size: 512x768", text)
        self.assertIn("Model: client-model.safetensors", text)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_lease_bound_includes_the_local_conversion_allowance(self):
        with override_settings(ART_SD_TIMEOUT_SECONDS=1, ART_SCHEDULER_LIMIT=2):
            from world.art.worker import _CONVERSION_ALLOWANCE_SECONDS, _LEASE_MARGIN_SECONDS

            # 2 x (1s timeout + conversion allowance) + 5s margin — a slow
            # local encode beyond the old flat margin keeps the batch safe.
            expected = 2 * (1 + _CONVERSION_ALLOWANCE_SECONDS) + _LEASE_MARGIN_SECONDS
            self.assertEqual(_lease_timeout(), expected)
            self.assertGreater(_lease_timeout(), 2 * 1 + _LEASE_MARGIN_SECONDS)


if __name__ == "__main__":
    unittest.main()
