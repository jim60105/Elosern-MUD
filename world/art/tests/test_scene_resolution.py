"""The room-aware scene source chain: precedence, facts, terminals, retention.

Change ``unified-scene-rendering`` (design §Decisions, delta
``scene-artwork-presentation``). This module proves the production boundary of
``world.art.presenter.describe_scene`` and ``world.rules.art_view`` on synthetic
facts only: an authored room override in front of the scene's own generated
artwork, the optional operator default, the REQUIRED bundled type illustration
and the distinct declared terminal, with every reached fault at its own
position, the retained startup facts attributed to the exact directory or image
they belong to, the malformed-metadata fallback to the declared town terminal,
the retention authorizations that keep a still-applicable known-good output
authorized, and the read-only guarantee this resolution owes the rest of the
game.

Every key, identity and path here is synthetic (the shared kit's reserved
``t_synth`` vocabulary); the closed town-terminal key and the ranks are read
from the production constants instead of being restated, and no shipped scene
key, room key or catalog symbol appears in this file.
"""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.art import descriptors, official, scene_definitions, subjects
# The map layer's authored tables validate themselves at import time; importing
# them here (against the REAL registries) keeps a later patch of the room-art
# vocabulary from re-running that validation on a synthetic set.
from world.maps import room_art  # noqa: F401
from world.art.presenter import TOWN_TERMINAL_KEY, describe_scene
from world.art.queue import claim, ensure, record_key, requeue, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from world.rules import art_view
from world.rules.art_view import SceneTarget, scene_target_for

PLACE_IDENTITY = "grid:t_synth_map:0,0"
SCENE_KEY = "t_synth_scene"
OTHER_SCENE_KEY = "t_synth_other"
ROOM_KEY = "t_synth_room"
SCENE_DESCRIPTION = "Synthetic scene description for the resolution contract"


