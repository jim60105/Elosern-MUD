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
    GalleryRecord,
    GalleryRecordError,
    MAX_OFFICIAL_GEOMETRY_OVERRIDES,
    SLOT_ORDER,
    append_card,
    cards_for,
    clear_official_geometry,
    clear_official_selection,
    clear_error,
    erroring_subjects,
    gallery_states,
    official_preferences_for,
    record_error,
    record_for,
    record_key,
    remove_card,
    set_default,
    set_official_geometry,
    set_official_selection,
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

    @covers_requirement("art-gallery-model::a-card-s-image-pixel-size-is-recorded-from-verified-bytes-at-append")
    def test_size_less_append_refuses(self):
        subject = _character("nosize")
        fields = _card_fields(subject)
        fields.pop("image_size")
        with self.assertRaises(GalleryRecordError):
            append_card(subject, **fields)
        self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_append_without_rect_fills_fitted_default(self):
        subject = _character("fitteddefault")
        stored = append_card(subject, **_card_fields(subject, image_size={"width": 768, "height": 1024}))
        self.assertEqual(stored["face_rect"], {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375})

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
        # The append-time default is the size-fitted rect: on 768x1024 the
        # pinned upper-half anchor scales h = 0.5 * 768 / 1024.
        self.assertEqual(stored["face_rect"], {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375})
        explicit = {"x": 0.1, "y": 0.2, "w": 0.4, "h": 0.3}
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


# A file-local synthetic identity: the writers validate the identity GRAMMAR
# only; whether the catalog admits the image stays the catalog's answer.
_OFFICIAL = "preset/t_synth_preset/hero.png"
_OFFICIAL_OTHER = "preset/t_synth_preset/other.png"
_RECT = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375}
_STAGE = {"scale": 1.4, "x": 0.1, "y": -0.2}


