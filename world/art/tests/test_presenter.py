"""Tests for the read-only art presenter primitives."""

from pathlib import Path
import io
import json
import shutil
import socket
import tempfile
import uuid
from contextlib import ExitStack
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.art import official, official_refs
from world.art.fake_sd_client import FakeSDWebUIClient
from world.art.fallback_keys import FALLBACK_EXTENSION, FALLBACK_KEYS
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecord,
    append_card,
    cards_for,
    default_face_rect,
    identity_stage,
    official_preferences_for,
    record_for,
    set_official_geometry,
    set_official_selection,
)
from world.art.official import (
    OfficialCatalog,
    OfficialContent,
    OfficialImage,
    current_catalog,
    load_catalog,
    reset_catalog,
)
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.presenter import (
    GALLERY_ASPECT_RATIO,
    MAX_PORTRAIT_MEDIA_URL,
    ORIGIN_OFFICIAL,
    ORIGIN_PLACEHOLDER,
    ORIGIN_RUNTIME,
    ORIGIN_SILHOUETTE,
    PAYLOAD_OFFICIAL,
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
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

from tools.spec_traceability import covers_requirement


_SYNTH_SCENE = sorted(SYNTH_ARCHETYPES)[0]
_SYNTH_TIER = sorted(SYNTH_MONSTER_TIERS)[0]


def open_synthetic_scope(case, *targets, extra=None):
    """Enter a synthetic-catalog scope bound to one test case's lifecycle.

    The kit's class decorator wraps ``test*`` methods only, so anything a
    ``setUp`` builds against the catalogs would escape its scope. Call this as
    the FIRST statement of ``setUp`` (before ``super().setUp()``); the scope is
    torn down with the test via ``case.addCleanup``.
    """
    scope = synthetic_registries(*targets, extra=extra)
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope


def _scene(key="t_synth_forest"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


class ArtPresenterTests(EvenniaTestCase):
    character_typeclass = PlayerCharacter

    def setUp(self):
        # Scene-keyed records are opaque identities below; the one archetype
        # resolution test resolves a kit archetype against the patched catalog.
        open_synthetic_scope(self, "archetypes")
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
        self._write_asset("scene/t_synth_forest.png")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_forest.png",
            error=None,
        )
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)
        self.assertEqual(payload["url"], "/art/scene/t_synth_forest.png")
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertNotIn("out_path", payload)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_done_record_with_a_missing_file_resolves_to_unavailable(self):
        subject = _scene()
        ensure(subject, "desc")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_forest.png",
            error=None,
        )
        payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_missing_pending_failed_and_disabled_states_resolve_to_placeholders(self):
        pending = ArtSubject(ArtSubjectKind.SCENE, "t_synth_tavern")
        ensure(pending, "desc")
        for subject in (
            _scene("not_ensured"),
            pending,
        ):
            payload = resolve_subject(subject)
            self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
            self.assertIsNone(payload["url"])

        failed = ArtSubject(ArtSubjectKind.SCENE, "t_synth_dungeon")
        ensure(failed, "desc")
        claimed = claim(10)
        tokens = {record.db_key: str(record.db.generation_token) for record in claimed}
        settle(
            failed,
            generation_token=tokens[record_key(failed)],
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="boom",
        )
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
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
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
        payload = resolve_scene(_SYNTH_SCENE)
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
            (_scene("t_synth_dungeon"), ArtAssetStatus.FAILED),
        ):
            if expected == ArtAssetStatus.FAILED:
                ensure(subject, "desc")
                claimed = claim(10)
                settle(
                    subject,
                    generation_token=str(claimed[0].db.generation_token),
                    status=ArtAssetStatus.FAILED,
                    output_identity=None,
                    error="boom",
                )
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
        url = media_url_for("scene/t_synth_forest.png")
        self.assertTrue(url.startswith("/art/"))
        self.assertNotIn(".art", url)

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_existing_png_asset_survives_a_switch_to_another_format(self):
        subject = _scene()
        ensure(subject, "desc")
        self._write_asset("scene/t_synth_forest.png")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_forest.png",
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
        self.assertEqual(payload["url"], "/art/scene/t_synth_forest.png")

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_foreign_directory_identity_resolves_to_unavailable(self):
        subject = ArtSubject(ArtSubjectKind.MONSTER, "goblin")
        ensure(subject, "desc")
        self._write_asset("scene/goblin.png")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/goblin.png",
            error=None,
        )
        # A monster identity living outside portrait/monster/ fails the
        # subject-shape validation no matter which format is configured.
        # Filled seam (gallery-builtin-fallbacks): the unusable identity falls
        # through to the built-in silhouette, which rides the decorative
        # `fallback` field beside the subject's true unavailable state and
        # never becomes this payload's own image
        # (builtin-silhouette-stage-fallback).
        with patch("world.observability.log_info"):
            payload = resolve_subject(subject)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertTrue(payload["fallback"]["url"].startswith("/art/defaults/"))

    @covers_requirement("art-queue-worker::media-serving-maps-validated-stored-identities-to-same-origin-urls-without-exposing-the-store-root")
    def test_all_four_store_extensions_present_as_assets(self):
        for extension in (".png", ".webp", ".jpg", ".avif"):
            subject = _scene(f"mixed_store_{extension[1:]}")
            identity = f"scene/mixed_store_{extension[1:]}{extension}"
            ensure(subject, "desc")
            self._write_asset(identity)
            claimed = claim(10)
            settle(
                subject,
                generation_token=str(claimed[0].db.generation_token),
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
        # The monster dispatch arm validates threat_tier against the monster
        # tier catalog and applies its traits, so the entity is built inside a
        # synthetic tier scope and asserted against a kit tier key.
        open_synthetic_scope(self, "monster_tiers")
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
        self.monster.threat_tier = _SYNTH_TIER
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
        # Filled seam: an artless character resolves a built-in silhouette,
        # carried decoratively beside its true missing state.
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertIsNone(payload["url"])
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertTrue(payload["fallback"]["url"].startswith("/art/defaults/"))
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
        self.assertEqual(payload["subject_key"], f"portrait:monster:{_SYNTH_TIER}")
        # Filled seam: an artless monster resolves the monster_anon default as
        # its decorative silhouette.
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertIsNone(payload["url"])
        self.assertEqual(payload["fallback"]["key"], "monster_anon")
        self.assertTrue(payload["fallback"]["url"].startswith("/art/defaults/"))

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


class _CardPayloadCase(EvenniaTestCase):
    """Shared card-with-file harness for per-field payload assertions."""

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
            "image_size": {"width": 768, "height": 1024},
            "source": "generated",
        }
        fields.update(overrides)
        append_card(subject, **fields)
        return subject, image_id, identity


