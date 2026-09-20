"""Full-title schema guard tests for the character panel envelope budget."""
import unittest
from web.webclient.presentation.character import MAX_FULL_TITLE_CODE_POINTS, validate_character
from web.webclient.presentation.protocol import ProtocolValidationError
from ._support import _T_COMPOSED_TITLE, _T_TITLE, _valid_panel


class CharacterFullTitleSchemaTests(unittest.TestCase):
    """The optional ``full_title`` row: bounded, non-blank, absent when empty."""


    def test_absent_field_is_accepted_and_never_synthesized(self):
        normalized = validate_character(_valid_panel())
        self.assertNotIn("full_title", normalized)


    def test_a_valid_full_title_round_trips(self):
        normalized = validate_character(
            _valid_panel(full_title=_T_COMPOSED_TITLE)
        )
        self.assertEqual(normalized["full_title"], _T_COMPOSED_TITLE)


    def test_the_field_bound_matches_the_python_constant(self):
        at_bound = "長" * MAX_FULL_TITLE_CODE_POINTS
        self.assertEqual(
            validate_character(_valid_panel(full_title=at_bound))["full_title"],
            at_bound,
        )
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(full_title=at_bound + "長"))


    def test_blank_non_string_and_null_forms_reject(self):
        for bad in ("", "　", "   ", 7, 1.5, True, [_T_TITLE.display_name_zh], None):
            with self.subTest(bad=bad), self.assertRaises(ProtocolValidationError):
                validate_character(_valid_panel(full_title=bad))


    def test_the_panel_stays_read_only_with_a_title(self):
        # full_title joins the exact available field set; an unknown sibling
        # of it is still rejected.
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(titles=[_T_COMPOSED_TITLE]))


if __name__ == "__main__":
    unittest.main()
