"""Gallery-only cutover integration: one carrier, one publication path.

Deterministic synthetic subjects, temp roots and an injected image client; no
shipped artwork or copy is read.
"""

import json
import tempfile
import uuid
from pathlib import Path

from django.test import Client, override_settings
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from world.art import gallery as gallery_api
from world.art import official
from world.art import scene_definitions
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.queue import (
    claim,
    enqueue_gallery_job,
    gallery_record_key,
    reclaim_expired_leases,
    settle_gallery_failed,
    settle_gallery_generated,
)
from world.art.store import GalleryJobRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.art.worker import _write_temp, drain_synchronous, output_identity_for
from world.tests.synthetic_data import SYNTH_MONSTER_SPECIES, synthetic_registries


def _png(width=4, height=4) -> bytes:
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


class GalleryOnlyCutoverTests(EvenniaTestCase):
    def setUp(self):
        scope = synthetic_registries("monster_species")
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name) / "store"
        self.root.mkdir()
        self.official_root = Path(self.tempdir.name) / "official"
        self.settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_OFFICIAL_ROOT=str(self.official_root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        official.reset_catalog()
        self.addCleanup(official.reset_catalog)
        scene_definitions.reset_bundled_scenes()
        self.addCleanup(scene_definitions.reset_bundled_scenes)

    # -- harness ----------------------------------------------------------
    @staticmethod
    def _character(key="9001"):
        return ArtSubject(ArtSubjectKind.CHARACTER, key)

    @staticmethod
    def _monster():
        return ArtSubject(
            ArtSubjectKind.MONSTER, sorted(SYNTH_MONSTER_SPECIES)[0]
        )

    def _enqueue(self, subject, image_id=None, description="desc"):
        return enqueue_gallery_job(
            subject,
            description,
            image_id=image_id or str(uuid.uuid4()),
            binding=None,
            face_rect=None,
            requested_fields=[],
        )

    def _drain(self, limit=10):
        from unittest.mock import patch

        with patch(
            "world.art.worker.resolve_sd_client", return_value=FakeSDWebUIClient()
        ):
            drain_synchronous(limit)

    def _card(self, subject, image_id=None):
        image_id = image_id or str(uuid.uuid4())
        identity = (
            f"gallery/{subject.kind.value.split(':')[-1]}/{subject.key}/"
            f"{image_id}.png"
        )
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_png())
        gallery_api.append_card(
            subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="generated",
            image_size={"width": 4, "height": 4},
        )
        return image_id, identity

    # -- cutover ----------------------------------------------------------
    def test_enqueue_claim_settle_appends_one_card_and_deletes_the_spent_job(self):
        subject = self._character()
        job = self._enqueue(subject)
        image_id = job.db.gallery_image_id
        self._drain()
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=job.db_key).exists())
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [image_id])
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=job.db_key).exists())

    def test_capped_successful_replacement_commits_new_card_then_drops_displaced_file(self):
        subject = self._monster()
        old_id, old_identity = self._card(subject)
        new_id = str(uuid.uuid4())
        job = self._enqueue(subject, new_id)
        self._drain()
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [new_id])
        self.assertTrue((self.root / cards[0]["stored_identity"]).is_file())
        self.assertFalse((self.root / old_identity).exists())
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=job.db_key).exists())

    def test_capped_failed_replacement_keeps_prior_card_bytes_and_records_the_error(self):
        subject = self._monster()
        old_id, old_identity = self._card(subject)
        prior = (self.root / old_identity).read_bytes()
        job = self._enqueue(subject, str(uuid.uuid4()))
        from unittest.mock import patch

        failing = FakeSDWebUIClient()
        from world.art.sd_worker import SDError

        failing.fail_every_call(SDError("sd_connection_error", "offline"))
        with patch("world.art.worker.resolve_sd_client", return_value=failing):
            drain_synchronous(10)
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [old_id])
        self.assertEqual((self.root / old_identity).read_bytes(), prior)
        self.assertEqual(
            gallery_api.record_for(subject).db.last_error_code,
            "sd_connection_error",
        )
        self.assertFalse(GalleryJobRecord.objects.filter(db_key=job.db_key).exists())

    def test_stale_success_after_reclaim_changes_nothing_and_cleans_its_temp(self):
        subject = self._character()
        job = self._enqueue(subject)
        claimed = claim(10)[0]
        token = str(claimed.db.generation_token)
        reclaim_expired_leases(0.0)
        identity = output_identity_for(job)
        tmp_path = _write_temp(identity, _png(1, 1))
        settled = settle_gallery_generated(
            job.db_key,
            generation_token=token,
            output_identity=identity,
            tmp_path=tmp_path,
            prompt={"positive": "p", "negative": "n"},
            seed=None,
            checkpoint=None,
        )
        self.assertIsNone(settled)
        self.assertFalse(Path(tmp_path).exists())
        self.assertEqual(gallery_api.cards_for(subject), [])
        self.assertIsNotNone(GalleryJobRecord.objects.filter(db_key=job.db_key).first())

    def test_stale_failure_after_reclaim_records_no_error(self):
        subject = self._character()
        job = self._enqueue(subject)
        claimed = claim(10)[0]
        token = str(claimed.db.generation_token)
        reclaim_expired_leases(0.0)
        self.assertIsNone(
            settle_gallery_failed(job.db_key, generation_token=token, error="stale")
        )
        self.assertIsNone(gallery_api.record_for(subject))
        self.assertEqual(GalleryJobRecord.objects.filter(db_key=job.db_key).count(), 1)

    def test_generation_state_derives_only_from_live_jobs_errors_and_cards(self):
        from world.art import descriptors
        from world.art.presenter import describe_portrait

        subject = self._character()
        self.assertEqual(
            describe_portrait(subject)["generation_state"],
            descriptors.GENERATION_MISSING,
        )
        job = self._enqueue(subject)
        self.assertEqual(
            describe_portrait(subject)["generation_state"],
            descriptors.GENERATION_PENDING,
        )
        claimed = claim(10)[0]
        settle_gallery_failed(
            job.db_key,
            generation_token=str(claimed.db.generation_token),
            error="sd_timeout",
        )
        self.assertEqual(
            describe_portrait(subject)["generation_state"],
            descriptors.GENERATION_FAILED,
        )
        self._card(subject)
        self.assertEqual(
            describe_portrait(subject)["generation_state"],
            descriptors.GENERATION_FAILED,
        )
        gallery_api.clear_error(subject)
        self.assertEqual(
            describe_portrait(subject)["generation_state"],
            descriptors.GENERATION_DONE,
        )

    # -- media ------------------------------------------------------------
    def test_former_fixed_routes_are_absent_and_independent_routes_survive(self):
        for identity in (
            "scene/t_synth_fixed.png",
            "portrait/character/9001.png",
            "portrait/monster/t_synth_monster.png",
        ):
            target = self.root / identity
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(_png())
            self.assertEqual(Client().get(f"/art/{identity}").status_code, 404)

        subject = self._character()
        _image_id, gallery_identity = self._card(subject)
        response = Client().get(f"/art/{gallery_identity}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

        # A committed bundled scene identity survives its own admission rules.
        scene_definitions.load_bundled_scene_catalog()
        key = sorted(scene_definitions.SCENE_ART_KEYS)[0]
        bundled_url = scene_definitions.current_bundled_scenes().url_for(key)
        self.assertIsNotNone(bundled_url)
        self.assertEqual(
            Client().get(bundled_url if bundled_url.startswith("/") else f"/{bundled_url}").status_code,
            200,
        )

        # A default fallback identity survives from the fixed defaults root.
        static_root = Path(self.tempdir.name) / "static"
        defaults = static_root / "art" / "defaults"
        defaults.mkdir(parents=True)
        (defaults / "man.webp").write_bytes(b"fallback")
        with override_settings(STATICFILES_DIRS=[str(static_root)]):
            self.assertEqual(Client().get("/art/defaults/man.webp").status_code, 200)

    def test_an_admitted_official_identity_survives_gallery_retirement(self):
        folder = self.official_root / "preset" / "t_synth_preset"
        folder.mkdir(parents=True)
        (folder / "a.png").write_bytes(_png())
        (folder / "manifest.json").write_text(
            json.dumps({"default": "a.png"}), encoding="utf-8"
        )
        from unittest.mock import patch

        with patch.object(
            official, "_registered_preset_keys", return_value=frozenset({"t_synth_preset"})
        ):
            official.load_catalog()
            identity = "preset/t_synth_preset/a.png"
            url = official.current_catalog().url_for(identity)
            self.assertIsNotNone(url)
            self.assertEqual(
                Client().get(url if url.startswith("/") else f"/{url}").status_code,
                200,
            )