class StagePayloadTests(_CardPayloadCase):
    """``stage`` rides every asset payload and null on placeholders."""

    @covers_requirement(
        "webclient-art-panel::resolved-artwork-carries-stage-without-changing-asset-or-placeholder-truth"
    )
    def test_resolved_card_carries_its_stage_verbatim(self):
        triple = {"scale": 0.6, "x": -0.2, "y": 0.1}
        subject, image_id, identity = self._append_card_with_file(stage=triple)
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["stage"], triple)
        # The stage never disturbs the asset truth it rides on.
        self.assertEqual(payload["url"], f"/art/{identity}")

    @covers_requirement(
        "webclient-art-panel::resolved-artwork-carries-stage-without-changing-asset-or-placeholder-truth"
    )
    def test_missing_or_malformed_stored_stage_degrades_to_identity(self):
        subject = self._subject()
        self._append_card_with_file()
        # A card stored without the key reads as identity.
        card = dict(cards_for(subject)[0])
        card.pop("stage")
        with patch("world.art.presenter.resolve_display", return_value=("card", card)):
            payload = resolve_character(self.player)
        self.assertEqual(payload["stage"], {"scale": 1.0, "x": 0.0, "y": 0.0})
        # A malformed stored triple degrades to identity with one diagnostic,
        # and the asset itself still resolves.
        broken = dict(cards_for(subject)[0])
        broken["stage"] = {"scale": 3.5, "x": 0, "y": 0}
        with patch(
            "world.art.presenter.resolve_display", return_value=("card", broken)
        ), patch(
            "world.art.presenter.log_warn"
        ) as warn:
            payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["stage"], {"scale": 1.0, "x": 0.0, "y": 0.0})
        events = [c for c in warn.call_args_list if c.args and c.args[0] == "art_stage_invalid"]
        self.assertEqual(len(events), 1, events)


