"""Slice of ``test_service``: GalleryPruneTests.
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
    make_monster_species,
    synthetic_registries,
)

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
            image_size={"width": 1000, "height": 1000},
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
        self.assertEqual(
            prune_gallery_orphans(),
            {"files": 0, "records": 0, "records_unregistered": 0},
        )

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


_GONE = "t_prune_gone"
_KEPT = "t_prune_kept"
_GONE_CARD = "cccc0000-0000-4000-8000-000000000001"
_GONE_JOB = "cccc0000-0000-4000-8000-000000000002"
_KEPT_CARD = "cccc0000-0000-4000-8000-000000000003"


def _species_scope(*keys):
    """A monster-species scope registering exactly the kit species plus ``keys``."""
    return synthetic_registries(
        "monster_species",
        extra={"monster_species": {key: make_monster_species(key) for key in keys}},
    )


class UnregisteredMonsterPruneTests(EvenniaTestCase):
    """The startup prune reclaims stored art of monster keys no registry holds."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.gone = ArtSubject(ArtSubjectKind.MONSTER, _GONE)
        self.kept = ArtSubject(ArtSubjectKind.MONSTER, _KEPT)
        # Seeded while both keys are registered: the stored state of a species
        # that a later registry edit removes.
        with _species_scope(_GONE, _KEPT):
            from world.art.queue import enqueue_gallery_job

            self.gone_card = self._card(self.gone, _GONE_CARD)
            self.kept_card = self._card(self.kept, _KEPT_CARD)
            self.gone_job = enqueue_gallery_job(
                self.gone, "d", image_id=_GONE_JOB,
                binding=None, face_rect=None, requested_fields=[],
            )
            self.gone_classic = ensure(self.gone, "d")
            self.gone_output = self._write(f"portrait/monster/{_GONE}.png")
            self.gone_prior = self._write(f"portrait/monster/{_GONE}-prior.png")
            self.gone_classic.db.status = ArtAssetStatus.DONE
            self.gone_classic.db.output_identity = f"portrait/monster/{_GONE}.png"
            self.gone_classic.db.prior_output_identity = f"portrait/monster/{_GONE}-prior.png"
        self.gone_files = (self.gone_card, self.gone_output, self.gone_prior)

    def _write(self, identity: str) -> Path:
        path = self.root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"img")
        return path

    def _card(self, subject, image_id) -> Path:
        identity = f"gallery/monster/{subject.key}/{image_id}.png"
        path = self._write(identity)
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
            image_size={"width": 1000, "height": 1000},
        )
        return path

    def _records_naming(self, key):
        return sorted(
            [
                *(
                    record.db_key
                    for record in ArtAssetRecord.objects.all()
                    if record.db.subject_key == key
                ),
                *(
                    record.db_key
                    for record in gallery_api.GalleryRecord.objects.all()
                    if record.db.subject_key == key
                ),
            ]
        )

    def test_an_unregistered_species_leaves_nothing_behind(self):
        self.assertEqual(len(self._records_naming(_GONE)), 3)
        with _species_scope(_KEPT):
            result = prune_gallery_orphans()
        self.assertEqual(self._records_naming(_GONE), [])
        for path in self.gone_files:
            with self.subTest(path=path.name):
                self.assertFalse(path.exists())
        self.assertEqual(result["records_unregistered"], 2)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["files"], 3)

    def test_a_registered_species_is_untouched(self):
        before = gallery_api.record_for(self.kept)
        cards_before = list(before.db.cards)
        default_before = before.db.default_image_id
        with _species_scope(_KEPT):
            prune_gallery_orphans()
        after = gallery_api.record_for(self.kept)
        self.assertIsNotNone(after)
        self.assertEqual(after.pk, before.pk)
        self.assertEqual(list(after.db.cards), cards_before)
        self.assertEqual(after.db.default_image_id, default_before)
        self.assertTrue(self.kept_card.is_file())

    def test_the_prune_stays_idempotent(self):
        with _species_scope(_KEPT):
            prune_gallery_orphans()
            self.assertEqual(
                prune_gallery_orphans(),
                {"files": 0, "records": 0, "records_unregistered": 0},
            )
        self.assertTrue(self.kept_card.is_file())

    def test_an_empty_or_failing_registry_deletes_nothing(self):
        cases = (
            ("empty", {"return_value": {}}),
            ("failing", {"side_effect": RuntimeError("registry down")}),
        )
        for label, behaviour in cases:
            with self.subTest(registry=label):
                with patch("world.art.service.get_monster_visual_registry", **behaviour):
                    result = prune_gallery_orphans()
                self.assertEqual(result["records_unregistered"], 0)
                self.assertEqual(len(self._records_naming(_GONE)), 3)
                for path in self.gone_files:
                    self.assertTrue(path.exists())

    def test_an_unreadable_reference_set_keeps_classic_records_and_files(self):
        with _species_scope(_KEPT), patch(
            "world.art.gallery.referenced_stored_identities",
            side_effect=RuntimeError("db down"),
        ):
            prune_gallery_orphans()
        # The gallery record and the job record are still reclaimed; the
        # classic record waits for a pass that can prove its files unreferenced.
        self.assertEqual(self._records_naming(_GONE), [self.gone_classic.db_key])
        self.assertTrue(self.gone_output.exists())
        self.assertTrue(self.gone_prior.exists())

    def test_a_failed_classic_unlink_keeps_the_record_for_the_next_pass(self):
        real_unlink = Path.unlink

        def failing_for_classic(path, *args, **kwargs):
            if path.name.startswith(_GONE) and "portrait" in path.parts:
                raise OSError("busy")
            return real_unlink(path, *args, **kwargs)

        with _species_scope(_KEPT):
            with patch("pathlib.Path.unlink", failing_for_classic):
                prune_gallery_orphans()
            # The record survives so its files stay reachable...
            self.assertEqual(self._records_naming(_GONE), [self.gone_classic.db_key])
            self.assertTrue(self.gone_output.exists())
            # ...and the next healthy pass reclaims both.
            prune_gallery_orphans()
        self.assertEqual(self._records_naming(_GONE), [])
        self.assertFalse(self.gone_output.exists())
        self.assertFalse(self.gone_prior.exists())
