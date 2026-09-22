"""Slice of ``test_service``: MonsterGalleryGenerationTests, MonsterStartupSyncTests.
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
    _SYNTH_SCENES,
    _SYNTH_TIERS,
    _SYNTH_ARMOR,
)

class MonsterGalleryGenerationTests(EvenniaTestCase):
    """The request seam serves the monster kind from its declaration alone.

    Change ``gallery-monster-generation``: the seam is kind-driven, so the
    monster path proves the DECLARATIONS work — no age attribute is ever
    read, the description is the registry text, an argument naming an
    undeclared capability is a typed rejection, and the settled card obeys
    the declared one-card cap with empty provenance.
    """

    def setUp(self):
        # The seam resolves the monster kind through the tier catalog and
        # composes its registry-driven description; run against kit tiers.
        open_synthetic_scope(self, "monster_tiers")
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.tier = _SYNTH_TIERS[0]
        self.subject = monster_subject_for(self.tier)

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
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_a_monster_subject_queues_one_job_with_no_age_read_and_registry_text(self):
        description = "a monster description"
        with (
            patch("world.art.service.character_ages") as ages,
            patch(
                "world.art.service.description_for", return_value=description
            ) as compose,
        ):
            image_id = request_gallery_image(self.subject)
        # The age precondition is NOT declared for this kind: never read.
        ages.assert_not_called()
        compose.assert_called_once_with(
            self.subject,
            entity=None,
            apparent_age=None,
            fields=None,
            custom_prompt="",
        )
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(
            job.db_key, f"art:portrait:monster:{self.tier}:gen:{image_id}"
        )
        self.assertEqual(job.db.status, ArtAssetStatus.PENDING)
        self.assertIsNone(job.db.gallery_binding or None)
        self.assertEqual(job.db.source_description, description)
        self.assertEqual(list(job.db.gallery_requested_fields), [])
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        self.assertEqual([card["image_id"] for card in cards], [image_id])

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_a_scene_subject_is_refused_at_the_seam(self):
        # Any well-formed scene subject is refused by kind; the key needs no
        # registration for the seam's kind-declaration check.
        scene = ArtSubject(ArtSubjectKind.SCENE, "t_synth_scene")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(scene)
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_undeclared_capability_is_rejected_never_ignored(self):
        # Each argument naming a capability the monster declaration lacks is
        # a typed error naming that capability — before any render or write.
        # The binding snapshot key is arbitrary: the capability is refused by
        # the kind's declaration before any snapshot validation runs.
        cases = (
            ({"fields": ("appearance",)}, "field selection"),
            ({"custom_prompt": "月光下的低階怪物"}, "free-text"),
            (
                {"binding": {"mask": ["armor"], "snapshot": {"armor": _SYNTH_ARMOR}}},
                "binding",
            ),
        )
        for kwargs, capability_name in cases:
            with self.subTest(**kwargs):
                with patch("world.art.sd_worker.render_prompt_pair") as render:
                    with self.assertRaises(ValueError) as caught:
                        request_gallery_image(self.subject, **kwargs)
                self.assertIn(capability_name, str(caught.exception))
                render.assert_not_called()
        # Total rejection: nothing was written for any refused argument.
        self.assertEqual(self._gallery_jobs(), [])
        self.assertIsNone(gallery_api.record_for(self.subject))

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_an_unregistered_monster_key_is_rejected_before_any_write(self):
        raw = ArtSubject(ArtSubjectKind.MONSTER, "not_a_tier")
        with self.assertRaises(ArtSubjectError):
            request_gallery_image(raw)
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_whitespace_only_text_is_the_legal_no_op_for_a_kind_without_free_text(self):
        # Established prompt semantics: text normalizing to nothing carries
        # nothing the kind could lose, so it is accepted as the no-op the
        # validator already defines — not a capability violation.
        image_id = request_gallery_image(self.subject, custom_prompt="   ")
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].db.gallery_image_id, image_id)
        self.assertEqual(list(jobs[0].db.gallery_requested_fields), [])
        self.assertNotIn("月光", jobs[0].db.source_description)

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_retry_keeps_the_error_while_a_monster_job_is_in_flight(self):
        # The moot clear is ONLY for the card-present decline: an in-flight
        # monster job keeps the recorded error, exactly as for a character.
        from world.art.service import retry_gallery_subject

        request_gallery_image(self.subject)  # pending job, in flight
        gallery_api.record_error(self.subject, "sd_connection_error")
        self.assertFalse(retry_gallery_subject(self.subject))
        self.assertEqual(len(self._gallery_jobs()), 1)  # nothing new enqueued
        state = gallery_api.record_for(self.subject)
        self.assertEqual(state.db.last_error_code, "sd_connection_error")

    @covers_requirement(
        "art-gallery-generation::one-validated-service-seam-requests-every-gallery-image"
    )
    def test_a_character_key_colliding_with_a_monster_tier_never_crosses_kinds(self):
        # A named character may LEGALLY carry the same stable key text as a
        # registered monster tier. Resolution is through the subject's own
        # kind producer, so re-driving either subject can only ever touch its
        # own kind's job — never the identically-named other subject.
        from evennia.utils.create import create_object

        from typeclasses.characters import PlayerCharacter

        from world.art.service import retry_gallery_subject

        collision = self.tier
        character = create_object(PlayerCharacter, key="collision-host")
        character.db.age = 30
        character.db.apparent_age = 30
        character.db.portrait_policy = {"mode": "named", "stable_key": collision}
        monster_subject = monster_subject_for(collision)
        character_subject = ArtSubject(ArtSubjectKind.CHARACTER, collision)

        with patch("world.art.service.log_info"):
            self.assertTrue(retry_gallery_subject(monster_subject))
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(
            jobs[0].db_key.startswith(f"art:{monster_subject.full()}:gen:")
        )
        # Re-driving the colliding CHARACTER subject resolves to the living
        # character, producing a character-kind job, never a second monster job.
        with patch("world.art.service.log_info"):
            self.assertTrue(retry_gallery_subject(character_subject))
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 2)
        self.assertTrue(
            any(
                job.db_key.startswith(f"art:{character_subject.full()}:gen:")
                for job in jobs
            )
        )
        self.assertEqual(
            sum(
                1
                for job in jobs
                if job.db_key.startswith(f"art:{monster_subject.full()}:gen:")
            ),
            1,
        )


    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_monster_card_settles_unbound_default_with_empty_provenance(self):
        image_id = request_gallery_image(self.subject)
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        # Exactly one card, the shared default rectangle, unbound, and default.
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card["image_id"], image_id)
        self.assertIsNone(card["binding"])
        self.assertEqual(card["face_rect"], dict(gallery_api.DEFAULT_FACE_RECT))
        self.assertEqual(card["requested_fields"], [])
        self.assertEqual(
            gallery_api.record_for(self.subject).db.default_image_id, image_id
        )
        # The file lives under the monster kind directory.
        self.assertTrue(card["stored_identity"].startswith(f"gallery/monster/{self.tier}/"))
        self.assertTrue((self.root / card["stored_identity"]).exists())

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_second_monster_card_replaces_the_first_under_the_cap(self):
        first = request_gallery_image(self.subject)
        self._drain()
        second = request_gallery_image(self.subject)
        self._drain()
        cards = gallery_api.cards_for(self.subject)
        # The declared maximum of one card is honored: replaced, not appended.
        self.assertEqual([card["image_id"] for card in cards], [second])
        self.assertNotEqual(first, second)
        self.assertEqual(
            gallery_api.record_for(self.subject).db.default_image_id, second
        )

class MonsterStartupSyncTests(EvenniaTestCase):
    """Startup synchronization routes every monster tier through the gallery.

    Change ``gallery-monster-autogen``: the tier loop shares ONE guarded
    helper with every character path, the classic generic-monster record is
    retired from production, every failure is bounded per tier, and the
    startup step order (prune → seed → sync) guarantees a seed card occupies
    the gallery before the automatic pass reads it.
    """

    def setUp(self):
        # Startup synchronization loops the registered tier/scene sets; run
        # against the kit catalogs so the tier loop iterates SYNTH rows.
        open_synthetic_scope(self, "archetypes", "monster_tiers")
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name).resolve()
        self.seed_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.seed_dir.cleanup)
        self.seed_root = Path(self.seed_dir.name).resolve()
        self.art_settings = override_settings(
            ART_STORE_ROOT=str(self.root),
            ART_SEED_ROOT=str(self.seed_root),
            ART_SD_CLIENT="world.art.fake_sd_client.FakeSDWebUIClient",
        )
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)
        self.tiers = _SYNTH_TIERS

    def _job_keys(self):
        return sorted(
            record.db_key
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        )

    def _monster_job_keys(self, tier):
        return [
            key
            for key in self._job_keys()
            if key.startswith(f"art:portrait:monster:{tier}:gen:")
        ]

    def _classic_keys(self):
        return sorted(
            record.db_key
            for record in ArtAssetRecord.objects.all()
            if not str(record.db.gallery_image_id or "")
        )

    def _drain(self):
        from world.art.worker import drain_synchronous

        with patch(
            "world.art.worker.resolve_sd_client", return_value=FakeSDWebUIClient()
        ):
            # Drain past the scene classic jobs too so every gallery job is claimed.
            drain_synchronous(200)

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records"
    )
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_a_fresh_startup_gives_each_tier_one_gallery_request_and_drains_to_one_card(self):
        # The monster kind declares NO age precondition: no age attribute is
        # ever read on this path.
        with patch("world.art.service.character_ages") as ages:
            art_sync_all()
        ages.assert_not_called()
        for tier in self.tiers:
            self.assertEqual(len(self._monster_job_keys(tier)), 1)
        # No classic monster record was ever written; scenes keep theirs.
        classic = self._classic_keys()
        self.assertEqual(
            classic, sorted(f"art:scene:{archetype}" for archetype in _SYNTH_SCENES)
        )
        self._drain()
        for tier in self.tiers:
            subject = monster_subject_for(tier)
            cards = gallery_api.cards_for(subject)
            self.assertEqual(len(cards), 1)
            self.assertIsNone(cards[0]["binding"])
            self.assertEqual(cards[0]["face_rect"], dict(gallery_api.DEFAULT_FACE_RECT))
            self.assertEqual(
                gallery_api.record_for(subject).db.default_image_id, cards[0]["image_id"]
            )
            self.assertTrue((self.root / cards[0]["stored_identity"]).exists())
        # The drained per-image jobs are spent and gone; still zero classic monster keys.
        self.assertEqual(self._classic_keys(), sorted(f"art:scene:{a}" for a in _SYNTH_SCENES))

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_consecutive_startups_never_replace_a_tiers_card_or_its_stored_file(self):
        art_sync_all()
        self._drain()
        subject = monster_subject_for(self.tiers[0])
        cards = gallery_api.cards_for(subject)
        self.assertEqual(len(cards), 1)
        stored = cards[0]["stored_identity"]
        self.assertTrue((self.root / stored).exists())
        # Consecutive restarts: the card occupies the gallery, so nothing is
        # requested and nothing is replaced.
        art_sync_all()
        art_sync_all()
        self.assertEqual(self._monster_job_keys(self.tiers[0]), [])
        self.assertEqual(gallery_api.cards_for(subject), cards)
        self.assertTrue((self.root / stored).exists())

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    def test_an_in_flight_tier_job_suppresses_a_second_request(self):
        art_sync_all()
        tier = self.tiers[0]
        self.assertEqual(len(self._monster_job_keys(tier)), 1)
        # A second startup sees the pending job and enqueues nothing more.
        art_sync_all()
        self.assertEqual(len(self._monster_job_keys(tier)), 1)
        # The job claimed and still in progress likewise suppresses a second.
        from world.art.queue import claim

        claimed = [
            record
            for record in claim(500)
            if record.db_key.startswith(f"art:portrait:monster:{tier}:gen:")
        ]
        self.assertEqual(len(claimed), 1)
        art_sync_all()
        self.assertEqual(len(self._monster_job_keys(tier)), 1)

    @covers_requirement(
        "art-gallery-autogen::automatic-generation-is-idempotent-against-the-subject-s-gallery"
    )
    @covers_requirement(
        "art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive"
    )
    def test_the_real_startup_dispatch_leaves_a_seed_carded_tier_alone(self):
        # Dispatches the REAL ``at_server_start()`` launch site: unrelated
        # steps are stubbed out, the three art steps run for real, and the
        # wrapper records the launch order itself. A monster seed image
        # occupies the tier's gallery before the automatic pass runs, so no
        # generation is ever requested for it and the seed card/file survive
        # a later drain untouched. A launch site wired in any other order
        # fails this test.
        import server.conf.at_server_startstop as at
        from world.art.gallery_seed import derive_image_id

        tier = self.tiers[0]
        folder = self.seed_root / "monster" / tier
        folder.mkdir(parents=True)
        (folder / "sentinel.png").write_bytes(b"\x89PNG seed bytes")
        expected_id = derive_image_id(f"monster/{tier}/sentinel.png")
        launched: list[str] = []
        art_steps = ("art_gallery_prune", "art_seed_sync", "art_sync_all")
        real_startup_step = at._startup_step

        def _recording_step(name, run, **kwargs):
            if name in art_steps:
                launched.append(name)
                return real_startup_step(name, run, **kwargs)
            return None

        with (
            patch.object(at, "_startup_step", side_effect=_recording_step),
            patch("world.art.gallery_seed.log_warn"),
            patch("world.art.gallery_seed.log_info"),
        ):
            at.at_server_start()
        self.assertEqual(launched, list(art_steps))
        self.assertEqual(
            [name for name in at.STARTUP_STEP_ORDER if name in art_steps],
            list(art_steps),
        )
        subject = monster_subject_for(tier)
        cards = gallery_api.cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [expected_id])
        seed_file = self.root / cards[0]["stored_identity"]
        seed_bytes = seed_file.read_bytes()
        self.assertEqual(self._monster_job_keys(tier), [])
        self._drain()
        self.assertEqual(gallery_api.cards_for(subject), cards)
        self.assertEqual(seed_file.read_bytes(), seed_bytes)

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records"
    )
    def test_a_failing_tier_is_bounded_and_the_remaining_tiers_still_synchronize(self):
        failing = self.tiers[0]
        real_request = request_gallery_image

        def _boom(entity_or_subject, **kwargs):
            if isinstance(entity_or_subject, ArtSubject) and entity_or_subject.key == failing:
                raise RuntimeError("gallery boom")
            return real_request(entity_or_subject, **kwargs)

        with (
            patch("world.art.service.request_gallery_image", side_effect=_boom),
            patch("world.art.service.log_warn") as warn,
        ):
            art_sync_all()  # must not raise
        self.assertEqual(self._monster_job_keys(failing), [])
        for tier in self.tiers[1:]:
            self.assertEqual(len(self._monster_job_keys(tier)), 1)
        self.assertTrue(
            any(
                call.args
                and call.args[0] == "art_startup_sync_skipped"
                and call.kwargs["context"] == {"kind": "monster", "key": failing}
                for call in warn.call_args_list
            )
        )
        # Scenes were unaffected by the failing tier.
        self.assertEqual(
            self._classic_keys(),
            sorted(f"art:scene:{a}" for a in _SYNTH_SCENES),
        )

    @covers_requirement(
        "art-asset-lifecycle::startup-synchronization-idempotently-ensures-scene-and-generic-monster-records"
    )
    def test_a_pre_existing_classic_record_is_left_alone_and_still_resolves_classic(self):
        from world.art.presenter import resolve_subject
        from world.art.queue import claim, settle

        tier = self.tiers[0]
        subject = monster_subject_for(tier)
        identity = f"portrait/monster/{tier}.png"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"classic")
        ensure(subject, "desc")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )
        before = ArtAssetRecord.objects.filter(db_key=f"art:portrait:monster:{tier}").first()
        self.assertEqual(before.db.status, ArtAssetStatus.DONE)
        art_sync_all()
        # The classic record's presence never suppresses the tier's gallery
        # request: an empty gallery still gets exactly one job.
        self.assertEqual(len(self._monster_job_keys(tier)), 1)
        after = ArtAssetRecord.objects.filter(db_key=f"art:portrait:monster:{tier}").first()
        self.assertIsNotNone(after)
        self.assertEqual(after.db.status, ArtAssetStatus.DONE)
        self.assertEqual(after.db.output_identity, identity)
        # An empty gallery still resolves through the chain's classic step.
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)
        self.assertIn(identity, payload["url"])
