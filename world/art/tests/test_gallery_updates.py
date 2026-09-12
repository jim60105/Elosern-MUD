"""Tests for the in-place gallery card writers and the public subject-key resolver.

``EvenniaTestCase`` covers the two sole-writer card updates
(``update_card_face_rect`` / ``update_card_binding``) against a temporary
store root — verbatim field updates, order/default byte-stability, the
tolerant-locate refusals, the kind capability gate, and the one
``gallery_card_updated`` event — plus the read-only
``resolve_gallery_subject_by_key`` seam over a synthetic catalog scope
(live character, registry tier, dead key, bad prefix, kind collision).
"""

from contextlib import contextmanager
import copy
import tempfile
from pathlib import Path
from unittest.mock import patch
import uuid

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.art import gallery_kinds
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecord,
    GalleryRecordError,
    append_card,
    cards_for,
    record_for,
    update_card_binding,
    update_card_face_rect,
)
from world.art.service import resolve_gallery_subject_by_key
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    monster_subject_for,
)
from world.tests.synthetic_data import (
    SYNTH_ARCHETYPES,
    SYNTH_MONSTER_TIERS,
    synthetic_registries,
)

from tools.spec_traceability import covers_requirement


def _open_synthetic_scope(case, *targets, extra=None):
    """Enter a synthetic-catalog scope bound to one test case's lifecycle.

    The same kit pattern ``world/art/tests/test_service.py`` uses: the scope
    must open before ``super().setUp()`` and closes with the test.
    """
    scope = synthetic_registries(*targets, extra=extra)
    scope.__enter__()
    case.addCleanup(scope.__exit__, None, None, None)
    return scope


