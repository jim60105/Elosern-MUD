"""Slice of ``test_worker``: GalleryWorkerTests.
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

class GalleryWorkerTests(WorkerStoreIsolation):
    """Per-image gallery jobs published through the worker's settle boundary."""

    _IMAGE_ID = "aaaaaaaa-1111-4111-8111-111111111111"

    def setUp(self):
        super().setUp()
        self.character = self._subject("42", ArtSubjectKind.CHARACTER)

    def _gallery_job(self, image_id=None, description="desc"):
        return enqueue_gallery_job(
            self.character,
            description,
            image_id=image_id or self._IMAGE_ID,
            binding=None,
            face_rect=None,
            requested_fields=[],
        )

    def _gallery_job_for(self, image_id=None):
        key = gallery_record_key(self.character, image_id or self._IMAGE_ID)
        return ArtAssetRecord.objects.filter(db_key=key).first()

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_output_identity_for_is_per_image_for_gallery_and_exact_for_classic(self):
        classic = self._record(self._subject("t_synth_forest"))
        self.assertEqual(output_identity_for(classic), "scene/t_synth_forest.png")
        job = self._gallery_job()
        self.assertEqual(
            output_identity_for(job),
            f"gallery/character/42/{self._IMAGE_ID}.png",
        )
        with override_settings(ART_SD_OUTPUT_FORMAT="webp", ART_SD_OUTPUT_EXTENSION=".webp"):
            self.assertEqual(
                output_identity_for(job),
                f"gallery/character/42/{self._IMAGE_ID}.webp",
            )

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_a_successful_gallery_job_publishes_exactly_one_card(self):
        job = self._gallery_job()
        fake = FakeSDWebUIClient()
        fake.seed = 4242
        from world.art.signals import asset_completed

        completed = []
        asset_completed.connect(
            lambda sender, subject_key, **_kwargs: completed.append(subject_key),
            dispatch_uid="gallery-asset-completed-test",
            weak=False,
        )
        self.addCleanup(
            lambda: asset_completed.disconnect(dispatch_uid="gallery-asset-completed-test")
        )
        with self._client(fake):
            drain_synchronous(10)
        # The targeted panel push still fires for a settled gallery job's subject.
        self.assertEqual(completed, [self.character.full()])
        identity = f"gallery/character/42/{self._IMAGE_ID}.png"
        target = self.root / "gallery" / "character" / "42" / f"{self._IMAGE_ID}.png"
        self.assertTrue(target.is_file())
        cards = gallery_api.cards_for(self.character)
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card["image_id"], self._IMAGE_ID)
        self.assertEqual(card["stored_identity"], identity)
        self.assertEqual(card["source"], "generated")
        self.assertEqual(card["seed"], 4242)
        # The verbatim pair the client returned (the fake's defaults are the
        # GeneratedImage defaults), carried as exactly positive/negative.
        self.assertEqual(sorted(card["prompt"]), ["negative", "positive"])
        self.assertEqual(card["prompt"]["positive"], "")
        self.assertEqual(card["prompt"]["negative"], "")
        self.assertEqual(card["face_rect"], DEFAULT_FACE_RECT)
        self.assertIsNone(card["binding"])
        self.assertEqual(list(card["requested_fields"]), [])
        self.assertIsNone(card["checkpoint"])
        # The spent job record is gone; no classic record was ever touched.
        self.assertIsNone(self._gallery_job_for())
        self.assertIsNone(
            ArtAssetRecord.objects.filter(db_key=record_key(self.character)).first()
        )
        # No stray temporary files under the gallery tree.
        leftovers = [p for p in target.parent.iterdir() if p.name != f"{self._IMAGE_ID}.png"]
        self.assertEqual(leftovers, [])

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_a_failed_gallery_job_appends_no_card_and_records_the_code(self):
        # A pre-existing card must survive a later failure untouched.
        gallery_api.append_card(
            self.character,
            image_id="00000000-0000-4000-8000-000000000001",
            stored_identity="gallery/character/42/00000000-0000-4000-8000-000000000001.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )
        (self.root / "gallery" / "character" / "42").mkdir(parents=True)
        job = self._gallery_job()
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_connection_error", "offline"))
        before = [p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()]
        with self._client(fake):
            drain_synchronous(10)
        cards = gallery_api.cards_for(self.character)
        self.assertEqual([card["image_id"] for card in cards],
                         ["00000000-0000-4000-8000-000000000001"])
        record = gallery_api.record_for(self.character)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        self.assertIsNotNone(record.db.last_error_at)
        self.assertIsNone(self._gallery_job_for())
        self.assertFalse((self.root / "gallery" / "character" / "42" / f"{self._IMAGE_ID}.png").exists())
        after = [p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()]
        self.assertEqual(after, before)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_a_stale_gallery_claim_publishes_no_card_and_removes_its_temp(self):
        job = self._gallery_job()
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        held_token = str(claimed[0].db.generation_token)
        # The job is reclaimed to pending mid-flight (worker died, lease lost).
        self.assertEqual(reclaim_expired_leases(0.001), 1)
        tmp_path = _write_temp(
            f"gallery/character/42/{self._IMAGE_ID}.png", DEFAULT_PNG
        )
        from world.art.queue import settle_gallery_generated

        stored = settle_gallery_generated(
            job.db_key,
            generation_token=held_token,
            output_identity=f"gallery/character/42/{self._IMAGE_ID}.png",
            tmp_path=tmp_path,
            prompt={"positive": "p", "negative": "n"},
            seed=1,
            checkpoint=None,
        )
        self.assertIsNone(stored)
        self.assertFalse(Path(tmp_path).exists())
        self.assertEqual(gallery_api.cards_for(self.character), [])
        self.assertFalse(
            (self.root / "gallery" / "character" / "42" / f"{self._IMAGE_ID}.png").exists()
        )

    @covers_requirement("art-gallery-generation::generation-while-the-image-server-is-unreachable-is-a-reported-failure-never-a-gate")
    def test_a_successful_settle_clears_the_recorded_error(self):
        # A previously recorded failure is last-attempt state: the settle
        # that appends a card clears it as part of the same publish.
        gallery_api.record_error(self.character, "sd_connection_error")
        job = self._gallery_job()
        with self._client(FakeSDWebUIClient()):
            drain_synchronous(10)
        self.assertEqual(len(gallery_api.cards_for(self.character)), 1)
        record = gallery_api.record_for(self.character)
        self.assertIsNone(record.db.last_error_code)
        self.assertIsNone(record.db.last_error_at)
        self.assertIsNone(self._gallery_job_for())
        # A clear failure never rewrites the settle's outcome: the appended
        # card is the authoritative publish.
        gallery_api.record_error(self.character, "sd_timeout")
        job = self._gallery_job(image_id="bbbbbbbb-2222-4222-8222-222222222222")
        with self._client(FakeSDWebUIClient()):
            with patch(
                "world.art.gallery.clear_error", side_effect=RuntimeError("db down")
            ):
                drain_synchronous(10)
        cards = gallery_api.cards_for(self.character)
        self.assertEqual(len(cards), 2)
        self.assertIsNone(self._gallery_job_for("bbbbbbbb-2222-4222-8222-222222222222"))

    @covers_requirement("art-gallery-generation::generation-while-the-image-server-is-unreachable-is-a-reported-failure-never-a-gate")
    def test_a_failed_settle_after_a_success_records_the_new_code(self):
        # Success first: one card, no error.
        with self._client(FakeSDWebUIClient()):
            self._gallery_job()
            drain_synchronous(10)
        cards_before = gallery_api.cards_for(self.character)
        self.assertEqual(len(cards_before), 1)
        self.assertIsNone(
            gallery_api.record_for(self.character).db.last_error_code
        )
        # Then a failure: the new bounded code lands, every card survives.
        failing = FakeSDWebUIClient()
        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        self._gallery_job(image_id="cccccccc-3333-4333-8333-333333333333")
        with self._client(failing):
            drain_synchronous(10)
        record = gallery_api.record_for(self.character)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        self.assertIsInstance(record.db.last_error_at, float)
        self.assertEqual(gallery_api.cards_for(self.character), cards_before)

    @covers_requirement("art-queue-worker::the-internal-worker-contract-generates-every-output-through-the-sd-webui-client-and-confines-paths-to-the-store-root")
    def test_an_unresolvable_client_still_settles_gallery_jobs_failed(self):
        # A mixed batch: one classic scene record AND one gallery job for a
        # character. The client seam itself fails to resolve, so the whole
        # batch settles through the config-failure path: the gallery job must
        # settle failed on the GALLERY record (never the classic one) and its
        # spent record must be deleted; the classic record settles failed once.
        scene = self._subject("t_synth_forest")
        self._record(scene)
        self._gallery_job()
        with patch(
            "world.art.worker.resolve_sd_client",
            side_effect=ImportError("no module named nope"),
        ):
            with patch("world.art.worker.log_info") as info:
                drain_synchronous(10)
        settles = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "gallery_settle"
        ]
        self.assertEqual(len(settles), 1, settles)
        # The event fields are captured BEFORE the spent record's deletion:
        # a non-empty image id survives the settle (task 3.4).
        self.assertEqual(
            settles[0].kwargs["context"],
            {
                "subject": self.character.full(),
                "image_id": self._IMAGE_ID,
                "kind": self.character.kind.value,
                "status": ArtAssetStatus.FAILED,
                "reason": "sd_client_config_error",
            },
        )
        scene_record = self._record_for(scene)
        self.assertEqual(scene_record.db.status, ArtAssetStatus.FAILED)
        self.assertEqual(scene_record.db.last_error_code, "sd_client_config_error")
        self.assertIsNone(self._gallery_job_for())
        record = gallery_api.record_for(self.character)
        self.assertIsNotNone(record)
        self.assertEqual(record.db.last_error_code, "sd_client_config_error")
        self.assertEqual(gallery_api.cards_for(self.character), [])
        # Only the claimed classic record exists besides the deleted job.
        keys = {r.db_key for r in ArtAssetRecord.objects.all()}
        self.assertEqual(keys, {record_key(scene)})
