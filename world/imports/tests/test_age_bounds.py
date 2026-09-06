"""Permanent regression guard: never delete or loosen the 0-10000 age bounds."""

from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.imports.tests.helpers import example_record
from world.imports.validate import _check_age_range, validate_character


class AgeBoundsTests(TestCase):
    def _fields(self, record):
        return {issue.field for issue in validate_character(record).rejections}

    def test_negative_age_is_rejected_naming_the_field(self):
        record = example_record()
        record["age"] = -1
        self.assertIn("age", self._fields(record))

    def test_negative_apparent_age_is_independently_rejected(self):
        record = example_record()
        record["apparent_age"] = -1
        self.assertIn("apparent_age", self._fields(record))

    def test_age_above_the_maximum_is_rejected_naming_the_field(self):
        record = example_record()
        record["age"] = 10001
        self.assertIn("age", self._fields(record))

    def test_apparent_age_above_the_maximum_is_independently_rejected(self):
        record = example_record()
        record["apparent_age"] = 10001
        self.assertIn("apparent_age", self._fields(record))

    @covers_requirement("import-schema::character-schema-v1-bounds-age-and-apparent-age-to-the-0-10000-reasonable-range")
    @covers_requirement("import-reference-example::one-valid-reference-character-card-exists-and-stays-valid")
    def test_both_range_ends_pass(self):
        for value in (0, 10000):
            record = example_record()
            record["age"] = record["apparent_age"] = value
            with self.subTest(value=value):
                fields = self._fields(record)
                self.assertNotIn("age", fields)
                self.assertNotIn("apparent_age", fields)

    def test_omitting_either_age_field_rejects(self):
        for key in ("age", "apparent_age"):
            record = example_record()
            del record[key]
            with self.subTest(key=key):
                self.assertIn(key, self._fields(record))

    def test_boolean_age_is_rejected_as_a_non_integer(self):
        # ``type(value) is not int`` idiom: JSON booleans never count as the
        # integer age a record must carry.
        record = example_record()
        record["age"] = True
        self.assertIn("age", self._fields(record))

    def test_fractional_apparent_age_is_rejected_as_a_non_integer(self):
        record = example_record()
        record["apparent_age"] = 22.5
        self.assertIn("apparent_age", self._fields(record))

    def test_integral_float_is_accepted_as_an_integer(self):
        # Existing jsonschema behavior kept verbatim: 22.0 satisfies the
        # integer type check, so it must stay a plain pass.
        record = example_record()
        record["age"] = record["apparent_age"] = 22.0
        fields = self._fields(record)
        self.assertNotIn("age", fields)
        self.assertNotIn("apparent_age", fields)

    def test_semantic_range_check_is_a_real_bounds_check(self):
        # Direct call proves the semantic mirror decides on the numbers:
        # out-of-range integers reject naming their own field, in-range
        # values pass, and non-exact ints stay silent for the structural
        # phase that owns shape.
        record = example_record()
        record["age"] = -1
        record["apparent_age"] = 10001
        self.assertEqual(
            [issue.field for issue in _check_age_range(record)],
            ["age", "apparent_age"],
        )
        for low, high in ((0, 0), (10000, 10000), (0, 10000), (22, 33)):
            record["age"], record["apparent_age"] = low, high
            with self.subTest(ages=(low, high)):
                self.assertEqual(_check_age_range(record), [])
        record["age"] = False
        record["apparent_age"] = 10000.0
        self.assertEqual(_check_age_range(record), [])
