"""Tests for the read-only art presenter primitives."""

from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.art.fake_sd_client import FakeSDWebUIClient
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


class ArtPresenterTests(EvenniaTest):
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

    @covers_requirement("adult-portrait-gate::rejected-prompt-content-never-reaches-the-presenter-or-browser")
    def test_gate_rejected_character_resolves_only_to_the_unavailable_placeholder(self):
        self.player.db.portrait_policy = {"mode": "named", "stable_key": str(self.player.pk)}
        self.player.age = 17
        payload = resolve_character(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["url"])
        self.assertNotIn("underage", str(payload))
        self.assertNotIn("17", str(payload))

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


class ResolveEntityTests(EvenniaTest):
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

    def test_named_character_resolves_through_the_adult_gate(self):
        payload = resolve_entity(self.player)
        self.assertEqual(payload["subject_key"], f"portrait:character:{self.player.pk}")
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        self.assertIn("subject_key", payload)

    def test_valid_adult_character_reaches_the_generation_client(self):
        from world.art.subjects import character_subject_for

        subject = character_subject_for(self.player)
        self.assertIsNotNone(subject)
        ensure(subject, "desc")
        fake = FakeSDWebUIClient()
        self._drain_with_fake(fake)
        generated = {generated_subject.full() for generated_subject, _ in fake.calls}
        self.assertIn(subject.full(), generated)

    def test_generic_monster_resolves_its_archetype_subject(self):
        payload = resolve_entity(self.monster)
        self.assertEqual(payload["subject_key"], "portrait:monster:low")
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)

    def test_age_seventeen_never_reaches_a_worker(self):
        self.player.age = 17
        payload = resolve_entity(self.player)
        self.assertEqual(payload["kind"], PLACEHOLDER_UNAVAILABLE)
        self.assertIsNone(payload["subject_key"])
        self.assertIsNone(payload["url"])
        self._assert_no_generation_requested(f"portrait:character:{self.player.pk}")

    def test_apparent_age_seventeen_never_reaches_a_worker(self):
        self.player.apparent_age = 17
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
        self.player.age = "adult"
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


if __name__ == "__main__":
    import unittest

    unittest.main()