def _fingerprint(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _official_image(identity: str, kind: str, key: str) -> official.OfficialImage:
    return official.OfficialImage(
        identity=identity,
        kind=kind,
        key=key,
        fingerprint=_fingerprint(identity),
        image_size={"width": 16, "height": 9},
        face_rect={"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5},
        stage={"scale": 1.0, "x": 0.0, "y": 0.0},
    )


def _bundled_image(key: str) -> scene_definitions.BundledSceneImage:
    return scene_definitions.BundledSceneImage(
        key=key,
        identity=f"{scene_definitions.BUNDLED_SCENE_IDENTITY_PREFIX}{key}/{_fingerprint(key)}"
        f"{scene_definitions.BUNDLED_SCENE_EXTENSION}",
        filename=scene_definitions.bundled_asset_filename(key),
        fingerprint=_fingerprint(f"bundled:{key}"),
        image_size={"width": 16, "height": 9},
    )


class _SceneFixture(EvenniaTestCase):
    """One synthetic scene world: definitions, bundled art and operator art.

    The three snapshots the resolution reads are patched with REAL snapshot
    objects (never mocks), so the walk reads admitted identities, fingerprints,
    geometry and retained faults exactly as it does in production.
    """

    def setUp(self) -> None:
        super().setUp()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store_root = Path(self.temp.name)

        self.definitions = {
            SCENE_KEY: scene_definitions.SceneArtDefinition(
                key=SCENE_KEY, terminal_key=OTHER_SCENE_KEY
            ),
            OTHER_SCENE_KEY: scene_definitions.SceneArtDefinition(
                key=OTHER_SCENE_KEY, terminal_key=OTHER_SCENE_KEY
            ),
        }
        self.bundled = {
            SCENE_KEY: _bundled_image(SCENE_KEY),
            OTHER_SCENE_KEY: _bundled_image(OTHER_SCENE_KEY),
            TOWN_TERMINAL_KEY: _bundled_image(TOWN_TERMINAL_KEY),
        }
        self.contents = {
            ("scene", SCENE_KEY): official.OfficialContent(
                kind="scene",
                key=SCENE_KEY,
                default_identity=f"scene/{SCENE_KEY}/a.png",
                images=(f"scene/{SCENE_KEY}/a.png",),
            ),
            ("room", ROOM_KEY): official.OfficialContent(
                kind="room",
                key=ROOM_KEY,
                default_identity=f"room/{ROOM_KEY}/b.png",
                images=(f"room/{ROOM_KEY}/b.png",),
            ),
        }
        self.official_images = {
            identity: _official_image(identity, kind, key)
            for (kind, key), content in self.contents.items()
            for identity in content.images
        }
        self.patch_snapshots()

    def patch_snapshots(self) -> None:
        catalog = official.OfficialCatalog(dict(self.contents), dict(self.official_images))
        for target, name, value in (
            (scene_definitions, "SCENE_ART_DEFINITIONS", dict(self.definitions)),
            (scene_definitions, "_BUNDLED", scene_definitions.BundledSceneCatalog(dict(self.bundled))),
            # The archetype registry every subject/room read resolves against.
            (
                subjects,
                "SCENE_ARCHETYPE_REGISTRY",
                {key: None for key in self.definitions},
            ),
            (
                art_view,
                "SCENE_ARCHETYPE_REGISTRY",
                {key: None for key in self.definitions},
            ),
            (official, "_CATALOG", catalog),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # --- helpers ---------------------------------------------------------

    def target(self, *, archetype=SCENE_KEY, room_key=None, invalid=False, identity=PLACE_IDENTITY):
        return SceneTarget(
            identity=identity,
            trusted_identity=True,
            archetype=archetype,
            room_art_key=room_key,
            room_binding_invalid=invalid,
        )

    def subject(self, key: str = SCENE_KEY) -> ArtSubject:
        return ArtSubject(ArtSubjectKind.SCENE, key)

    def publish(self, key: str = SCENE_KEY, *, body: bytes = b"synthetic stored output"):
        """Run one real queue lifecycle and publish one readable stored output."""
        subject = self.subject(key)
        ensure(subject, SCENE_DESCRIPTION)
        claimed = next(
            record
            for record in claim(ArtAssetRecord.objects.count() + 1)
            if record.db_key == record_key(subject)
        )
        identity = f"scene/{key}.png"
        path = self.store_root / identity
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        settle(
            subject,
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
            generation_token=str(claimed.db.generation_token),
        )
        return identity

    def entries(self, descriptor: dict) -> list[dict]:
        return list(descriptor["attempts"])


@override_settings()
class SourceChainTests(_SceneFixture):
    """The five positions, their order and the facts each one carries."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_healthy_room_override_is_the_first_ranked_attempt(self):
        descriptor = describe_scene(self.target(room_key=ROOM_KEY))
        entries = self.entries(descriptor)
        first = entries[0]
        self.assertEqual(first["type"], "image")
        self.assertEqual(first["source_id"], descriptors.scene_room_source_id(ROOM_KEY))
        self.assertEqual(first["rank"], descriptors.SCENE_RANK_ROOM)
        self.assertEqual(
            first["resource"]["resource_id"], f"room/{ROOM_KEY}/b.png"
        )
        self.assertEqual(first["resource"]["origin"], descriptors.ORIGIN_OFFICIAL)
        self.assertEqual(
            first["resource"]["url"], f"/art/official/{_fingerprint(f'room/{ROOM_KEY}/b.png')}/room/{ROOM_KEY}/b.png"
        )
        # Every position keeps its own stable rank, in chain order.
        self.assertEqual(
            [entry["rank"] for entry in entries],
            sorted(entry["rank"] for entry in entries),
        )

    def test_generated_artwork_precedes_the_operator_and_bundled_positions(self):
        identity = self.publish()
        descriptor = describe_scene(self.target())
        entries = self.entries(descriptor)
        generated = entries[0]
        self.assertEqual(generated["type"], "image")
        self.assertEqual(
            generated["source_id"], descriptors.scene_generated_source_id(self.subject().full())
        )
        self.assertEqual(generated["rank"], descriptors.SCENE_RANK_GENERATED)
        self.assertEqual(generated["resource"]["origin"], descriptors.ORIGIN_RUNTIME)
        self.assertTrue(generated["resource"]["url"].startswith(f"/art/{identity}"))
        self.assertEqual(
            generated["resource"]["version"],
            descriptors.generated_version(identity, str(ArtAssetRecord.objects.get(db_key=record_key(self.subject())).db.generation_token)),
        )
        self.assertEqual(descriptor["generation_subject"], self.subject().full())
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_DONE)
        self.assertEqual(
            [entry["rank"] for entry in entries[1:]],
            [descriptors.SCENE_RANK_OPERATOR, descriptors.SCENE_RANK_BUNDLED],
        )
        self.assertNotIn("terminal", [entry.get("source_id") for entry in entries])

    def test_recalled_failure_stays_visible_before_the_healthy_substitute(self):
        subject = self.subject()
        ensure(subject, SCENE_DESCRIPTION)
        claimed = next(
            record
            for record in claim(ArtAssetRecord.objects.count() + 1)
            if record.db_key == record_key(subject)
        )
        settle(
            subject,
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="sd_connection_error",
            generation_token=str(claimed.db.generation_token),
        )
        descriptor = describe_scene(self.target())
        entries = self.entries(descriptor)
        fault = entries[0]
        self.assertEqual(fault["type"], "fault")
        self.assertEqual(fault["reason"], descriptors.REASON_GENERATION_FAILED)
        self.assertEqual(fault["rank"], descriptors.SCENE_RANK_GENERATED)
        self.assertEqual(
            entries[1]["source_id"], descriptors.scene_operator_source_id(SCENE_KEY)
        )
        self.assertEqual(entries[1]["rank"], descriptors.SCENE_RANK_OPERATOR)
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)

    def test_required_bundled_position_carries_the_required_resource_fact(self):
        del self.bundled[SCENE_KEY]
        self.patch_snapshots()
        descriptor = describe_scene(self.target())
        bundled = [
            entry
            for entry in self.entries(descriptor)
            if entry["rank"] == descriptors.SCENE_RANK_BUNDLED
        ]
        self.assertEqual(len(bundled), 1)
        self.assertEqual(
            bundled[0]["source_id"], descriptors.scene_bundled_source_id(SCENE_KEY)
        )
        self.assertEqual(bundled[0]["type"], "fault")
        self.assertEqual(bundled[0]["reason"], descriptors.REASON_REQUIRED_RESOURCE_MISSING)

    def test_identical_terminal_is_never_attempted_twice(self):
        descriptor = describe_scene(self.target(archetype=OTHER_SCENE_KEY))
        self.assertIsNone(descriptor["terminal"])
        positions = [
            entry
            for entry in self.entries(descriptor)
            if entry["rank"] == descriptors.SCENE_RANK_TERMINAL
        ]
        self.assertEqual(positions, [])

    def test_distinct_terminal_carries_the_declared_image_at_its_own_rank(self):
        descriptor = describe_scene(self.target())
        terminal = descriptor["terminal"]
        self.assertEqual(terminal["kind"], descriptors.TERMINAL_SCENE_IMAGE)
        self.assertEqual(
            terminal["source_id"], descriptors.scene_terminal_source_id(OTHER_SCENE_KEY)
        )
        self.assertEqual(terminal["rank"], descriptors.SCENE_RANK_TERMINAL)
        self.assertEqual(
            terminal["resource"]["origin"], descriptors.ORIGIN_BUNDLED_OFFICIAL
        )


@override_settings()
class SourceFactAttributionTests(_SceneFixture):
    """A directory fact and an image fact never collide on one position."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_directory_and_selected_image_facts_keep_distinct_source_ids(self):
        image_identity = f"room/{ROOM_KEY}/b.png"
        self.contents[("room", ROOM_KEY)] = official.OfficialContent(
            kind="room",
            key=ROOM_KEY,
            default_identity=image_identity,
            images=(image_identity,),
            requested_default=f"room/{ROOM_KEY}/declared.png",
        )
        faults = {
            ("room", ROOM_KEY): (
                official.SourceFault(
                    scope=official.SOURCE_SCOPE_DEFAULT,
                    identity=f"room/{ROOM_KEY}/declared.png",
                    reason=official.SOURCE_REASON_REFERENCE_MISSING,
                ),
                official.SourceFault(
                    scope=official.SOURCE_SCOPE_METADATA,
                    identity=image_identity,
                    reason=official.SOURCE_REASON_METADATA_INVALID,
                ),
            )
        }
        self.patch_snapshots()
        patcher = patch.object(
            official,
            "_CATALOG",
            official.OfficialCatalog(
                dict(self.contents), dict(self.official_images), None, faults
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        descriptor = describe_scene(self.target(room_key=ROOM_KEY))
        room_entries = [
            entry
            for entry in self.entries(descriptor)
            if entry["rank"] == descriptors.SCENE_RANK_ROOM
        ]
        fault_ids = [entry["source_id"] for entry in room_entries if entry["type"] == "fault"]
        self.assertEqual(
            fault_ids,
            [
                descriptors.scene_room_source_id(ROOM_KEY),
                f"{descriptors.SCENE_ROOM_SOURCE_PREFIX}:{image_identity}",
            ],
        )
        # The directory fact keeps the position's own source id, the image fact
        # names the exact image it belongs to, and the candidate occupies the
        # same source id as a DIFFERENT entry type — so no two entries collide
        # on one (type, source_id, rank), which the canonical wire rejects.
        keys = [(entry["type"], entry["source_id"], entry["rank"]) for entry in room_entries]
        self.assertEqual(len(keys), len(set(keys)))
        candidate = [entry for entry in room_entries if entry["type"] == "image"]
        self.assertEqual(len(candidate), 1)
        self.assertEqual(
            candidate[0]["source_id"], descriptors.scene_room_source_id(ROOM_KEY)
        )

    def test_a_repeated_position_fact_keeps_the_first_in_chain_order(self):
        """A contract guard: the wire allows one entry per (type, source, rank)."""
        faults = {
            ("room", ROOM_KEY): (
                official.SourceFault(
                    scope=official.SOURCE_SCOPE_DEFAULT,
                    identity=f"room/{ROOM_KEY}/declared.png",
                    reason=official.SOURCE_REASON_REFERENCE_MISSING,
                ),
                official.SourceFault(
                    scope=official.SOURCE_SCOPE_SOURCE,
                    identity=f"room/{ROOM_KEY}",
                    reason=official.SOURCE_REASON_UNAVAILABLE,
                ),
            )
        }
        self.patch_snapshots()
        patcher = patch.object(
            official,
            "_CATALOG",
            official.OfficialCatalog(
                dict(self.contents), dict(self.official_images), None, faults
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        descriptor = describe_scene(self.target(room_key=ROOM_KEY))
        room_entries = [
            entry
            for entry in self.entries(descriptor)
            if entry["rank"] == descriptors.SCENE_RANK_ROOM
        ]
        keys = [(entry["type"], entry["source_id"], entry["rank"]) for entry in room_entries]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(
            [entry["reason"] for entry in room_entries if entry["type"] == "fault"],
            [official.SOURCE_REASON_REFERENCE_MISSING],
        )


@override_settings()
class MalformedMetadataTests(_SceneFixture):
    """An unusable archetype is stated explicitly, never hidden."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_malformed_metadata_falls_back_to_the_town_terminal(self):
        descriptor = describe_scene(self.target(archetype="t_synth_absent"))
        entries = self.entries(descriptor)
        self.assertEqual(len(entries), 1)
        fault = entries[0]
        self.assertEqual(fault["type"], "fault")
        self.assertEqual(fault["reason"], descriptors.REASON_CONFIGURATION_INVALID)
        self.assertEqual(
            fault["source_id"], descriptors.scene_terminal_source_id(TOWN_TERMINAL_KEY)
        )
        self.assertEqual(fault["rank"], descriptors.SCENE_RANK_TERMINAL)
        terminal = descriptor["terminal"]
        self.assertEqual(terminal["kind"], descriptors.TERMINAL_SCENE_IMAGE)
        self.assertEqual(
            terminal["source_id"], descriptors.scene_terminal_source_id(TOWN_TERMINAL_KEY)
        )
        self.assertIsNone(descriptor["generation_subject"])
        self.assertIsNone(descriptor["generation_state"])
        self.assertEqual(descriptor["retention_sources"], [])
        self.assertEqual(descriptor["subject_id"], PLACE_IDENTITY)

    def test_town_terminal_is_a_member_of_the_declared_terminal_vocabulary(self):
        self.assertIn(TOWN_TERMINAL_KEY, scene_definitions.TERMINAL_SCENE_KEYS)

    def test_malformed_metadata_without_its_image_keeps_only_the_configuration_fact(self):
        del self.bundled[TOWN_TERMINAL_KEY]
        self.patch_snapshots()
        descriptor = describe_scene(self.target(archetype="t_synth_absent"))
        self.assertIsNone(descriptor["terminal"])
        self.assertEqual(len(self.entries(descriptor)), 1)
        self.assertEqual(
            self.entries(descriptor)[0]["reason"], descriptors.REASON_CONFIGURATION_INVALID
        )


@override_settings()
class GenerationStateTests(_SceneFixture):
    """The recorded generation truth, independent of any candidate."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_pending_generation_claims_no_candidate_and_counts_as_pending(self):
        ensure(self.subject(), SCENE_DESCRIPTION)
        descriptor = describe_scene(self.target())
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_PENDING)
        self.assertEqual(
            [entry for entry in self.entries(descriptor) if entry["rank"] == descriptors.SCENE_RANK_GENERATED],
            [],
        )

    def test_a_vanished_generated_output_is_a_reached_output_missing_fact(self):
        identity = self.publish()
        (self.store_root / identity).unlink()
        descriptor = describe_scene(self.target())
        generated = [
            entry
            for entry in self.entries(descriptor)
            if entry["rank"] == descriptors.SCENE_RANK_GENERATED
        ]
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0]["type"], "fault")
        self.assertEqual(generated[0]["reason"], descriptors.REASON_GENERATED_OUTPUT_MISSING)

    def test_disabled_generation_never_erases_a_recorded_failure(self):
        subject = self.subject()
        ensure(subject, SCENE_DESCRIPTION)
        claimed = next(
            record
            for record in claim(ArtAssetRecord.objects.count() + 1)
            if record.db_key == record_key(subject)
        )
        settle(
            subject,
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="sd_connection_error",
            generation_token=str(claimed.db.generation_token),
        )
        with override_settings(ART_SCHEDULER_ENABLED=False):
            descriptor = describe_scene(self.target())
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        self.assertEqual(
            [entry for entry in self.entries(descriptor) if entry["rank"] == descriptors.SCENE_RANK_GENERATED][0]["reason"],
            descriptors.REASON_GENERATION_FAILED,
        )


@override_settings()
class RetentionAuthorizationTests(_SceneFixture):
    """Only a still-applicable, still-readable known-good output authorizes pixels."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def sources(self, descriptor: dict) -> dict:
        return {
            entry["source_id"]: entry["token"]
            for entry in descriptor["retention_sources"]
        }

    def test_generated_authorization_survives_a_requeue_and_a_failed_regeneration(self):
        self.publish()
        published = self.sources(describe_scene(self.target()))
        generated = descriptors.scene_generated_source_id(self.subject().full())
        self.assertIn(generated, published)

        requeue(self.subject())
        pending = self.sources(describe_scene(self.target()))
        self.assertEqual(pending.get(generated), published[generated])

        claimed = claim(ArtAssetRecord.objects.count() + 1)[0]
        settle(
            self.subject(),
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="sd_connection_error",
            generation_token=str(claimed.db.generation_token),
        )
        failed = self.sources(describe_scene(self.target()))
        self.assertEqual(failed.get(generated), published[generated])

    def test_generated_authorization_disappears_with_its_output(self):
        identity = self.publish()
        (self.store_root / identity).unlink()
        self.assertEqual(self.sources(describe_scene(self.target())), {})

    def test_room_authorization_requires_the_binding_and_its_admitted_default(self):
        bound = self.sources(describe_scene(self.target(room_key=ROOM_KEY)))
        room_source = descriptors.scene_room_source_id(ROOM_KEY)
        self.assertIn(room_source, bound)

        unbound = self.sources(describe_scene(self.target()))
        self.assertNotIn(room_source, unbound)
        self.assertEqual(unbound, {})

        # A replaced room default is a different applicable output: its token
        # changes, so content the operator no longer binds stops being
        # authorized.
        self.contents[("room", ROOM_KEY)] = official.OfficialContent(
            kind="room",
            key=ROOM_KEY,
            default_identity=f"room/{ROOM_KEY}/c.png",
            images=(f"room/{ROOM_KEY}/c.png",),
        )
        self.official_images[f"room/{ROOM_KEY}/c.png"] = _official_image(
            f"room/{ROOM_KEY}/c.png", "room", ROOM_KEY
        )
        self.patch_snapshots()
        replaced = self.sources(describe_scene(self.target(room_key=ROOM_KEY)))
        self.assertIn(room_source, replaced)
        self.assertNotEqual(replaced[room_source], bound[room_source])

    def test_an_untrusted_identity_authorizes_nothing(self):
        self.publish()
        untrusted = SceneTarget(
            identity="room:1",
            trusted_identity=False,
            archetype=SCENE_KEY,
            room_art_key=ROOM_KEY,
            room_binding_invalid=False,
        )
        self.assertEqual(describe_scene(untrusted)["retention_sources"], [])


class SceneTargetTests(_SceneFixture):
    """The read-only logical scene input the map owner's metadata produces."""

    def test_metadata_is_honored_only_when_registered(self):
        scene_registry = {"t_synth_registered": None}
        room_registry = frozenset({"t_synth_room"})
        location = create_object(Room, key="t_synth_room_object", location=None)
        self.addCleanup(location.delete)
        location.scene_archetype = "t_synth_registered"
        location.room_art_key = "t_synth_room"
        location.scene_identity = "place:t_synth"
        with (
            patch.object(scene_definitions, "ROOM_ART_KEY_SET", room_registry),
            patch.object(art_view, "SCENE_ARCHETYPE_REGISTRY", scene_registry),
        ):
            target = scene_target_for(location)
        self.assertEqual(target.identity, "place:t_synth")
        self.assertTrue(target.trusted_identity)
        self.assertEqual(target.archetype, "t_synth_registered")
        self.assertEqual(target.room_art_key, "t_synth_room")
        self.assertFalse(target.room_binding_invalid)

    def test_an_unregistered_binding_is_invalid_rather_than_absent(self):
        room_registry: frozenset = frozenset()
        location = create_object(Room, key="t_synth_room_object", location=None)
        self.addCleanup(location.delete)
        location.scene_archetype = None
        location.room_art_key = "t_synth_unregistered"
        location.scene_identity = None
        with patch.object(scene_definitions, "ROOM_ART_KEY_SET", room_registry):
            target = scene_target_for(location)
        self.assertEqual(target.room_art_key, "t_synth_unregistered")
        self.assertTrue(target.room_binding_invalid)
        self.assertFalse(target.trusted_identity)
        self.assertTrue(target.identity.startswith("room:"))

    def test_an_unbounded_stored_binding_is_never_echoed(self):
        room_registry: frozenset = frozenset()
        location = create_object(Room, key="t_synth_room_object", location=None)
        self.addCleanup(location.delete)
        location.room_art_key = {"not": "a key"}
        with patch.object(scene_definitions, "ROOM_ART_KEY_SET", room_registry):
            target = scene_target_for(location)
        self.assertIsNone(target.room_art_key)
        self.assertTrue(target.room_binding_invalid)


@override_settings()
class ReadOnlyResolutionTests(_SceneFixture):
    """Resolution reads canonical state and mutates none of it."""

    def setUp(self) -> None:
        super().setUp()
        settings_override = override_settings(ART_STORE_ROOT=str(self.store_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_resolution_writes_no_record_and_no_room_attribute(self):
        identity = self.publish()

        def attributes(obj):
            return sorted(
                (attribute.key, attribute.category, repr(attribute.value))
                for attribute in obj.attributes.all()
            )

        room = create_object(Room, key="t_synth_read_only_room", location=None)
        self.addCleanup(room.delete)
        room.scene_archetype = SCENE_KEY
        room.room_art_key = ROOM_KEY
        room.scene_identity = PLACE_IDENTITY
        before_room = attributes(room)
        record = ArtAssetRecord.objects.get(db_key=record_key(self.subject()))
        before_record = (
            record.db.status,
            str(record.db.output_identity),
            str(record.db.generation_token),
            attributes(record),
        )
        before_count = ArtAssetRecord.objects.count()

        describe_scene(self.target(room_key=ROOM_KEY))
        scene_target_for(room)

        record.refresh_from_db()
        self.assertEqual(
            (record.db.status, str(record.db.output_identity), str(record.db.generation_token), attributes(record)),
            before_record,
        )
        self.assertEqual(ArtAssetRecord.objects.count(), before_count)
        room.refresh_from_db()
        self.assertEqual(attributes(room), before_room)
        self.assertTrue((self.store_root / identity).exists())


if __name__ == "__main__":
    unittest.main()
