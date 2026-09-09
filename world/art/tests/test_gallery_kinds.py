"""Tests for the closed gallery kind capability declaration (gallery-kind-capabilities).

Pure ``unittest.TestCase``: the declaration module imports nothing and performs
no I/O, so every contract here — exhaustive kind coverage, the admitted card
maxima, the four readable capability fields, the explicit no-gallery scene
declaration, and the immutability of both records and table — runs without
Evennia, settings, or the database. Synthetic violations are injected through
the one supported seam: ``unittest.mock.patch.dict`` against the module-private
declaration dict.
"""

import unittest
from unittest.mock import patch

from world.art import gallery_kinds
from world.art.subjects import ArtSubjectKind

from tools.spec_traceability import covers_requirement

_ALL_KIND_VALUES = tuple(kind.value for kind in ArtSubjectKind)


def _record(**changes):
    """The real declaration copy-seamed with these fields changed."""
    base = gallery_kinds.GALLERY_KIND_CAPABILITIES[changes.pop("key")]
    return base.with_values(**changes)


def _violations_with(key: str, **changes):
    """Contract violations for the real vocabulary with one entry replaced."""
    with patch.dict(
        gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
        {key: _record(key=key, **changes)},
    ):
        return gallery_kinds.validate_declaration_contract(_ALL_KIND_VALUES)


