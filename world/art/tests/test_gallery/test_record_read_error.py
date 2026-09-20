"""Slice of ``test_gallery``: GalleryRecordWriteTests (deletion, tolerant-read and error-state half; the append/cap/write-seam half is the same-named sibling class in ``test_record_write.py``).
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

    @covers_requirement(
        "art-gallery-kind-capabilities::gallery-enforcement-reads-the-declaration-instead-of-comparing-kinds"
    )
    def test_a_kind_declared_without_a_gallery_is_refused_at_every_write_seam(self):
        # The scene refusal is a declaration consequence, not a kind test: a
        # MONSTER whose declaration is patched to has_gallery=False must be
        # refused by record creation and card validation alike, nothing stored.
        no_gallery = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.MONSTER.value
        ].with_values(has_gallery=False, store_directory=None)
        subject = _monster("nogallery")
        fields = _card_fields(subject)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.MONSTER.value: no_gallery},
        ):
            with self.assertRaises(GalleryRecordError):
                record_for(subject, create=True)
            with self.assertRaises(GalleryRecordError):
                validate_card(fields, subject)
            with self.assertRaises(GalleryRecordError):
                append_card(subject, **fields)
        self.assertIsNone(record_for(subject))
        # The scene kind itself is refused through the same declared path.
        with self.assertRaises(GalleryRecordError):
            record_for(_scene(), create=True)
        with self.assertRaises(GalleryRecordError):
            validate_card(_card_fields(_scene()), _scene())

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_deleting_a_card_unlinks_exactly_its_confined_file(self):
        subject = _character("delfile")
        image_id = _new_id()
        keep = _new_id()
        target = self._make_file(_identity(subject, image_id))
        kept = self._make_file(_identity(subject, keep))
        append_card(subject, **_card_fields(subject, image_id=image_id))
        append_card(subject, **_card_fields(subject, image_id=keep))
        remove_card(subject, image_id)
        self.assertFalse(target.exists())
        self.assertTrue(kept.exists())
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [keep])

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_an_unresolvable_identity_is_removed_with_a_bounded_log_and_no_unlink(self):
        subject = _character("delink")
        image_id = _new_id()
        external = Path(self.tempdir.name).parent / "precious.png"
        external.write_bytes(b"do not touch")
        # The record holds a valid card whose identity file is replaced by a
        # symlink to an outside file: deletion must remove the card, refuse
        # the symlink, and leave the external file alive.
        target = self._make_file(_identity(subject, image_id))
        target.unlink()
        target.symlink_to(external)
        append_card(subject, **_card_fields(subject, image_id=image_id))
        with patch("world.art.gallery.log_warn") as warn:
            remove_card(subject, image_id)
        self.assertTrue(external.exists())
        events = [c for c in warn.call_args_list if c.args and c.args[0] == "gallery_card_file_unresolvable"]
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["subject"], subject.full())
        self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_a_missing_file_is_a_bounded_debug_not_a_raise(self):
        subject = _character("nofile")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        with patch("world.art.gallery.log_debug") as debug:
            remove_card(subject, image_id)
        self.assertEqual(cards_for(subject), [])
        events = [c for c in debug.call_args_list if c.args and c.args[0] == "gallery_card_file_missing"]
        self.assertEqual(len(events), 1)

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_deleting_the_default_card_clears_the_default(self):
        subject = _character("deldefault")
        first = _new_id()
        second = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        append_card(subject, **_card_fields(subject, image_id=second))
        remove_card(subject, first)
        record = record_for(subject)
        self.assertIsNone(record.db.default_image_id)
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [second])
        with self.assertRaises(GalleryRecordError):
            remove_card(subject, "not-an-uuid-at-all-xyz")

    @covers_requirement("art-gallery-model::malformed-stored-cards-are-skipped-never-fatal")
    def test_a_malformed_entry_is_skipped_and_logged_once(self):
        subject = _character("malformed")
        valid = _new_id()
        append_card(subject, **_card_fields(subject, image_id=valid))
        record = record_for(subject)
        record.db.cards = [*record.db.cards, "not a mapping"]
        with patch("world.art.gallery.log_warn") as warn:
            cards = cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [valid])
        events = [c for c in warn.call_args_list if c.args and c.args[0] == "gallery_card_invalid"]
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0].kwargs["context"]["subject"], subject.full())
        self.assertIsNone(events[0].kwargs["context"]["image_id"])

    @covers_requirement("art-gallery-model::malformed-stored-cards-are-skipped-never-fatal")
    def test_unhashable_corrupted_members_never_raise_out_of_a_read(self):
        subject = _character("unhashable")
        valid = _new_id()
        append_card(subject, **_card_fields(subject, image_id=valid))
        record = record_for(subject)
        bad = dict(
            _card_fields(subject, face_rect=dict(DEFAULT_FACE_RECT)),
            source=["generated"],
        )
        record.db.cards = [*record.db.cards, bad]
        with patch("world.art.gallery.log_warn"):
            cards = cards_for(subject)  # must not raise TypeError
        self.assertEqual([card["image_id"] for card in cards], [valid])

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_a_nul_identity_card_is_removed_with_a_bounded_log(self):
        subject = _character("nulfile")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        record = record_for(subject)
        poisoned = dict(record.db.cards[0])
        poisoned["stored_identity"] = f"gallery/character/{subject.key}/{image_id}\x00.png"
        record.db.cards = [poisoned]
        with patch("world.art.gallery.log_warn"):
            remove_card(subject, image_id)  # must not raise ValueError
        self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-model::equipment-snapshots-are-read-from-stored-state-without-materializing-a-handler")
    def test_a_real_character_without_equipment_reads_empty_untouched(self):
        from evennia.utils.create import create_object
        from typeclasses.characters import PlayerCharacter

        character = create_object(PlayerCharacter, key="gallery-snapshot-host")
        snapshot = snapshot_for(character)
        self.assertEqual(
            snapshot,
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        )
        self.assertIsNone(character.db.equipment)

    @covers_requirement("art-gallery-model::malformed-stored-cards-are-skipped-never-fatal")
    def test_a_contract_broken_entry_logs_its_readable_image_id(self):
        subject = _character("brokenid")
        good = _new_id()
        append_card(subject, **_card_fields(subject, image_id=good))
        record = record_for(subject)
        broken = dict(_card_fields(subject, face_rect=dict(DEFAULT_FACE_RECT)), image_id=good)
        broken["source"] = "imported"
        broken["image_id"] = _new_id()
        record.db.cards = [*record.db.cards, broken]
        with patch("world.art.gallery.log_warn") as warn:
            cards = cards_for(subject)
        self.assertEqual([card["image_id"] for card in cards], [good])
        events = [c for c in warn.call_args_list if c.args and c.args[0] == "gallery_card_invalid"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["image_id"], broken["image_id"])

    @covers_requirement("art-gallery-model::malformed-stored-cards-are-skipped-never-fatal")
    def test_an_all_malformed_record_reads_empty(self):
        subject = _character("allbad")
        append_card(subject, **_card_fields(subject))
        record = record_for(subject)
        record.db.cards = [42, ["list"], {"image_id": _new_id()}]
        with patch("world.art.gallery.log_warn"):
            self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_record_error_and_clear_error_round_trip_lazily(self):
        subject = _character("errored")
        record_error(subject, "sd_connection_error")
        record = record_for(subject)
        self.assertEqual(record.db.last_error_code, "sd_connection_error")
        self.assertIsInstance(record.db.last_error_at, float)
        self.assertEqual(cards_for(subject), [])
        clear_error(subject)
        self.assertIsNone(record.db.last_error_code)
        self.assertIsNone(record.db.last_error_at)
        # Clearing on a subject that never had a record stays a silent no-op.
        clear_error(_character("neverrecorded"))
        self.assertIsNone(record_for(_character("neverrecorded")))
        with self.assertRaises(GalleryRecordError):
            record_error(subject, "")

    @covers_requirement("art-gallery-model::one-gallery-record-per-art-subject-carries-an-ordered-card-list-and-a-default")
    def test_a_recreated_cards_list_survives_fetch(self):
        subject = _character("listreload")
        first = _new_id()
        append_card(subject, **_card_fields(subject, image_id=first))
        second = _new_id()
        append_card(subject, **_card_fields(subject, image_id=second))
        refetched = GalleryRecord.objects.get(pk=record_for(subject).pk)
        self.assertEqual(len(refetched.db.cards), 2)

    @covers_requirement("art-gallery-model::the-recorded-generation-error-is-last-attempt-state-not-a-permanent-mark")
    def test_a_second_failure_replaces_the_first_code(self):
        subject = _character("replaced")
        record_error(subject, "sd_connection_error")
        first_at = record_for(subject).db.last_error_at
        record_error(subject, "sd_timeout")
        record = record_for(subject)
        self.assertEqual(record.db.last_error_code, "sd_timeout")
        self.assertGreaterEqual(record.db.last_error_at, first_at)
        # Fresh read: the replacement survived the round trip; the error
        # fields hold exactly the new code (no append-style history).
        refetched = GalleryRecord.objects.get(pk=record.pk)
        self.assertEqual(refetched.db.last_error_code, "sd_timeout")

    @covers_requirement("art-gallery-model::the-recorded-generation-error-is-last-attempt-state-not-a-permanent-mark")
    def test_clearing_leaves_every_card_and_the_default_untouched(self):
        subject = _character("cleartouched")
        image_id = _new_id()
        append_card(subject, **_card_fields(subject, image_id=image_id))
        record_error(subject, "sd_connection_error")
        cards_before = cards_for(subject)
        default_before = record_for(subject).db.default_image_id
        clear_error(subject)
        record = record_for(subject)
        self.assertIsNone(record.db.last_error_code)
        self.assertIsNone(record.db.last_error_at)
        self.assertEqual(cards_for(subject), cards_before)
        self.assertEqual(record.db.default_image_id, default_before)

    @covers_requirement("art-gallery-model::one-read-only-accessor-reports-every-subject-whose-gallery-carries-an-error")
    def test_the_accessor_reports_only_erroring_subjects(self):
        erroring = _character("badgen")
        clean = _character("well")
        empty = _character("alsofine")
        append_card(clean, **_card_fields(clean))
        append_card(empty, **_card_fields(empty))
        record_error(erroring, "sd_connection_error")
        rows = erroring_subjects()
        self.assertEqual([row.subject for row in rows], [erroring])
        self.assertEqual(rows[0].error_code, "sd_connection_error")
        self.assertIsInstance(rows[0].error_at, float)

    @covers_requirement("art-gallery-model::one-read-only-accessor-reports-every-subject-whose-gallery-carries-an-error")
    def test_the_accessor_on_an_empty_store_creates_nothing(self):
        self.assertEqual(erroring_subjects(), [])
        self.assertEqual(gallery_states(), [])
        self.assertEqual(GalleryRecord.objects.count(), 0)

    @covers_requirement("art-gallery-model::one-read-only-accessor-reports-every-subject-whose-gallery-carries-an-error")
    def test_an_unparseable_record_is_skipped_not_fatal(self):
        good = _character("stillseen")
        record_error(good, "sd_timeout")
        broken = _character("corrupt")
        record_error(broken, "sd_connection_error")
        # Corrupt the persisted identity the way a bad deploy could: a kind
        # that no longer parses.
        record_for(broken).db.kind = "monster"
        rows = erroring_subjects()
        self.assertEqual([row.subject for row in rows], [good])

    @covers_requirement("art-gallery-model::one-read-only-accessor-reports-every-subject-whose-gallery-carries-an-error")
    def test_the_state_accessor_lists_healthy_records_and_valid_card_counts(self):
        subject = _character("stateview")
        append_card(subject, **_card_fields(subject))
        record_for(subject).db.cards.append({"not": "a card"})
        record_error(subject, "sd_timeout")
        states = gallery_states()
        self.assertEqual([state.subject for state in states], [subject])
        state = states[0]
        # The malformed entry is skipped; only the valid card counts.
        self.assertEqual(state.card_count, 1)
        self.assertTrue(state.has_default)
        self.assertEqual(state.error_code, "sd_timeout")
        self.assertIsInstance(state.error_at, float)
