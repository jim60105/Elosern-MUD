"""Tests for the read-only art presenter primitives."""

from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.gallery import DEFAULT_FACE_RECT, append_card, cards_for
from world.art.presenter import (
    PLACEHOLDER_MISSING,
    PLACEHOLDER_UNAVAILABLE,
    media_url_for,
    resolve_character,
    resolve_entity,
    resolve_scene,
    resolve_subject,
)
from world.art.queue import claim, ensure, record_key, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtPresenterTests(EvenniaTestCase):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.player = create_object(PlayerCharacter, key="presenter-player")
        self.player.age = 22
        self.player.apparent_age = 22

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _write_asset(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_done_record_resolves_to_a_same_origin_url(self):
        subject = _scene()
        ensure(subject, "desc")
        self._write_asset("scene/forest_path.png")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)
        self.assertEqual(payload["url"], "/art/scene/forest_path.png")
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertNotIn("out_path", payload)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_done_record_with_a_missing_file_resolves_to_unavailable(self):
        subject = _scene()
        ensure(subject, "desc")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_missing_pending_failed_and_disabled_states_resolve_to_placeholders(self):
        pending = ArtSubject(ArtSubjectKind.SCENE, "tavern_interior")
        ensure(pending, "desc")
        for subject in (
            _scene("not_ensured"),
            pending,
        ):
            payload = resolve_subject(subject)
            self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
            self.assertIsNone(payload["url"])

        failed = ArtSubject(ArtSubjectKind.SCENE, "dungeon_interior")
        ensure(failed, "desc")
        claim(10)
        settle(failed, status=ArtAssetStatus.FAILED, output_identity=None, error="boom")
        payload = resolve_subject(failed)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertEqual(payload["status"], ArtAssetStatus.FAILED)
        self.assertIsNone(payload["url"])

    @covers_requirement("art-asset-lifecycle::rejected-prompt-content-never-reaches-the-presenter-or-browser")
    def test_malformed_subject_ages_resolve_only_to_the_unavailable_placeholder(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.age = "twenty-two"
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertNotIn("portrait rejected", str(payload))
        self.assertNotIn("twenty-two", str(payload))

    def test_character_without_a_named_policy_resolves_to_the_placeholder(self):
        self.player.db.portrait_policy = None
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_valid_character_portrait_resolves_to_a_same_origin_url(self):
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "42")
        ensure(subject, "desc")
        self._write_asset("portrait/character/42.png")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="portrait/character/42.png",
            error=None,
        )
        self.player.db.portrait_policy = {"mode": "named", "stable_key": "42"}
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["url"], "/art/portrait/character/42.png")

    def test_resolve_scene_handles_valid_and_unresolvable_archetypes(self):
        self.assertEqual(resolve_scene("not_a_scene")["kind"], PLACEHOLDER_UNAVAILABLE)
        payload = resolve_scene("forest_path")
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)

    @covers_requirement("art-queue-worker::in-flight-generation-exposes-a-wire-stable-status")
    def test_claimed_record_is_presented_as_pending_while_the_worker_holds_it(self):
        subject = _scene()
        ensure(subject, "desc")
        claim(10)
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertEqual(payload["status"], ArtAssetStatus.PENDING)
        self.assertIsNone(payload["url"])
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        self.assertEqual(record.db.status, ArtAssetStatus.IN_PROGRESS)

    @covers_requirement("art-queue-worker::in-flight-generation-exposes-a-wire-stable-status")
    def test_settled_statuses_pass_through_unchanged(self):
        for subject, expected in (
            (_scene("not_ensured"), ArtAssetStatus.MISSING),
            (_scene("dungeon_interior"), ArtAssetStatus.FAILED),
        ):
            if expected == ArtAssetStatus.FAILED:
                ensure(subject, "desc")
                claim(10)
                settle(subject, status=ArtAssetStatus.FAILED,
                       output_identity=None, error="boom")
            payload = resolve_subject(subject)
            self.assertEqual(payload["status"], expected)

    @covers_requirement("art-subject-model::subject-producer-validation-rejects-unrepresentable-keys")
    def test_slash_portrait_key_resolves_to_unavailable_without_a_queue_record(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": "a/b"}
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertFalse(
            ArtAssetRecord.objects.filter(
                db_key="art:portrait:character:a/b"
            ).exists()
        )

    def test_media_url_never_leaks_the_store_root(self):
        url = media_url_for("scene/forest_path.png")
        self.assertTrue(url.startswith("/art/"))
        self.assertNotIn(".art", url)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_existing_png_asset_survives_a_switch_to_another_format(self):
        subject = _scene()
        ensure(subject, "desc")
        self._write_asset("scene/forest_path.png")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/forest_path.png",
            error=None,
        )
        # Store mid-way through a format switch: the configured format is
        # webp, but the existing png asset must keep presenting until this
        # subject is regenerated under the new format.
        with override_settings(
            ART_SD_OUTPUT_FORMAT="webp", ART_SD_OUTPUT_EXTENSION=".webp"
        ):
            payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["url"], "/art/scene/forest_path.png")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_foreign_directory_identity_resolves_to_unavailable(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, "goblin")
        ensure(subject, "desc")
        self._write_asset("scene/goblin.png")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity="scene/goblin.png",
            error=None,
        )
        # A monster identity living outside portrait/monster/ fails the
        # subject-shape validation no matter which format is configured.
        # Filled seam (gallery-builtin-fallbacks): the unusable identity now
        # falls through to the built-in fallback instead of the placeholder.
        with patch("world.observability.log_info"):
            payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_all_four_store_extensions_present_as_assets(self):
        for extension in (".png", ".webp", ".jpg", ".avif"):
            subject = _scene(f"mixed_store_{extension[1:]}")
            identity = f"scene/mixed_store_{extension[1:]}{extension}"
            ensure(subject, "desc")
            self._write_asset(identity)
            claim(10)
            settle(
                subject,
                status=ArtAssetStatus.DONE,
                output_identity=identity,
                error=None,
            )
            payload = resolve_subject(subject)
            with self.subTest(extension=extension):
                self.assertEqual(payload["kind"], "asset")
                self.assertEqual(payload["url"], f"/art/{identity}")


