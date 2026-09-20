"""Slice of ``test_gallery``: CardContractTests, EquipmentSnapshotTests.
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
    REPO_ROOT,
    _character,
    _scene,
    _new_id,
    _identity,
    _card_fields,
    _FakeEntity,
)

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