class DeclarationContractTests(unittest.TestCase):
    @covers_requirement(
        "art-gallery-kind-capabilities::the-declaration-covers-every-subject-kind-exhaustively"
    )
    def test_the_declaration_covers_the_real_kind_vocabulary_exactly(self):
        self.assertEqual(
            gallery_kinds.validate_declaration_contract(_ALL_KIND_VALUES), []
        )
        # Exactly one entry per member: the table size and the vocabulary size
        # agree, and every member value resolves.
        self.assertEqual(len(gallery_kinds.GALLERY_KIND_CAPABILITIES), len(_ALL_KIND_VALUES))
        for value in _ALL_KIND_VALUES:
            self.assertEqual(
                gallery_kinds.GALLERY_KIND_CAPABILITIES[value].kind_value, value
            )

    @covers_requirement(
        "art-gallery-kind-capabilities::the-declaration-covers-every-subject-kind-exhaustively"
    )
    def test_a_new_kind_without_a_declaration_fails_naming_it(self):
        vocabulary = _ALL_KIND_VALUES + ("portrait:pet",)
        violations = gallery_kinds.validate_declaration_contract(vocabulary)
        self.assertEqual(len(violations), 1, violations)
        self.assertIn("portrait:pet", violations[0])
        self.assertIn("no gallery capability declaration", violations[0])

    @covers_requirement(
        "art-gallery-kind-capabilities::the-declaration-covers-every-subject-kind-exhaustively"
    )
    def test_a_stale_entry_for_a_removed_kind_fails_naming_it(self):
        vocabulary = tuple(value for value in _ALL_KIND_VALUES if "monster" not in value)
        violations = gallery_kinds.validate_declaration_contract(vocabulary)
        self.assertEqual(len(violations), 1, violations)
        self.assertIn("portrait:monster", violations[0])

    @covers_requirement(
        "art-gallery-kind-capabilities::the-declaration-covers-every-subject-kind-exhaustively"
    )
    def test_a_record_whose_kind_value_disagrees_with_its_key_fails(self):
        violations = _violations_with(
            ArtSubjectKind.CHARACTER.value, kind_value=ArtSubjectKind.MONSTER.value
        )
        self.assertEqual(len(violations), 1, violations)
        self.assertIn(ArtSubjectKind.CHARACTER.value, violations[0])
        self.assertIn(ArtSubjectKind.MONSTER.value, violations[0])

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_a_maximum_outside_the_admitted_values_fails_naming_kind_and_value(self):
        character_value = ArtSubjectKind.CHARACTER.value
        for illegal in (2, 3, 1.0, True, "1"):
            with self.subTest(maximum=illegal):
                violations = _violations_with(
                    character_value, max_cards=illegal
                )
                self.assertTrue(
                    any(character_value in v and "maximum" in v for v in violations),
                    violations,
                )

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_a_flag_that_is_not_a_bool_fails_naming_the_field(self):
        monster_value = ArtSubjectKind.MONSTER.value
        with self.subTest(field="has_gallery"):
            violations = _violations_with(monster_value, has_gallery=1)
            self.assertTrue(
                any("has_gallery" in v for v in violations), violations
            )
        with self.subTest(field="supports_bindings"):
            violations = _violations_with(monster_value, supports_bindings="yes")
            self.assertTrue(
                any("supports_bindings" in v for v in violations), violations
            )
        # The request-precondition fields (gallery-monster-generation) face the
        # same exactly-a-bool rule as the older flags.
        for flag in (
            "requires_age_precondition",
            "supports_field_selection",
            "supports_free_text",
        ):
            with self.subTest(field=flag):
                violations = _violations_with(monster_value, **{flag: 0})
                self.assertTrue(
                    any(flag in v for v in violations), violations
                )

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_a_cross_field_impossibility_fails_naming_the_kind(self):
        character_value = ArtSubjectKind.CHARACTER.value
        with self.subTest(case="gallery without a directory"):
            violations = _violations_with(character_value, store_directory="")
            self.assertTrue(
                any(character_value in v and "store directory" in v for v in violations),
                violations,
            )
        scene_value = ArtSubjectKind.SCENE.value
        with self.subTest(case="no-gallery kind claiming a directory"):
            violations = _violations_with(scene_value, store_directory="scene")
            self.assertTrue(
                any(scene_value in v and "store directory" in v for v in violations),
                violations,
            )
        with self.subTest(case="no-gallery kind claiming binding support"):
            violations = _violations_with(scene_value, supports_bindings=True)
            self.assertTrue(
                any(scene_value in v and "binding" in v for v in violations),
                violations,
            )
        # A no-gallery kind may not claim any request precondition either.
        for flag in (
            "requires_age_precondition",
            "supports_field_selection",
            "supports_free_text",
        ):
            with self.subTest(case=f"no-gallery kind claiming {flag}"):
                violations = _violations_with(scene_value, **{flag: True})
                self.assertTrue(
                    any(scene_value in v and flag in v for v in violations),
                    violations,
                )

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_every_declared_capability_is_readable_from_one_place(self):
        character = gallery_kinds.capabilities_for(ArtSubjectKind.CHARACTER.value)
        monster = gallery_kinds.capabilities_for(ArtSubjectKind.MONSTER.value)
        for record in (character, monster):
            self.assertIsInstance(record.kind_value, str)
            self.assertIsInstance(record.has_gallery, bool)
            self.assertTrue(record.has_gallery)
            self.assertIsInstance(record.store_directory, str)
            self.assertTrue(record.store_directory)
            self.assertIsInstance(record.supports_bindings, bool)
            for flag in (
                "requires_age_precondition",
                "supports_field_selection",
                "supports_free_text",
            ):
                self.assertIsInstance(getattr(record, flag), bool)
        self.assertEqual(character.store_directory, "character")
        self.assertIsNone(character.max_cards)
        self.assertTrue(character.supports_bindings)
        self.assertTrue(character.requires_age_precondition)
        self.assertTrue(character.supports_field_selection)
        self.assertTrue(character.supports_free_text)
        self.assertEqual(monster.store_directory, "monster")
        self.assertEqual(monster.max_cards, 1)
        self.assertFalse(monster.supports_bindings)
        self.assertFalse(monster.requires_age_precondition)
        self.assertFalse(monster.supports_field_selection)
        self.assertFalse(monster.supports_free_text)

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_the_monster_kind_declares_strictly_fewer_capabilities(self):
        # The monster's fewer capabilities are a declaration, not a special
        # case in the code that serves it: one read of the two records shows
        # the monster lacking ALL FOUR discretionary capabilities while the
        # character declares every one of them.
        character = gallery_kinds.capabilities_for(ArtSubjectKind.CHARACTER.value)
        monster = gallery_kinds.capabilities_for(ArtSubjectKind.MONSTER.value)
        declared = (
            "supports_bindings",
            "requires_age_precondition",
            "supports_field_selection",
            "supports_free_text",
        )
        for flag in declared:
            self.assertTrue(getattr(character, flag), flag)
            self.assertFalse(getattr(monster, flag), flag)
        self.assertIsNone(character.max_cards)
        self.assertEqual(monster.max_cards, 1)

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_the_scene_kind_is_declared_as_having_no_gallery(self):
        scene = gallery_kinds.capabilities_for(ArtSubjectKind.SCENE.value)
        self.assertFalse(scene.has_gallery)
        self.assertIsNone(scene.store_directory)
        self.assertIsNone(scene.max_cards)
        self.assertFalse(scene.supports_bindings)
        # A no-gallery kind contributes no store directory segment.
        self.assertNotIn("scene", gallery_kinds.gallery_store_directory_segments())
        self.assertEqual(
            gallery_kinds.gallery_store_directory_segments(),
            frozenset({"character", "monster"}),
        )
        # The reverse lookup only knows gallery-bearing segments.
        self.assertIsNone(gallery_kinds.kind_value_for_store_directory("scene"))
        self.assertEqual(
            gallery_kinds.kind_value_for_store_directory("monster"),
            ArtSubjectKind.MONSTER.value,
        )
        self.assertEqual(
            gallery_kinds.kind_value_for_store_directory("character"),
            ArtSubjectKind.CHARACTER.value,
        )
        self.assertIsNone(gallery_kinds.kind_value_for_store_directory("bogus"))

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_the_directory_vocabulary_follows_a_patched_declaration(self):
        # The segments are derived fresh from the declaration: a kind patched
        # to lose its gallery leaves the vocabulary too (single source of
        # truth over the patch seam).
        with patch.dict(
            gallery_kinds._CAPABILITIES_BY_KIND_VALUE,
            {
                ArtSubjectKind.MONSTER.value: _record(
                    key=ArtSubjectKind.MONSTER.value,
                    has_gallery=False,
                    store_directory=None,
                )
            },
        ):
            self.assertEqual(
                gallery_kinds.gallery_store_directory_segments(),
                frozenset({"character"}),
            )

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_an_undeclared_kind_value_raises_loudly(self):
        with self.assertRaises(KeyError) as caught:
            gallery_kinds.capabilities_for("portrait:pet")
        self.assertIn("portrait:pet", str(caught.exception))
        with self.assertRaises(KeyError):
            gallery_kinds.has_gallery("portrait:pet")


