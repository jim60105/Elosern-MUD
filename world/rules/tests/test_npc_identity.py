"""NPC identity validation tests.

Covers the single-validator contracts: strip-normalize, reject-on-stripped-form,
the code-point bounds, and the whitespace/control/markup rejections for both an
authored title and an authored name, plus cross-registry name uniqueness.
"""

import unittest

from tools.spec_traceability import covers_requirement

from world.rules.npc_identity import (
    MAX_NPC_NAME_CODE_POINTS,
    MAX_NPC_TITLE_CODE_POINTS,
    NPCNameError,
    NPCTitleError,
    validate_npc_name,
    validate_unique_npc_names,
    validate_npc_title,
)

_FULL_WIDTH_SPACE = "\u3000"


class ValidateNPCTitleTests(unittest.TestCase):
    """The single validator every authored title write path validates against."""

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_legal_title_round_trips_stripped(self):
        self.assertEqual(validate_npc_title(" 南門守衛 "), "南門守衛")
        self.assertEqual(
            validate_npc_title(f"{_FULL_WIDTH_SPACE}雜貨店老闆{_FULL_WIDTH_SPACE}"),
            "雜貨店老闆",
        )

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_boundary_lengths_are_decided_exactly(self):
        at_bound = "守" * MAX_NPC_TITLE_CODE_POINTS
        self.assertEqual(validate_npc_title(at_bound), at_bound)
        with self.assertRaises(NPCTitleError):
            validate_npc_title(at_bound + "守")

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_internal_whitespace_and_separator_are_rejected(self):
        for value in ("南門 守衛", f"南門{_FULL_WIDTH_SPACE}守衛", "南門\t守衛"):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_control_and_nonprintable_characters_are_rejected(self):
        for value in ("南門\x00守衛", "南門\x1b守衛", "南門\u200b守衛"):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_markup_delimiter_is_rejected(self):
        with self.assertRaises(NPCTitleError):
            validate_npc_title("|r南門守衛|n")

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_non_text_values_are_rejected(self):
        for value in (None, 42, True, False, 3.5, ["南門守衛"], {"t": "南門守衛"}):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_empty_and_whitespace_only_values_are_rejected(self):
        for value in ("", "   ", _FULL_WIDTH_SPACE, " \t\u3000 "):
            with self.subTest(value=value):
                with self.assertRaises(NPCTitleError):
                    validate_npc_title(value)

    @covers_requirement('npc-identity-titles::npc-titles-are-validated-single-line-plain-text')
    def test_rejection_messages_are_stable_english_identifiers(self):
        cases = {
            123: "npc title must be text",
            "  ": "npc title must be non-empty after stripping",
            "守" * (MAX_NPC_TITLE_CODE_POINTS + 1): "npc title must be at most",
            "南 門": "npc title must not contain whitespace",
            "南\x00門": "npc title contains a control character",
            "南|門": "npc title contains an Evennia markup delimiter",
        }
        for value, expected in cases.items():
            with self.subTest(value=repr(value)):
                with self.assertRaises(NPCTitleError) as caught:
                    validate_npc_title(value)
                self.assertIn(expected, str(caught.exception))
                self.assertTrue(
                    all(ord(char) < 128 for char in str(caught.exception))
                )


class ValidateNPCNameTests(unittest.TestCase):
    """The shared authored-name rule (npc-title-authored-identities).

    Traceability annotations are attached after the change's delta syncs
    (tasks 6.2 fixes the canonical requirement IDs); behavior is pinned here.
    """

    def test_legal_name_round_trips_stripped(self):
        self.assertEqual(validate_npc_name(" 黑鬍 "), "黑鬍")
        self.assertEqual(
            validate_npc_name(f"{_FULL_WIDTH_SPACE}岑影‧鐵硨{_FULL_WIDTH_SPACE}"),
            "岑影‧鐵硨",
        )

    def test_interior_ordinary_whitespace_is_allowed(self):
        # The single deliberate divergence from the title rule: multi-word
        # names are legal entity keys and must validate untouched.
        self.assertEqual(validate_npc_name("Jorn Urial"), "Jorn Urial")

    def test_boundary_lengths_are_decided_exactly(self):
        at_bound = "守" * MAX_NPC_NAME_CODE_POINTS
        self.assertEqual(validate_npc_name(at_bound), at_bound)
        with self.assertRaises(NPCNameError):
            validate_npc_name(at_bound + "守")

    def test_full_width_separator_is_rejected(self):
        with self.assertRaises(NPCNameError):
            validate_npc_name(f"南門{_FULL_WIDTH_SPACE}守衛")

    def test_control_and_nonprintable_characters_are_rejected(self):
        for value in ("雷加\x00拳", "雷加\x1b拳", "雷加\u200b拳"):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_markup_delimiter_is_rejected(self):
        with self.assertRaises(NPCNameError):
            validate_npc_name("|r雷加|n")

    def test_non_text_values_are_rejected(self):
        for value in (None, 42, True, False, 3.5, ["雷加"], {"n": "雷加"}):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_empty_and_whitespace_only_values_are_rejected(self):
        for value in ("", "   ", _FULL_WIDTH_SPACE, " \t\u3000 "):
            with self.subTest(value=value):
                with self.assertRaises(NPCNameError):
                    validate_npc_name(value)

    def test_rejection_messages_are_stable_english_identifiers(self):
        cases = {
            123: "npc name must be text",
            "  ": "npc name must be non-empty after stripping",
            "守" * (MAX_NPC_NAME_CODE_POINTS + 1): "npc name must be at most",
            f"南{_FULL_WIDTH_SPACE}門": "npc name contains the identity separator",
            "雷\x00加": "npc name contains a control character",
            "雷|加": "npc name contains an Evennia markup delimiter",
        }
        for value, expected in cases.items():
            with self.subTest(value=repr(value)):
                with self.assertRaises(NPCNameError) as caught:
                    validate_npc_name(value)
                self.assertIn(expected, str(caught.exception))
                self.assertTrue(
                    all(ord(char) < 128 for char in str(caught.exception))
                )


class ValidateUniqueNPCNamesTests(unittest.TestCase):
    """Cross-registry authored-name uniqueness checker (design D4)."""

    def test_unique_entries_pass(self):
        validate_unique_npc_names([("shop:a", "甲"), ("guild_rank:b", "乙")])

    def test_duplicate_names_are_rejected_naming_both_holders(self):
        with self.assertRaises(NPCNameError) as caught:
            validate_unique_npc_names([("shop:a", "甲"), ("guild_rank:b", "甲")])
        message = str(caught.exception)
        self.assertIn("shop:a", message)
        self.assertIn("guild_rank:b", message)
