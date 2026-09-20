"""Slice of ``test_service``: AutogenRetrofitTests.
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

class AutogenRetrofitTests(EvenniaTestCase):
    """Every automatic character path is one guarded, unbound gallery request."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="autogen-player")
        self.player.age = 28
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
        self.classic_key = f"art:portrait:character:{self.player.pk}"

    def _gallery_jobs(self):
        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
            # Scoped to THIS subject: startup sync now enqueues monster-tier
            # gallery jobs too (``gallery-monster-autogen``).
            and record.db_key.startswith(f"art:{self.subject.full()}:gen:")
        ]

    def _seed_card(self, image_id):
        identity = f"gallery/character/{self.player.pk}/{image_id}.png"
        (self.root / identity).parent.mkdir(parents=True, exist_ok=True)
        (self.root / identity).write_bytes(b"seeded")
        return gallery_api.append_card(
            self.subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="seed",
        )

    def _drain(self):
        from world.art.worker import drain_synchronous

        with patch(
            "world.art.worker.resolve_sd_client", return_value=FakeSDWebUIClient()
        ):
            # Startup sync enqueues the classic registry subjects too; drain
            # past them so the gallery job is always claimed.
            drain_synchronous(200)

    def _schedule(self):
        with self.captureOnCommitCallbacks(execute=True):
            schedule_portrait_ensure(self.player)

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_a_committed_path_drains_to_exactly_one_unbound_default_card(self):
        self._schedule()
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertNotIn(self.classic_key,
                         {record.db_key for record in ArtAssetRecord.objects.all()})
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        self.assertEqual(len(cards), 1)
        self.assertIsNone(cards[0]["binding"])
        self.assertEqual(cards[0]["face_rect"], dict(gallery_api.DEFAULT_FACE_RECT))
        record = gallery_api.record_for(self.subject)
        self.assertEqual(record.db.default_image_id, cards[0]["image_id"])
        self.assertTrue(
            (self.root / cards[0]["stored_identity"]).exists()
        )
        # No classic fixed-identity record was ever created on any path.
        self.assertNotIn(
            self.classic_key,
            {record.db_key for record in ArtAssetRecord.objects.all()},
        )

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_repeated_recovery_after_a_drain_appends_nothing(self):
        art_sync_all()
        self.assertEqual(len(self._gallery_jobs()), 1)
        self._drain()
        self.assertEqual(len(gallery_api.cards_for(self.subject)), 1)
        # Consecutive restarts: recovery sees the occupied gallery and stops.
        art_sync_all()
        art_sync_all()
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(len(gallery_api.cards_for(self.subject)), 1)

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_a_seed_synced_subject_is_never_auto_generated(self):
        self._seed_card("a1b2c3d4-0000-4000-8000-000000000001")
        art_sync_all()
        self._schedule()
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(len(gallery_api.cards_for(self.subject)), 1)

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_an_in_flight_job_suppresses_a_second_request(self):
        self._schedule()
        first = self._gallery_jobs()
        self.assertEqual(len(first), 1)
        # Recovery and a second schedule both see the pending job.
        art_sync_all()
        self._schedule()
        self.assertEqual(len(self._gallery_jobs()), 1)
        # A spent (terminal, not yet pruned) job never blocks a later request.
        job = self._gallery_jobs()[0]
        job.db.status = ArtAssetStatus.FAILED
        job.save()
        self._schedule()
        self.assertEqual(len(self._gallery_jobs()), 2)

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_the_failed_card_path_still_asks_again_next_time(self):
        # A failed generation leaves no card and no in-flight job, so the
        # next automatic pass is allowed to request again.
        self._schedule()
        job = self._gallery_jobs()[0]
        job.db.status = ArtAssetStatus.FAILED
        job.save()
        self.assertEqual(gallery_api.cards_for(self.subject), [])
        art_sync_all()
        self.assertEqual(len(self._gallery_jobs()), 2)

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_a_failing_request_never_rolls_back_gameplay_and_logs_bounded(self):
        with (
            patch(
                "world.art.service.request_gallery_image",
                side_effect=RuntimeError("gallery boom"),
            ),
            patch("world.art.service.log_warn") as warn,
        ):
            # Nested INSIDE the patches: on_commit callbacks run when the
            # capture block exits, while the failing seam is still patched.
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(self._gallery_jobs(), [])
        self.assertTrue(
            any(
                call.args and call.args[0] == "art_portrait_ensure_failed"
                for call in warn.call_args_list
            )
        )

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_retry_reports_truthfully_through_the_guard(self):
        from world.art.service import retry_gallery_subject

        self.assertTrue(retry_gallery_subject(self.subject))
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertNotIn(
            self.classic_key,
            {record.db_key for record in ArtAssetRecord.objects.all()},
        )
        # The in-flight guard suppresses the second attempt honestly.
        self.assertFalse(retry_gallery_subject(self.subject))
        self.assertEqual(len(self._gallery_jobs()), 1)
        # A carded subject is left alone too.
        for job in self._gallery_jobs():
            job.db.status = ArtAssetStatus.FAILED
            job.save()
        self._seed_card("a1b2c3d4-0000-4000-8000-000000000002")
        self.assertFalse(retry_gallery_subject(self.subject))
        # The spent FAILED job survives; no NEW job was enqueued.
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_requeue_forces_one_card_beyond_the_idempotency_guard(self):
        from world.art.service import requeue_gallery_subject

        self._schedule()
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        self.assertEqual(len(cards), 1)
        # Staff force path: an occupied gallery does not suppress the request.
        with patch("world.art.service.log_info"):
            requeue_gallery_subject(self.subject)
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        # The existing card is untouched until the new card is appended.
        self.assertEqual(gallery_api.cards_for(self.subject), cards)
        self._drain()
        after = gallery_api.cards_for(self.subject)
        self.assertEqual(len(after), 2)
        self.assertEqual(after[0], cards[0])
        self.assertIsNone(after[1]["binding"])
        self.assertEqual(after[1]["face_rect"], dict(gallery_api.DEFAULT_FACE_RECT))
        # The default stays the first card.
        self.assertEqual(
            gallery_api.record_for(self.subject).db.default_image_id,
            cards[0]["image_id"],
        )

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_an_ineligible_subject_still_rejects_before_anything(self):
        self.player.attributes.remove("age")
        with patch("world.art.sd_worker.render_prompt_pair") as render:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                schedule_portrait_ensure(self.player)
            self.assertEqual(len(callbacks), 0)
            from world.art.service import requeue_gallery_subject

            with self.assertRaises(ArtSubjectError):
                requeue_gallery_subject(self.subject)
        render.assert_not_called()
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(gallery_api.cards_for(self.subject), [])
