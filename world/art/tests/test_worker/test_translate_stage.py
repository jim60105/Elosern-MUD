"""Worker integration contracts for the local prompt-translation stage."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from django.test import override_settings

from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.fake_translate import FakeTranslator
from world.art.queue import (
    enqueue_gallery_job,
    record_key,
    requeue,
    source_hash,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubjectKind
from world.art.translate import TranslateError
import world.art.worker as worker

from ._support import WorkerStoreIsolation


class _ExplodingTranslator:
    def translate(self, lines: tuple[str, ...]) -> tuple[str, ...]:
        raise RuntimeError("translation exploded")


class TranslationStageTests(WorkerStoreIsolation):
    @contextmanager
    def _translator(self, fake: FakeTranslator):
        with override_settings(
            ART_TRANSLATE_ENABLED=True,
            ART_TRANSLATE_BACKEND="world.art.fake_translate.FakeTranslator",
        ):
            with patch(
                "world.art.fake_translate.FakeTranslator", return_value=fake
            ):
                yield

    def test_enabled_stage_translates_classic_scene_character_and_monster(self):
        description = "含有漢字"
        subjects = (
            self._subject("t_synth_translation", ArtSubjectKind.SCENE),
            self._subject("42", ArtSubjectKind.CHARACTER),
            self._subject("low", ArtSubjectKind.MONSTER),
        )
        originals = {}
        for subject in subjects:
            record = self._record(subject, description)
            originals[record.db_key] = (
                str(record.db.source_description),
                str(record.db.source_hash),
            )
        fake = FakeSDWebUIClient()
        translator = FakeTranslator()
        with self._translator(translator):
            with self._client(fake):
                worker.drain_synchronous(10)

        self.assertEqual(
            [description for _subject, description in fake.calls],
            ["[fake-translation]"] * len(subjects),
        )
        self.assertEqual(translator.calls, [(description,)] * len(subjects))
        for subject in subjects:
            record = ArtAssetRecord.objects.get(db_key=record_key(subject))
            self.assertEqual(record.db.status, ArtAssetStatus.DONE)
            self.assertEqual(
                (str(record.db.source_description), str(record.db.source_hash)),
                originals[record.db_key],
            )

    def test_enabled_stage_translates_gallery_without_mutating_the_spent_job(self):
        subject = self._subject("42", ArtSubjectKind.CHARACTER)
        description = "畫像漢字"
        job = enqueue_gallery_job(
            subject,
            description,
            image_id="aaaaaaaa-1111-4111-8111-111111111111",
            binding=None,
            face_rect=None,
            requested_fields=[],
        )
        original = (str(job.db.source_description), str(job.db.source_hash))
        fake = FakeSDWebUIClient()
        translator = FakeTranslator()
        real_settle = worker.settle_gallery_generated

        def observe_before_deletion(*args, **kwargs):
            stored = ArtAssetRecord.objects.get(db_key=job.db_key)
            self.assertEqual(
                (str(stored.db.source_description), str(stored.db.source_hash)),
                original,
            )
            return real_settle(*args, **kwargs)

        with self._translator(translator):
            with patch.object(
                worker, "settle_gallery_generated", side_effect=observe_before_deletion
            ):
                with self._client(fake):
                    worker.drain_synchronous(10)

        self.assertEqual(fake.calls, [(subject, "[fake-translation]")])
        self.assertEqual(translator.calls, [(description,)])
        self.assertIsNone(
            ArtAssetRecord.objects.filter(db_key=job.db_key).first(),
            "gallery settlement deletes only after the boundary observed source text",
        )

    def test_disabled_stage_leaves_description_and_backend_unresolved(self):
        subject = self._subject("t_synth_disabled_translation")
        description = "原始漢字"
        self._record(subject, description)
        first = FakeSDWebUIClient()
        with self._client(first):
            worker.drain_synchronous(10)
        target = self.root / "scene" / "t_synth_disabled_translation.png"
        baseline = target.read_bytes()
        requeue(subject)

        second = FakeSDWebUIClient()
        with patch(
            "world.art.translate.resolve_translate_backend",
            side_effect=AssertionError("disabled stage must not resolve"),
        ):
            with self._client(second):
                worker.drain_synchronous(10)
        self.assertEqual(second.calls, [(subject, description)])
        self.assertEqual(target.read_bytes(), baseline)

    def test_translation_failures_degrade_to_the_original_prompt_without_record_code(self):
        cases = (
            (
                "unavailable",
                "world.art.no_such_translate_backend.Backend",
                None,
            ),
            (
                "bounded",
                "world.art.fake_translate.FakeTranslator",
                TranslateError("art_translate_error", "scripted"),
            ),
            (
                "unexpected",
                "world.art.tests.test_worker.test_translate_stage._ExplodingTranslator",
                None,
            ),
        )
        for name, backend, scripted in cases:
            with self.subTest(case=name):
                subject = self._subject(f"t_synth_translate_{name}")
                description = "故障漢字"
                self._record(subject, description)
                client = FakeSDWebUIClient()
                with override_settings(
                    ART_TRANSLATE_ENABLED=True, ART_TRANSLATE_BACKEND=backend
                ):
                    if scripted is None:
                        with self._client(client):
                            worker.drain_synchronous(10)
                    else:
                        translator = FakeTranslator()
                        translator.fail_every_call(scripted)
                        with patch(
                            "world.art.fake_translate.FakeTranslator",
                            return_value=translator,
                        ):
                            with self._client(client):
                                worker.drain_synchronous(10)
                record = ArtAssetRecord.objects.get(db_key=record_key(subject))
                self.assertEqual(record.db.status, ArtAssetStatus.DONE)
                self.assertEqual(client.calls, [(subject, description)])
                self.assertFalse(
                    str(record.db.last_error_code or "").startswith("art_translate_")
                )
                self.assertEqual(record.db.source_hash, source_hash(description))

    def test_translation_enabled_does_not_change_the_lease_formula(self):
        with override_settings(
            ART_SD_TIMEOUT_SECONDS=1,
            ART_SCHEDULER_LIMIT=2,
            ART_REMBG_ENABLED=False,
            ART_TRANSLATE_ENABLED=True,
        ):
            self.assertEqual(worker._lease_timeout(), 2 * (1 + 60) + 5)
        with override_settings(
            ART_SD_TIMEOUT_SECONDS=1,
            ART_SCHEDULER_LIMIT=2,
            ART_REMBG_ENABLED=True,
            ART_REMBG_ALLOWANCE_SECONDS=120,
            ART_TRANSLATE_ENABLED=True,
        ):
            self.assertEqual(worker._lease_timeout(), 2 * (1 + 60 + 120) + 5)
