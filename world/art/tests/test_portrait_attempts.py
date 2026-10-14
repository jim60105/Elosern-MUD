"""The canonical portrait source enumeration: ordered attempts, faults, terminal.

Change ``unified-portrait-source-resolution``. This module proves two layers:

* the synthetic mechanism layer — independently expected source order, ranks,
  canonical source identities, the bounded fault of an explicit source that
  cannot resolve, the classic record's missing output and recorded failure, the
  alpha terminal's rank, and the read-only/no-write guarantee; and
* one production-boundary smoke — real gallery cards written through the
  shipped writers plus a real startup catalog admission, resolved once through
  the production resolver and once through the canonical enumerator, with the
  ordered faults and the unchanged persistent state asserted together.

Everything synthetic lives on the shared kit's reserved ``t_`` vocabulary or on
a temporary store/official root; no shipped key, path, or catalog symbol is
restated here.
"""

import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from PIL import Image

from typeclasses.characters import PlayerCharacter
from world.art import descriptors, official, official_refs
from world.art.gallery import (
    GalleryRecord,
    append_card,
    cards_for,
    default_face_rect,
    identity_stage,
    official_preferences_for,
    record_for,
    record_error,
    set_official_selection,
)
from world.art.official import current_catalog, load_catalog, reset_catalog
from world.art.official_refs import PRESET_PROVENANCE_ATTRIBUTE
from world.art.presenter import (
    GALLERY_ASPECT_RATIO,
    PLACEHOLDER_UNAVAILABLE,
    describe_entity,
    describe_portrait,
    resolve_subject,
)
from world.art.queue import claim, ensure, settle
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectKind
from web.webclient.presentation import artwork as artwork_wire

from tools.spec_traceability import covers_requirement


# A file-local synthetic preset key, a real decodable PNG, and the geometry the
# catalog validates against its 4x4 decoded size.
_PRESET_KEY = "t_synth_preset"
_OFFICIAL_RECT = {"x": 0.25, "y": 0.25, "w": 0.5, "h": 0.5}
_OFFICIAL_STAGE = {"scale": 1.4, "x": 0.1, "y": -0.2}
_SYNTH_SCENE = "t_synth_forest"
_CARD_SIZE = {"width": 768, "height": 1024}


def _png(width=4, height=4) -> bytes:
    """A real, decodable PNG of the given pixel size."""
    buffer = io.BytesIO()
    Image.new("L", (width, height)).save(buffer, format="PNG")
    return buffer.getvalue()


def _subject_directory(subject: ArtSubject) -> str:
    """The store directory one subject's classic output identity lives under."""
    if subject.kind is ArtSubjectKind.SCENE:
        return "scene"
    if subject.kind is ArtSubjectKind.MONSTER:
        return "portrait/monster"
    return "portrait/character"


