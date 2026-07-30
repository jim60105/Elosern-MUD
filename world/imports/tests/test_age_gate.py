"""Permanent regression guard: never delete or loosen the adult age gate."""

from unittest import TestCase

from world.imports.tests.helpers import example_record
from world.imports.validate import validate_character


class AgeGateTests(TestCase):
    def test_age_17_is_always_rejected(self):
        record = example_record()
        record["age"] = 17
        self.assertIn("age", {issue.field for issue in validate_character(record).rejections})

    def test_apparent_age_17_is_independently_rejected(self):
        record = example_record()
        record["apparent_age"] = 17
        self.assertIn(
            "apparent_age",
            {issue.field for issue in validate_character(record).rejections},
        )

    def test_exactly_18_passes_the_age_gate(self):
        record = example_record()
        record["age"] = record["apparent_age"] = 18
        fields = {issue.field for issue in validate_character(record).rejections}
        self.assertNotIn("age", fields)
        self.assertNotIn("apparent_age", fields)

    def test_omitting_either_age_field_rejects(self):
        for key in ("age", "apparent_age"):
            record = example_record()
            del record[key]
            with self.subTest(key=key):
                self.assertIn(
                    key, {issue.field for issue in validate_character(record).rejections}
                )
