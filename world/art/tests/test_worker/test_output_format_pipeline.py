"""Slice of ``test_worker``: OutputFormatPipelineTests.
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
from world.art.fake_cutout import FakeCutoutBackend
from world.art.cutout import CutoutError
from world.art import gallery as gallery_api
from world.art.gallery import DEFAULT_FACE_RECT
from world.art.queue import (
    claim,
    ensure,
    enqueue_gallery_job,
    gallery_record_key,
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
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

from ._support import (
    WorkerStoreIsolation,
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
        self.assertEqual(record.db.output_identity, "scene/t_synth_forest.webp")
        target = self.root / "scene" / "t_synth_forest.webp"
        self.assertTrue(target.is_file())
        self.assertEqual(Image.open(target.open("rb")).format, "WEBP")

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_format_change_replaces_file_and_deletes_prior_after_commit(self):
        subject = self._subject("t_synth_dungeon")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "t_synth_dungeon.png"
        self.assertTrue(png_path.is_file())
        requeue(subject)
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/t_synth_dungeon.webp")
        self.assertTrue((self.root / "scene" / "t_synth_dungeon.webp").is_file())
        # The stale png is deleted only after the transition committed; the
        # record never points at the deleted file at any point.
        self.assertFalse(png_path.exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_same_extension_regeneration_deletes_nothing_extra(self):
        subject = self._subject("t_synth_dungeon")
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
        self.assertEqual(listing, ["t_synth_dungeon.png"])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_encode_failure_sets_sd_format_error_and_keeps_prior(self):
        subject = self._subject("t_synth_dungeon")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "t_synth_dungeon.png"
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
        self.assertEqual(record.db.output_identity, "scene/t_synth_dungeon.png")
        self.assertEqual(png_path.read_bytes(), prior_bytes)
        self.assertFalse((self.root / "scene" / "t_synth_dungeon.webp").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_reclaimed_record_never_lets_the_stale_claim_publish(self):
        subject = self._subject("t_synth_dungeon")
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

        outcome = _settle_one(racing, held, subject, token_a)
        self.assertIsNone(outcome)
        record = self._record_for(subject)
        # The stale worker (token A) must not publish under the newer claim
        # (token B): the record stays in_progress under B, unpublished.
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(record.db.generation_token, racing.token_b)
        self.assertNotEqual(racing.token_b, token_a)
        self.assertIsNone(record.db.output_identity)
        self.assertFalse((self.root / "scene" / "t_synth_dungeon.png").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_settle_failure_before_commit_keeps_prior_file_on_disk(self):
        subject = self._subject("t_synth_dungeon")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "t_synth_dungeon.png"
        prior_bytes = png_path.read_bytes()
        requeue(subject)
        with self._formats("webp", ".webp"):
            # Claim the record (fresh token), then requeue mid-flight so the
            # held token goes stale: settle_generated must refuse and the
            # prior file must stay on disk AND keep being referenced.
            claimed = claim(10)
            self.assertEqual(len(claimed), 1)
            held = claimed[0]
            token_held = str(held.db.generation_token)
            requeue(subject)
            from world.art.worker import _settle_one

            outcome = _settle_one(
                FakeSDWebUIClient(),
                held,
                subject,
                token_held,
            )
            self.assertIsNone(outcome)
        record = self._record_for(subject)
        self.assertEqual(record.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(record.db.output_identity, "scene/t_synth_dungeon.png")
        self.assertEqual(png_path.read_bytes(), prior_bytes)
        self.assertFalse((self.root / "scene" / "t_synth_dungeon.webp").exists())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_cleanup_deletion_error_logs_and_never_reverts(self):
        subject = self._subject("t_synth_dungeon")
        self._record(subject)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        png_path = self.root / "scene" / "t_synth_dungeon.png"
        requeue(subject)
        with self._formats("webp", ".webp"):
            with patch("pathlib.Path.unlink", side_effect=OSError("read-only")):
                with patch("world.art.worker.log_warn") as warned:
                    with self._client(FakeSDWebUIClient()):
                        drain_synchronous(10)
        record = self._record_for(subject)
        # The DONE transition stays committed; the orphan remains; bounded log.
        self.assertEqual(record.db.status, ArtAssetStatus.DONE)
        self.assertEqual(record.db.output_identity, "scene/t_synth_dungeon.webp")
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