class _PortraitAttemptCase(EvenniaTestCase):
    """The shared harness: a temporary store, a temporary official root, one identity."""

    def setUp(self):
        super().setUp()
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
        official_refs._reported_unresolved.clear()
        self.addCleanup(official_refs._reported_unresolved.clear)
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
    def _character(self, stable_key, *, equipment=None, provenance=True):
        entity = create_object(PlayerCharacter, key=f"attempt-{stable_key}")
        entity.age = entity.apparent_age = 30
        entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
        if provenance:
            entity.attributes.add(PRESET_PROVENANCE_ATTRIBUTE, _PRESET_KEY)
        if equipment is not None:
            entity.db.equipment = equipment
        return entity

    def _subject(self, stable_key="attempt-hero") -> ArtSubject:
        return ArtSubject(ArtSubjectKind.CHARACTER, stable_key)

    def _card(self, subject, *, binding=None, image_id=None) -> dict:
        """Write one real gallery card and its file through the shipped writer."""
        image_id = image_id or str(uuid.uuid4())
        directory = "monster" if subject.kind is ArtSubjectKind.MONSTER else "character"
        identity = f"gallery/{directory}/{subject.key}/{image_id}.png"
        target = self.store / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"runtime-image")
        return append_card(
            subject,
            image_id=image_id,
            stored_identity=identity,
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=binding,
            source="seed",
            created_at=100.0,
            image_size=dict(_CARD_SIZE),
        )

    def _classic_identity(self, subject) -> str:
        return f"{_subject_directory(subject)}/{subject.key}.png"

    def _settle_classic(
        self, subject, *, status=ArtAssetStatus.DONE, error=None, write=True
    ):
        """Settle one real classic record through the shipped queue writers."""
        ensure(subject, "desc")
        token = str(claim(10)[0].db.generation_token)
        identity = self._classic_identity(subject)
        if write:
            target = self.store / identity
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"classic-asset")
        return settle(
            subject,
            generation_token=token,
            status=status,
            output_identity=identity,
            error=error,
        )

    def _index(self, name="hero.png", width=4, height=4, **manifest) -> str:
        """Admit one real official image through the real startup load."""
        folder = self.official_root / "preset" / _PRESET_KEY
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_bytes(_png(width, height))
        if manifest:
            (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        load_catalog()
        return f"preset/{_PRESET_KEY}/{name}"

    def _state(self, subject) -> tuple:
        """Every observable fact a presentation must never change."""
        preferences = official_preferences_for(subject)
        return (
            GalleryRecord.objects.count(),
            ArtAssetRecord.objects.count(),
            sorted(cards_for(subject), key=lambda card: card["image_id"]),
            preferences.selection,
            preferences.geometry,
            sorted(
                path.relative_to(self.store).as_posix()
                for path in self.store.rglob("*")
            ),
        )

    def _ordered(self, descriptor) -> list:
        """The attempt facts that fix precedence: type, source identity and rank."""
        return [
            (attempt["type"], attempt["source_id"], attempt["rank"])
            for attempt in descriptor["attempts"]
        ]


class PortraitAttemptOrderTests(_PortraitAttemptCase):
    """Source order, source identity, fault position and generation truth."""

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    @covers_requirement("artwork-descriptor::source-priority-and-retained-access-are-explicit")
    def test_a_bound_card_is_the_rank_ten_candidate_beside_the_alpha_terminal(self):
        subject = self._subject("bound-attempt")
        entity = self._character("bound-attempt", equipment={"armor": "t_coat"})
        card = self._card(
            subject, binding={"mask": ["armor"], "snapshot": {"armor": "t_coat"}}
        )
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(
            self._ordered(descriptor),
            [("image", f"portrait.bound:{card['image_id']}", descriptors.PORTRAIT_RANK_BOUND)],
        )
        resource = descriptor["attempts"][0]["resource"]
        self.assertEqual(resource["origin"], descriptors.ORIGIN_RUNTIME)
        self.assertEqual(resource["url"], f"/art/{card['stored_identity']}")
        self.assertEqual(resource["resource_id"], card["stored_identity"])
        self.assertRegex(resource["version"], r"[0-9a-f]{64}")
        self.assertEqual(resource["geometry"]["face_rect"], dict(card["face_rect"]))
        self.assertEqual(resource["geometry"]["stage"], identity_stage())
        self.assertEqual(resource["geometry"]["aspect_ratio"], GALLERY_ASPECT_RATIO)
        self.assertEqual(resource["geometry"]["image_size"], dict(_CARD_SIZE))
        # The descriptor's own identity, revision and independent generation truth.
        self.assertEqual(descriptor["subject_id"], subject.full())
        self.assertEqual(descriptor["generation_subject"], subject.full())
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_DONE)
        self.assertEqual(descriptor["retention_sources"], [])
        self.assertRegex(descriptor["revision"], r"[0-9a-f]{64}")
        # The authoritative alpha terminal sits at its own rank with its own source.
        terminal = descriptor["terminal"]
        self.assertEqual(terminal["kind"], descriptors.TERMINAL_ALPHA_MASK)
        self.assertEqual(terminal["rank"], descriptors.PORTRAIT_RANK_ALPHA)
        self.assertEqual(terminal["rank"], descriptors.GALLERY_RANK_ALPHA)
        self.assertRegex(terminal["source_id"], r"^portrait\.alpha:.+$")
        self.assertEqual(terminal["resource"]["origin"], descriptors.ORIGIN_SILHOUETTE)
        self.assertNotEqual(terminal["resource"]["resource_id"], resource["resource_id"])

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    @covers_requirement(
        "official-art-personalization::stale-official-selections-are-retained-but-ignored-for-resolution"
    )
    @covers_requirement(
        "portrait-source-attempts::portrait-source-order-retains-current-policy"
    )
    def test_a_broken_personal_selection_precedes_the_default_candidate(self):
        subject = self._subject("stale-selection")
        entity = self._character("stale-selection")
        self._index()
        # The retained selection names an image the snapshot does not admit.
        selection = f"preset/{_PRESET_KEY}/gone.png"
        set_official_selection(subject, selection)
        # The FIRST card of the card-less record installs itself as the record
        # default without discarding the player's selection, so the stored state
        # really does hold both an unresolvable explicit selection and a valid
        # default card.
        card = self._card(subject)
        self.assertEqual(record_for(subject).db.default_image_id, card["image_id"])
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(
            self._ordered(descriptor),
            [
                ("fault", f"portrait.personal:{selection}", descriptors.PORTRAIT_RANK_PERSONAL),
                ("image", f"portrait.default:{card['image_id']}", descriptors.PORTRAIT_RANK_DEFAULT),
            ],
        )
        fault = descriptor["attempts"][0]
        self.assertEqual(fault["reason"], descriptors.REASON_EXPLICIT_REFERENCE_MISSING)
        self.assertNotIn("resource", fault)
        self.assertNotIn("url", json.dumps(fault))
        # The default remains selectable and the preference survives untouched.
        self.assertEqual(official_preferences_for(subject).selection, selection)
        payload = resolve_subject(subject, entity=entity)
        self.assertEqual(payload["url"], f"/art/{card['stored_identity']}")
        self.assertEqual(payload["origin"], descriptors.ORIGIN_RUNTIME)
        self.assertEqual(official_preferences_for(subject).selection, selection)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_a_named_default_that_cannot_resolve_is_a_bounded_fault(self):
        subject = self._subject("vanished-default")
        card = self._card(subject)
        (self.store / card["stored_identity"]).unlink()
        descriptor = describe_portrait(subject)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.default:{card['image_id']}",
                    descriptors.PORTRAIT_RANK_DEFAULT,
                )
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["reason"], descriptors.REASON_GENERATED_OUTPUT_MISSING
        )
        # A vanished stored output is never handed to another card and never
        # re-derives a "missing" generation: the record still holds the card.
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_DONE)
        self.assertEqual(descriptor["terminal"]["resource"]["origin"], descriptors.ORIGIN_SILHOUETTE)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    def test_an_unset_selection_and_default_add_no_attempt(self):
        subject = self._subject("no-art")
        entity = self._character("no-art", provenance=False)
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(descriptor["attempts"], [])
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_MISSING)
        self.assertEqual(descriptor["generation_subject"], subject.full())
        self.assertIsNotNone(descriptor["terminal"])

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    @covers_requirement("artwork-descriptor::descriptors-preserve-independent-artwork-facts")
    def test_a_missing_completed_output_is_its_own_fault(self):
        subject = self._subject("missing-output")
        self._settle_classic(subject, write=False)
        with patch("world.art.presenter.log_warn") as warned:
            descriptor = describe_portrait(subject)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.classic:{subject.full()}",
                    descriptors.PORTRAIT_RANK_CLASSIC,
                )
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["reason"], descriptors.REASON_GENERATED_OUTPUT_MISSING
        )
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_DONE)
        events = [call.args[0] for call in warned.call_args_list if call.args]
        self.assertEqual(events.count("art_asset_output_missing"), 1)
        # The flat contract keeps its own truthful placeholder for the same case.
        self.assertEqual(resolve_subject(subject)["kind"], PLACEHOLDER_UNAVAILABLE)

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    @covers_requirement("artwork-descriptor::descriptors-preserve-independent-artwork-facts")
    def test_a_recorded_failure_is_reported_without_touching_state(self):
        subject = self._subject("failed-job")
        entity = self._character("failed-job")
        with override_settings(ART_SCHEDULER_ENABLED=False):
            self._settle_classic(
                subject, status=ArtAssetStatus.FAILED, error="sd_unreachable", write=False
            )
            before = self._state(subject)
            descriptor = describe_portrait(subject, entity)
            self.assertEqual(self._state(subject), before)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.classic:{subject.full()}",
                    descriptors.PORTRAIT_RANK_CLASSIC,
                )
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["reason"], descriptors.REASON_GENERATION_FAILED
        )
        # The recorded failure is the descriptor's own independent fact.
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        self.assertEqual(descriptor["generation_subject"], subject.full())
        # Generation disabled and nothing presentable: the terminal carries the
        # presentation while the state stays truthful.
        self.assertEqual(descriptor["terminal"]["resource"]["origin"], descriptors.ORIGIN_SILHOUETTE)
        self.assertEqual(resolve_subject(subject, entity=entity)["origin"], "silhouette")

    @covers_requirement(
        "official-art-resolution::every-presentation-payload-distinguishes-official-runtime-and-silhouette-origin"
    )
    def test_a_finished_official_image_never_completes_a_failed_generation(self):
        subject = self._subject("official-with-failure")
        entity = self._character("official-with-failure")
        self._settle_classic(
            subject, status=ArtAssetStatus.FAILED, error="sd_unreachable", write=False
        )
        identity = self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.classic:{subject.full()}",
                    descriptors.PORTRAIT_RANK_CLASSIC,
                ),
                (
                    "image",
                    f"portrait.official:preset/{_PRESET_KEY}",
                    descriptors.PORTRAIT_RANK_OFFICIAL,
                ),
            ],
        )
        candidate = descriptor["attempts"][1]["resource"]
        self.assertEqual(candidate["origin"], descriptors.ORIGIN_OFFICIAL)
        self.assertEqual(candidate["resource_id"], identity)
        self.assertEqual(candidate["url"], current_catalog().url_for(identity))
        # Availability of the read-only image and the recorded failure are
        # independent facts of the same descriptor.
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        payload = resolve_subject(subject, entity=entity)
        self.assertEqual(payload["origin"], descriptors.ORIGIN_OFFICIAL)
        self.assertEqual(payload["url"], candidate["url"])
        self.assertIsNone(payload["status"])

    @covers_requirement(
        "art-source-fault-facts::faults-are-attributed-to-requested-sources"
    )
    @covers_requirement("artwork-descriptor::descriptors-preserve-independent-artwork-facts")
    def test_a_metadata_fault_names_its_own_degraded_image(self):
        subject = self._subject("degraded-metadata")
        entity = self._character("degraded-metadata")
        # A manifest rectangle that cannot lie inside the unit square degrades
        # the declared metadata; the substitution is a retained startup fact.
        identity = self._index(face_rect={"x": 0.5, "y": 0.0, "w": 0.9, "h": 0.9})
        descriptor = describe_portrait(subject, entity)
        source = f"portrait.official:preset/{_PRESET_KEY}"
        self.assertEqual(
            self._ordered(descriptor),
            [
                ("fault", f"portrait.official:{identity}", descriptors.PORTRAIT_RANK_OFFICIAL),
                ("image", source, descriptors.PORTRAIT_RANK_OFFICIAL),
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["reason"], descriptors.REASON_METADATA_INVALID
        )
        candidate = descriptor["attempts"][1]["resource"]
        # Safe geometry accompanies the fault: the fitted rectangle, validated
        # once and shared with the flat payload.
        fitted = default_face_rect({"width": 4, "height": 4})
        self.assertEqual(candidate["geometry"]["face_rect"], fitted)
        self.assertEqual(candidate["geometry"]["aspect_ratio"], GALLERY_ASPECT_RATIO)
        payload = resolve_subject(subject, entity=entity)
        self.assertEqual(payload["face_rect"], fitted)
        self.assertEqual(payload["status"], None)

    @covers_requirement(
        "art-source-fault-facts::faults-are-attributed-to-requested-sources"
    )
    def test_a_replaced_manifest_default_and_its_substitute_never_collide(self):
        # Real startup admission: the manifest declares a default no listing
        # entry carries, so the deterministic substitute is admitted with the
        # declared default's own retained fault before it.
        subject = self._subject("replaced-default")
        entity = self._character("replaced-default")
        identity = self._index(default="gone.png")
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.official:preset/{_PRESET_KEY}/gone.png",
                    descriptors.PORTRAIT_RANK_OFFICIAL,
                ),
                (
                    "fault",
                    f"portrait.official:{identity}",
                    descriptors.PORTRAIT_RANK_OFFICIAL,
                ),
                (
                    "image",
                    f"portrait.official:preset/{_PRESET_KEY}",
                    descriptors.PORTRAIT_RANK_OFFICIAL,
                ),
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["reason"],
            descriptors.REASON_EXPLICIT_REFERENCE_MISSING,
        )
        self.assertEqual(
            descriptor["attempts"][1]["reason"], descriptors.REASON_METADATA_INVALID
        )
        self.assertEqual(descriptor["attempts"][2]["resource"]["resource_id"], identity)
        # Two faults of one layer must never collide on one source id and rank:
        # the canonical wire validator refuses such a descriptor outright.
        artwork_wire.validate_artwork(descriptor)

    @covers_requirement("artwork-descriptor::descriptors-preserve-independent-artwork-facts")
    def test_a_recorded_gallery_failure_is_the_subjects_generation_truth(self):
        subject = self._subject("gallery-failure")
        entity = self._character("gallery-failure", provenance=False)
        # The shipped gallery writer records the failure; no card and no
        # classic record exist, so the failure is the only generation fact.
        record_error(subject, "sd_unreachable")
        with override_settings(ART_SCHEDULER_ENABLED=False):
            descriptor = describe_portrait(subject, entity)
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        self.assertEqual(descriptor["generation_subject"], subject.full())
        self.assertEqual(descriptor["attempts"], [])
        # A stored card never erases the recorded failure either.
        self._card(subject)
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_FAILED)
        self.assertEqual(len(descriptor["attempts"]), 1)

    @covers_requirement(
        "official-art-resolution::official-payloads-are-catalog-derived-confined-and-fall-through-when-unresolvable"
    )
    @covers_requirement(
        "portrait-source-attempts::portrait-source-order-retains-current-policy"
    )
    def test_an_unconfigured_official_source_adds_no_fault(self):
        subject = self._subject("no-reference")
        entity = self._character("no-reference", provenance=False)
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(descriptor["attempts"], [])
        self.assertNotIn(
            descriptors.PORTRAIT_RANK_OFFICIAL,
            [attempt["rank"] for attempt in descriptor["attempts"]],
        )

    @covers_requirement(
        "art-gallery-resolution::the-chain-ends-at-one-fallback-seam"
    )
    def test_a_scene_subject_has_no_person_source_and_no_terminal(self):
        scene = ArtSubject(ArtSubjectKind.SCENE, _SYNTH_SCENE)
        descriptor = describe_portrait(scene)
        self.assertEqual(descriptor["attempts"], [])
        self.assertIsNone(descriptor["terminal"])
        record = self._settle_classic(scene)
        descriptor = describe_portrait(scene)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "image",
                    f"portrait.classic:{scene.full()}",
                    descriptors.PORTRAIT_RANK_CLASSIC,
                )
            ],
        )
        self.assertEqual(
            descriptor["attempts"][0]["resource"]["geometry"]["aspect_ratio"],
            record.db.aspect_ratio,
        )
        self.assertIsNone(descriptor["terminal"])

    @covers_requirement(
        "official-art-resolution::official-payloads-are-catalog-derived-confined-and-fall-through-when-unresolvable"
    )
    def test_describe_entity_answers_a_refusal_descriptor(self):
        """An admitted entity with no eligible subject still gets its own facts.

        Catalog admission is a membership decision the caller already made, so
        the enumerator never answers ``None`` for an entity it was handed: it
        answers the complete REFUSAL descriptor — no image attempt, no
        generated subject key, no prompt — plus the deterministic
        attribute-selected alpha terminal. Only a genuinely absent entity is
        ``None``.
        """
        plain = create_object(PlayerCharacter, key="attempt-ineligible")
        plain.age = plain.apparent_age = 30
        refused = describe_entity(plain)
        self.assertEqual(refused["attempts"], [])
        self.assertIsNone(refused["generation_subject"])
        self.assertIsNone(refused["generation_state"])
        self.assertEqual(refused["retention_sources"], [])
        self.assertEqual(refused["terminal"]["kind"], "alpha_mask")
        self.assertEqual(refused["terminal"]["resource"]["origin"], "silhouette")
        self.assertEqual(refused["subject_id"], str(plain.pk))
        plain.db.portrait_policy = {"mode": "named", "stable_key": "ineligible"}
        plain.age = "thirty"
        ineligible = describe_entity(plain)
        self.assertEqual(ineligible["attempts"], [])
        self.assertIsNone(ineligible["generation_subject"])
        self.assertEqual(ineligible["terminal"]["kind"], "alpha_mask")
        # A refused subject discloses NO subject key: the descriptor names the
        # position's opaque runtime identity, never the rejected policy's own
        # stable key.
        self.assertEqual(ineligible["subject_id"], str(plain.pk))
        self.assertNotIn("ineligible", repr(ineligible))
        plain.age = 30
        descriptor = describe_entity(plain)
        self.assertEqual(descriptor["subject_id"], "portrait:character:ineligible")
        self.assertIsNone(describe_entity(object()))

    @covers_requirement("artwork-descriptor::source-priority-and-retained-access-are-explicit")
    def test_every_enumeration_is_read_only_and_reproducible(self):
        subject = self._subject("stable-attempts")
        entity = self._character("stable-attempts")
        self._card(subject)
        self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        before = self._state(subject)
        first = describe_portrait(subject, entity)
        second = describe_portrait(subject, entity)
        self.assertEqual(first, second)
        self.assertEqual(self._state(subject), before)
        candidate = next(
            attempt for attempt in first["attempts"] if attempt["type"] == "image"
        )
        self.assertEqual(
            candidate["source_id"], f"portrait.default:{cards_for(subject)[0]['image_id']}"
        )


