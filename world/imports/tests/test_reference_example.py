"""Permanent executable guard for the frozen reference record."""

from tools.spec_traceability import covers_requirement

from pathlib import Path

from unittest import TestCase

from world.imports.tests.helpers import EXAMPLE_PATH, example_record
from world.imports.validate import validate_batch
from world.rules.npc_identity import validate_npc_title

GM_CHARACTERS_DOC = (
    Path(__file__).parents[3] / "docs" / "gm" / "characters.md"
)


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
        self.assertTrue(record["skills"] and record["passives"])
        self.assertGreater(len(record["sexual_baseline"]), 3)
        self.assertGreater(len(record["persona"]), 1)

    @covers_requirement("import-reference-example::the-reference-example-exercises-the-persona-block-with-a-background")
    def test_reference_persona_demonstrates_the_background_key(self):
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        record = example_record()
        persona = record["persona"]
        self.assertIsInstance(persona, dict)
        self.assertIn("background", persona)
        self.assertTrue(persona["background"].strip())


class ReferenceTitleTests(TestCase):
    @covers_requirement("npc-identity-titles::the-reference-card-and-the-gm-import-documentation-carry-the-title-field")
    def test_reference_card_carries_a_validator_clean_title(self):
        record = example_record()
        self.assertEqual(record["title"], "參考範例")
        self.assertEqual(validate_npc_title(record["title"]), "參考範例")
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        self.assertFalse(report.records[0].rejections)
        self.assertFalse(report.records[0].warnings)


class GmImportDocumentationTests(TestCase):
    """npc-title-import-pipeline: the GM import doc carries the field and the split."""

    @classmethod
    def setUpClass(cls):
        cls.doc = GM_CHARACTERS_DOC.read_text(encoding="utf-8")

    def test_required_field_table_documents_the_title(self):
        # The table row names the field, its code-point bound, and the
        # NPC-only effect; the inline example record carries it.
        self.assertIn("| `title` |", self.doc)
        self.assertIn("只對 NPC 匯入生效", self.doc)
        self.assertIn('"title"', self.doc)

    def test_doc_states_the_display_name_comes_from_key(self):
        self.assertIn("顯示姓名來自 `key`", self.doc)

    def test_doc_states_the_validation_responsibility_split(self):
        # The CLI is file-scope only; the existing-NPC name gate is stated to
        # run at load time (design D4's documented responsibility line).
        self.assertIn("由 `load_batch()` 在載入時整批把關", self.doc)
        self.assertIn("CLI", self.doc)
