"""Slice of ``test_gallery``: StoreRootConfinementTests, FaceRectValidationTests, BindingValidationTests.
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
    validate_image_size,
    default_face_rect,
    validate_stage,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectKind
from tools.spec_traceability import covers_requirement

class StageValidationTests(unittest.TestCase):
    @covers_requirement("art-gallery-model::per-card-stage-transforms-are-bounded-atomic-presentation-metadata")
    def test_inclusive_bounds_preserve_values_in_fresh_plain_mapping(self):
        for value in ({"scale": 0.2, "x": -0.5, "y": 0.5}, {"scale": 2, "x": 0.5, "y": -0.5}):
            result = validate_stage(value)
            self.assertEqual(result, value)
            self.assertIs(type(result), dict)
            self.assertIsNot(result, value)

    @covers_requirement("art-gallery-model::per-card-stage-transforms-are-bounded-atomic-presentation-metadata")
    def test_hostile_shapes_types_and_bounds_refuse(self):
        for field in ("scale", "x", "y"):
            for invalid in (True, False, float("nan"), float("inf"), -float("inf"), None, "0", [], 3, -1):
                with self.subTest(field=field, invalid=invalid):
                    value = {"scale": 1, "x": 0, "y": 0}
                    value[field] = invalid
                    with self.assertRaises(GalleryRecordError):
                        validate_stage(value)
        for value in (None, [], {}, {"scale": 1, "x": 0}, {"scale": 1, "x": 0, "y": 0, "z": 0}):
            with self.subTest(value=value), self.assertRaises(GalleryRecordError):
                validate_stage(value)


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

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_size_aware_square_tolerance_and_boundary(self):
        # 0.4 on 768 is 307.2 px; 0.3 on 1024 is 307.2 px => diff 0.0 <= 1.0 px
        rect = {"x": 0.1, "y": 0.1, "w": 0.4, "h": 0.3}
        size_768_1024 = {"width": 768, "height": 1024}
        size_1000 = {"width": 1000, "height": 1000}
        self.assertEqual(validate_face_rect(rect, image_size=size_768_1024), rect)
        with self.assertRaises(GalleryRecordError):
            validate_face_rect(rect, image_size=size_1000)

        # DEFAULT_FACE_RECT is not square on 768x1024 (w*768 = 384, h*1024 = 512, diff = 128 px)
        with self.assertRaises(GalleryRecordError):
            validate_face_rect(DEFAULT_FACE_RECT, image_size=size_768_1024)

        # Tolerance boundary: 1 px inside, 2 px out on 1000x1000
        # pixel_w = 0.5 * 1000 = 500 px.
        # 1 px inside: h = 501/1000 = 0.501 => abs(500 - 501) = 1.0 <= 1.0 -> ok
        inside = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.501}
        self.assertEqual(validate_face_rect(inside, image_size=size_1000), inside)
        # 2 px out: h = 502/1000 = 0.502 => abs(500 - 502) = 2.0 > 1.0 -> rejects
        outside = {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.502}
        with self.assertRaises(GalleryRecordError):
            validate_face_rect(outside, image_size=size_1000)

        # None image_size retains bounds-only behavior
        self.assertEqual(validate_face_rect(rect, image_size=None), rect)
        self.assertEqual(validate_face_rect(DEFAULT_FACE_RECT, image_size=None), DEFAULT_FACE_RECT)

    @covers_requirement("art-gallery-model::face-rectangles-are-normalized-bounded-and-default-to-the-shared-upper-half-constant")
    def test_default_face_rect_computation(self):
        fitted = default_face_rect({"width": 768, "height": 1024})
        self.assertEqual(fitted, {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.375})
        square = default_face_rect({"width": 1000, "height": 1000})
        self.assertEqual(square, DEFAULT_FACE_RECT)


class ImageSizeValidationTests(unittest.TestCase):
    @covers_requirement("art-gallery-model::a-card-s-image-pixel-size-is-recorded-from-verified-bytes-at-append")
    def test_positive_integer_pairs_accepted(self):
        self.assertEqual(
            validate_image_size({"width": 768, "height": 1024}),
            {"width": 768, "height": 1024},
        )

    @covers_requirement("art-gallery-model::a-card-s-image-pixel-size-is-recorded-from-verified-bytes-at-append")
    def test_malformed_image_sizes_rejected(self):
        bad_sizes = {
            "missing_height": {"width": 100},
            "missing_width": {"height": 100},
            "extra_key": {"width": 100, "height": 100, "depth": 3},
            "zero_width": {"width": 0, "height": 100},
            "zero_height": {"width": 100, "height": 0},
            "negative_width": {"width": -10, "height": 100},
            "negative_height": {"width": 100, "height": -10},
            "float_width": {"width": 100.5, "height": 100},
            "bool_width": {"width": True, "height": 100},
            "str_width": {"width": "100", "height": "100"},
            "not_a_mapping": [100, 100],
        }
        for label, val in bad_sizes.items():
            with self.subTest(size=label):
                with self.assertRaises(GalleryRecordError):
                    validate_image_size(val)


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
