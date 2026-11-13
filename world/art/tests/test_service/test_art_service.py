"""Slice of ``test_service``: ArtServiceTests.
"""
import io
from unittest.mock import patch
import unittest
from contextlib import contextmanager
import tempfile
from pathlib import Path
from django.db import transaction
from django.test import override_settings
from PIL import Image
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
from world.lore.monster_visuals import get_monster_visual_registry
from tools.spec_traceability import covers_requirement
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_ITEMS,
    synthetic_registries,
)

from ._support import (
    open_synthetic_scope,
    _SYNTH_SCENE,
    _scene,
)

class ArtServiceTests(EvenniaTestCase):
    def setUp(self):
        # The startup-sync coverage tests below assert over the REGISTERED
        # subject set, which is exactly what startup synchronization reads:
        # run the whole class against the kit catalogs so the loops iterate
        # SYNTH_* rows instead of shipped content.
        open_synthetic_scope(self, "archetypes", "monster_species")
        super().setUp()
        self.player = create_object(PlayerCharacter, key="service-player")
        self.player.age = 22
        self.player.apparent_age = 22

    def _records(self):
        return {record.db_key: record for record in ArtAssetRecord.objects.all()}

    def _scene_job_keys(self, archetype):
        return sorted(
            record.db_key
            for record in ArtAssetRecord.objects.all()
            if record.db_key.startswith(f"art:scene:{archetype}:gen:")
        )

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_startup_sync_requests_one_gallery_card_per_registered_scene(self):
        art_sync_all()
        records = self._records()
        for archetype in SYNTH_ARCHETYPES:
            with self.subTest(archetype=archetype):
                # The scene kind is gallery-bearing: no classic subject record
                # and exactly one gallery request on a fresh database.
                self.assertNotIn(f"art:scene:{archetype}", records)
                job_keys = self._scene_job_keys(archetype)
                self.assertEqual(len(job_keys), 1)
                self.assertEqual(
                    records[job_keys[0]].db.status, ArtAssetStatus.PENDING
                )
        # ``gallery-monster-autogen``: every registered VISUAL species gets a
        # gallery request, never a classic fixed-identity record.
        visual_registry = get_monster_visual_registry()
        for visual_key in visual_registry:
            self.assertNotIn(f"art:portrait:monster:{visual_key}", records)
        classic = [
            key for key, record in records.items() if not str(record.db.gallery_image_id or "")
        ]
        self.assertEqual(classic, [])
        monster_jobs = [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
            and record.db_key.startswith("art:portrait:monster:")
        ]
        self.assertEqual(len(monster_jobs), len(visual_registry))

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_a_carded_scene_requests_nothing(self):
        subject = scene_subject_for(_SYNTH_SCENE)
        card = gallery_api.append_card(
            subject,
            image_id="dddd0000-0000-4000-8000-000000000001",
            stored_identity=(
                f"gallery/scene/{_SYNTH_SCENE}/dddd0000-0000-4000-8000-000000000001.png"
            ),
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            image_size={"width": 16, "height": 9},
            source="seed",
        )
        art_sync_all()
        self.assertEqual(self._scene_job_keys(_SYNTH_SCENE), [])
        self.assertEqual(gallery_api.cards_for(subject), [card])

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_a_scene_emptied_by_deletion_requests_nothing(self):
        subject = scene_subject_for(_SYNTH_SCENE)
        identity = (
            f"gallery/scene/{_SYNTH_SCENE}/dddd0000-0000-4000-8000-000000000002.png"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            with override_settings(ART_STORE_ROOT=tempdir):
                target = Path(tempdir) / identity
                target.parent.mkdir(parents=True)
                target.write_bytes(b"card")
                gallery_api.append_card(
                    subject,
                    image_id="dddd0000-0000-4000-8000-000000000002",
                    stored_identity=identity,
                    prompt=None,
                    seed=None,
                    checkpoint=None,
                    requested_fields=[],
                    binding=None,
                    image_size={"width": 16, "height": 9},
                    source="seed",
                )
                gallery_api.remove_card(subject, "dddd0000-0000-4000-8000-000000000002")
                self.assertEqual(gallery_api.cards_for(subject), [])
                self.assertIsNotNone(gallery_api.record_for(subject))
                art_sync_all()
                ensure_scene_asset(_SYNTH_SCENE)
        self.assertEqual(self._scene_job_keys(_SYNTH_SCENE), [])

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_a_failed_first_scene_generation_is_retried_at_startup(self):
        subject = scene_subject_for(_SYNTH_SCENE)
        gallery_api.record_error(subject, "sd_connection_error")
        art_sync_all()
        self.assertEqual(len(self._scene_job_keys(_SYNTH_SCENE)), 1)

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_a_pending_scene_job_is_left_untouched(self):
        ensure_scene_asset(_SYNTH_SCENE)
        job_keys = self._scene_job_keys(_SYNTH_SCENE)
        self.assertEqual(len(job_keys), 1)
        art_sync_all()
        self.assertEqual(self._scene_job_keys(_SYNTH_SCENE), job_keys)
        self.assertEqual(
            self._records()[job_keys[0]].db.status, ArtAssetStatus.PENDING
        )

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-requests-gallery-art-for-every-registered-scene-and-species"
    )
    def test_an_operator_scene_image_still_requests_generation(self):
        from world.art import official

        official.reset_catalog()
        self.addCleanup(official.reset_catalog)
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "official"
            folder = root / "scene" / _SYNTH_SCENE
            folder.mkdir(parents=True)
            buffer = io.BytesIO()
            Image.new("RGB", (1536, 864)).save(buffer, format="PNG")
            (folder / "operator.png").write_bytes(buffer.getvalue())
            with (
                override_settings(ART_OFFICIAL_ROOT=str(root)),
                patch.object(
                    official,
                    "_registered_scene_keys",
                    return_value=frozenset({_SYNTH_SCENE}),
                ),
            ):
                self.assertEqual(official.load_catalog()["images"], 1)
                art_sync_all()
        self.assertEqual(len(self._scene_job_keys(_SYNTH_SCENE)), 1)

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
            and record.db_key.startswith(f"art:portrait:character:{self.player.pk}:gen:")
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
                "world.art.service._ensure_gallery_subject",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            schedule_portrait_ensure(self.player)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(self.player.creation_pending is not None)

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_requests_one_gallery_card_for_a_validated_archetype(self):
        ensure_scene_asset(_SYNTH_SCENE)
        job_keys = self._scene_job_keys(_SYNTH_SCENE)
        self.assertEqual(len(job_keys), 1)
        ensure_scene_asset(_SYNTH_SCENE)
        self.assertEqual(self._scene_job_keys(_SYNTH_SCENE), job_keys)
        self.assertNotIn(f"art:scene:{_SYNTH_SCENE}", self._records())

    @covers_requirement("art-asset-lifecycle::successful-room-entry-ensures-the-scene-asset-for-a-validated-archetype")
    def test_ensure_scene_asset_is_a_noop_for_none_or_unresolvable_archetype(self):
        ensure_scene_asset(None)
        ensure_scene_asset("not_a_scene")
        self.assertEqual(self._records(), {})

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_scene_asset_failure_is_bounded_and_never_blocks_the_move(self):
        with patch(
            "world.art.service._ensure_scene_gallery_subject",
            side_effect=RuntimeError("art boom"),
        ):
            ensure_scene_asset(_SYNTH_SCENE)
        self.assertEqual(self._records(), {})