class FaceRectPayloadTests(_CardPayloadCase):
    """``face_rect`` on every payload (art-gallery-resolution)."""

    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_a_resolved_card_payload_carries_its_own_rectangle(self):
        explicit = {"x": 0.1, "y": 0.2, "w": 0.4, "h": 0.3}
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
        with patch(
            "world.art.presenter.resolve_display", return_value=("card", card)
        ), patch(
            "world.art.presenter.log_warn"
        ) as warn:
            payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], "asset")
        self.assertEqual(payload["face_rect"], default_face_rect(card["image_size"]))
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
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
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
        done = ArtSubject(ArtSubjectKind.SCENE, "t_synth_tavern")
        from world.art.queue import claim as claim2, ensure as ensure2, settle as settle2

        ensure2(done, "desc")
        claimed = claim2(10)
        settle2(
            done,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity="scene/t_synth_tavern.png",
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
        # A filled seam decorates every subject that resolved no card and no
        # classic done asset: no record at all, and an unusable done identity.
        seam = {"identity": "defaults/monster_default.png", "key": "man", "face_rect": None}
        no_record = ArtSubject(ArtSubjectKind.MONSTER, "seam-no-record")
        with patch("world.art.presenter.fallback_for", return_value=seam):
            payload = resolve_subject(no_record)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertEqual(
            payload["fallback"],
            {
                "key": "man",
                "url": "/art/defaults/monster_default.png",
                "face_rect": dict(DEFAULT_FACE_RECT),
            },
        )
        # The unpatched seam fills persons but still returns None for scenes:
        # a scene subject keeps the byte-identical truthful placeholder.
        scene = ArtSubject(ArtSubjectKind.SCENE, "seam-no-record-scene")
        payload = resolve_subject(scene)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertEqual(payload["origin"], ORIGIN_PLACEHOLDER)
        self.assertIsNone(payload["fallback"])


class SilhouettePayloadTests(EvenniaTestCase):
    """The decorative built-in silhouette every payload carries.

    The resolved fallback is presentation data for a still-absent portrait: it
    rides the ``fallback`` field beside the subject's true status, never
    becomes the payload's own media URL, and reports one use event only when
    it is the presented figure (art-gallery-fallback).
    """

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.tempdir.name))
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _character(self, stable_key: str):
        entity = create_object(PlayerCharacter, key=f"silhouette-{stable_key}")
        entity.age = 30
        entity.apparent_age = 30
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        return entity

    @covers_requirement(
        "art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use"
    )
    def test_a_silhouette_payload_never_claims_generation_success(self):
        missing, pending, failed = (
            "silhouette-missing",
            "silhouette-pending",
            "silhouette-failed",
        )
        pending_subject = ArtSubject(ArtSubjectKind.CHARACTER, pending)
        failed_subject = ArtSubject(ArtSubjectKind.CHARACTER, failed)
        ensure(pending_subject, "desc")
        ensure(failed_subject, "desc")
        tokens = {record.db_key: str(record.db.generation_token) for record in claim(10)}
        settle(
            failed_subject,
            generation_token=tokens[record_key(failed_subject)],
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="boom",
        )
        cases = (
            (missing, ArtAssetStatus.MISSING),
            (pending, ArtAssetStatus.PENDING),
            (failed, ArtAssetStatus.FAILED),
        )
        for stable_key, expected_status in cases:
            with self.subTest(status=expected_status):
                entity = self._character(stable_key)
                subject = ArtSubject(ArtSubjectKind.CHARACTER, stable_key)
                with patch("world.observability.log_info") as logged:
                    payload = resolve_character(entity)
                # The silhouette is carried, never presented as an image.
                self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
                self.assertIsNone(payload["url"])
                self.assertIsNone(payload["face_rect"])
                self.assertIsNone(payload["stage"])
                self.assertNotIn("已生成", str(payload))
                # The subject's own key stays the subject's; the silhouette
                # key lives only inside the decorative field.
                self.assertEqual(payload["subject_key"], subject.full())
                silhouette = payload["fallback"]
                self.assertIn(silhouette["key"], FALLBACK_KEYS)
                self.assertEqual(
                    silhouette["url"],
                    f"/art/defaults/{silhouette['key']}{FALLBACK_EXTENSION}",
                )
                self.assertEqual(sorted(silhouette["face_rect"]), ["h", "w", "x", "y"])
                # The true status passes through: an absent record is missing,
                # a claimed one is wire-stable pending, a settled one is failed.
                self.assertEqual(payload["status"], expected_status)
                events = [
                    call
                    for call in logged.call_args_list
                    if call.args and call.args[0] == "gallery_fallback_used"
                ]
                self.assertEqual(len(events), 1, events)
                # Presentation writes nothing: the persisted record keeps the
                # status it had (a claimed one stays in progress for its
                # worker; the wire-stable pending is presentation only).
                record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
                stored = {
                    ArtAssetStatus.MISSING: None,
                    ArtAssetStatus.PENDING: ArtAssetStatus.IN_PROGRESS,
                    ArtAssetStatus.FAILED: ArtAssetStatus.FAILED,
                }[expected_status]
                if stored is None:
                    self.assertIsNone(record)
                else:
                    self.assertEqual(record.db.status, stored)

    @covers_requirement(
        "art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use"
    )
    def test_a_real_image_carries_the_reference_without_reporting_a_use(self):
        entity = self._character("silhouette-card")
        subject = ArtSubject(ArtSubjectKind.CHARACTER, "silhouette-card")
        image_id = str(uuid.uuid4())
        identity = f"gallery/character/{subject.key}/{image_id}.png"
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        append_card(
            subject,
            image_id=image_id,
            stored_identity=identity,
            prompt={"positive": "a hero", "negative": "blur"},
            seed=7,
            checkpoint="realVision.safetensors",
            requested_fields=["appearance"],
            binding=None,
            image_size={"width": 768, "height": 1024},
            source="generated",
        )
        with patch("world.observability.log_info") as logged:
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{identity}")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)
        # The reference rides beside the resolved image for a browser-side
        # load-failure re-render, and is not a use of the fallback.
        self.assertIn(payload["fallback"]["key"], FALLBACK_KEYS)
        self.assertTrue(payload["fallback"]["url"].startswith("/art/defaults/"))
        events = [
            call
            for call in logged.call_args_list
            if call.args and call.args[0] == "gallery_fallback_used"
        ]
        self.assertEqual(events, [])

    @covers_requirement(
        "webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded"
    )
    def test_a_policy_less_entity_carries_its_attribute_selected_silhouette(self):
        before = ArtAssetRecord.objects.count()
        woman = create_object(PlayerCharacter, key="no-policy-woman")
        woman.sex = "female"
        woman.apparent_age = 30
        payload = resolve_character(woman)
        # The unavailable placeholder row: no policy, no subject key, no URL.
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        # The decoration comes from the entity's stored attributes, never from
        # a shared shape, and installs nothing.
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertEqual(payload["fallback"]["key"], "woman")
        self.assertEqual(ArtAssetRecord.objects.count(), before)
        self.assertIsNone(woman.db.portrait_policy)

    @covers_requirement(
        "webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded"
    )
    def test_a_monster_without_a_resolvable_tier_carries_monster_anon(self):
        before = ArtAssetRecord.objects.count()
        monster = create_object(Monster, key="silhouette-monster")
        monster.threat_tier = "mythical"
        payload = resolve_entity(monster)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertEqual(payload["fallback"]["key"], "monster_anon")
        self.assertEqual(
            payload["fallback"]["url"],
            f"/art/defaults/monster_anon{FALLBACK_EXTENSION}",
        )
        self.assertEqual(ArtAssetRecord.objects.count(), before)

    @covers_requirement(
        "webclient-art-panel::the-portrait-catalog-is-server-authored-age-checked-and-bounded"
    )
    def test_a_rejected_age_pair_carries_the_decoration_and_writes_nothing(self):
        # The malformed-age rung of the same terminal path: no subject key, no
        # URL, no record — and the entity's own attribute-selected silhouette.
        before = ArtAssetRecord.objects.count()
        rejected = self._character("silhouette-bad-age")
        rejected.age = "twenty"
        payload = resolve_character(rejected)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        self.assertIsNone(payload["stage"])
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertEqual(payload["fallback"]["key"], "man")
        self.assertEqual(payload["fallback"]["url"], f"/art/defaults/man{FALLBACK_EXTENSION}")
        self.assertEqual(ArtAssetRecord.objects.count(), before)
        self.assertNotIn("twenty", str(payload))


