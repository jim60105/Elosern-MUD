"""Tests for the bulk seed-art synchronization seam (gallery-seed-sync).

Pure ``unittest.TestCase`` classes cover the path-derived id derivation and
the manifest parser (no DB, facade patched); ``EvenniaTestCase`` classes run
``sync_all()`` against temporary seed and store roots to prove the
skip-once contract, append-exactly-one-card-per-file idempotency, incremental
adds, bounded-diagnostic skips, seed provenance, the ordinary-card lifecycle,
the manifest default/rectangle rules, the monster one-card cap, and that
player-generated cards are never disturbed.
"""

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase

from world.art import gallery_seed
from world.art import gallery_kinds
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    append_card,
    cards_for,
    record_for,
    remove_card,
    set_default,
)
from world.art.gallery_seed import SEED_SYNC_EVENT, derive_image_id, sync_all
from world.art.subjects import ArtSubject, ArtSubjectKind

from tools.spec_traceability import covers_requirement

_SEED_BYTES = b"\x89PNG seed bytes"


def _unique(kind_directory: str) -> str:
    """A fresh subject key per test so DB rows never collide."""
    return f"{kind_directory}_{uuid.uuid4().hex[:10]}"


def _character(key):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _monster(key):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


class _SeedTree:
    """Builder for ``<root>/<kind>/<subject-key>/<file>`` seed trees."""

    def __init__(self, root: Path):
        self.root = root

    def image(self, kind_directory: str, subject_key: str, filename: str, content: bytes = _SEED_BYTES) -> Path:
        folder = self.root / kind_directory / subject_key
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / filename
        path.write_bytes(content)
        return path

    def manifest(self, kind_directory: str, subject_key: str, payload) -> Path:
        folder = self.root / kind_directory / subject_key
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / gallery_seed.MANIFEST_FILENAME
        path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload),
            encoding="utf-8",
        )
        return path


class _CollectingDiagnostics:
    """Stand-in for ``_Diagnostics`` recording every emitted reason."""

    def __init__(self):
        self.reasons: list[str] = []

    def emit(self, reason: str, **context) -> None:
        self.reasons.append(reason)


class _TempRoots(EvenniaTestCase):
    """Shared temporary seed root + store root with patched event sinks."""

    def setUp(self):
        super().setUp()
        self.seed_dir = tempfile.TemporaryDirectory()
        self.store_dir = tempfile.TemporaryDirectory()
        self.seed_root = Path(self.seed_dir.name).resolve()
        self.store_root = Path(self.store_dir.name).resolve()
        self._settings = override_settings(
            ART_SEED_ROOT=str(self.seed_root), ART_STORE_ROOT=str(self.store_root)
        )
        self._settings.enable()
        self.tree = _SeedTree(self.seed_root)
        patcher = patch.object(gallery_seed, "log_warn")
        self.warn = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(gallery_seed, "log_info")
        self.info = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self._settings.disable()
        self.seed_dir.cleanup()
        self.store_dir.cleanup()
        super().tearDown()

    def _events(self):
        return [
            (call.args[0], call.kwargs["context"])
            for call in [*self.warn.call_args_list, *self.info.call_args_list]
        ]

    def _phases(self):
        return [context["phase"] for _, context in self._events()]

    def _reasons(self):
        return [
            context.get("reason")
            for _, context in self._events()
            if context["phase"] == "diagnostic"
        ]

    def _identity_for(self, subject: ArtSubject, filename: str) -> tuple[str, str]:
        """(image_id, stored_identity) a seed file must sync under."""
        kind_dir = "character" if subject.kind is ArtSubjectKind.CHARACTER else "monster"
        image_id = derive_image_id(f"{kind_dir}/{subject.key}/{filename}")
        return image_id, f"gallery/{kind_dir}/{subject.key}/{image_id}{Path(filename).suffix}"


