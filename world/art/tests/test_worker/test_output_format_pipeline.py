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
    enqueue_gallery_job,
    gallery_record_key,
    reclaim_expired_leases,
)
from world.art.sd_worker import GeneratedImage, SDError
from world.art.store import ArtAssetStatus, GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import (
    _lease_timeout,
    _run_and_settle_batch,
    drain,
    drain_synchronous,
    output_identity_for,
)

from tools.spec_traceability import covers_requirement

from ._support import (
    WorkerStoreIsolation,
)


class OutputFormatPipelineTests(WorkerStoreIsolation):
    """The worker-side conversion: extension-aware per-image publication."""

    def _formats(self, output_format: str, extension: str):
        """Override the format pair together (settings derive one from the other)."""
        return override_settings(
            ART_SD_OUTPUT_FORMAT=output_format,
            ART_SD_OUTPUT_EXTENSION=extension,
        )

    def _gallery_job(self, subject, image_id):
        return enqueue_gallery_job(
            subject,
            "desc",
            image_id=image_id,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_configured_format_drives_the_published_extension(self):
        subject = self._subject()
        job = self._record(subject)
        image_id = job.db.gallery_image_id
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(
            cards[0]["stored_identity"],
            f"gallery/scene/t_synth_forest/{image_id}.webp",
        )
        target = self.root / cards[0]["stored_identity"]
        self.assertTrue(target.is_file())
        with Image.open(target.open("rb")) as image:
            self.assertEqual(image.format, "WEBP")
        self.assertIsNone(self._job_for(job))

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_a_capped_format_change_replaces_only_the_displaced_file(self):
        subject = self._subject("t_synth_dungeon")
        first = self._record(subject, "png")
        first_identity = output_identity_for(first)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        self.assertTrue((self.root / first_identity).is_file())
        job = self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["image_id"], "bbbbbbbb-2222-4222-8222-222222222222")
        self.assertTrue((self.root / cards[0]["stored_identity"]).is_file())
        # The displaced png is removed only after the new card committed, and
        # the card never points at the deleted file.
        self.assertFalse((self.root / first_identity).exists())

    @covers_requirement("art-output-format-pipeline::generated-art-is-converted-locally-to-the-configured-output-format-at-the-configured-quality")
    def test_an_uncapped_format_change_retains_prior_cards_and_files(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        first = self._gallery_job(subject, "aaaaaaaa-1111-4111-8111-111111111111")
        first_identity = output_identity_for(first)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")
        with self._formats("webp", ".webp"):
            with self._client(FakeSDWebUIClient()):
                drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards],
                         ["aaaaaaaa-1111-4111-8111-111111111111",
                          "bbbbbbbb-2222-4222-8222-222222222222"])
        self.assertTrue((self.root / first_identity).is_file())
        self.assertTrue((self.root / cards[1]["stored_identity"]).is_file())

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_same_extension_regeneration_publishes_one_new_card(self):
        subject = self._subject("t_synth_dungeon")
        first = self._record(subject, "one")
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        second = self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["image_id"], "bbbbbbbb-2222-4222-8222-222222222222")
        listing = sorted(p.name for p in (self.root / "gallery" / "scene" / subject.key).iterdir())
        self.assertEqual(listing, ["bbbbbbbb-2222-4222-8222-222222222222.png"])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_encode_failure_sets_sd_format_error_and_keeps_prior(self):
        subject = self._subject("t_synth_dungeon")
        first = self._record(subject)
        first_identity = output_identity_for(first)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        prior_bytes = (self.root / first_identity).read_bytes()
        job = self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")

        class _GarbageClient:
            def generate(self, subject, description):
                return GeneratedImage(data=b"not-an-image", seed=99)

        with self._formats("webp", ".webp"):
            with self._client(_GarbageClient()):
                drain_synchronous(10)
        self.assertEqual(
            [state.error_code for state in gallery_api.erroring_subjects()],
            ["sd_format_error"],
        )
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["stored_identity"], first_identity)
        self.assertEqual((self.root / first_identity).read_bytes(), prior_bytes)
        self.assertFalse(
            (self.root / "gallery" / "scene" / subject.key / "bbbbbbbb-2222-4222-8222-222222222222.webp").exists()
        )
        self.assertIsNone(self._job_for(job))

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_reclaimed_job_never_lets_the_stale_claim_publish(self):
        subject = self._subject("t_synth_dungeon")
        job = self._record(subject)
        held = claim(10)[0]
        token_a = str(held.db.generation_token)

        class _ReclaimMidFlightClient:
            """Reclaim + fresh claim (token B) DURING the in-flight generation."""

            def __init__(self):
                self.token_b: str | None = None

            def generate(self, subject, description):
                reclaim_expired_leases(0.0)
                fresh = claim(10)[0]
                self.token_b = str(fresh.db.generation_token)
                return GeneratedImage(data=DEFAULT_PNG, seed=1)

        racing = _ReclaimMidFlightClient()
        from world.art.worker import _settle_one

        outcome = _settle_one(racing, held, subject, token_a)
        self.assertIsNone(outcome)
        current = self._job_for(job)
        self.assertEqual(current.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertEqual(current.db.generation_token, racing.token_b)
        self.assertNotEqual(racing.token_b, token_a)
        self.assertIsNone(current.db.last_error_code)
        self.assertEqual(gallery_api.cards_for(subject), [])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_settle_failure_before_commit_keeps_prior_card_on_disk(self):
        subject = self._subject("t_synth_dungeon")
        first = self._record(subject)
        first_identity = output_identity_for(first)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        prior_bytes = (self.root / first_identity).read_bytes()
        job = self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")
        with self._formats("webp", ".webp"):
            claimed = claim(10)[0]
            token_held = str(claimed.db.generation_token)
            reclaim_expired_leases(0.0)
            from world.art.worker import _settle_one

            outcome = _settle_one(
                FakeSDWebUIClient(),
                claimed,
                subject,
                token_held,
            )
            self.assertIsNone(outcome)
        current = self._job_for(job)
        self.assertEqual(current.db.status, ArtAssetStatus.PENDING)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["stored_identity"], first_identity)
        self.assertEqual((self.root / first_identity).read_bytes(), prior_bytes)
        self.assertFalse(
            (self.root / "gallery" / "scene" / subject.key / "bbbbbbbb-2222-4222-8222-222222222222.webp").exists()
        )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_cleanup_deletion_error_logs_and_never_reverts(self):
        subject = self._subject("t_synth_dungeon")
        first = self._record(subject)
        first_identity = output_identity_for(first)
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        self._gallery_job(subject, "bbbbbbbb-2222-4222-8222-222222222222")
        with self._formats("webp", ".webp"):
            with patch("pathlib.Path.unlink", side_effect=OSError("read-only")):
                with patch("world.art.gallery.log_warn") as warned:
                    with self._client(FakeSDWebUIClient()):
                        drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        self.assertTrue(cards[0]["stored_identity"].endswith(".webp"))
        # The committed card is the authoritative publish; the orphan remains.
        self.assertTrue((self.root / first_identity).exists())
        messages = [call.args[0] for call in warned.call_args_list]
        self.assertTrue(
            any("gallery_card_file_delete_failed" in message for message in messages),
            messages,
        )

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
                    decoded_width=512,
                    decoded_height=768,
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
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        with Image.open(self.root / cards[0]["stored_identity"]) as image:
            text = image.text["parameters"]
        self.assertIn("CLIENT PROMPT", text)
        self.assertNotIn("LIBRARY PROMPT", text)
        self.assertIn("Negative prompt: CLIENT NEGATIVE", text)
        self.assertIn("Steps: 23", text)
        self.assertIn("Sampler: DPM++ 2M", text)
        self.assertIn("Schedule type: Karras", text)
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