def _character(key="t_update_hero"):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _monster(key="t_update_goblin"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


def _new_id():
    return str(uuid.uuid4())


def _identity(subject, image_id, extension=".png"):
    kind_dir = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
    return f"gallery/{kind_dir}/{subject.key}/{image_id}{extension}"


def _card_fields(subject, image_id=None, **overrides):
    """One complete generated-source card, overridable per key."""
    image_id = image_id or _new_id()
    fields = {
        "image_id": image_id,
        "stored_identity": _identity(subject, image_id),
        "prompt": {"positive": "a hero", "negative": "blur"},
        "seed": 1234,
        "checkpoint": "realVision.safetensors",
        # Declaration-aware, mirroring world/art/tests/test_gallery.py: a
        # kind with no declared field selection stores empty provenance.
        "requested_fields": (
            ["appearance"]
            if gallery_kinds.capabilities_for(subject.kind.value).supports_field_selection
            else []
        ),
        "binding": None,
        "source": "generated",
    }
    fields.update(overrides)
    return fields


def _binding(mask=("armor",), snapshot=None):
    return {
        "mask": list(mask),
        "snapshot": (
            snapshot if snapshot is not None else {"armor": "t_wayfarer_pass"}
        ),
    }


def _raw_cards(subject):
    """The persisted raw card list, re-read from the database row."""
    record = GalleryRecord.objects.get(pk=record_for(subject).pk)
    return copy.deepcopy(
        [
            dict(entry) if isinstance(entry, dict) else entry
            for entry in record.db.cards or []
        ]
    )


class CardFaceRectUpdateTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _make_file(self, identity, content=b"image"):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_face_rect_update_equals_the_submitted_rect_exactly(self):
        subject = _character("rect_exact")
        image_id = _new_id()
        image_file = self._make_file(_identity(subject, image_id), b"bytes stay")
        append_card(subject, **_card_fields(subject, image_id=image_id))
        default_before = record_for(subject).db.default_image_id
        rect = {"x": 0.1, "y": 0.2, "w": 0.35, "h": 0.4}
        with patch("world.art.gallery.log_info") as info:
            updated = update_card_face_rect(subject, image_id, rect)
        self.assertEqual(updated["face_rect"], rect)
        stored = cards_for(subject)[0]
        self.assertEqual(stored["face_rect"], rect)
        # Every other field is byte-stable, and so is the record default.
        expected = copy.deepcopy(_card_fields(subject, image_id=image_id))
        actual = {key: copy.deepcopy(value) for key, value in stored.items()}
        self.assertEqual(actual.pop("face_rect"), rect)
        actual.pop("created_at")
        self.assertEqual(actual, expected)
        self.assertEqual(record_for(subject).db.default_image_id, default_before)
        # No file write happened: the confined image file is byte-identical.
        self.assertTrue(image_file.exists())
        self.assertEqual(image_file.read_bytes(), b"bytes stay")
        events = [
            c
            for c in info.call_args_list
            if c.args and c.args[0] == "gallery_card_updated"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0].kwargs["context"],
            {
                "subject": subject.full(),
                "image_id": image_id,
                "kind": subject.kind.value,
                "field": "face_rect",
            },
        )

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_an_update_never_reapplies_the_shared_default_constant(self):
        # DEFAULT_FACE_RECT is only the append-time default; an update
        # stores the submitted rect (here: the full-coverage legal extreme)
        # and never rewrites it back to the constant.
        subject = _character("rect_full")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        full = {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
        update_card_face_rect(subject, image_id, full)
        stored = cards_for(subject)[0]
        self.assertEqual(stored["face_rect"], full)
        self.assertNotEqual(stored["face_rect"], DEFAULT_FACE_RECT)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_updating_the_middle_card_keeps_order_and_siblings_byte_stable(self):
        subject = _character("rect_middle")
        first, middle, last = _new_id(), _new_id(), _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        append_card(subject, **_card_fields(subject, image_id=middle))
        append_card(subject, **_card_fields(subject, image_id=last))
        before = _raw_cards(subject)
        default_before = record_for(subject).db.default_image_id
        rect = {"x": 0.4, "y": 0.4, "w": 0.5, "h": 0.5}
        update_card_face_rect(subject, middle, rect)
        after = _raw_cards(subject)
        self.assertEqual([entry["image_id"] for entry in after], [first, middle, last])
        self.assertEqual(record_for(subject).db.default_image_id, default_before)
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[2], before[2])
        changed = {key for key in before[1] if before[1][key] != after[1][key]}
        self.assertEqual(changed, {"face_rect"})
        self.assertEqual(after[1]["face_rect"], rect)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_malformed_rect_refuses_and_changes_nothing(self):
        subject = _character("rect_malformed")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        before = _raw_cards(subject)
        for label, rect in {
            "outside_unit_square": {"x": 0.6, "y": 0.0, "w": 0.5, "h": 0.4},
            "zero_width": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.5},
            "string_value": {"x": "0.0", "y": 0.0, "w": 0.5, "h": 0.5},
            "not_a_mapping": [0.0, 0.0, 0.5, 0.5],
        }.items():
            with self.subTest(rect=label):
                with self.assertRaises(GalleryRecordError):
                    update_card_face_rect(subject, image_id, rect)
                self.assertEqual(_raw_cards(subject), before)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_an_id_no_valid_card_carries_refuses_in_the_remove_card_form(self):
        subject = _character("rect_unknown")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        # A never-minted id: the remove_card miss form, record unchanged.
        missing = _new_id()
        before = _raw_cards(subject)
        with self.assertRaises(GalleryRecordError) as refused:
            update_card_face_rect(subject, missing, dict(DEFAULT_FACE_RECT))
        self.assertEqual(
            str(refused.exception), f"no card with image_id {missing!r} exists"
        )
        self.assertEqual(_raw_cards(subject), before)
        # A malformed entry matching the id: the tolerant read refuses to
        # surface it, so updating it would launder corruption. The locate
        # reports it once, exactly as the tolerant read does.
        record = record_for(subject)
        broken = dict(
            _card_fields(subject, face_rect=dict(DEFAULT_FACE_RECT)),
            image_id=_new_id(),
            source="imported",
        )
        record.db.cards = [*record.db.cards, broken]
        broken_id = broken["image_id"]
        before_with_broken = _raw_cards(subject)
        with patch("world.art.gallery.log_warn") as warn:
            with self.assertRaises(GalleryRecordError) as refused:
                update_card_face_rect(subject, broken_id, dict(DEFAULT_FACE_RECT))
        self.assertEqual(
            str(refused.exception), f"no card with image_id {broken_id!r} exists"
        )
        self.assertEqual(_raw_cards(subject), before_with_broken)
        events = [
            c
            for c in warn.call_args_list
            if c.args and c.args[0] == "gallery_card_invalid"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["image_id"], broken_id)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_subject_with_no_record_refuses_with_the_record_form(self):
        subject = _character("rect_norecord")
        with self.assertRaises(GalleryRecordError) as refused:
            update_card_face_rect(subject, _new_id(), dict(DEFAULT_FACE_RECT))
        self.assertEqual(str(refused.exception), "this subject has no gallery record")
        self.assertIsNone(record_for(subject))

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_malformed_sibling_before_the_target_never_blocks_the_update(self):
        # The tolerant locate SKIPS malformed entries and keeps walking: a
        # broken entry anywhere in the list cannot hide a later valid card,
        # and the refusal paths emit no update event.
        subject = _character("rect_sibling")
        first, target = _new_id(), _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        append_card(subject, **_card_fields(subject, image_id=target))
        record = record_for(subject)
        record.db.cards = ["not a mapping", *record.db.cards]
        broken_before = _raw_cards(subject)
        rect = {"x": 0.0, "y": 0.5, "w": 0.5, "h": 0.5}
        with patch("world.art.gallery.log_warn"), patch(
            "world.art.gallery.log_info"
        ) as info:
            updated = update_card_face_rect(subject, target, rect)
        self.assertEqual(updated["face_rect"], rect)
        after = _raw_cards(subject)
        self.assertEqual(len(after), 3)
        self.assertEqual(after[0], broken_before[0])  # the broken entry survives
        self.assertEqual(after[1]["face_rect"], broken_before[1]["face_rect"])
        self.assertEqual(after[2]["face_rect"], rect)
        # Exactly one event — the update — on the successful call…
        events = [
            c
            for c in info.call_args_list
            if c.args and c.args[0] == "gallery_card_updated"
        ]
        self.assertEqual(len(events), 1)
        # …and zero on a refused one.
        with patch("world.art.gallery.log_info") as info:
            with self.assertRaises(GalleryRecordError):
                update_card_face_rect(subject, _new_id(), rect)
        self.assertEqual(
            [
                c
                for c in info.call_args_list
                if c.args and c.args[0] == "gallery_card_updated"
            ],
            [],
        )


class CardBindingUpdateTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()

    def tearDown(self):
        self.art_settings.disable()
        self.tempdir.cleanup()
        super().tearDown()

    def _make_file(self, identity, content=b"image"):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_binding_update_stores_the_normalized_binding_and_events_once(self):
        subject = _character("bind_save")
        image_id = _new_id()
        image_file = self._make_file(_identity(subject, image_id), b"bytes stay")
        append_card(subject, **_card_fields(subject, image_id=image_id))
        with patch("world.art.gallery.log_info") as info:
            updated = update_card_binding(
                subject,
                image_id,
                _binding(
                    mask=["armor", "weapon_main"],
                    snapshot={
                        "armor": "t_wayfarer_pass",
                        "weapon_main": "t_thorn_knife",
                    },
                ),
            )
        # Normalized into the declared slot order, snapshot over the mask.
        self.assertEqual(updated["binding"]["mask"], ["weapon_main", "armor"])
        self.assertEqual(
            updated["binding"]["snapshot"],
            {"weapon_main": "t_thorn_knife", "armor": "t_wayfarer_pass"},
        )
        stored = cards_for(subject)[0]
        self.assertEqual(stored["binding"], updated["binding"])
        # Placement metadata only: the face rect and default stay put.
        self.assertEqual(stored["face_rect"], DEFAULT_FACE_RECT)
        self.assertEqual(record_for(subject).db.default_image_id, image_id)
        # A binding save never touches the card's file.
        self.assertTrue(image_file.exists())
        self.assertEqual(image_file.read_bytes(), b"bytes stay")
        events = [
            c
            for c in info.call_args_list
            if c.args and c.args[0] == "gallery_card_updated"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0].kwargs["context"],
            {
                "subject": subject.full(),
                "image_id": image_id,
                "kind": subject.kind.value,
                "field": "binding",
            },
        )

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_an_explicit_none_binding_unbinds(self):
        subject = _character("bind_unbind")
        image_id = _new_id()
        append_card(
            subject, **_card_fields(subject, image_id=image_id, binding=_binding())
        )
        self.assertIsNotNone(cards_for(subject)[0]["binding"])
        updated = update_card_binding(subject, image_id, None)
        self.assertIsNone(updated["binding"])
        self.assertIsNone(cards_for(subject)[0]["binding"])
        self.assertEqual(len(cards_for(subject)), 1)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_malformed_binding_refuses_and_changes_nothing(self):
        subject = _character("bind_malformed")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        before = _raw_cards(subject)
        for label, binding in {
            "mask_snapshot_mismatch": {
                "mask": ["armor"],
                "snapshot": {
                    "armor": "t_wayfarer_pass",
                    "weapon_main": "t_thorn_knife",
                },
            },
            "unknown_slot": {"mask": ["t_boots"], "snapshot": {"t_boots": "t_boots"}},
            "empty_mask": {"mask": [], "snapshot": {}},
            "not_a_mapping": "t_wayfarer_pass",
        }.items():
            with self.subTest(binding=label):
                with self.assertRaises(GalleryRecordError):
                    update_card_binding(subject, image_id, binding)
                self.assertEqual(_raw_cards(subject), before)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_an_unknown_card_id_refuses_in_the_remove_card_form(self):
        subject = _character("bind_unknown")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        before = _raw_cards(subject)
        missing = _new_id()
        with self.assertRaises(GalleryRecordError) as refused:
            update_card_binding(subject, missing, _binding())
        self.assertEqual(
            str(refused.exception), f"no card with image_id {missing!r} exists"
        )
        self.assertEqual(_raw_cards(subject), before)

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_a_binding_for_a_kind_without_binding_support_is_refused(self):
        subject = _monster("bind_goblin")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        before = _raw_cards(subject)
        with patch("world.art.gallery.log_info") as info:
            with self.assertRaises(GalleryRecordError) as refused:
                update_card_binding(subject, image_id, _binding())
        # The typed refusal NAMES the undeclared capability, mirroring the
        # service seam's wording (gallery-card-update-api, D2).
        self.assertIn(
            f"subject kind {subject.kind.value!r} declares no binding support",
            str(refused.exception),
        )
        self.assertEqual(_raw_cards(subject), before)
        # No event fires for a refused update.
        events = [
            c
            for c in info.call_args_list
            if c.args and c.args[0] == "gallery_card_updated"
        ]
        self.assertEqual(events, [])

    @covers_requirement(
        "art-gallery-model::existing-cards-accept-in-place-face-rect-and-binding-updates-through-the-sole-writer"
    )
    def test_the_gate_is_unconditional_and_follows_the_declaration(self):
        # The refusal is unconditional: a monster with NO record gets the
        # capability error, never the no-record error.
        subject = _monster("bind_fresh_goblin")
        with self.assertRaises(GalleryRecordError) as refused:
            update_card_binding(subject, _new_id(), _binding())
        self.assertIn("declares no binding support", str(refused.exception))
        self.assertIsNone(record_for(subject))
        # Declaration-driven: a CHARACTER patched to drop binding support is
        # refused through the same typed path, and an explicit None unbind
        # stays legal for the unbound declaration.
        carded = _character("bind_declared")
        append_card(carded, **_card_fields(carded))
        image_id = cards_for(carded)[0]["image_id"]
        unbound = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(supports_bindings=False)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: unbound},
        ):
            with self.assertRaises(GalleryRecordError) as refused:
                update_card_binding(carded, image_id, _binding())
            self.assertIn("declares no binding support", str(refused.exception))
            updated = update_card_binding(carded, image_id, None)
        self.assertIsNone(updated["binding"])
        self.assertIsNone(cards_for(carded)[0]["binding"])


