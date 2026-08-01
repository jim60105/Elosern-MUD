from tools.spec_traceability import covers_requirement

from unittest import TestCase

from world.imports.tests.helpers import example_record
from world.imports.validate import (
    RecordClassificationError,
    classify_record,
    validate_character,
)


class DispatchTests(TestCase):
    def test_dispatch_uses_only_record_type(self):
        self.assertEqual(classify_record({"record_type": "character"}), "character")
        self.assertEqual(classify_record({"record_type": "world_entry"}), "world_entry")
        record = example_record()
        del record["age"]
        self.assertEqual(classify_record(record), "character")
        self.assertIn("age", {issue.field for issue in validate_character(record).rejections})

    @covers_requirement("import-schema::both-schemas-require-an-explicit-record-type-discriminator-not-implicit-field-sniffing")
    def test_invalid_discriminators_name_both_valid_values(self):
        for value in ("missing", None, "npc"):
            raw = {} if value == "missing" else {"record_type": value}
            with self.subTest(value=value), self.assertRaises(RecordClassificationError) as ctx:
                classify_record(raw)
            self.assertIn("character", str(ctx.exception))
            self.assertIn("world_entry", str(ctx.exception))
