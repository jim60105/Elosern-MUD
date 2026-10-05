"""Database integration tests for the official content reference's rules.

Companion to ``test_official_refs``: the pure module covers the grammar,
boundary, inference traps, diagnostics, and the monster seam without a database;
this one establishes the state-ful half with synthetic entities and synthetic
registries only —

- two preset-born characters sharing one reference while their gallery records
  stay disjoint and their geometry changes stay independent (the mounted source
  is never written);
- a preset preview resolving the same reference with no new character, gallery
  record, or stored file (a before/after database *and* store comparison);
- two NPCs sharing one numeric tier key, only the profile-bearing one resolving
  a named reference, and a dynamically generated NPC honoring an explicitly
  attached validated reference while inferring nothing from a lookalike display
  name;
- monsters resolving no reference even while the mounted root really holds and
  indexes a matching ``monster/<key>/`` content directory;
- an entity with no named portrait subject hashing its runtime identity for the
  built-in silhouette without acquiring a portrait policy, a gallery record, or
  a queue record, and never becoming an official reference.

Annotated with the canonical ``official-content-provenance`` requirement IDs
the archive sync published — the follow-up tasks 5.1 deferred, on the
``official-artwork-catalog`` precedent.
"""

import base64
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.art import official, official_refs
from world.art.gallery import (
    GalleryRecord,
    append_card,
    cards_for,
    record_for,
    update_card_face_rect,
)
from world.art.gallery_fallback import fallback_key_for_entity
from world.art.official_refs import (
    NPC_PROFILE_PROVENANCE_ATTRIBUTE,
    OFFICIAL_KIND_NPC,
    OFFICIAL_KIND_PRESET,
    PRESET_PROVENANCE_ATTRIBUTE,
    OfficialContentReference,
    official_content_reference_for_entity,
    official_content_reference_for_preset,
)
from world.art.store import ArtAssetRecord
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement
from world.lore.npc_card import NpcCard, NpcCardIdentity
from world.rules.npc_persona import initialize_npc_persona, provenance_profile_key

# A deterministic 1x1 PNG: enough for the catalog to admit an indexed image.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# Synthetic identities only: no shipped registry key appears in this module.
_SYNTH_PRESET = "t_synth_preset"
_SYNTH_PROFILE = "t_synth_profile"
_SYNTH_TIER = "t_synth_tier"
_SYNTH_SPECIES = "t_synth_species"


def patch_registry(name: str, value):
    """Patch one of the resolver's registry bindings (never a proxy mutation).

    ``NPC_PROFILE_REGISTRY`` is a read-only mapping proxy, so tests rebind the
    module attribute rather than mutating the registry itself.
    """
    return patch.object(official_refs, name, value)


def _synthetic_card() -> dict:
    """A complete, synthetic compact NPC card record."""
    card = NpcCard(
        identity=NpcCardIdentity(public="t_合成身分", hidden=""),
        appearance="t_合成外觀",
        personality="t_合成性格",
        speech_style="t_合成語氣",
        life_story="t_合成來歷",
        habit="t_合成習慣",
        social_connection="",
    )
    return card.to_record()


