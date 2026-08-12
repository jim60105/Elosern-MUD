"""Permanent executable guard for the frozen reference record."""

from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.imports.tests.helpers import EXAMPLE_PATH, example_record
from world.imports.validate import validate_batch


class ReferenceExampleTests(TestCase):
    @covers_requirement("import-reference-example::the-reference-example-demonstrates-the-base-value-stats-convention-correctly")
    def test_reference_example_is_clean_and_exercises_contract(self):
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        self.assertFalse(report.records[0].rejections)
        self.assertFalse(report.records[0].warnings)
        record = example_record()
        self.assertEqual(record["record_type"], "character")
        self.assertTrue(record["subrace"])
        self.assertEqual(len(record["stats"]), 8)
        self.assertTrue(record["disguised_stats"])
        self.assertLess(set(record["disguised_stats"]), set(record["stats"]))
        self.assertTrue(record["skills"] or record["passives"])
        self.assertGreater(len(record["sexual_baseline"]), 3)
        self.assertGreater(len(record["persona"]), 1)