class OfficialPreferenceWriteTests(EvenniaTestCase):
    """The four preference writers: lazy records, clearing, bounds, no files."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name).resolve()
        self.art_settings = override_settings(ART_STORE_ROOT=str(self.root))
        self.art_settings.enable()
        self.addCleanup(self.art_settings.disable)

    def _make_file(self, identity):
        target = self.root / identity
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"image")
        return target

    def _store_tree(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    @covers_requirement(
        "art-gallery-model::gallery-records-carry-entity-local-official-art-preferences-as-first-class-fields"
    )
    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    def test_a_selection_write_creates_a_card_less_record(self):
        subject = _character("selects")
        self.assertIsNone(record_for(subject))
        set_official_selection(subject, _OFFICIAL)
        record = record_for(subject)
        self.assertIsNotNone(record)
        self.assertEqual(record.db.cards, [])
        self.assertIsNone(record.db.default_image_id)
        preferences = official_preferences_for(subject)
        self.assertEqual(preferences.selection, _OFFICIAL)
        self.assertEqual(preferences.geometry, {})
        # The card read is untouched by preference state.
        self.assertEqual(cards_for(subject), [])

    def test_the_first_card_becomes_the_default_without_clearing_the_selection(self):
        # An automatic first-card default is not an explicit default SET, so a
        # settled generation never discards the player's official choice.
        subject = _character("autodefault")
        set_official_selection(subject, _OFFICIAL)
        image_id = _new_id()
        self._make_file(_identity(subject, image_id))
        append_card(subject, **_card_fields(subject, image_id=image_id))
        self.assertEqual(record_for(subject).db.default_image_id, image_id)
        self.assertEqual(official_preferences_for(subject).selection, _OFFICIAL)

    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    def test_an_explicit_default_clears_the_selection(self):
        subject = _character("mutuala")
        image_id = _new_id()
        self._make_file(_identity(subject, image_id))
        append_card(subject, **_card_fields(subject, image_id=image_id))
        set_official_selection(subject, _OFFICIAL)
        self.assertIsNone(record_for(subject).db.default_image_id)
        set_default(subject, image_id)
        self.assertEqual(record_for(subject).db.default_image_id, image_id)
        self.assertIsNone(official_preferences_for(subject).selection)
        # The card list itself was never touched by either act.
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [image_id])

    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    def test_a_selection_clears_an_explicit_default(self):
        subject = _character("mutualb")
        image_id = _new_id()
        self._make_file(_identity(subject, image_id))
        append_card(subject, **_card_fields(subject, image_id=image_id))
        set_official_selection(subject, _OFFICIAL)
        record = record_for(subject)
        self.assertIsNone(record.db.default_image_id)
        self.assertEqual(official_preferences_for(subject).selection, _OFFICIAL)
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [image_id])
        # Deleting the card afterwards leaves the selection exactly as stored.
        remove_card(subject, image_id)
        self.assertEqual(official_preferences_for(subject).selection, _OFFICIAL)

    def test_a_geometry_write_creates_a_record_and_replaces_one_identity(self):
        subject = _character("geometry")
        self.assertIsNone(record_for(subject))
        set_official_geometry(subject, _OFFICIAL, face_rect=dict(_RECT))
        self.assertEqual(
            official_preferences_for(subject).geometry, {_OFFICIAL: {"face_rect": _RECT}}
        )
        set_official_geometry(subject, _OFFICIAL, stage=dict(_STAGE))
        self.assertEqual(
            official_preferences_for(subject).geometry, {_OFFICIAL: {"stage": _STAGE}}
        )
        # A second identity is independent, and the selection is untouched.
        set_official_geometry(
            subject, _OFFICIAL_OTHER, face_rect=dict(_RECT), stage=dict(_STAGE)
        )
        set_official_selection(subject, _OFFICIAL)
        preferences = official_preferences_for(subject)
        self.assertEqual(preferences.selection, _OFFICIAL)
        self.assertEqual(
            preferences.geometry,
            {
                _OFFICIAL: {"stage": _STAGE},
                _OFFICIAL_OTHER: {"face_rect": _RECT, "stage": _STAGE},
            },
        )
        with self.assertRaises(GalleryRecordError):
            set_official_geometry(subject, _OFFICIAL)

    @covers_requirement(
        "art-gallery-model::gallery-records-carry-entity-local-official-art-preferences-as-first-class-fields"
    )
    def test_clearing_absent_preferences_creates_nothing(self):
        subject = _character("clearsnothing")
        clear_official_selection(subject)
        self.assertFalse(clear_official_geometry(subject, _OFFICIAL))
        self.assertIsNone(record_for(subject))

    def test_clearing_stored_preferences_reports_and_persists(self):
        subject = _character("clearstored")
        set_official_geometry(subject, _OFFICIAL, face_rect=dict(_RECT))
        set_official_selection(subject, _OFFICIAL)
        self.assertTrue(clear_official_geometry(subject, _OFFICIAL))
        self.assertEqual(official_preferences_for(subject).geometry, {})
        # Clearing the geometry never clears the selection.
        self.assertEqual(official_preferences_for(subject).selection, _OFFICIAL)
        self.assertFalse(clear_official_geometry(subject, _OFFICIAL))
        clear_official_selection(subject)
        self.assertIsNone(official_preferences_for(subject).selection)

    def test_the_override_map_is_bounded_and_an_existing_identity_still_writes(self):
        subject = _character("bounded")
        for index in range(MAX_OFFICIAL_GEOMETRY_OVERRIDES):
            set_official_geometry(
                subject, f"preset/t_synth_{index}/a.png", face_rect=dict(_RECT)
            )
        self.assertEqual(
            len(official_preferences_for(subject).geometry),
            MAX_OFFICIAL_GEOMETRY_OVERRIDES,
        )
        set_official_geometry(subject, "preset/t_synth_0/a.png", stage=dict(_STAGE))
        self.assertEqual(
            official_preferences_for(subject).geometry["preset/t_synth_0/a.png"],
            {"stage": _STAGE},
        )
        with self.assertRaises(GalleryRecordError):
            set_official_geometry(
                subject, "preset/t_synth_over/a.png", face_rect=dict(_RECT)
            )
        self.assertEqual(
            len(official_preferences_for(subject).geometry),
            MAX_OFFICIAL_GEOMETRY_OVERRIDES,
        )

    def test_malformed_identities_are_refused_by_every_writer(self):
        subject = _character("refusers")
        for identity in (
            None,
            7,
            "",
            "preset/bare",
            "preset/t_synth_preset/a.bmp",
            "preset/../a.png",
            "preset/t_synth_preset/a\u200b.png",
        ):
            with self.subTest(identity=repr(identity)):
                with self.assertRaises(GalleryRecordError):
                    set_official_selection(subject, identity)
                with self.assertRaises(GalleryRecordError):
                    set_official_geometry(subject, identity, face_rect=dict(_RECT))
                with self.assertRaises(GalleryRecordError):
                    clear_official_geometry(subject, identity)
        self.assertIsNone(record_for(subject))

    @covers_requirement(
        "art-gallery-model::gallery-records-carry-entity-local-official-art-preferences-as-first-class-fields"
    )
    @covers_requirement(
        "official-art-personalization::a-personal-official-selection-is-an-entity-local-art-preference"
    )
    def test_preference_writes_touch_no_file_and_no_card(self):
        subject = _character("nofiles")
        image_id = _new_id()
        self._make_file(_identity(subject, image_id))
        append_card(subject, **_card_fields(subject, image_id=image_id))
        before_files = self._store_tree()
        before_cards = cards_for(subject)
        set_official_selection(subject, _OFFICIAL)
        set_official_geometry(
            subject, _OFFICIAL, face_rect=dict(_RECT), stage=dict(_STAGE)
        )
        clear_official_geometry(subject, _OFFICIAL)
        clear_official_selection(subject)
        self.assertEqual(self._store_tree(), before_files)
        self.assertEqual(cards_for(subject), before_cards)
        # The preference fields never become cards, and the monster one-card
        # cap is unaffected by them.
        monster = _monster("prefmonster")
        set_official_selection(monster, _OFFICIAL)
        set_official_geometry(monster, _OFFICIAL, stage=dict(_STAGE))
        self.assertEqual(cards_for(monster), [])
        monster_id = _new_id()
        self._make_file(_identity(monster, monster_id))
        append_card(monster, **_card_fields(monster, image_id=monster_id))
        self.assertEqual(
            [card["image_id"] for card in cards_for(monster)], [monster_id]
        )