class ResolveEntityTests(EvenniaTestCase):
    """Additive ``resolve_entity`` dispatch tests (task 1.3/1.4)."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "scene").mkdir()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.player = create_object(PlayerCharacter, key="entity-player")
        self.player.age = 22
        self.player.apparent_age = 22
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }
        self.monster = create_object(Monster, key="entity-wolf")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _drain_with_fake(self, fake):
        """Run a synchronous drain with ``fake`` injected through the seam."""
        with patch("world.art.worker.resolve_sd_client", return_value=fake):
            from world.art.worker import drain_synchronous

            return drain_synchronous(10)

    def _generation_keys(self):
        """Full subject keys the fake client was asked to generate for."""
        from world.art.worker import drain_synchronous

        fake = FakeSDWebUIClient()
        with patch("world.art.worker.resolve_sd_client", return_value=fake):
            drain_synchronous(10)
        return {subject.full() for subject, _ in fake.calls}

    def _assert_no_generation_requested(self, subject_key):
        """Assert the fake client never received a generation for a subject."""
        self.assertNotIn(subject_key, self._generation_keys())

    def test_named_character_resolves_through_the_canonical_age_check(self):
        with patch("world.observability.log_info"):
            payload = resolve_entity(self.player)
        self.assertEqual(payload["subject_key"], f"portrait:character:{self.player.pk}")
        # Filled seam: an artless character now resolves a built-in fallback.
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))
        self.assertIn("subject_key", payload)

    def test_valid_canonical_ages_reach_the_generation_client(self):
        from world.art.subjects import character_subject_for

        subject = character_subject_for(self.player)
        self.assertIsNotNone(subject)
        ensure(subject, "desc")
        fake = FakeSDWebUIClient()
        self._drain_with_fake(fake)
        generated = {generated_subject.full() for generated_subject, _ in fake.calls}
        self.assertIn(subject.full(), generated)

    def test_generic_monster_resolves_its_archetype_subject(self):
        with patch("world.observability.log_info"):
            payload = resolve_entity(self.monster)
        self.assertEqual(payload["subject_key"], "portrait:monster:low")
        # Filled seam: an artless monster resolves the monster_anon default.
        self.assertEqual(payload["kind"], "asset")
        self.assertTrue(payload["url"].startswith("/art/defaults/"))

    def test_non_integer_age_never_reaches_a_worker(self):
        self.player.age = "22"
        payload = resolve_entity(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])
        self._assert_no_generation_requested(f"portrait:character:{self.player.pk}")

    def test_non_integer_apparent_age_never_reaches_a_worker(self):
        self.player.apparent_age = "22"
        payload = resolve_entity(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self._assert_no_generation_requested(f"portrait:character:{self.player.pk}")

    def test_missing_age_values_reject_without_a_prompt(self):
        self.player.attributes.remove("age")
        payload = resolve_entity(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])

    def test_malformed_age_values_reject_without_a_prompt(self):
        self.player.age = "twenty"
        payload = resolve_entity(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])

    def test_unknown_threat_tier_falls_back_to_placeholder(self):
        self.monster.threat_tier = "mythical"
        payload = resolve_entity(self.monster)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])

    def test_entity_without_policy_resolves_to_unavailable(self):
        plain = create_object(PlayerCharacter, key="plain-entity")
        plain.age = 30
        plain.apparent_age = 30
        payload = resolve_entity(plain)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])


class FaceRectPayloadTests(EvenniaTestCase):
    """``face_rect`` on every payload (art-gallery-resolution)."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.player = create_object(PlayerCharacter, key="rect-player")
        self.player.age = 22
        self.player.apparent_age = 22
        self.player.db.portrait_policy = {
            "mode": "named",
            "stable_key": str(self.player.pk),
        }

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _subject(self):
        from world.art.subjects import character_subject_for

        return character_subject_for(self.player)

    def _append_card_with_file(self, **overrides):
        subject = self._subject()
        image_id = str(uuid.uuid4())
        identity = f"gallery/character/{subject.key}/{image_id}.png"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        fields = {
            "image_id": image_id,
            "stored_identity": identity,
            "prompt": {"positive": "a hero", "negative": "blur"},
            "seed": 7,
            "checkpoint": "realVision.safetensors",
            "requested_fields": ["appearance"],
            "binding": None,
            "source": "generated",
        }
        fields.update(overrides)
        append_card(subject, **fields)
        return subject, image_id, identity

    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_a_resolved_card_payload_carries_its_own_rectangle(self):
        explicit = {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}
        subject, image_id, identity = self._append_card_with_file(face_rect=explicit)
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["url"], f"/art/{identity}")
        self.assertEqual(payload["face_rect"], explicit)

    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_a_malformed_stored_rectangle_degrades_to_the_default_with_one_warning(self):
        subject, image_id, identity = self._append_card_with_file()
        card = dict(cards_for(subject)[0])
        card["face_rect"] = {"x": 0.5, "y": 0.0, "w": 0.9, "h": 0.9}
        with patch("world.art.presenter.resolve_card", return_value=card), patch(
            "world.art.presenter.log_warn"
        ) as warn:
            payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["face_rect"], dict(DEFAULT_FACE_RECT))
        events = [c for c in warn.call_args_list if c.args and c.args[0] == "art_face_rect_invalid"]
        self.assertEqual(len(events), 1, events)

    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_a_classic_asset_payload_carries_the_shared_default_rectangle(self):
        subject = self._subject()
        from world.art.queue import claim, ensure, settle
        from world.art.store import ArtAssetStatus

        ensure(subject, "desc")
        target = self.root / f"portrait/character/{subject.key}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")
        claim(10)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity=f"portrait/character/{subject.key}.png",
            error=None,
        )
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["face_rect"], dict(DEFAULT_FACE_RECT))

    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_every_placeholder_payload_carries_a_null_rectangle(self):
        # missing record -> PLACEHOLDER_MISSING
        subject = ArtSubject(ArtSubjectKind.SCENE, "rect_not_ensured")
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        # no policy -> unavailable
        plain = create_object(PlayerCharacter, key="rect-plain")
        plain.age = 30
        plain.apparent_age = 30
        payload = resolve_character(plain)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        # done record with a missing file -> unavailable
        done = ArtSubject(ArtSubjectKind.SCENE, "tavern_interior")
        from world.art.queue import claim as claim2, ensure as ensure2, settle as settle2

        ensure2(done, "desc")
        claim2(10)
        settle2(
            done,
            status=ArtAssetStatus.DONE,
            output_identity="scene/tavern_interior.png",
            error=None,
        )
        payload = resolve_subject(done)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])

    @covers_requirement(
        "art-gallery-resolution::the-chain-ends-at-one-fallback-seam"
    )
    def test_the_seam_is_consulted_on_every_fall_through_path(self):
        # A filled seam must win over the placeholder for every subject that
        # resolved no card and no classic done asset: no record at all, and
        # an unusable done identity.
        seam = {"identity": "defaults/monster_default.png", "face_rect": None}
        no_record = ArtSubject(ArtSubjectKind.MONSTER, "seam-no-record")
        with patch("world.art.presenter.fallback_for", return_value=seam):
            payload = resolve_subject(no_record)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["url"], "/art/defaults/monster_default.png")
        self.assertEqual(payload["face_rect"], dict(DEFAULT_FACE_RECT))
        # The unpatched seam fills persons but still returns None for scenes:
        # a scene subject keeps the byte-identical truthful placeholder.
        scene = ArtSubject(ArtSubjectKind.SCENE, "seam-no-record-scene")
        payload = resolve_subject(scene)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)


if __name__ == "__main__":
    import unittest

    unittest.main()
