"""Slice of ``test_service``: GalleryRequestSeamTests, GalleryPromptCompositionTests.
"""
from unittest.mock import patch
import unittest
from contextlib import contextmanager
import tempfile
from pathlib import Path
from django.db import transaction
from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.art.queue import ensure, record_key, source_hash
from world.art import gallery as gallery_api
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.gallery_prompt import (
    CUSTOM_PROMPT_MAX,
    GalleryPromptError,
)
from world.art.sd_worker import SDError
from world.art.service import requeue_gallery_subject
from world.art.service import prune_gallery_orphans
from world.art.subjects import (
    ArtSubjectError,
    monster_description,
    monster_subject_for,
    scene_subject_for,
)
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    request_gallery_image,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_ITEMS,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

from ._support import (
    open_synthetic_scope,
    _SYNTH_WEAPON,
    _SYNTH_OFFHAND,
    _SYNTH_ARMOR,
    _SYNTH_TRINKET,
    _valid_binding,
)

class GalleryRequestSeamTests(EvenniaTestCase):
    """request_gallery_image validates before any write and never gates."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="gallery-player")
        self.player.age = 30
        self.player.apparent_age = 25
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.player.pk))

    def _gallery_jobs(self):
        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @contextmanager
    def _client(self, client):
        with patch("world.art.worker.resolve_sd_client", return_value=client):
            yield

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_a_valid_request_queues_exactly_one_job_with_the_supplied_metadata(self):
        rect = {"x": 0.2, "y": 0.1, "w": 0.5, "h": 0.5}
        with patch("world.art.service.log_info") as info:
            image_id = request_gallery_image(
                self.player, binding=_valid_binding(), face_rect=rect
            )
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.db_key, f"art:{self.subject.full()}:gen:{image_id}")
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        self.assertEqual(dict(job.db.gallery_binding), _valid_binding())
        self.assertEqual(dict(job.db.gallery_face_rect), rect)
        self.assertEqual(gallery_api.cards_for(self.subject), [])
        generates = [
            call for call in info.call_args_list if call.args and call.args[0] == "gallery_generate"
        ]
        self.assertEqual(len(generates), 1)
        self.assertEqual(
            generates[0].kwargs["context"],
            {"subject": self.subject.full(), "image_id": image_id, "kind": self.subject.kind.value},
        )

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_invalid_binding_or_rect_never_reaches_the_queue(self):
        with patch("world.art.queue._prompt_digest_or_empty") as digest:
            with self.assertRaises(gallery_api.GalleryRecordError):
                request_gallery_image(self.player, binding={"mask": []})
            with self.assertRaises(gallery_api.GalleryRecordError):
                request_gallery_image(
                    self.player, face_rect={"x": 0.8, "y": 0.8, "w": 0.5, "h": 0.5}
                )
        self.assertEqual(self._gallery_jobs(), [])
        digest.assert_not_called()

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_ineligible_subject_is_rejected_deterministically(self):
        self.player.attributes.remove("age")
        with patch("world.art.sd_worker.render_prompt_pair") as render:
            with self.assertRaises(ArtSubjectError):
                request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])
        render.assert_not_called()

        self.player.age = 30
        self.player.attributes.remove("apparent_age")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])

        self.player.apparent_age = 25
        self.player.age = "not-an-integer"
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(self.player)
        self.assertEqual(self._gallery_jobs(), [])

        plain = create_object(NPC, key="gallery-no-policy")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(plain)
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-generation::generation-while-the-image-server-is-unreachable-is-a-reported-failure-never-a-gate"
    )
    def test_an_offline_request_settles_failed_with_the_named_code_and_no_card(self):
        request_gallery_image(self.player)
        fake = FakeSDWebUIClient()
        fake.fail_every_call(SDError("sd_connection_error", "offline"))
        with self._client(fake):
            from world.art.worker import drain_synchronous

            drain_synchronous(10)
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(gallery_api.cards_for(self.subject), [])
        record = gallery_api.record_for(self.subject)
        self.assertIsNotNone(record)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        self.assertIsNotNone(record.db.last_error_at)

class GalleryPromptCompositionTests(EvenniaTestCase):
    """The seam's field selection: provenance on the card, validation first."""

    def setUp(self):
        # Equipment-field composition reads the item catalog: the player wears
        # synthetic gear inside an items scope, and every summary assertion
        # resolves through the patched kit rows.
        open_synthetic_scope(self, "items")
        super().setUp()
        self.player = create_object(PlayerCharacter, key="composition-player")
        self.player.age = 30
        self.player.apparent_age = 25
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.player.db.equipment = {
            "weapon_main": _SYNTH_WEAPON,
            "weapon_off": _SYNTH_OFFHAND,
            "armor": _SYNTH_ARMOR,
            "accessories": [_SYNTH_TRINKET],
        }
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.player.pk))

    def _gallery_jobs(self):
        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    def _drain(self):
        from world.art.worker import drain_synchronous

        with patch(
            "world.art.worker.resolve_sd_client", return_value=FakeSDWebUIClient()
        ):
            drain_synchronous(10)

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_selection_settles_onto_the_card_normalized_and_composed(self):
        request_gallery_image(
            self.player,
            fields=("armor", "appearance", "accessories"),
            custom_prompt="月下持杖，藍袍拖地",
        )
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        # Stored in declared-catalog order, never the caller's listing order.
        self.assertEqual(
            list(job.db.gallery_requested_fields),
            ["appearance", "armor", "accessories"],
        )
        summary = SYNTH_ITEMS[_SYNTH_ARMOR].presentation.summary_zh
        self.assertIn(summary, job.db.source_description)
        self.assertIn("月下持杖，藍袍拖地", job.db.source_description)
        self.assertNotIn(
            SYNTH_ITEMS[_SYNTH_WEAPON].presentation.summary_zh,
            job.db.source_description,
        )
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["requested_fields"], ["appearance", "armor", "accessories"])

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_request_without_a_selection_records_the_empty_provenance(self):
        request_gallery_image(self.player)
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(list(jobs[0].db.gallery_requested_fields), [])
        # Nothing selected means neither persona appearance nor equipment.
        for summary in (
            SYNTH_ITEMS[_SYNTH_ARMOR].presentation.summary_zh,
            SYNTH_ITEMS[_SYNTH_WEAPON].presentation.summary_zh,
        ):
            self.assertNotIn(summary, jobs[0].db.source_description)

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_an_invalid_selection_never_reaches_the_queue_or_the_prompt(self):
        with patch("world.art.queue._prompt_digest_or_empty") as digest:
            with patch("world.art.service.description_for") as compose:
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, fields=("armor", "nope"))
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, fields=("armor", "armor"))
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, fields="armor")
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, fields=["armor", 7])
        self.assertEqual(self._gallery_jobs(), [])
        compose.assert_not_called()
        digest.assert_not_called()

    @covers_requirement(
        "art-gallery-prompt-fields::free-form-prompt-text-is-bounded-sanitized-and-appended-verbatim"
    )
    def test_invalid_free_text_never_reaches_the_queue_or_the_prompt(self):
        with patch("world.art.queue._prompt_digest_or_empty") as digest:
            with patch("world.art.service.description_for") as compose:
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, custom_prompt="x" * (CUSTOM_PROMPT_MAX + 1))
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, custom_prompt="a\nb")
                with self.assertRaises(GalleryPromptError):
                    request_gallery_image(self.player, custom_prompt="a\u2028b")
        self.assertEqual(self._gallery_jobs(), [])
        compose.assert_not_called()
        digest.assert_not_called()

    @covers_requirement(
        "art-subject-model::subject-descriptions-are-deterministic-and-exclude-non-physical-truth"
    )
    def test_the_auto_paths_keep_the_explicit_appearance_only_selection(self):
        # The startup-recovery / spawn ensure path.
        with self.captureOnCommitCallbacks(execute=True):
            schedule_portrait_ensure(self.player)
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(list(jobs[0].db.gallery_requested_fields), ["appearance"])
        # The forced staff requeue path.
        jobs[0].delete()
        requeue_gallery_subject(self.subject)
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(list(jobs[0].db.gallery_requested_fields), ["appearance"])
        # Appearance-only reads no equipment even with items worn.
        for summary in (
            SYNTH_ITEMS[_SYNTH_ARMOR].presentation.summary_zh,
            SYNTH_ITEMS[_SYNTH_WEAPON].presentation.summary_zh,
        ):
            self.assertNotIn(summary, jobs[0].db.source_description)

    @covers_requirement(
        "art-gallery-prompt-fields::the-prompt-library-remains-the-sole-source-of-the-composed-template"
    )
    def test_the_selection_changes_the_rendered_prompt_digest(self):
        # Distinct field selections of the same character compose distinct
        # prompts: the digest (rendered prompt pair hash) differs per job.
        request_gallery_image(self.player, fields=("appearance",))
        first = self._gallery_jobs()[0]
        request_gallery_image(self.player, fields=("appearance", "armor"))
        second = [job for job in self._gallery_jobs() if job.pk != first.pk][0]
        self.assertNotEqual(first.db.prompt_digest, second.db.prompt_digest)