class IdDerivationTests(unittest.TestCase):
    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_the_derived_id_is_stable_canonical_and_path_specific(self):
        first = derive_image_id("character/heron/a.png")
        self.assertEqual(first, derive_image_id("character/heron/a.png"))
        self.assertNotEqual(first, derive_image_id("character/heron/b.png"))
        self.assertNotEqual(first, derive_image_id("monster/heron/a.png"))
        # Canonical lowercase uuid text, parseable back.
        self.assertEqual(str(uuid.UUID(first)), first)


class ManifestParsingTests(unittest.TestCase):
    """The parser reads one subject folder fd — no DB, no events needed."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.diagnostics = _CollectingDiagnostics()

    def tearDown(self):
        self.tempdir.cleanup()

    def _parse(self, payload, eligible=("a.png", "b.png")):
        folder = self.root / "subject"
        folder.mkdir(exist_ok=True)
        manifest = folder / gallery_seed.MANIFEST_FILENAME
        if payload is not None:
            manifest.write_text(
                payload if isinstance(payload, str) else json.dumps(payload),
                encoding="utf-8",
            )
        subject_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
        try:
            return gallery_seed._parse_manifest(
                subject_fd, set(eligible), self.diagnostics, "portrait:character/x"
            )
        finally:
            os.close(subject_fd)

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_absent_manifest_falls_back_silently(self):
        self.assertEqual(self._parse(None), (None, None))
        self.assertEqual(self.diagnostics.reasons, [])

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_a_valid_manifest_returns_its_declared_pair(self):
        rect = {"x": 0.1, "y": 0.0, "w": 0.5, "h": 0.5}
        result = self._parse({"default": "b.png", "face_rect": rect})
        self.assertEqual(result, ("b.png", rect))
        self.assertEqual(self.diagnostics.reasons, [])

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_every_violation_degrades_whole_with_one_diagnostic(self):
        cases = {
            "not json": "{not json",
            "not an object": '["a.png"]',
            "unexpected key": '{"default": "a.png", "extra": 1}',
            "missing default file": '{"default": "gone.png"}',
            "non-string default": '{"default": 7}',
            "invalid rectangle": '{"face_rect": {"x": 2, "y": 0, "w": 0.5, "h": 0.5}}',
            "rect overflows unit square": '{"face_rect": {"x": 0.8, "y": 0, "w": 0.5, "h": 0.5}}',
        }
        for label, payload in cases.items():
            with self.subTest(label):
                self.diagnostics.reasons.clear()
                self.assertEqual(self._parse(payload), (None, None))
                self.assertEqual(len(self.diagnostics.reasons), 1)

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_a_face_rect_only_manifest_still_applies_the_rectangle(self):
        rect = {"x": 0.25, "y": 0.1, "w": 0.4, "h": 0.4}
        self.assertEqual(self._parse({"face_rect": rect}), (None, rect))
        self.assertEqual(self.diagnostics.reasons, [])


class SeedRootSkipTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::bulk-seed-art-lives-outside-git-behind-one-directory-root-setting")
    def test_a_missing_root_logs_exactly_one_event_and_creates_nothing(self):
        missing = self.seed_root / "absent"
        with override_settings(ART_SEED_ROOT=str(missing)):
            summary = sync_all()
        self.assertTrue(summary["skipped"])
        self.assertEqual(self.warn.call_count, 1)
        self.assertEqual(self.info.call_count, 0)
        event, context = self.warn.call_args.args[0], self.warn.call_args.kwargs["context"]
        self.assertEqual(event, SEED_SYNC_EVENT)
        self.assertEqual(context["reason"], "seed_root_absent")

    @covers_requirement("art-gallery-seed-sync::bulk-seed-art-lives-outside-git-behind-one-directory-root-setting")
    def test_an_empty_root_setting_skips_without_touching_the_filesystem(self):
        with override_settings(ART_SEED_ROOT=""):
            summary = sync_all()
        self.assertTrue(summary["skipped"])
        self.assertEqual(self.warn.call_count, 1)
        self.assertEqual(
            self.warn.call_args.kwargs["context"]["reason"], "seed_root_unset"
        )

    @covers_requirement("art-gallery-seed-sync::bulk-seed-art-lives-outside-git-behind-one-directory-root-setting")
    def test_an_unreadable_root_is_one_skip_event_not_a_crash(self):
        unreadable = self.seed_root / "locked"
        unreadable.mkdir()
        self.tree.image("character", "heron", "a.png")
        unreadable.chmod(0o000)
        try:
            with override_settings(ART_SEED_ROOT=str(unreadable)):
                summary = sync_all()
        finally:
            unreadable.chmod(0o755)
        self.assertTrue(summary["skipped"])
        self.assertEqual(self.warn.call_count, 1)
        self.assertEqual(
            self.warn.call_args.kwargs["context"]["reason"], "seed_root_unreadable"
        )

    @covers_requirement("art-gallery-seed-sync::bulk-seed-art-lives-outside-git-behind-one-directory-root-setting")
    def test_a_symlinked_root_is_refused_with_one_skip_event(self):
        real = self.seed_root / "real"
        self.seed_root = real  # keep the tree builder pointed at the real folder
        self.tree = _SeedTree(real)
        self.tree.image("character", "heron", "a.png")
        link = self.store_root / "seedlink"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(real)
        try:
            with override_settings(ART_SEED_ROOT=str(link)):
                summary = sync_all()
        finally:
            link.unlink()
        self.assertTrue(summary["skipped"])
        self.assertEqual(self.warn.call_count, 1)
        self.assertEqual(
            self.warn.call_args.kwargs["context"]["reason"], "seed_root_symlink"
        )
        # Nothing synchronized: the heron subject has no record.
        self.assertEqual(cards_for(_character("heron")), [])


class SyncIdempotencyTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_first_run_appends_one_card_per_file_and_the_second_copies_nothing(self):
        hero = _unique("character")
        goblin = _unique("monster")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        self.tree.image("monster", goblin, "g.png")

        first = sync_all()
        self.assertFalse(first["skipped"])
        self.assertEqual(first["appended"], 3)
        self.assertEqual(first["copied"], 3)

        subject = _character(hero)
        cards = cards_for(subject)
        self.assertEqual(len(cards), 2)
        for filename in ("a.png", "b.png"):
            image_id, identity = self._identity_for(subject, filename)
            stored = next(card for card in cards if card["image_id"] == image_id)
            self.assertEqual(stored["stored_identity"], identity)
            served = self.store_root / identity
            self.assertTrue(served.is_file())
            self.assertEqual(served.read_bytes(), _SEED_BYTES)

        # Second run: zero file I/O for known ids. Poisoning the copied bytes
        # proves the idempotency path performs no copy at all.
        monster = _monster(goblin)
        _, monster_identity = self._identity_for(monster, "g.png")
        (self.store_root / monster_identity).write_bytes(b"poison")
        second = sync_all()
        self.assertEqual(second["appended"], 0)
        self.assertEqual(second["copied"], 0)
        self.assertEqual(second["already_present"], 3)
        self.assertEqual(len(cards_for(subject)), 2)
        self.assertEqual(len(cards_for(monster)), 1)
        self.assertEqual((self.store_root / monster_identity).read_bytes(), b"poison")

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_newly_added_file_appends_exactly_one_card(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        sync_all()
        subject = _character(hero)
        before = cards_for(subject)

        self.tree.image("character", hero, "z.png", b"\x89PNG second")
        summary = sync_all()
        after = cards_for(subject)
        self.assertEqual(summary["appended"], 1)
        self.assertEqual(len(after), len(before) + 1)
        # Existing cards are byte-for-byte the same and keep their order.
        self.assertEqual(after[: len(before)], before)
        image_id, identity = self._identity_for(subject, "z.png")
        self.assertEqual(after[-1]["image_id"], image_id)
        self.assertEqual((self.store_root / identity).read_bytes(), b"\x89PNG second")

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_unsupported_unresolvable_and_hostile_entries_are_bounded_skips(self):
        hero = _unique("character")
        hostile = "bad|key"  # '|' is legal in a filename, illegal in a subject key
        self.tree.image("character", hero, "good.png")
        self.tree.image("character", hero, "notes.txt")
        self.tree.image("character", hostile, "x.png")
        self.tree.image("scenes", "forest", "s.png")
        outside = self.store_root.parent / "outside.png"
        outside.write_bytes(b"hostile target")
        link = self.seed_root / "character" / hero / "link.png"
        link.symlink_to(outside)

        summary = sync_all()
        reasons = self._reasons()
        self.assertIn("unsupported_extension_skipped", reasons)
        self.assertIn("invalid_subject_key_skipped", reasons)
        self.assertIn("unknown_kind_directory_skipped", reasons)
        self.assertIn("symlink_skipped", reasons)
        # The valid entry still synchronized, and nothing leaked outside.
        cards = cards_for(_character(hero))
        self.assertEqual([card["stored_identity"] for card in cards], [self._identity_for(_character(hero), "good.png")[1]])
        self.assertEqual(summary["appended"], 1)
        self.assertFalse((self.store_root / "gallery" / "character" / hostile).exists())

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_nested_directory_and_uppercase_extension_are_skipped_with_diagnostics(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        (self.seed_root / "character" / hero / "sub").mkdir()
        self.tree.image("character", hero, "B.PNG")
        summary = sync_all()
        reasons = self._reasons()
        self.assertIn("nested_directory_skipped", reasons)
        self.assertIn("unsupported_extension_skipped", reasons)
        self.assertEqual(summary["appended"], 1)

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_hardlinked_source_is_refused_without_leaking_bytes(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        # A second name for the same inode: classification cannot tell which
        # name the tree operator declared, so both are refused.
        os.link(
            self.seed_root / "character" / hero / "a.png",
            self.seed_root / "character" / hero / "b.png",
        )
        summary = sync_all()
        reasons = self._reasons()
        self.assertEqual(summary["appended"], 0)
        self.assertIn("source_rejected", reasons)
        self.assertNotIn("source_unreadable", reasons)

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_hardlinked_destination_is_never_clobbered(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        subject = _character(hero)
        image_id, identity = self._identity_for(subject, "a.png")
        # Pre-plant the derived destination as a 2-link inode OUTSIDE the store.
        twin = self.store_root / "twin.bin"
        twin.write_bytes(b"priceless")
        destination = self.store_root / identity
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(twin, destination)
        sync_all()
        self.assertEqual(twin.read_bytes(), b"priceless")
        self.assertIn("destination_refused", self._reasons())
        self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_malformed_entry_referencing_the_identity_never_has_its_file_swapped(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        subject = _character(hero)
        image_id, identity = self._identity_for(subject, "a.png")
        # Plant a raw entry that fails validation but references the file the
        # seed file WOULD sync to — the closest possible corruption of the
        # store. The never-overwrite guarantee must still hold byte-for-byte.
        # Its id is deliberately NOT the derived one: an id match would skip
        # at the occupancy check; this probes the IDENTITY reservation.
        record = record_for(subject, create=True)
        served = self.store_root / identity
        served.parent.mkdir(parents=True, exist_ok=True)
        served.write_bytes(b"referenced bytes")
        record.db.cards = [
            {"image_id": "not-the-derived-id", "stored_identity": identity}
        ]
        record.save()
        summary = sync_all()
        self.assertEqual(summary["appended"], 0)
        self.assertEqual(served.read_bytes(), b"referenced bytes")
        self.assertIn("destination_referenced_skipped", self._reasons())
        self.assertEqual(cards_for(subject), [])

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_diagnostic_output_stops_at_the_budget_and_reports_the_suppressed_count(self):
        hero = _unique("character")
        for index in range(gallery_seed._MAX_DIAGNOSTICS + 5):
            self.tree.image("character", hero, f"bad{index}.txt")
        summary = sync_all()
        self.assertEqual(summary["diagnostics"], gallery_seed._MAX_DIAGNOSTICS)
        self.assertGreater(summary["suppressed_diagnostics"], 0)
        self.assertEqual(self.warn.call_count, gallery_seed._MAX_DIAGNOSTICS)

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_the_admitted_root_logs_exactly_one_summary_event(self):
        self.tree.image("character", _unique("character"), "a.png")
        sync_all()
        self.assertEqual(self._phases().count("summary"), 1)
        self.assertEqual(self.info.call_count, 1)


class ProvenanceLifecycleTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::seed-cards-carry-seed-provenance-and-no-reproduction-set")
    def test_seed_cards_carry_provenance_and_no_reproduction_set(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        sync_all()
        card = cards_for(_character(hero))[0]
        self.assertEqual(card["source"], "seed")
        self.assertIsNone(card["prompt"])
        self.assertIsNone(card["seed"])
        self.assertIsNone(card["checkpoint"])
        self.assertEqual(card["requested_fields"], [])
        self.assertIsNone(card["binding"])
        self.assertEqual(card["face_rect"], DEFAULT_FACE_RECT)

    @covers_requirement("art-gallery-seed-sync::seed-cards-carry-seed-provenance-and-no-reproduction-set")
    def test_a_seed_card_is_deletable_and_default_settable(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        sync_all()
        subject = _character(hero)
        first, second = cards_for(subject)
        set_default(subject, second["image_id"])
        self.assertEqual(record_for(subject).db.default_image_id, second["image_id"])
        remove_card(subject, first["image_id"])
        self.assertEqual([card["image_id"] for card in cards_for(subject)], [second["image_id"]])

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_deleted_seed_card_returns_on_the_next_start(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        sync_all()
        subject = _character(hero)
        remove_card(subject, cards_for(subject)[0]["image_id"])
        self.assertEqual(cards_for(subject), [])
        summary = sync_all()
        self.assertEqual(summary["appended"], 1)
        self.assertEqual(len(cards_for(subject)), 1)


class ManifestSyncTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_a_valid_manifest_sets_the_default_and_the_rectangle(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        rect = {"x": 0.2, "y": 0.05, "w": 0.6, "h": 0.4}
        self.tree.manifest("character", hero, {"default": "b.png", "face_rect": rect})
        sync_all()
        subject = _character(hero)
        record = record_for(subject)
        cards = cards_for(subject)
        expected_id, _ = self._identity_for(subject, "b.png")
        self.assertEqual(record.db.default_image_id, expected_id)
        for card in cards:
            self.assertEqual(card["face_rect"], rect)

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_without_a_manifest_sorted_name_and_the_shared_rectangle_apply(self):
        hero = _unique("character")
        self.tree.image("character", hero, "zeta.png")
        self.tree.image("character", hero, "alpha.png")
        sync_all()
        subject = _character(hero)
        expected_id, _ = self._identity_for(subject, "alpha.png")
        self.assertEqual(record_for(subject).db.default_image_id, expected_id)
        for card in cards_for(subject):
            self.assertEqual(card["face_rect"], DEFAULT_FACE_RECT)

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_an_invalid_manifest_degrades_with_one_diagnostic(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.manifest("character", hero, {"default": "gone.png"})
        sync_all()
        subject = _character(hero)
        expected_id, _ = self._identity_for(subject, "a.png")
        self.assertEqual(record_for(subject).db.default_image_id, expected_id)
        self.assertEqual(
            self._reasons().count("manifest_default_not_an_eligible_file"), 1
        )

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_a_players_chosen_default_survives_a_restart(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        sync_all()
        subject = _character(hero)
        chosen = cards_for(subject)[0]  # sorted-first default
        set_default(subject, chosen["image_id"])
        # A later restart ships a manifest naming the OTHER file.
        self.tree.manifest("character", hero, {"default": "b.png"})
        sync_all()
        self.assertEqual(record_for(subject).db.default_image_id, chosen["image_id"])

    @covers_requirement("art-gallery-seed-sync::an-optional-per-subject-manifest-declares-the-default-and-the-face-rectangle")
    def test_a_manifest_reclaims_default_when_the_subject_has_none(self):
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        sync_all()
        subject = _character(hero)
        first, second = cards_for(subject)
        remove_card(subject, first["image_id"])  # remove_card nulls the default
        self.assertIsNone(record_for(subject).db.default_image_id)
        self.tree.manifest("character", hero, {"default": "b.png"})
        sync_all()
        self.assertEqual(record_for(subject).db.default_image_id, second["image_id"])


class MonsterCapTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_monster_subject_receives_only_the_candidate_card(self):
        goblin = _unique("monster")
        self.tree.image("monster", goblin, "z.png")
        self.tree.image("monster", goblin, "a.png")
        summary = sync_all()
        cards = cards_for(_monster(goblin))
        self.assertEqual(len(cards), 1)
        expected_id, _ = self._identity_for(_monster(goblin), "a.png")
        self.assertEqual(cards[0]["image_id"], expected_id)
        self.assertIn("monster_cap_skipped", self._reasons())
        self.assertEqual(summary["monster_cap_skipped"], 1)

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_monster_holding_any_card_is_never_touched(self):
        goblin = _unique("monster")
        subject = _monster(goblin)
        image_id = str(uuid.uuid4())
        append_card(
            subject,
            image_id=image_id,
            stored_identity=f"gallery/monster/{goblin}/{image_id}.png",
            prompt=None,
            seed=None,
            checkpoint=None,
            requested_fields=[],
            binding=None,
            source="generated",
        )
        before = cards_for(subject)
        self.tree.image("monster", goblin, "a.png")
        summary = sync_all()
        self.assertEqual(cards_for(subject), before)
        self.assertEqual(summary["appended"], 0)
        self.assertIn("monster_card_present_skipped", self._reasons())

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_a_steady_state_monster_re_run_is_quiet(self):
        goblin = _unique("monster")
        self.tree.image("monster", goblin, "a.png")
        sync_all()
        self.warn.reset_mock()
        summary = sync_all()
        self.assertEqual(summary["appended"], 0)
        self.assertEqual(self._reasons(), [])

    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_the_seed_cap_follows_the_declaration_not_the_kind(self):
        # A CHARACTER whose declaration is patched to a one-card maximum must
        # seed exactly the candidate card, skipping the surplus with the
        # existing capped-skip diagnostic — with no edit to gallery_seed.py.
        hero = _unique("character")
        self.tree.image("character", hero, "a.png")
        self.tree.image("character", hero, "b.png")
        capped = gallery_kinds.GALLERY_KIND_CAPABILITIES[
            ArtSubjectKind.CHARACTER.value
        ].with_values(max_cards=1)
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {ArtSubjectKind.CHARACTER.value: capped},
        ):
            summary = sync_all()
        cards = cards_for(_character(hero))
        self.assertEqual(len(cards), 1)
        self.assertEqual(summary["appended"], 1)
        self.assertEqual(summary["monster_cap_skipped"], 1)
        self.assertIn("monster_cap_skipped", self._reasons())


class GeneratedCardIsolationTests(_TempRoots):
    @covers_requirement("art-gallery-seed-sync::seed-synchronization-is-idempotent-path-derived-and-additive")
    def test_syncing_leaves_generated_cards_untouched_in_content_order_and_binding(self):
        hero = _unique("character")
        subject = _character(hero)
        generated_id = str(uuid.uuid4())
        binding = {
            "mask": ["armor"],
            "snapshot": {"armor": "iron_helm"},
        }
        append_card(
            subject,
            image_id=generated_id,
            stored_identity=f"gallery/character/{hero}/{generated_id}.png",
            prompt={"positive": "a hero", "negative": "blur"},
            seed=7,
            checkpoint="rp.safetensors",
            requested_fields=["appearance"],
            binding=binding,
            source="generated",
        )
        before = cards_for(subject)
        self.tree.image("character", hero, "a.png")
        sync_all()
        after = cards_for(subject)
        self.assertEqual(after[0], before[0])
        self.assertEqual(after[0]["binding"], binding)
        self.assertEqual(record_for(subject).db.default_image_id, generated_id)
        self.assertEqual(len(after), 2)