class PortraitAttemptSmokeTests(_PortraitAttemptCase):
    """The production boundary: real writers, real admission, one real selection."""

    @covers_requirement(
        "art-gallery-resolution::display-resolution-is-one-deterministic-chain-from-equipment-to-fallback"
    )
    @covers_requirement(
        "art-source-fault-facts::faults-are-attributed-to-requested-sources"
    )
    @covers_requirement(
        "art-gallery-fallback::the-fallback-seam-supplies-a-url-and-a-face-rectangle-and-reports-its-use"
    )
    def test_real_gallery_official_and_alpha_resolution(self):
        subject = self._subject("boundary")
        entity = self._character("boundary")
        card = self._card(subject)
        identity = self._index(face_rect=dict(_OFFICIAL_RECT), stage=dict(_OFFICIAL_STAGE))
        before = self._state(subject)
        # Step 1: the readable default card is what production presents, and the
        # canonical enumeration names exactly that source at its own rank.
        payload = resolve_subject(subject, entity=entity)
        descriptor = describe_portrait(subject, entity)
        candidate = descriptor["attempts"][-1]
        self.assertEqual(payload["origin"], descriptors.ORIGIN_RUNTIME)
        self.assertEqual(payload["url"], f"/art/{card['stored_identity']}")
        self.assertEqual(candidate["source_id"], f"portrait.default:{card['image_id']}")
        self.assertEqual(candidate["resource"]["url"], payload["url"])
        self.assertEqual(candidate["resource"]["geometry"]["face_rect"], payload["face_rect"])
        self.assertEqual(candidate["resource"]["geometry"]["stage"], payload["stage"])
        self.assertEqual(candidate["resource"]["geometry"]["aspect_ratio"], payload["aspect_ratio"])
        self.assertEqual(descriptor["generation_state"], descriptors.GENERATION_DONE)
        self.assertEqual(descriptor["terminal"]["resource"]["url"], payload["fallback"]["url"])
        self.assertEqual(descriptor["retention_sources"], [])
        # Step 2: the stored card's file vanishes (no restart gap: the next read
        # simply finds it gone), so the explicit default fault leads and the
        # admitted official image becomes the first real candidate.
        (self.store / card["stored_identity"]).unlink()
        expected = self._state(subject)
        payload = resolve_subject(subject, entity=entity)
        descriptor = describe_portrait(subject, entity)
        self.assertEqual(
            self._ordered(descriptor),
            [
                (
                    "fault",
                    f"portrait.default:{card['image_id']}",
                    descriptors.PORTRAIT_RANK_DEFAULT,
                ),
                (
                    "image",
                    f"portrait.official:preset/{_PRESET_KEY}",
                    descriptors.PORTRAIT_RANK_OFFICIAL,
                ),
            ],
        )
        official = descriptor["attempts"][1]["resource"]
        self.assertEqual(official["resource_id"], identity)
        self.assertEqual(official["origin"], descriptors.ORIGIN_OFFICIAL)
        self.assertEqual(official["geometry"]["face_rect"], dict(_OFFICIAL_RECT))
        self.assertEqual(official["geometry"]["stage"], dict(_OFFICIAL_STAGE))
        self.assertEqual(payload["origin"], descriptors.ORIGIN_OFFICIAL)
        self.assertEqual(payload["url"], official["url"])
        self.assertEqual(payload["face_rect"], dict(_OFFICIAL_RECT))
        self.assertEqual(payload["stage"], dict(_OFFICIAL_STAGE))
        self.assertIsNone(payload["status"])
        # The alpha terminal is the subject's own committed silhouette, carried
        # beside the presented image.
        self.assertTrue(descriptor["terminal"]["source_id"].startswith("portrait.alpha:"))
        self.assertEqual(descriptor["terminal"]["rank"], descriptors.PORTRAIT_RANK_ALPHA)
        self.assertEqual(payload["fallback"]["url"], descriptor["terminal"]["resource"]["url"])
        self.assertEqual(
            payload["fallback"]["face_rect"], descriptor["terminal"]["resource"]["geometry"]["face_rect"]
        )
        # Nothing was created, deleted, repaired, or written by any of it: the
        # only difference from the first phase is the file this test deleted.
        self.assertEqual(self._state(subject), expected)
        self.assertEqual(official_preferences_for(subject).selection, before[3])


if __name__ == "__main__":
    unittest.main()
