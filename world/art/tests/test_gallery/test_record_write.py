"""Slice of ``test_gallery``: GalleryRecordWriteTests (append, default, monster-cap and write-seam half; the deletion/tolerant-read/error half is the same-named sibling class in ``test_record_read_error.py``).
"""
import ast
import tempfile
from pathlib import Path
from unittest.mock import patch
import uuid
import unittest
from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase
from world.art import gallery_kinds
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecord,
    GalleryRecordError,
    SLOT_ORDER,
    append_card,
    cards_for,
    clear_error,
    erroring_subjects,
    gallery_states,
    record_error,
    record_for,
    record_key,
    remove_card,
    set_default,
    snapshot_for,
    validate_binding,
    validate_card,
    validate_face_rect,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

from ._support import (
    _character,
    _monster,
    _scene,
    _new_id,
    _identity,
    _card_fields,
)

class GalleryRecordWriteTests(EvenniaTestCase):
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

    def _make_file(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        return target

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_an_unwritten_subject_reads_empty_and_creates_nothing(self):
        subject = _character("nobody")
        self.assertEqual(cards_for(subject), [])
        self.assertIsNone(record_for(subject))
        self.assertEqual(GalleryRecord.objects.filter(db_key=record_key(subject)).count(), 0)

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_the_first_append_creates_the_record_and_becomes_the_default(self):
        subject = _character()
        image_id = _new_id()
        stored = append_card(subject, **_card_fields(subject, image_id=image_id))
        record = record_for(subject)
        self.assertIsNotNone(record)
        self.assertEqual(record.db.kind, ArtSubjectKind.CHARACTER.value)
        self.assertEqual(record.db.subject_key, subject.key)
        self.assertEqual(record.db.default_image_id, image_id)
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [image_id])
        self.assertEqual(stored["image_id"], image_id)

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_a_later_append_keeps_the_default_and_appends_in_order(self):
        subject = _character("twocards")
        first = _new_id()
        second = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        append_card(subject, **_card_fields(subject, image_id=second))
        record = record_for(subject)
        self.assertEqual(record.db.default_image_id, first)
        self.assertEqual(
            [card["image_id"] for card in cards_for(subject)], [first, second]
        )

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_setting_an_unknown_default_is_rejected_and_changes_nothing(self):
        subject = _character("defaultme")
        first = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        with self.assertRaises(GalleryRecordError):
            set_default(subject, _new_id())
        self.assertEqual(record_for(subject).db.default_image_id, first)
        second = _new_id()
        append_card(subject, **_card_fields(subject, image_id=second))
        set_default(subject, second)
        self.assertEqual(record_for(subject).db.default_image_id, second)

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_set_default_rejects_a_record_a_scene_and_an_unwritten_subject(self):
        with self.assertRaises(GalleryRecordError):
            set_default(_character("ghost"), _new_id())
        with self.assertRaises(GalleryRecordError):
            set_default(_scene(), _new_id())
        with self.assertRaises(GalleryRecordError):
            append_card(_scene(), **{"image_id": _new_id()})

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_duplicate_image_id_is_rejected_and_the_list_is_unchanged(self):
        subject = _character("dupes")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        with self.assertRaises(GalleryRecordError):
            append_card(subject, **_card_fields(subject, image_id=image_id))
        self.assertEqual(len(cards_for(subject)), 1)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_seed_provenance_card_without_prompt_or_seed_is_accepted(self):
        subject = _character("seeded")
        stored = append_card(
            subject,
            **_card_fields(
                subject, prompt=None, seed=None, checkpoint=None, source="seed"
            ),
        )
        self.assertIsNone(stored["prompt"])
        self.assertIsNone(stored["seed"])
        self.assertEqual(len(cards_for(subject)), 1)

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_append_applies_the_shared_rect_and_stores_explicit_rects_verbatim(self):
        subject = _character("rects")
        stored = append_card(subject, **_card_fields(subject))
        self.assertEqual(stored["face_rect"], DEFAULT_FACE_RECT)
        explicit = {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}
        second = append_card(
            subject, **_card_fields(subject, face_rect=explicit)
        )
        self.assertEqual(second["face_rect"], explicit)
        with self.assertRaises(GalleryRecordError):
            append_card(
                subject,
                **_card_fields(
                    subject, face_rect={"x": 0.6, "y": 0.0, "w": 0.5, "h": 0.4}
                ),
            )
        self.assertEqual(len(cards_for(subject)), 2)

    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_a_bound_character_card_stores_the_normalized_binding(self):
        subject = _character("bound")
        stored = append_card(
            subject,
            **_card_fields(
                subject,
                binding={
                    "mask": ["armor", "weapon_main"],
                    "snapshot": {
                        "armor": "leather_vest",
                        "weapon_main": "short_sword",
                    },
                },
            ),
        )
        self.assertEqual(stored["binding"]["mask"], ["weapon_main", "armor"])
        self.assertEqual(
            stored["binding"]["snapshot"],
            {"weapon_main": "short_sword", "armor": "leather_vest"},
        )

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_a_second_monster_card_replaces_the_first_and_deletes_its_file(self):
        subject = _monster()
        first = _new_id()
        second = _new_id()
        first_file = self._make_file(_identity(subject, first))
        append_card(subject, **_card_fields(subject, image_id=first))
        second_file = self._make_file(_identity(subject, second))
        append_card(subject, **_card_fields(subject, image_id=second))
        cards = cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [second])
        self.assertEqual(record_for(subject).db.default_image_id, second)
        self.assertFalse(first_file.exists())
        self.assertTrue(second_file.exists())

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_a_bound_monster_card_is_rejected_and_the_record_is_unchanged(self):
        subject = _monster("boundgoblin")
        first = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        with self.assertRaises(GalleryRecordError):
            append_card(
                subject,
                **_card_fields(
                    subject,
                    binding={"mask": ["armor"], "snapshot": {"armor": "tattered_cloth"}},
                ),
            )
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [first])
        # Rejection happens before creation too: an unrecorded monster with a
        # bound card gains no record.
        with self.assertRaises(GalleryRecordError):
            append_card(
                _monster("freshgoblin"),
                **_card_fields(
                    _monster("freshgoblin"),
                    binding={"mask": ["armor"], "snapshot": {"armor": None}},
                ),
            )
        self.assertIsNone(record_for(_monster("freshgoblin")))

    @covers_requirement(
        "art-gallery-prompt-fields::the-gallery-prompt-field-catalog-is-a-closed-ordered-vocabulary"
    )
    def test_a_monster_card_claiming_field_provenance_is_refused(self):
        # Card requested_fields is a provenance claim; the write boundary
        # refuses a claim the kind's declaration could never support
        # (``gallery-monster-generation``) — with the record unchanged.
        subject = _monster("provenancegoblin")
        first = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        with self.assertRaises(GalleryRecordError):
            append_card(
                subject,
                **_card_fields(subject, requested_fields=["appearance"]),
            )
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [first])
        # Empty provenance stays legal — the settled monster shape.
        second = _new_id()
        stored = append_card(subject, **_card_fields(subject, image_id=second))
        self.assertEqual(stored["requested_fields"], [])

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_the_cap_follows_the_declaration_not_the_kind(self):
        # A CHARACTER declaration patched to declare a one-card maximum must
        # make appends replace — with no edit to gallery.py. Enforcement
        # follows the declared value, not an inline kind comparison.
        subject = _character("declaredcap")
        first = _new_id()
        second = _new_id()
        first_file = self._make_file(_identity(subject, first))
        append_card(subject, **_card_fields(subject, image_id=first))
        self._make_file(_identity(subject, second))
        capped = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(max_cards=1)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: capped},
        ):
            append_card(subject, **_card_fields(subject, image_id=second))
        self.assertEqual(
            [card["image_id"] for card in cards_for(subject)], [second]
        )
        self.assertEqual(record_for(subject).db.default_image_id, second)
        self.assertFalse(first_file.exists())

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_a_failed_replacement_unlink_leaves_the_committed_replacement_intact(self):
        # Declaration-driven cap path: the replacement commits FIRST; an
        # unlink failure afterwards is a bounded warn, never a raise, and
        # never rolls the record back.
        subject = _character("unlinkfail")
        first = _new_id()
        second = _new_id()
        self._make_file(_identity(subject, first))
        append_card(subject, **_card_fields(subject, image_id=first))
        self._make_file(_identity(subject, second))
        capped = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(max_cards=1)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: capped},
        ), patch("world.art.gallery.log_warn") as warn, patch(
            "pathlib.Path.unlink", side_effect=OSError("locked")
        ):
            append_card(subject, **_card_fields(subject, image_id=second))
        self.assertEqual(
            [card["image_id"] for card in cards_for(subject)], [second]
        )
        self.assertEqual(record_for(subject).db.default_image_id, second)
        self.assertIn(
            "gallery_card_file_delete_failed",
            [call.args[0] for call in warn.call_args_list],
        )

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_the_declared_null_maximum_keeps_a_character_record_uncapped(self):
        # The sentinel-integer regression: a character must retain EVERY card
        # in append order, delete no stored file, and never move the default.
        subject = _character("manyuncapped")
        ids = []
        files = []
        for _ in range(6):
            image_id = _new_id()
            files.append(self._make_file(_identity(subject, image_id)))
            append_card(subject, **_card_fields(subject, image_id=image_id))
            ids.append(image_id)
        self.assertEqual([card["image_id"] for card in cards_for(subject)], ids)
        self.assertEqual(record_for(subject).db.default_image_id, ids[0])
        self.assertTrue(all(path.exists() for path in files))

    @covers_requirement("art-gallery-model::monster-subjects-hold-at-most-one-card")
    def test_a_bound_card_is_rejected_for_any_kind_declaring_no_binding_support(self):
        # Not monster-specific: a CHARACTER whose declaration is patched to
        # drop binding support must reject a bound card, record unchanged.
        subject = _character("nobindings")
        first = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        unbound = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(supports_bindings=False)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: unbound},
        ):
            with self.assertRaises(GalleryRecordError):
                append_card(
                    subject,
                    **_card_fields(
                        subject,
                        image_id=_new_id(),
                        binding={"mask": ["armor"], "snapshot": {"armor": "cloth"}},
                    ),
                )
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [first])
