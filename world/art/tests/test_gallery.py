"""Tests for the gallery record model: card contract, validation, and writes.

Pure ``unittest.TestCase`` classes cover the store-root confinement helper,
the face-rect / binding / card-contract validators, and the equipment
snapshot reader (no DB needed); ``EvenniaTestCase`` covers the lazily created
record, the write API, the monster one-card cap, confined deletion, and
tolerant reads against a temporary store root.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import patch
import uuid
import unittest

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTestCase

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

REPO_ROOT = Path(__file__).resolve().parents[3]



def _character(key="heron"):
    return ArtSubject(ArtSubjectKind.CHARACTER, key)


def _monster(key="goblin"):
    return ArtSubject(ArtSubjectKind.MONSTER, key)


def _scene(key="forest_path"):
    return ArtSubject(ArtSubjectKind.SCENE, key)


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
        "requested_fields": ["appearance"],
        "binding": None,
        "source": "generated",
    }
    fields.update(overrides)
    return fields


class _FakeDb:
    """Minimal ``entity.db`` namespace: reads return the stored value/None."""

    def __init__(self, values=None):
        self._values = dict(values or {})

    def __getattr__(self, name):
        return self._values.get(name)

    def get(self, name, default=None):
        return self._values.get(name, default)


class _FakeEntity:
    def __init__(self, equipment=...):
        values = {} if equipment is ... else {"equipment": equipment}
        self.db = _FakeDb(values)


class StoreRootConfinementTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.settings_override = override_settings(ART_STORE_ROOT=str(self.root))
        self.settings_override.enable()
        (self.root / "gallery" / "character").mkdir(parents=True)
        (self.root / "gallery" / "character" / "a.png").write_bytes(b"x")

    def tearDown(self):
        self.settings_override.disable()
        self.tempdir.cleanup()

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_confined_identity_resolves_to_the_real_file(self):
        resolved = resolved_under_store_root("gallery/character/a.png")
        self.assertEqual(resolved, self.root / "gallery" / "character" / "a.png")

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_parent_traversal_and_absolute_paths_are_rejected(self):
        outside = Path(self.tempdir.name).parent / "outside.png"
        outside.write_bytes(b"keep me")
        for identity in (
            "../outside.png",
            "gallery/../../outside.png",
            str(outside),
            "/etc/passwd",
        ):
            with self.subTest(identity=identity):
                self.assertIsNone(resolved_under_store_root(identity))
        self.assertTrue(outside.exists())

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_symlinked_components_are_rejected_even_inside_the_root(self):
        external = Path(self.tempdir.name).parent / "external.png"
        external.write_bytes(b"do not touch")
        # A file-level symlink pointing outside the root.
        (self.root / "gallery" / "character" / "link.png").symlink_to(external)
        self.assertIsNone(
            resolved_under_store_root("gallery/character/link.png")
        )
        self.assertTrue(external.exists())
        # A directory-level symlink: the store root itself stays trusted, but
        # any component below it that is a link is refused, even when the
        # target is another legal spot inside the root.
        (self.root / "monsterlinks").symlink_to(self.root / "gallery")
        self.assertIsNone(
            resolved_under_store_root("monsterlinks/character/a.png")
        )

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_an_embedded_nul_identity_is_refused_without_raising(self):
        # resolve() raises ValueError (not OSError) on NUL paths; the helper
        # must refuse, not propagate.
        self.assertIsNone(
            resolved_under_store_root("gallery/character/a\x00.png")
        )

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_root_itself_and_empty_identity_are_refused(self):
        for identity in ("", ".", "gallery/.."):
            with self.subTest(identity=identity):
                self.assertIsNone(resolved_under_store_root(identity))


class FaceRectValidationTests(unittest.TestCase):
    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_the_shared_constant_is_the_upper_half_rect(self):
        self.assertEqual(
            DEFAULT_FACE_RECT, {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}
        )
        self.assertEqual(validate_face_rect(DEFAULT_FACE_RECT), DEFAULT_FACE_RECT)

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_a_valid_rect_is_stored_verbatim(self):
        rect = {"x": 0.1, "y": 0.0, "w": 0.9, "h": 1.0}
        self.assertEqual(validate_face_rect(rect), rect)

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_every_out_of_bounds_form_is_rejected(self):
        malformed = {
            "x_plus_w_over_one": {"x": 0.6, "y": 0.0, "w": 0.5, "h": 0.1},
            "y_plus_h_over_one": {"x": 0.0, "y": 0.6, "w": 0.1, "h": 0.5},
            "zero_width": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.5},
            "negative_height": {"x": 0.0, "y": 0.0, "w": 0.5, "h": -0.1},
            "value_below_zero": {"x": -0.01, "y": 0.0, "w": 0.5, "h": 0.5},
            "value_above_one": {"x": 0.0, "y": 0.0, "w": 1.01, "h": 0.1},
            "missing_key": {"x": 0.0, "y": 0.0, "w": 0.5},
            "extra_key": {"x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5, "z": 0.0},
            "string_value": {"x": "0.0", "y": 0.0, "w": 0.5, "h": 0.5},
            "boolean_value": {"x": True, "y": 0.0, "w": 0.5, "h": 0.5},
            "not_a_mapping": (0.0, 0.0, 0.5, 0.5),
        }
        for label, rect in malformed.items():
            with self.subTest(rect=label):
                with self.assertRaises(GalleryRecordError):
                    validate_face_rect(rect)


class BindingValidationTests(unittest.TestCase):
    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_none_is_a_legal_unbound_binding(self):
        self.assertIsNone(validate_binding(None))

    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_the_mask_is_stored_in_declared_order(self):
        binding = validate_binding(
            {
                "mask": ["armor", "weapon_main"],
                "snapshot": {"armor": "leather_vest", "weapon_main": "short_sword"},
            }
        )
        self.assertEqual(binding["mask"], ["weapon_main", "armor"])

    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_accessory_keys_are_stored_sorted(self):
        binding = validate_binding(
            {
                "mask": ["accessories"],
                "snapshot": {"accessories": ["ring_b", "amulet_a", "ring_c"]},
            }
        )
        self.assertEqual(binding["snapshot"]["accessories"], ["amulet_a", "ring_b", "ring_c"])

    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_an_all_empty_snapshot_is_a_legal_binding(self):
        binding = validate_binding(
            {
                "mask": ["weapon_main", "weapon_off", "armor", "accessories"],
                "snapshot": {
                    "weapon_main": None,
                    "weapon_off": None,
                    "armor": None,
                    "accessories": [],
                },
            }
        )
        self.assertEqual(binding["mask"], list(SLOT_ORDER))
        self.assertEqual(
            binding["snapshot"],
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        )

    @covers_requirement("art-gallery-model::a-card-binding-is-a-non-empty-slot-mask-plus-a-normalized-snapshot-over-exactly-the-masked-slots")
    def test_every_malformed_form_is_rejected(self):
        malformed = {
            "empty_mask": {"mask": [], "snapshot": {}},
            "nested_mask_members": {"mask": [["armor"]], "snapshot": {"armor": None}},
            "unknown_slot": {
                "mask": ["shield"],
                "snapshot": {"shield": None},
            },
            "duplicate_slot": {
                "mask": ["armor", "armor"],
                "snapshot": {"armor": None},
            },
            "snapshot_key_mismatch": {
                "mask": ["armor", "weapon_main"],
                "snapshot": {"armor": "leather_vest"},
            },
            "extra_snapshot_key": {
                "mask": ["armor"],
                "snapshot": {"armor": None, "weapon_main": None},
            },
            "empty_string_item": {
                "mask": ["armor"],
                "snapshot": {"armor": ""},
            },
            "boolean_item": {
                "mask": ["armor"],
                "snapshot": {"armor": True},
            },
            "accessories_not_a_list": {
                "mask": ["accessories"],
                "snapshot": {"accessories": "ring"},
            },
            "mask_not_a_list": {"mask": "armor", "snapshot": {"armor": None}},
            "not_a_mapping": ["mask", "snapshot"],
            "wrong_keys": {"mask": ["armor"], "snap": {"armor": None}},
        }
        for label, binding in malformed.items():
            with self.subTest(binding=label):
                with self.assertRaises(GalleryRecordError):
                    validate_binding(binding)


class CardContractTests(unittest.TestCase):
    def setUp(self):
        self.subject = _character()

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_generated_card_stores_exactly_the_contract_keys(self):
        stored = validate_card(
            _card_fields(self.subject, face_rect=dict(DEFAULT_FACE_RECT)),
            self.subject,
        )
        self.assertEqual(
            set(stored),
            {
                "image_id",
                "stored_identity",
                "prompt",
                "seed",
                "checkpoint",
                "requested_fields",
                "face_rect",
                "binding",
                "source",
                "created_at",
            },
        )
        for environment_key in (
            "steps",
            "cfg_scale",
            "width",
            "height",
            "sampler",
            "scheduler",
        ):
            self.assertNotIn(environment_key, stored)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_extra_missing_and_wrongly_typed_keys_are_rejected(self):
        base = _card_fields(self.subject)
        complete = dict(base, face_rect=dict(DEFAULT_FACE_RECT))
        missing_created = {k: v for k, v in complete.items() if k != "created_at"}
        violations = {
            "extra_key": dict(complete, steps=20),
            "missing_prompt": {k: v for k, v in complete.items() if k != "prompt"},
            "missing_requested_fields": {
                k: v for k, v in complete.items() if k != "requested_fields"
            },
            "wrong_prompt_shape": dict(complete, prompt="a hero"),
            "prompt_extra_key": dict(
                complete, prompt={"positive": "a", "negative": "b", "style": "c"}
            ),
            "negative_seed": dict(complete, seed=-1),
            "boolean_seed": dict(complete, seed=True),
            "empty_checkpoint": dict(complete, checkpoint=""),
            "requested_fields_not_a_list": dict(complete, requested_fields="appearance"),
            "unknown_source": dict(complete, source="imported"),
            "non_numeric_created_at": dict(complete, created_at="1699000000"),
        }
        for label, card in violations.items():
            with self.subTest(card=label):
                with self.assertRaises(GalleryRecordError):
                    validate_card(card, self.subject)
        # A write missing the created_at contract key fails the stored-form
        # validator even though the write API is allowed to omit it.
        with self.assertRaises(GalleryRecordError):
            validate_card(missing_created, self.subject, api_defaults=False)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_unhashable_and_non_finite_violations_stay_typed_errors(self):
        # Corruption must never escape as a bare TypeError/ValueError from
        # the validators (readers only catch GalleryRecordError).
        base = _card_fields(self.subject)
        complete = dict(base, face_rect=dict(DEFAULT_FACE_RECT))
        for label, card in {
            "unhashable_source": dict(complete, source=["generated"]),
            "unhashable_created_at": dict(complete, created_at=float("nan")),
            "infinite_created_at": dict(complete, created_at=float("inf")),
        }.items():
            with self.subTest(card=label):
                with self.assertRaises(GalleryRecordError):
                    validate_card(card, self.subject)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_face_rect_and_created_at_may_be_omitted_at_the_write_boundary(self):
        stored = validate_card(_card_fields(self.subject), self.subject)
        self.assertEqual(stored["face_rect"], DEFAULT_FACE_RECT)
        self.assertIsInstance(stored["created_at"], float)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_non_canonical_uuid_image_id_is_rejected(self):
        for image_id in (
            _new_id().upper(),
            "not-a-uuid",
            _new_id().replace("-", ""),
            42,
        ):
            with self.subTest(image_id=str(image_id)[:20]):
                fields = _card_fields(self.subject)
                fields["image_id"] = image_id
                # keep the identity consistent with the substituted id shape
                fields["stored_identity"] = _identity(
                    self.subject,
                    image_id if isinstance(image_id, str) else "x",
                )
                with self.assertRaises(GalleryRecordError):
                    validate_card(fields, self.subject)

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_store_identity_outside_the_gallery_shape_is_rejected(self):
        image_id = _new_id()
        subject = self.subject
        broken = {
            "wrong_directory": f"portrait/character/{subject.key}/{image_id}.png",
            "wrong_kind": f"gallery/monster/{subject.key}/{image_id}.png",
            "wrong_subject": f"gallery/character/other/{image_id}.png",
            "identity_id_mismatch": f"gallery/character/{subject.key}/{_new_id()}.png",
            "unknown_extension": _identity(subject, image_id, ".bmp"),
            "no_extension": _identity(subject, image_id, ""),
            "extra_segment": f"gallery/character/{subject.key}/deep/{image_id}.png",
        }
        for label, identity in broken.items():
            with self.subTest(identity=label):
                with self.assertRaises(GalleryRecordError):
                    validate_card(
                        _card_fields(subject, image_id=image_id, stored_identity=identity),
                        subject,
                    )

    @covers_requirement("art-gallery-model::an-image-card-carries-the-exact-reproduction-placement-and-provenance-contract")
    def test_a_scene_subject_can_have_no_cards(self):
        scene = _scene()
        image_id = _new_id()
        with self.assertRaises(GalleryRecordError):
            validate_card(
                {
                    "image_id": image_id,
                    "stored_identity": f"gallery/scene/{scene.key}/{image_id}.png",
                    "prompt": None,
                    "seed": None,
                    "checkpoint": None,
                    "requested_fields": [],
                    "binding": None,
                    "source": "seed",
                },
                scene,
            )

    @covers_requirement("art-gallery-model::malformed-stored-cards-are-skipped-never-fatal")
    def test_a_stored_entry_needs_the_complete_contract(self):
        # The read-side validation (api_defaults=False) rejects an entry that
        # lacks face_rect even though the write API would have defaulted it.
        fields = _card_fields(self.subject)
        with self.assertRaises(GalleryRecordError):
            validate_card(fields, self.subject, api_defaults=False)


class EquipmentSnapshotTests(unittest.TestCase):
    @covers_requirement("art-gallery-model::equipment-snapshots-are-read-from-stored-state-without-materializing-a-handler")
    def test_missing_equipment_reads_empty_without_touching_the_entity(self):
        entity = _FakeEntity()
        self.assertEqual(
            snapshot_for(entity),
            {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []},
        )
        # The read wrote nothing: the namespace still holds no equipment key.
        self.assertNotIn("equipment", entity.db._values)

    @covers_requirement("art-gallery-model::equipment-snapshots-are-read-from-stored-state-without-materializing-a-handler")
    def test_a_worn_loadout_reads_back_with_sorted_accessories(self):
        entity = _FakeEntity(
            {
                "weapon_main": "short_sword",
                "weapon_off": None,
                "armor": "leather_vest",
                "accessories": ["ring_b", "amulet_a"],
            }
        )
        self.assertEqual(
            snapshot_for(entity),
            {
                "weapon_main": "short_sword",
                "weapon_off": None,
                "armor": "leather_vest",
                "accessories": ["amulet_a", "ring_b"],
            },
        )

    @covers_requirement("art-gallery-model::equipment-snapshots-are-read-from-stored-state-without-materializing-a-handler")
    def test_every_malformed_storage_shape_fails_closed_to_empty(self):
        malformed = {
            "string": "wearing a hat",
            "list": ["short_sword"],
            "slot_wrong_type": {"weapon_main": 5, "armor": None},
            "slot_boolean": {"weapon_main": True},
            "slot_empty_string": {"armor": ""},
            "accessories_not_a_list": {"accessories": "ring"},
            "accessories_wrong_members": {"accessories": ["ring", 7]},
            "accessories_empty_member": {"accessories": ["ring", ""]},
        }
        for label, raw in malformed.items():
            with self.subTest(storage=label):
                self.assertEqual(
                    snapshot_for(_FakeEntity(raw)),
                    {
                        "weapon_main": None,
                        "weapon_off": None,
                        "armor": None,
                        "accessories": [],
                    },
                )

    @covers_requirement("art-gallery-model::equipment-snapshots-are-read-from-stored-state-without-materializing-a-handler")
    def test_missing_keys_read_as_their_empty_defaults(self):
        entity = _FakeEntity({"weapon_main": "short_sword"})
        self.assertEqual(
            snapshot_for(entity),
            {
                "weapon_main": "short_sword",
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
        )

    @covers_requirement("art-gallery-model::world-art-gallery-py-is-the-sole-writer-of-gallery-records-and-deletion-never-dangles")
    def test_only_the_gallery_module_references_gallery_records(self):
        """AST scan: no other production module names GalleryRecord at all.

        Read-only gallery API imports (cards_for, ...) stay legal for later
        changes; any reference to the record CLASS — by name, attribute
        chain, import alias, or string (create_script-style) — is the
        record-mutation foothold the single-writer rule forbids.
        """
        offenders = []
        for root in ("world", "typeclasses", "commands", "server", "web"):
            for path in sorted((REPO_ROOT / root).rglob("*.py")):
                relative = path.relative_to(REPO_ROOT)
                if "tests" in path.parts or "__pycache__" in path.parts:
                    continue
                if relative.as_posix() == "world/art/gallery.py":
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                referenced = any(
                    (isinstance(node, ast.Name) and node.id == "GalleryRecord")
                    or (isinstance(node, ast.Attribute) and node.attr == "GalleryRecord")
                    or (
                        isinstance(node, ast.Import)
                        and any(alias.name.startswith("world.art.gallery") and "GalleryRecord" in alias.name for alias in node.names)
                    )
                    or (
                        isinstance(node, ast.ImportFrom)
                        and node.module == "world.art.gallery"
                        and any(alias.name == "GalleryRecord" for alias in node.names)
                    )
                    or (
                        isinstance(node, ast.Constant)
                        and isinstance(node.value, str)
                        and "GalleryRecord" in node.value
                    )
                    for node in ast.walk(tree)
                )
                if referenced:
                    offenders.append(relative.as_posix())
        self.assertEqual(offenders, [])


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


if __name__ == "__main__":
    import unittest

    unittest.main()
