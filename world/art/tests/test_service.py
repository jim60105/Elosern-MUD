"""Tests for the sole-writer art service and its deterministic seams."""

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
from world.art.service import requeue_character_portrait
from world.art.service import prune_gallery_orphans
from world.art.subjects import ArtSubjectError
from world.art.service import (
    art_sync_all,
    ensure_scene_asset,
    request_gallery_image,
    schedule_portrait_ensure,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.items import ITEM_REGISTRY

from tools.spec_traceability import covers_requirement


def _scene(key):
    return ArtSubject(ArtSubjectKind.SCENE, key)


def _valid_binding():
    return {"mask": ["armor"], "snapshot": {"armor": "leather_armor"}}


class ArtServiceTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="service-player")
        self.player.age = 22
        self.player.apparent_age = 22

    def _records(self):
        return {record.db_key: record for record in ArtAssetRecord.objects.all()}

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_ensures_every_registered_subject_on_a_fresh_db(self):
        art_sync_all()
        records = self._records()
        for archetype in SCENE_ARCHETYPE_REGISTRY:
            self.assertIn(f"art:scene:{archetype}", records)
            self.assertIn(
                records[f"art:scene:{archetype}"].db.status,
                (ArtAssetStatus.MISSING, ArtAssetStatus.PENDING),
            )
        for tier in MONSTER_TIER_REGISTRY:
            self.assertIn(f"art:portrait:monster:{tier}", records)
        self.assertEqual(len(records), len(SCENE_ARCHETYPE_REGISTRY) + len(MONSTER_TIER_REGISTRY))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_leaves_pending_in_progress_and_done_records_untouched(self):
        subject = _scene("forest_path")
        ensure(subject, "desc")
        art_sync_all()
        self.assertEqual(len(self._records()), len(SCENE_ARCHETYPE_REGISTRY) + len(MONSTER_TIER_REGISTRY))

    @covers_requirement("art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records")
    def test_startup_sync_consolidates_duplicate_records(self):
        from world.art.queue import _create_record

        subject = _scene("forest_path")
        first = _create_record(subject)
        second = _create_record(subject)
        second.db.status = ArtAssetStatus.DONE
        second.db.output_identity = "scene/forest_path.png"
        art_sync_all()
        records = ArtAssetRecord.objects.filter(db_key=record_key(subject))
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.first().db.status, ArtAssetStatus.DONE)

    @covers_requirement("art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_recovery_requests_a_gallery_job_for_a_missing_named_policy(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        art_sync_all()
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:portrait:character:{self.player.pk}:gen:")
        )
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)
        # The retrofit: no classic fixed-identity record is ever created.
        self.assertNotIn(f"art:portrait:character:{self.player.pk}", self._records())

    @covers_requirement("art-asset-lifecycle::startup-recovery-rescans-explicit-unique-portrait-policies")
    @covers_requirement("art-asset-lifecycle::the-age-check-runs-on-every-lifecycle-path-and-rejects-deterministically-without-a-persisted-marker")
    def test_recovery_skips_an_ineligible_subject_deterministically(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.attributes.remove("age")
        art_sync_all()
        key = f"art:portrait:character:{self.player.pk}"
        self.assertNotIn(key, self._records())
        art_sync_all()
        self.assertNotIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_schedule_portrait_ensure_runs_the_gate_and_enqueues_one_gallery_job(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        key = f"art:portrait:character:{self.player.pk}"
        jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{key}:gen:"))
        self.assertEqual(jobs[0].db.status, ArtAssetStatus.PENDING)
        self.assertNotIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::portrait-character-enqueue-validates-canonical-age-attributes-immediately-before-enqueue")
    def test_rejected_portrait_produces_no_record_and_no_worker_call(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.attributes.remove("age")
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch("world.art.worker._run_and_settle_batch") as worker,
        ):
            schedule_portrait_ensure(self.player)
        # The missing canonical age rejects at schedule time: no on_commit
        # callback is even registered, and no record or worker call is
        # produced.
        self.assertEqual(len(callbacks), 0)
        worker.assert_not_called()
        key = f"art:portrait:character:{self.player.pk}"
        self.assertNotIn(key, self._records())

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_an_art_callback_exception_never_propagates_to_the_owning_workflow(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch(
                "world.art.service._ensure_character_portrait",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(self.player.creation_pending is not None)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_creates_or_leaves_a_record_for_a_validated_archetype(self):
        ensure_scene_asset("forest_path")
        self.assertIn("art:scene:forest_path", self._records())
        ensure_scene_asset("forest_path")
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key="art:scene:forest_path").count(), 1
        )

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_is_a_noop_for_none_or_unresolvable_archetype(self):
        ensure_scene_asset(None)
        ensure_scene_asset("not_a_scene")
        self.assertEqual(self._records(), {})

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_scene_asset_failure_is_bounded_and_never_blocks_the_move(self):
        with patch(
            "world.art.service.queue_ensure",
            side_effect=RuntimeError("art boom"),
        ):
            ensure_scene_asset("forest_path")
        self.assertEqual(self._records(), {})


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

        self.assertTrue(retry_gallery_subject(str(self.player.pk)))
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertNotIn(
            self.classic_key,
            {record.db_key for record in ArtAssetRecord.objects.all()},
        )
        # The in-flight guard suppresses the second attempt honestly.
        self.assertFalse(retry_gallery_subject(str(self.player.pk)))
        self.assertEqual(len(self._gallery_jobs()), 1)
        # A carded subject is left alone too.
        for job in self._gallery_jobs():
            job.db.status = ArtAssetStatus.FAILED
            job.save()
        self._seed_card("a1b2c3d4-0000-4000-8000-000000000002")
        self.assertFalse(retry_gallery_subject(str(self.player.pk)))
        # The spent FAILED job survives; no NEW job was enqueued.
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_requeue_forces_one_card_beyond_the_idempotency_guard(self):
        from world.art.service import requeue_character_portrait

        self._schedule()
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        self.assertEqual(len(cards), 1)
        # Staff force path: an occupied gallery does not suppress the request.
        with patch("world.art.service.log_info"):
            requeue_character_portrait(str(self.player.pk))
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
            from world.art.service import requeue_character_portrait

            with self.assertRaises(ArtSubjectError):
                requeue_character_portrait(str(self.player.pk))
        render.assert_not_called()
        self.assertEqual(self._gallery_jobs(), [])
        self.assertEqual(gallery_api.cards_for(self.subject), [])


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
        super().setUp()
        self.player = create_object(PlayerCharacter, key="composition-player")
        self.player.age = 30
        self.player.apparent_age = 25
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.player.db.equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": "leather_armor",
            "accessories": ["silver_hairpin"],
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
        summary = ITEM_REGISTRY["leather_armor"].presentation.summary_zh
        self.assertIn(summary, job.db.source_description)
        self.assertIn("月下持杖，藍袍拖地", job.db.source_description)
        self.assertNotIn(ITEM_REGISTRY["plain_sword"].presentation.summary_zh,
                         job.db.source_description)
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
            ITEM_REGISTRY["leather_armor"].presentation.summary_zh,
            ITEM_REGISTRY["plain_sword"].presentation.summary_zh,
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
        requeue_character_portrait(str(self.player.pk))
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(list(jobs[0].db.gallery_requested_fields), ["appearance"])
        # Appearance-only reads no equipment even with items worn.
        for summary in (
            ITEM_REGISTRY["leather_armor"].presentation.summary_zh,
            ITEM_REGISTRY["plain_sword"].presentation.summary_zh,
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


class GalleryPruneTests(EvenniaTestCase):
    """The startup prune reclaims orphan files and spent job records only."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.subject = ArtSubject(ArtSubjectKind.CHARACTER, "9001")

    def _write(self, identity: str) -> Path:
        path = self.root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"img")
        return path

    def _card(self, image_id: str, identity: str):
        gallery_api.append_card(
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

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_an_orphan_gallery_file_is_reclaimed_and_referenced_files_survive(self):
        referenced = self._write("gallery/character/9001/11111111-1111-4111-8111-111111111111.png")
        self._card(
            "11111111-1111-4111-8111-111111111111",
            "gallery/character/9001/11111111-1111-4111-8111-111111111111.png",
        )
        outside_gallery = self._write("portrait/character/legacy.png")
        orphan = self._write("gallery/character/9001/deadbeef-1111-4111-8111-111111111111.png")
        result = prune_gallery_orphans()
        self.assertFalse(orphan.exists())
        self.assertTrue(referenced.exists())
        self.assertTrue(outside_gallery.exists())
        self.assertEqual(result["files"], 1)
        # Idempotent: a second pass deletes nothing.
        self.assertEqual(prune_gallery_orphans(), {"files": 0, "records": 0})

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_a_missing_or_unreadable_gallery_tree_never_raises(self):
        # No gallery/ directory at all.
        prune_gallery_orphans()
        tree = self._write("gallery/character/9001/x.png").parent
        with patch("pathlib.Path.rglob", side_effect=OSError("unreadable tree")):
            prune_gallery_orphans()
        self.assertTrue(tree.is_dir())

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_a_failing_deletion_is_bounded_and_a_failed_reference_read_deletes_nothing(self):
        orphan = self._write("gallery/character/9001/deadbeef-1111-4111-8111-111111111111.png")
        # One deletion raising never aborts the sweep and never raises out.
        with patch("pathlib.Path.unlink", side_effect=OSError("busy")):
            result = prune_gallery_orphans()
        self.assertEqual(result["files"], 0)
        self.assertTrue(orphan.exists())
        # Without a readable reference set NOTHING may be deleted — not even
        # orphans: a prune must never delete a file a card references.
        with patch(
            "world.art.gallery.referenced_stored_identities",
            side_effect=RuntimeError("db down"),
        ):
            result = prune_gallery_orphans()
        self.assertEqual(result["files"], 0)
        self.assertTrue(orphan.exists())

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_unclaimable_job_records_are_pruned_while_claimable_jobs_survive(self):
        from world.art.queue import enqueue_gallery_job
        import time

        # A claimable pending job and a lease-expired in_progress job survive.
        pending = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000001",
            binding=None, face_rect=None, requested_fields=[],
        )
        in_flight = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000002",
            binding=None, face_rect=None, requested_fields=[],
        )
        in_flight.db.status = ArtAssetStatus.IN_PROGRESS
        in_flight.db.claimed_at = time.time()
        # An unresolvable-subject job and a terminal-status job never publish.
        broken = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000003",
            binding=None, face_rect=None, requested_fields=[],
        )
        broken.db.subject_key = "bad|key"
        dead = enqueue_gallery_job(
            self.subject, "d", image_id="aaaa0000-0000-4000-8000-000000000004",
            binding=None, face_rect=None, requested_fields=[],
        )
        dead.db.status = ArtAssetStatus.FAILED
        result = prune_gallery_orphans()
        self.assertEqual(result["records"], 2)
        keys = {record.db_key for record in ArtAssetRecord.objects.all()}
        self.assertIn(pending.db_key, keys)
        # A live in-progress job (lease unexpired) is never pruned.
        self.assertIn(in_flight.db_key, keys)
        self.assertEqual(in_flight.db.status, ArtAssetStatus.IN_PROGRESS)
        self.assertNotIn(broken.db_key, keys)
        self.assertNotIn(dead.db_key, keys)

    @covers_requirement(
        "art-gallery-generation::interrupted-gallery-generations-are-reclaimed-at-startup"
    )
    def test_an_in_progress_job_past_its_lease_is_retained_for_reclaim(self):
        from world.art.queue import claim

        job = self._job("bbbb0000-0000-4000-8000-000000000001")
        claimed = claim(10)
        self.assertEqual(len(claimed), 1)
        # Force the lease far past its expiry WITHOUT reclaiming.
        claimed[0].db.claimed_at = 0.0
        claimed[0].save()
        result = prune_gallery_orphans()
        self.assertEqual(result["records"], 0)
        self.assertEqual(job.db.status, ArtAssetStatus.IN_PROGRESS)
        # The shared reclaim (not the prune) returns it to pending.
        from world.art.queue import reclaim_expired_leases

        self.assertEqual(reclaim_expired_leases(0.001), 1)

    def _job(self, image_id):
        from world.art.queue import enqueue_gallery_job

        return enqueue_gallery_job(
            self.subject, "d", image_id=image_id,
            binding=None, face_rect=None, requested_fields=[],
        )


if __name__ == "__main__":
    unittest.main()