class PresetProvenanceTests(EvenniaTest):
    """Requirement: preset-born characters resolve their template reference."""

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    def _preset_born(self, name: str) -> NPC:
        character = create_object(NPC, key=name)
        character.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, _SYNTH_PRESET)
        return character

    def _subject(self, character: NPC) -> ArtSubject:
        return ArtSubject(ArtSubjectKind.CHARACTER, str(character.pk))

    def _append_card(self, subject: ArtSubject, face_rect: dict) -> dict:
        image_id = str(uuid.uuid4())
        return append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/character/{subject.key}/{image_id}.png",
            prompt=None,
            seed=3,
            checkpoint="t_checkpoint",
            requested_fields=[],
            face_rect=dict(face_rect),
            image_size={"width": 8, "height": 8},
            binding=None,
            source="generated",
        )

    @covers_requirement(
        "official-content-provenance::preset-born-characters-resolve-their-template-reference-and-keep-their-own-gallery"
    )
    def test_two_preset_born_characters_share_the_reference_and_keep_disjoint_galleries(self):
        first = self._preset_born("t_preset_born_first")
        second = self._preset_born("t_preset_born_second")
        first_subject, second_subject = self._subject(first), self._subject(second)
        self._append_card(first_subject, {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5})
        self._append_card(second_subject, {"x": 0.2, "y": 0.2, "w": 0.4, "h": 0.4})
        first_before = cards_for(first_subject)
        second_before = cards_for(second_subject)

        with patch_registry("PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}):
            first_reference = official_content_reference_for_entity(first)
            second_reference = official_content_reference_for_entity(second)

        expected = OfficialContentReference(OFFICIAL_KIND_PRESET, _SYNTH_PRESET)
        self.assertEqual(first_reference, expected)
        self.assertEqual(second_reference, expected)
        # Disjoint mutable state: distinct records with distinct cards.
        self.assertIsNot(record_for(first_subject), record_for(second_subject))
        self.assertNotEqual(first_before, second_before)
        # One character's geometry override never touches the other's record.
        updated = update_card_face_rect(
            first_subject,
            first_before[0]["image_id"],
            {"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.3},
        )
        self.assertEqual(updated["face_rect"], {"x": 0.3, "y": 0.3, "w": 0.3, "h": 0.3})
        self.assertEqual(cards_for(second_subject), second_before)
        first_after = cards_for(first_subject)
        self.assertNotEqual(first_after, first_before)
        self.assertNotEqual(first_after, second_before)

    @covers_requirement(
        "official-content-provenance::preset-born-characters-resolve-their-template-reference-and-keep-their-own-gallery"
    )
    def test_a_preset_preview_resolves_without_creating_any_state(self):
        with tempfile.TemporaryDirectory() as store:
            with override_settings(ART_STORE_ROOT=store):
                before = (
                    ObjectDB.objects.count(),
                    GalleryRecord.objects.count(),
                    ArtAssetRecord.objects.count(),
                    sorted(entry.name for entry in Path(store).iterdir()),
                )
                with patch_registry("PLAYER_PRESET_REGISTRY", {_SYNTH_PRESET: object()}):
                    reference = official_content_reference_for_preset(_SYNTH_PRESET)
                after = (
                    ObjectDB.objects.count(),
                    GalleryRecord.objects.count(),
                    ArtAssetRecord.objects.count(),
                    sorted(entry.name for entry in Path(store).iterdir()),
                )
        self.assertEqual(reference, OfficialContentReference(OFFICIAL_KIND_PRESET, _SYNTH_PRESET))
        self.assertEqual(before, after)


class NpcProvenanceTests(EvenniaTest):
    """Requirements: authored NPC provenance, tier separation, explicit-only."""

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    @covers_requirement(
        "official-content-provenance::authored-npcs-carry-a-stable-profile-provenance-established-at-creation"
    )
    def test_only_the_profile_bearing_npc_resolves_a_named_reference(self):
        with patch_registry("NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}):
            with_profile = create_object(NPC, key="t_npc_profile_bearer")
            with_profile.attributes.add(NPC_PROFILE_PROVENANCE_ATTRIBUTE, _SYNTH_PROFILE)
            with_profile.attributes.add("npc_tier_key", _SYNTH_TIER)
            tier_only = create_object(NPC, key="t_npc_tier_only")
            tier_only.attributes.add("npc_tier_key", _SYNTH_TIER)
            tier_only.db.display_name = _SYNTH_PROFILE

            self.assertEqual(
                official_content_reference_for_entity(with_profile),
                OfficialContentReference(OFFICIAL_KIND_NPC, _SYNTH_PROFILE),
            )
            self.assertIsNone(official_content_reference_for_entity(tier_only))

    @covers_requirement(
        "official-content-provenance::dynamically-generated-npcs-may-only-carry-an-explicit-allowed-reference"
    )
    def test_a_generated_npc_infers_nothing_and_honors_only_an_explicit_reference(self):
        generated = create_object(NPC, key="t_generated_occupant")
        initialize_npc_persona(
            generated,
            _synthetic_card(),
            {"kind": "generated_quest", "quest": "t_quest", "stage": 0, "occupant": 0},
        )
        generated.db.display_name = _SYNTH_PROFILE
        with patch_registry("NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}):
            # The lookalike display name is not a reference and no provenance
            # exists: the generated NPC resolves nothing.
            self.assertIsNone(official_content_reference_for_entity(generated))
            # An allowed authored channel explicitly attaches the validated
            # reference; it then resolves exactly like any provenance-derived one.
            generated.attributes.add(
                NPC_PROFILE_PROVENANCE_ATTRIBUTE, _SYNTH_PROFILE
            )
            self.assertEqual(
                official_content_reference_for_entity(generated),
                OfficialContentReference(OFFICIAL_KIND_NPC, _SYNTH_PROFILE),
            )

    @covers_requirement(
        "official-content-provenance::an-official-content-reference-is-typed-validated-and-provenance-derived"
    )
    def test_the_resolver_reads_the_attribute_not_the_persona_meta(self):
        # A profile-keyed persona provenance without the entity attribute (a
        # pre-change host) resolves nothing: this change adds the attribute and
        # never re-derives it from an existing writer's record.
        legacy = create_object(NPC, key="t_legacy_host")
        with patch_registry("NPC_PROFILE_REGISTRY", {_SYNTH_PROFILE: object()}):
            initialize_npc_persona(
                legacy,
                _synthetic_card(),
                {"kind": "profile", "profile": _SYNTH_PROFILE},
            )
            self.assertEqual(provenance_profile_key(legacy), _SYNTH_PROFILE)
            self.assertIsNone(official_content_reference_for_entity(legacy))


class MonsterBoundaryTests(EvenniaTest):
    """Requirement: monsters resolve no official image before the catalog."""

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
        self.addCleanup(official.reset_catalog)

    @covers_requirement(
        "official-content-provenance::monster-species-references-await-the-separate-species-catalog-and-forbid-tier-substitution"
    )
    def test_a_populated_matching_monster_directory_resolves_no_reference(self):
        with tempfile.TemporaryDirectory() as root:
            content = Path(root) / "monster" / _SYNTH_SPECIES
            content.mkdir(parents=True)
            (content / "a.png").write_bytes(_TINY_PNG)
            with override_settings(ART_OFFICIAL_ROOT=root):
                official.reset_catalog()
                official.load_catalog()
                # The directory really is populated and indexed ...
                self.assertIsNotNone(
                    official.current_catalog().content("monster", _SYNTH_SPECIES)
                )
                monster = create_object(Monster, key=_SYNTH_SPECIES)
                monster.threat_tier = _SYNTH_SPECIES
                monster.db.display_name = _SYNTH_SPECIES
                # ... and the resolver still yields nothing: no producer exists
                # keyed by threat tier or display name.
                self.assertIsNone(official_content_reference_for_entity(monster))


class PlaceholderIdentityTests(EvenniaTest):
    """Requirement: entity identity is a hash input only."""

    def setUp(self):
        super().setUp()
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)

    @covers_requirement(
        "official-content-provenance::entity-identity-is-a-hash-input-only-never-a-manufactured-portrait-subject"
    )
    def test_placeholder_identity_hashing_creates_no_portrait_state(self):
        entity = create_object(NPC, key="t_placeholder_npc")
        identity = str(entity.pk)
        with (
            patch_registry("PLAYER_PRESET_REGISTRY", {identity: object()}),
            patch_registry("NPC_PROFILE_REGISTRY", {identity: object()}),
        ):
            self.assertIsNone(official_content_reference_for_entity(entity))
            fallback_key = fallback_key_for_entity(entity, identity)
        self.assertTrue(fallback_key)
        self.assertFalse(entity.attributes.has("portrait_policy"))
        self.assertFalse(entity.attributes.has(PRESET_PROVENANCE_ATTRIBUTE))
        self.assertIsNone(
            record_for(ArtSubject(ArtSubjectKind.CHARACTER, identity))
        )
        self.assertEqual(GalleryRecord.objects.count(), 0)
        self.assertEqual(ArtAssetRecord.objects.count(), 0)

if __name__ == "__main__":
    unittest.main()