# A file-local synthetic preset key, a real decodable PNG, and the geometry
# the catalog validates against its 4x4 decoded size.
_PRESET_KEY = "t_synth_preset"
_FINGERPRINT = "a" * 64
_OFFICIAL_RECT = {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}
_OFFICIAL_STAGE = {"scale": 1.4, "x": 0.1, "y": -0.2}


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def _snapshot(identity: str, *, name="hero.png", **overrides) -> OfficialCatalog:
    """A hand-built official snapshot: one content directory, one image."""
    image = OfficialImage(
        identity=identity,
        kind="preset",
        key=_PRESET_KEY,
        fingerprint=_FINGERPRINT,
        image_size={"width": 4, "height": 4},
        face_rect=overrides.pop("face_rect", dict(_OFFICIAL_RECT)),
        stage=overrides.pop("stage", dict(_OFFICIAL_STAGE)),
    )
    content = OfficialContent(
        kind="preset",
        key=_PRESET_KEY,
        default_identity=identity,
        images=(identity,),
    )
    return OfficialCatalog({("preset", _PRESET_KEY): content}, {identity: image})


class OfficialPayloadTests(EvenniaTestCase):
    """The official-default payload branch (tasks 2.1, 2.2, 3.1).

    Every case resolves a preset-born character whose stored provenance names
    a registered content reference, so the official step is the one under
    test; the catalog snapshot is either loaded from a synthetic tree or
    injected whole, which is also how the wire-budget boundary is pinned.
    """

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = Path(self.tempdir.name) / "store"
        self.store.mkdir()
        self.official_root = Path(self.tempdir.name).resolve() / "official"
        self.settings = override_settings(
            ART_STORE_ROOT=str(self.store),
            ART_OFFICIAL_ROOT=str(self.official_root),
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        for patcher in (
            patch.object(
                official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
            ),
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY}),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    # -- harness ----------------------------------------------------------
    def _index(self, name="hero.png", **manifest) -> str:
        folder = self.official_root / "preset" / _PRESET_KEY
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png())
        if manifest:
            (folder / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def _character(self, stable_key="official-hero", *, age=30, apparent_age=30):
        entity = create_object(PlayerCharacter, key=f"official-{stable_key}")
        entity.age = age
        entity.apparent_age = apparent_age
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        entity.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, _PRESET_KEY)
        return entity

    def _subject(self, stable_key="official-hero") -> ArtSubject:
        return ArtSubject(ArtSubjectKind.CHARACTER, stable_key)

    def _state(self, entity) -> tuple:
        """The entity's and the store's observable state, for before/after pins."""
        return (
            str(entity.attributes.get("age")),
            str(entity.attributes.get("apparent_age")),
            str(entity.attributes.get(PRESET_PROVENANCE_ATTRIBUTE)),
            repr(entity.db.portrait_policy),
            tuple(
                sorted(path.relative_to(self.store).as_posix() for path in self.store.rglob("*"))
            ),
        )

    # -- payload shape ----------------------------------------------------
    @covers_requirement(
        "official-art-resolution::every-presentation-payload-distinguishes-official-runtime-and-silhouette-origin"
    )
    @covers_requirement(
        "official-art-resolution::official-payloads-are-catalog-derived-confined-and-fall-through-when-unresolvable"
    )
    def test_an_official_default_presents_with_its_metadata_geometry(self):
        identity = self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character()
        subject = self._subject()
        with patch("world.observability.log_info") as logged:
            payload = resolve_character(entity)
        self.assertEqual(payload["kind"], PAYLOAD_OFFICIAL)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        # An official image is never a generated/done portrait.
        self.assertIsNone(payload["status"])
        self.assertNotIn("已生成", str(payload))
        # The fingerprinted same-origin URL, the declared rectangle and the
        # non-identity declared stage all survive to the payload.
        self.assertEqual(payload["url"], current_catalog().url_for(identity))
        self.assertIn(current_catalog().fingerprint_for(identity), payload["url"])
        self.assertTrue(payload["url"].startswith("/art/official/"))
        self.assertEqual(payload["face_rect"], _OFFICIAL_RECT)
        self.assertEqual(payload["stage"], _OFFICIAL_STAGE)
        self.assertEqual(payload["aspect_ratio"], GALLERY_ASPECT_RATIO)
        self.assertEqual(payload["subject_key"], subject.full())
        self.assertEqual(payload["alt"], subject.full())
        # The decorative silhouette rides beside the presented image and
        # reports no use (report=False on the real-image rungs).
        self.assertIsNotNone(payload["fallback"])
        self.assertEqual(
            [
                call
                for call in logged.call_args_list
                if call.args and call.args[0] == "gallery_fallback_used"
            ],
            [],
        )
        # No path, license, manifest, or prompt text, and no state acquired.
        for leaked in ("ART_OFFICIAL_ROOT", str(self.official_root), "LICENSE", "prompt"):
            self.assertNotIn(leaked, str(payload))
        self.assertEqual(ArtAssetRecord.objects.count(), 0)
        self.assertEqual(GalleryRecord.objects.count(), 0)
        self.assertEqual(
            sorted(path.relative_to(self.store).as_posix() for path in self.store.rglob("*")),
            [],
        )
        self.assertEqual(entity.attributes.get(PRESET_PROVENANCE_ATTRIBUTE), _PRESET_KEY)

    @covers_requirement(
        "official-art-resolution::the-extended-chain-stays-deterministic-offline-and-side-effect-free"
    )
    @covers_requirement(
        "official-art-resolution::every-presentation-payload-distinguishes-official-runtime-and-silhouette-origin"
    )
    def test_a_runtime_card_outranks_the_official_default(self):
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character("card-first")
        subject = self._subject("card-first")
        image_id = str(uuid.uuid4())
        identity = f"gallery/character/{subject.key}/{image_id}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        append_card(
            subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=1,
            checkpoint="t_checkpoint",
            requested_fields=["appearance"],
            face_rect=dict(DEFAULT_FACE_RECT),
            image_size={"width": 8, "height": 8},
            binding=None,
            source="generated",
        )
        with patch(
            "world.art.presenter.official_default_for",
            side_effect=AssertionError("the official step must never be consulted"),
        ):
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{identity}")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)

    def test_a_classic_done_asset_outranks_the_official_default(self):
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character("classic-first")
        subject = self._subject("classic-first")
        ensure(subject, "desc")
        token = str(claim(10)[0].db.generation_token)
        identity = f"portrait/character/{subject.key}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")
        settle(
            subject,
            generation_token=token,
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )
        with patch(
            "world.art.presenter.official_default_for",
            side_effect=AssertionError("the official step must never be consulted"),
        ):
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{identity}")

    @covers_requirement(
        "official-art-resolution::official-payloads-are-catalog-derived-confined-and-fall-through-when-unresolvable"
    )
    def test_a_disappeared_official_entry_falls_through_to_the_seam(self):
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character()
        self.assertEqual(resolve_character(entity)["origin"], ORIGIN_OFFICIAL)
        # The artwork update removed the content directory; the new snapshot
        # simply lacks it, with no restart gap and no preference deletion.
        shutil.rmtree(self.official_root / "preset")
        load_catalog()
        with patch.object(official_refs, "log_warn") as warned:
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        self.assertIsNotNone(payload["fallback"])
        self.assertEqual(
            [
                call
                for call in warned.call_args_list
                if call.args and call.args[0] == "official_content_reference_unresolved"
            ],
            [],
        )
        self.assertEqual(entity.attributes.get(PRESET_PROVENANCE_ATTRIBUTE), _PRESET_KEY)

    def test_the_payload_boundary_revalidates_the_snapshots_geometry(self):
        # A snapshot carrying geometry that cannot have come from the catalog's
        # own admission (a non-pixel-square rectangle, an out-of-range stage)
        # still degrades per contract instead of shipping unvalidated values.
        identity = f"preset/{_PRESET_KEY}/hero.png"
        snapshot = _snapshot(
            identity,
            face_rect={"x": 0.1, "y": 0.1, "w": 0.9, "h": 0.2},
            stage={"scale": 0.05, "x": 0.0, "y": 0.0},
        )
        entity = self._character()
        with (
            patch.object(official, "_CATALOG", snapshot),
            patch("world.art.presenter.log_warn") as warned,
        ):
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["face_rect"], default_face_rect({"width": 4, "height": 4}))
        self.assertEqual(payload["stage"], identity_stage())
        events = [call.args[0] for call in warned.call_args_list if call.args]
        self.assertIn("art_face_rect_invalid", events)
        self.assertIn("art_stage_invalid", events)

    def test_a_url_inside_the_wire_budget_is_presented_and_one_outside_falls_through(self):
        entity = self._character()
        prefix = f"/art/official/{_FINGERPRINT}/preset/{_PRESET_KEY}/"
        at_budget = "c" * (MAX_PORTRAIT_MEDIA_URL - len(prefix) - len(".png")) + ".png"
        identity = f"preset/{_PRESET_KEY}/{at_budget}"
        self.assertEqual(len(f"/art/official/{_FINGERPRINT}/{identity}"), MAX_PORTRAIT_MEDIA_URL)
        with patch.object(official, "_CATALOG", _snapshot(identity)):
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["url"], f"/art/official/{_FINGERPRINT}/{identity}")

        # One character over the ceiling: the catalog's URL cannot travel the
        # wire, so the step falls through exactly like an absent reference
        # rather than failing the whole panel.
        over = "d" * (MAX_PORTRAIT_MEDIA_URL - len(prefix) - len(".png") + 1) + ".png"
        over_identity = f"preset/{_PRESET_KEY}/{over}"
        self.assertGreater(
            len(f"/art/official/{_FINGERPRINT}/{over_identity}"), MAX_PORTRAIT_MEDIA_URL
        )
        with (
            patch.object(official, "_CATALOG", _snapshot(over_identity)),
            patch("world.art.presenter.log_warn") as warned,
        ):
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertIsNone(payload["url"])
        events = [call.args[0] for call in warned.call_args_list if call.args]
        self.assertEqual(events.count("art_official_url_over_wire_budget"), 1)

    # -- eligibility ordering --------------------------------------------
    @covers_requirement(
        "official-art-resolution::eligibility-checks-order-before-official-and-runtime-presentation"
    )
    def test_eligibility_runs_ahead_of_official_presentation(self):
        # A fully valid directory unlocks nothing for a character whose
        # canonical ages fail: the official step is never even consulted.
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character(age=None, apparent_age=30)
        with (
            patch(
                "world.art.presenter.official_default_for",
                side_effect=AssertionError("the official step must not run"),
            ),
            patch("world.observability.log_info") as logged,
        ):
            payload = resolve_character(entity)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertEqual(payload["origin"], ORIGIN_SILHOUETTE)
        self.assertIsNone(payload["url"])
        self.assertIsNone(payload["face_rect"])
        self.assertIsNone(payload["subject_key"])
        self.assertNotIn(ORIGIN_OFFICIAL, str(payload["origin"]))
        self.assertEqual(
            len(
                [
                    call
                    for call in logged.call_args_list
                    if call.args and call.args[0] == "gallery_fallback_used"
                ]
            ),
            1,
        )
        self.assertEqual(ArtAssetRecord.objects.count(), 0)
        self.assertNotIn("portrait rejected", repr(payload))

    def test_a_monster_never_presents_an_official_origin(self):
        folder = self.official_root / "monster" / "official-monster"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "a.png").write_bytes(_png())
        load_catalog()
        # The snapshot really holds the matching content directory...
        self.assertIsNotNone(current_catalog().content("monster", "official-monster"))
        monster = create_object(Monster, key="official-monster-actor")
        # ...and the monster still resolves no reference (no producer), so the
        # official step resolves nothing for it.
        payload = resolve_subject(
            ArtSubject(ArtSubjectKind.MONSTER, "official-monster"), entity=monster
        )
        self.assertNotEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertIsNone(payload["url"])

    @covers_requirement(
        "official-art-resolution::the-extended-chain-stays-deterministic-offline-and-side-effect-free"
    )
    def test_a_hundred_presentations_write_nothing_and_call_no_network(self):
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        entity = self._character()
        tripwires = (
            patch.object(
                socket, "create_connection", side_effect=AssertionError("network")
            ),
            patch.object(
                socket.socket, "connect", side_effect=AssertionError("network")
            ),
            patch("world.art.gallery.append_card", side_effect=AssertionError("card write")),
            patch("world.art.gallery.set_default", side_effect=AssertionError("default write")),
            patch(
                "world.art.queue.enqueue_gallery_job",
                side_effect=AssertionError("enqueue"),
            ),
            patch(
                "world.art.service.request_gallery_image",
                side_effect=AssertionError("enqueue"),
            ),
            patch.object(official, "open_dir_fd", side_effect=AssertionError("re-walk")),
            patch.object(official, "load_catalog", side_effect=AssertionError("re-load")),
        )
        with ExitStack() as stack:
            for tripwire in tripwires:
                stack.enter_context(tripwire)
            before = (GalleryRecord.objects.count(), ArtAssetRecord.objects.count(), self._state(entity))
            payloads = [resolve_character(entity) for _ in range(100)]
            after = (GalleryRecord.objects.count(), ArtAssetRecord.objects.count(), self._state(entity))
        self.assertTrue(all(payload == payloads[0] for payload in payloads))
        self.assertEqual(payloads[0]["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(before, after)


class PersonalOfficialPayloadTests(EvenniaTestCase):
    """The personal official-selection payload branch (tasks 2.1-2.3).

    Every case resolves a preset-born character whose stored provenance names
    a registered content reference, so the selection's own branch is the one
    under test; the selection and its geometry overrides are written through
    the public gallery preference API, and the catalog snapshot is loaded from
    a synthetic tree — which is how acceptance criterion 4 (two characters
    sharing official bytes, independent choices) becomes observable.
    """

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.store = Path(self.tempdir.name) / "store"
        self.store.mkdir()
        self.official_root = Path(self.tempdir.name).resolve() / "official"
        self.settings = override_settings(
            ART_STORE_ROOT=str(self.store),
            ART_OFFICIAL_ROOT=str(self.official_root),
        )
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        reset_catalog()
        self.addCleanup(reset_catalog)
        for patcher in (
            patch.object(
                official_refs, "PLAYER_PRESET_REGISTRY", {_PRESET_KEY: object()}
            ),
            patch.object(
                official,
                "_registered_preset_keys",
                return_value=frozenset({_PRESET_KEY}),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    # -- harness ----------------------------------------------------------
    def _write_image(self, name, width=4, height=4, **manifest) -> None:
        folder = self.official_root / "preset" / _PRESET_KEY
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png(width, height))
        manifest_path = folder / "manifest.json"
        if manifest:
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        elif manifest_path.exists():
            manifest_path.unlink()

    def _index(self, name="hero.png", width=4, height=4, **manifest) -> str:
        self._write_image(name, width, height, **manifest)
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def _character(self, stable_key="official-hero", *, equipment=None):
        entity = create_object(PlayerCharacter, key=f"official-{stable_key}")
        entity.age = entity.apparent_age = 30
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        entity.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, _PRESET_KEY)
        if equipment is not None:
            entity.db.equipment = equipment
        return entity

    def _subject(self, stable_key="official-hero") -> ArtSubject:
        return ArtSubject(ArtSubjectKind.CHARACTER, stable_key)

    def _card(self, subject, **overrides):
        fields = {
            "image_id": str(uuid.uuid4()),
            "stored_identity": None,
            "prompt": None,
            "seed": None,
            "checkpoint": None,
            "requested_fields": [],
            "binding": None,
            "source": "seed",
            "created_at": 100.0,
            "image_size": {"width": 768, "height": 1024},
        }
        directory = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        fields["stored_identity"] = (
            f"gallery/{directory}/{subject.key}/{fields['image_id']}.png"
        )
        fields.update(overrides)
        target = self.store / fields["stored_identity"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"runtime-image")
        return append_card(subject, **fields)

    def _classic_done_asset(self, subject) -> str:
        """A classic ``done`` asset record with its file, for step 5."""
        ensure(subject, "desc")
        identity = f"portrait/character/{subject.key}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"classic-asset")
        claimed = claim(10)
        settle(
            subject,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )
        return identity

    # -- payload shape ----------------------------------------------------
    @covers_requirement(
        "official-art-resolution::every-presentation-payload-distinguishes-official-runtime-and-silhouette-origin"
    )
    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_a_selected_official_image_presents_ahead_of_the_default_card(self):
        identity = self._index(
            face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        entity = self._character()
        subject = self._subject()
        set_official_selection(subject, identity)
        card = self._card(subject)
        payload = resolve_character(entity)
        self.assertEqual(payload["kind"], PAYLOAD_OFFICIAL)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["url"], current_catalog().url_for(identity))
        self.assertEqual(payload["face_rect"], _OFFICIAL_RECT)
        self.assertEqual(payload["stage"], _OFFICIAL_STAGE)
        # An official image is never a generated/done portrait...
        self.assertIsNone(payload["status"])
        self.assertNotIn("已生成", str(payload))
        # ...and the runtime card, its default, and its file are untouched.
        record = record_for(subject)
        self.assertEqual(record.db.default_image_id, card["image_id"])
        self.assertEqual(
            [row["image_id"] for row in cards_for(subject)], [card["image_id"]]
        )
        self.assertTrue((self.store / card["stored_identity"]).exists())

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_an_equipment_bound_card_outranks_the_selection(self):
        identity = self._index()
        entity = self._character(equipment={"armor": "t_coat"})
        subject = self._subject()
        bound = self._card(
            subject,
            binding={"mask": ["armor"], "snapshot": {"armor": "t_coat"}},
        )
        set_official_selection(subject, identity)
        payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{bound['stored_identity']}")
        self.assertEqual(official_preferences_for(subject).selection, identity)

    @covers_requirement(
        "official-art-resolution::official-payloads-are-catalog-derived-confined-and-fall-through-when-unresolvable"
    )
    def test_a_selection_resolves_ahead_of_the_classic_asset_and_falls_back_when_stale(self):
        identity = self._index()
        entity = self._character()
        subject = self._subject()
        classic = self._classic_done_asset(subject)
        set_official_selection(subject, identity)
        # Step 4 outranks step 5 while the selection resolves...
        self.assertEqual(resolve_character(entity)["origin"], ORIGIN_OFFICIAL)
        # ...and a maintenance update that removes the directory (no restart
        # gap) falls through to the classic asset with the preference retained.
        shutil.rmtree(self.official_root / "preset")
        load_catalog()
        payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{classic}")
        self.assertEqual(payload["status"], ArtAssetStatus.DONE)
        self.assertEqual(official_preferences_for(subject).selection, identity)

    # -- personal geometry ------------------------------------------------
    @covers_requirement(
        "art-gallery-resolution::every-resolution-payload-carries-a-face-rectangle-or-null"
    )
    def test_a_personal_override_beats_the_catalog_geometry_and_never_writes(self):
        identity = self._index(
            face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        entity = self._character()
        subject = self._subject()
        rect = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
        stage = {"scale": 0.6, "x": 0.0, "y": -0.2}
        set_official_selection(subject, identity)
        set_official_geometry(subject, identity, face_rect=dict(rect), stage=dict(stage))
        source = self.official_root / "preset" / _PRESET_KEY / "hero.png"
        before = source.read_bytes()
        payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["face_rect"], rect)
        self.assertEqual(payload["stage"], stage)
        # The mounted source and the catalog's own facts are unchanged: an
        # override is entity-local presentation state.
        self.assertEqual(source.read_bytes(), before)
        entry = current_catalog().entry(identity)
        self.assertEqual(entry.face_rect, _OFFICIAL_RECT)
        self.assertEqual(entry.stage, _OFFICIAL_STAGE)

    @covers_requirement(
        "official-art-personalization::official-image-geometry-overrides-are-personal-identity-keyed-and-update-tolerant"
    )
    def test_an_update_invalidated_override_degrades_with_one_diagnostic(self):
        identity = self._index("hero.png", width=4, height=4)
        entity = self._character()
        subject = self._subject()
        stored_rect = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
        set_official_selection(subject, identity)
        set_official_geometry(subject, identity, face_rect=dict(stored_rect))
        self.assertEqual(resolve_character(entity)["face_rect"], stored_rect)
        # The artwork update replaces the bytes at the same identity with a
        # taller image, so the stored square is no longer square on it.
        self._write_image("hero.png", width=4, height=8)
        load_catalog()
        with patch("world.art.presenter.log_warn") as warn:
            payload = resolve_character(entity)
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(
            payload["face_rect"], default_face_rect({"width": 4, "height": 8})
        )
        events = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "art_official_override_invalid"
        ]
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["component"], "face_rect")
        self.assertEqual(events[0].kwargs["context"]["identity"], identity)
        # The preference is retained exactly as stored.
        self.assertEqual(
            official_preferences_for(subject).geometry, {identity: {"face_rect": stored_rect}}
        )

    @covers_requirement(
        "official-art-personalization::official-image-geometry-overrides-are-personal-identity-keyed-and-update-tolerant"
    )
    def test_a_malformed_stored_stage_override_is_dropped_by_the_tolerant_read(self):
        identity = self._index(
            face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE)
        )
        entity = self._character()
        subject = self._subject()
        set_official_selection(subject, identity)
        # Simulate storage a pre-validation version could have written: every
        # tolerant read drops the malformed component with exactly one bounded
        # event (the chain's step-4 read and the payload's override read), so
        # the payload carries the catalog's own stage and no render-time
        # override diagnostic fires.
        record_for(subject).db.official_geometry = {identity: {"stage": {"scale": 3.5}}}
        single_read = official_preferences_for(subject)
        with patch("world.art.gallery.log_warn") as read_warn, patch(
            "world.art.presenter.log_warn"
        ) as warn:
            payload = resolve_character(entity)
        self.assertEqual(single_read.geometry, {})
        self.assertEqual(payload["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payload["stage"], _OFFICIAL_STAGE)
        invalid = [
            call
            for call in read_warn.call_args_list
            if call.args and call.args[0] == "gallery_preference_invalid"
        ]
        # One bounded diagnostic per tolerant read, never a storm.
        self.assertEqual(len(invalid), 2, invalid)
        self.assertTrue(
            all(call.kwargs["context"]["field"] == "official_geometry" for call in invalid),
            invalid,
        )
        self.assertEqual(
            [
                call
                for call in warn.call_args_list
                if call.args and call.args[0] == "art_official_override_invalid"
            ],
            [],
        )
        # The malformed entry is dropped, not rewritten or deleted wholesale.
        self.assertEqual(
            official_preferences_for(subject).geometry, {}
        )
        self.assertEqual(record_for(subject).db.official_geometry.keys(), {identity})

    # -- acceptance criterion 4 -------------------------------------------
    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    @covers_requirement(
        "official-art-personalization::official-image-geometry-overrides-are-personal-identity-keyed-and-update-tolerant"
    )
    def test_two_characters_sharing_official_bytes_choose_independently(self):
        # One content directory (one manifest) holding two admitted images, so
        # both characters share the reference and its bytes.
        self._write_image("a.png", stage=dict(_OFFICIAL_STAGE))
        self._write_image("b.png", stage=dict(_OFFICIAL_STAGE))
        load_catalog()
        first_identity = f"preset/{_PRESET_KEY}/a.png"
        second_identity = f"preset/{_PRESET_KEY}/b.png"
        fitted = default_face_rect({"width": 4, "height": 4})
        one = self._character("twin-one")
        two = self._character("twin-two")
        one_subject = self._subject("twin-one")
        two_subject = self._subject("twin-two")
        one_rect = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
        two_stage = {"scale": 0.5, "x": 0.2, "y": 0.0}
        set_official_selection(one_subject, first_identity)
        set_official_geometry(one_subject, first_identity, face_rect=dict(one_rect))
        set_official_selection(two_subject, second_identity)
        set_official_geometry(two_subject, second_identity, stage=dict(two_stage))
        sources = {
            path: path.read_bytes()
            for path in (self.official_root / "preset" / _PRESET_KEY).iterdir()
        }
        one_payload = resolve_character(one)
        two_payload = resolve_character(two)
        self.assertEqual(one_payload["url"], current_catalog().url_for(first_identity))
        self.assertEqual(two_payload["url"], current_catalog().url_for(second_identity))
        self.assertEqual(one_payload["face_rect"], one_rect)
        self.assertEqual(two_payload["face_rect"], fitted)
        self.assertEqual(two_payload["stage"], two_stage)
        self.assertEqual(one_payload["stage"], _OFFICIAL_STAGE)
        self.assertNotEqual(one_payload["url"], two_payload["url"])
        self.assertNotEqual(one_payload["face_rect"], two_payload["face_rect"])
        self.assertNotEqual(one_payload["stage"], two_payload["stage"])
        # Neither character's state, nor the shared mounted source, moved.
        self.assertEqual(official_preferences_for(one_subject).selection, first_identity)
        self.assertEqual(official_preferences_for(two_subject).selection, second_identity)
        self.assertEqual(
            official_preferences_for(two_subject).geometry,
            {second_identity: {"stage": two_stage}},
        )
        self.assertEqual(
            {path: path.read_bytes() for path in sources}, sources
        )
        self.assertEqual(len(cards_for(one_subject)), 0)
        self.assertEqual(len(cards_for(two_subject)), 0)

    @covers_requirement(
        "official-art-resolution::the-extended-chain-stays-deterministic-offline-and-side-effect-free"
    )
    def test_a_hundred_selection_presentations_write_nothing(self):
        identity = self._index(face_rect=dict(_OFFICIAL_RECT))
        entity = self._character()
        subject = self._subject()
        set_official_selection(subject, identity)
        set_official_geometry(
            subject, identity, face_rect={"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}
        )
        tripwires = (
            patch.object(
                socket, "create_connection", side_effect=AssertionError("network")
            ),
            patch.object(
                socket.socket, "connect", side_effect=AssertionError("network")
            ),
            patch("world.art.gallery.append_card", side_effect=AssertionError("card write")),
            patch("world.art.gallery.set_default", side_effect=AssertionError("default write")),
            patch(
                "world.art.gallery.set_official_selection",
                side_effect=AssertionError("preference write"),
            ),
            patch(
                "world.art.gallery.set_official_geometry",
                side_effect=AssertionError("preference write"),
            ),
            patch(
                "world.art.service.request_gallery_image",
                side_effect=AssertionError("enqueue"),
            ),
            patch.object(official, "open_dir_fd", side_effect=AssertionError("re-walk")),
            patch.object(official, "load_catalog", side_effect=AssertionError("re-load")),
        )
        with ExitStack() as stack:
            for tripwire in tripwires:
                stack.enter_context(tripwire)
            before = (
                GalleryRecord.objects.count(),
                ArtAssetRecord.objects.count(),
                repr(record_for(subject).attributes.all()),
            )
            payloads = [resolve_character(entity) for _ in range(100)]
            after = (
                GalleryRecord.objects.count(),
                ArtAssetRecord.objects.count(),
                repr(record_for(subject).attributes.all()),
            )
        self.assertTrue(all(payload == payloads[0] for payload in payloads))
        self.assertEqual(payloads[0]["origin"], ORIGIN_OFFICIAL)
        self.assertEqual(payloads[0]["url"], current_catalog().url_for(identity))
        self.assertEqual(before, after)


if __name__ == "__main__":
    import unittest

    unittest.main()