class SubjectKeyResolverTests(EvenniaTestCase):
    def setUp(self):
        _open_synthetic_scope(self, "archetypes", "monster_tiers")
        super().setUp()
        self.player = create_object(PlayerCharacter, key="resolver-player")
        self.player.db.age = 22
        self.player.db.apparent_age = 22
        self.player.db.portrait_policy = {"mode": "named", "stable_key": "t_rail_hero"}

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_a_live_character_key_resolves_to_subject_plus_live_entity(self):
        subject, entity = resolve_gallery_subject_by_key("portrait:character:t_rail_hero")
        self.assertEqual(subject, ArtSubject(ArtSubjectKind.CHARACTER, "t_rail_hero"))
        self.assertEqual(entity, self.player)
        # Read-only: no gallery record was created for the subject, and the
        # entity's own state is byte-stable.
        self.assertIsNone(record_for(subject))
        self.assertEqual(
            self.player.db.portrait_policy,
            {"mode": "named", "stable_key": "t_rail_hero"},
        )
        self.assertEqual(self.player.db.age, 22)

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_the_resolver_checks_no_age_precondition(self):
        # The preconditions stay where they are: a character whose declared
        # age precondition would reject a GENERATION request still resolves,
        # because the resolver checks nothing but the key.
        ageless = create_object(PlayerCharacter, key="resolver-ageless")
        ageless.db.portrait_policy = {"mode": "named", "stable_key": "t_rail_ageless"}
        subject, entity = resolve_gallery_subject_by_key(
            "portrait:character:t_rail_ageless"
        )
        self.assertEqual(subject.key, "t_rail_ageless")
        self.assertEqual(entity, ageless)

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_a_registered_monster_tier_key_resolves_through_the_producer(self):
        tier_key = sorted(SYNTH_MONSTER_TIERS)[0]
        subject, entity = resolve_gallery_subject_by_key(f"portrait:monster:{tier_key}")
        self.assertEqual(subject, monster_subject_for(tier_key))
        self.assertIsNone(entity)

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_an_unregistered_monster_tier_key_raises_the_typed_error(self):
        with self.assertRaises(ArtSubjectError):
            resolve_gallery_subject_by_key("portrait:monster:t_never_registered")

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_a_dead_character_key_raises_the_typed_error_naming_the_key(self):
        with self.assertRaises(ArtSubjectError) as refused:
            resolve_gallery_subject_by_key("portrait:character:t_rail_dead")
        self.assertIn("t_rail_dead", str(refused.exception))

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_an_unknown_prefix_raises_the_typed_error(self):
        for label, key in {
            "no_prefix": "t_rail_hero",
            "unknown_kind": "gallery:t_rail_hero",
            "empty": "",
        }.items():
            with self.subTest(key=label):
                with self.assertRaises(ArtSubjectError):
                    resolve_gallery_subject_by_key(key)

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_a_malformed_key_under_a_valid_prefix_raises_the_typed_error(self):
        with self.assertRaises(ArtSubjectError):
            resolve_gallery_subject_by_key("portrait:character:")
        with self.assertRaises(ArtSubjectError):
            resolve_gallery_subject_by_key("portrait:character:t_bad|key")

    @covers_requirement(
        "art-gallery-model::one-public-read-only-seam-resolves-a-serialized-subject-key-to-subject-and-entity"
    )
    def test_a_scene_key_never_resolves_even_under_a_character_key_collision(self):
        # Resolution dispatches on the key's OWN kind: a scene key may
        # legally share its text with a living character's stable key, and
        # the scene key must still be the typed miss, never that
        # character's subject.
        archetype = sorted(SYNTH_ARCHETYPES)[0]
        collider = create_object(PlayerCharacter, key="resolver-collider")
        collider.db.portrait_policy = {"mode": "named", "stable_key": archetype}
        with self.assertRaises(ArtSubjectError):
            resolve_gallery_subject_by_key(f"scene:{archetype}")
        # The same text under the character prefix still resolves the
        # character — the collision cuts only one way.
        subject, entity = resolve_gallery_subject_by_key(f"portrait:character:{archetype}")
        self.assertEqual(subject.kind, ArtSubjectKind.CHARACTER)
        self.assertEqual(subject.key, archetype)
        self.assertEqual(entity, collider)
