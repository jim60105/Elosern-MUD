"""Permanent executable guard for the frozen reference record."""

from tools.spec_traceability import covers_requirement

from pathlib import Path

from unittest import TestCase

from world.imports.tests.helpers import EXAMPLE_PATH, example_record
from world.imports.validate import validate_batch
from world.lore.npc_card import NPC_CARD_FIELDS, normalize_card

GM_CHARACTERS_DOC = (
    Path(__file__).parents[3] / "docs" / "gm" / "characters.md"
)


class ReferenceExampleTests(TestCase):
    @covers_requirement("import-reference-example::the-reference-example-demonstrates-the-base-value-stats-convention-correctly", "import-reference-example::the-reference-example-exercises-every-major-schema-branch-and-a-complete-npc-card")
    def test_reference_example_is_clean_and_exercises_contract(self):
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        self.assertFalse(report.records[0].rejections)
        self.assertFalse(report.records[0].warnings)
        record = example_record()
        self.assertEqual(record["record_type"], "character")
        self.assertTrue(record["subrace"])
        self.assertEqual(len(record["stats"]), 8)
        # The example's race (human) cannot use divine arts, so the
        # divine-arts-seeding-guard boundary forbids a populated layer here.
        self.assertFalse(record["disguised_stats"])
        self.assertTrue(record["skills"] and record["passives"])
        self.assertGreater(len(record["sexual_baseline"]), 3)
        normalize_card(record["persona"])

    @covers_requirement("import-reference-example::the-reference-example-carries-a-complete-compact-npc-card")
    def test_reference_persona_is_a_complete_normalized_card(self):
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        self.assertFalse(report.records[0].rejections)
        self.assertFalse(report.records[0].warnings)
        persona = example_record()["persona"]
        self.assertEqual(set(persona), NPC_CARD_FIELDS)
        self.assertNotIn("background", persona)
        # Already in normalized form, so the validated card equals the file.
        self.assertEqual(normalize_card(persona).to_record(), persona)
        self.assertEqual(report.records[0].record["persona"], persona)


class ReferenceTitleTests(TestCase):
    def test_reference_card_carries_no_title_field(self):
        record = example_record()
        self.assertNotIn("title", record)
        report = validate_batch([EXAMPLE_PATH])
        self.assertTrue(report.all_valid)
        self.assertFalse(report.records[0].rejections)
        self.assertFalse(report.records[0].warnings)


class GmImportDocumentationTests(TestCase):
    """npc-title-authoring-removal: the GM import doc documents no title field."""

    @classmethod
    def setUpClass(cls):
        cls.doc = GM_CHARACTERS_DOC.read_text(encoding="utf-8")

    def test_documentation_carries_no_title_field(self):
        self.assertNotIn("| `title` |", self.doc)
        self.assertNotIn('"title"', self.doc)

    def test_doc_states_the_display_name_comes_from_key(self):
        self.assertIn("顯示姓名來自 `key`", self.doc)

    def test_doc_states_the_validation_responsibility_split(self):
        # The CLI is file-scope only; the existing-NPC name gate is stated to
        # run at load time (design D4's documented responsibility line).
        self.assertIn("由 `load_batch()` 在載入時整批把關", self.doc)
        self.assertIn("CLI", self.doc)