class DeclarationImmutabilityTests(unittest.TestCase):
    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_a_capability_record_refuses_mutation(self):
        record = gallery_kinds.capabilities_for(ArtSubjectKind.MONSTER.value)
        with self.assertRaises(TypeError):
            record.max_cards = 99
        with self.assertRaises(TypeError):
            del record.max_cards
        with self.assertRaises(TypeError):
            record.store_directory = "elsewhere"
        # No caller observes a changed capability.
        self.assertEqual(record.max_cards, 1)
        self.assertEqual(record.store_directory, "monster")

    @covers_requirement(
        "art-gallery-kind-capabilities::one-closed-declaration-states-what-every-subject-kind-s-gallery-may-do"
    )
    def test_the_table_refuses_mutation(self):
        table = gallery_kinds.GALLERY_KIND_CAPABILITIES
        before = dict(table.items())
        with self.assertRaises(TypeError):
            table[ArtSubjectKind.MONSTER.value] = None
        with self.assertRaises(TypeError):
            del table[ArtSubjectKind.MONSTER.value]
        with self.assertRaises(TypeError):
            table["portrait:pet"] = None
        with self.assertRaises(TypeError):
            table.secret = None
        with self.assertRaises(TypeError):
            del table.secret
        self.assertEqual(dict(table.items()), before)
        # The view retains no mutable dict of its own for a consumer to
        # reach around the frozen interface with.
        self.assertEqual(table.__slots__, ())
        # Reads through the view agree with the accessors.
        self.assertIs(
            table[ArtSubjectKind.CHARACTER.value],
            gallery_kinds.capabilities_for(ArtSubjectKind.CHARACTER.value),
        )


if __name__ == "__main__":
    unittest.main()
