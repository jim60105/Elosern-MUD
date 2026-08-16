from tools.spec_traceability import covers_requirement

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from world.imports.loader import ImportRejected, load_batch
from world.imports.tests.helpers import EXAMPLE_PATH, example_record
from world.imports.validate import main, validate_batch


class BatchTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()
        super().tearDown()

    def write(self, name, record):
        path = self.root / name
        path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        return path

    @covers_requirement("import-validation::import-validation-is-all-or-nothing-across-a-batch-of-files")
    @covers_requirement("import-validation::every-reported-issue-names-the-record-the-field-and-the-reason", "import-validation::validate-py-provides-a-cli-that-validates-one-or-more-record-files")
    def test_one_bad_record_fails_batch_but_reports_every_file(self):
        bad = example_record()
        bad["age"] = 17
        bad_path = self.write("bad.json", bad)
        report = validate_batch([EXAMPLE_PATH, bad_path])
        self.assertFalse(report.all_valid)
        self.assertEqual(len(report.records), 2)
        self.assertEqual(main([str(EXAMPLE_PATH), str(bad_path)]), 1)

    def test_rejected_batch_constructs_nothing_and_carries_report(self):
        bad = example_record()
        bad["age"] = 17
        bad_path = self.write("bad.json", bad)
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected) as ctx:
                load_batch([EXAMPLE_PATH, bad_path])
        instantiate.assert_not_called()
        self.assertEqual(len(ctx.exception.report.records), 2)

    def test_valid_mixed_batch_constructs_only_characters(self):
        world_path = self.write(
            "world.json",
            {
                "record_type": "world_entry",
                "schema_version": 1,
                "key": "tavern",
                "content": "A quiet tavern.",
            },
        )
        entities = load_batch([EXAMPLE_PATH, world_path])
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].key, "human_reference")

    def test_duplicate_world_keys_reject_every_duplicate(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "duplicate",
            "content": "First.",
        }
        first = self.write("first.json", world)
        world["content"] = "Second."
        second = self.write("second.json", world)
        report = validate_batch([first, second])
        self.assertFalse(report.all_valid)
        self.assertTrue(all(item.rejections for item in report.records))

    @covers_requirement("import-loader::loader-py-instantiates-entities-only-after-batch-validation-reports-zero-rejections")
    def test_construction_failure_rolls_back_earlier_entities(self):
        second = example_record()
        second["key"] = "second_reference"
        second_path = self.write("second.json", second)
        from world.imports import loader

        real_construct = loader._instantiate_validated_character
        calls = 0

        def fail_second(record, typeclass):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected construction failure")
            return real_construct(record, typeclass)

        with patch(
            "world.imports.loader._instantiate_validated_character",
            side_effect=fail_second,
        ), self.assertRaises(RuntimeError):
            load_batch([EXAMPLE_PATH, second_path])
        self.assertFalse(NPC.objects.filter(db_key__in=["human_reference", "second_reference"]).exists())

    def test_world_key_with_report_words_is_still_detected_as_duplicate(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": "x in batch",
            "content": "First.",
        }
        first = self.write("phrase-first.json", world)
        world["content"] = "Second."
        second = self.write("phrase-second.json", world)
        self.assertFalse(validate_batch([first, second]).all_valid)

    def test_unhashable_invalid_world_key_reports_schema_error_without_crashing(self):
        world = {
            "record_type": "world_entry",
            "schema_version": 1,
            "key": ["not", "hashable"],
            "content": "Invalid.",
        }
        path = self.write("unhashable.json", world)
        report = validate_batch([path])
        self.assertFalse(report.all_valid)

    @covers_requirement("import-validation::batch-import-rejects-duplicate-character-keys")
    def test_duplicate_character_keys_fail_the_whole_batch(self):
        first = example_record()
        first_path = self.write("first.json", first)
        second = example_record()
        second["key"] = first["key"]
        second_path = self.write("second.json", second)
        report = validate_batch([first_path, second_path])
        self.assertFalse(report.all_valid)
        self.assertTrue(all(item.rejections for item in report.records))
        with patch("world.imports.loader._instantiate_validated_character") as instantiate:
            with self.assertRaises(ImportRejected):
                load_batch([first_path, second_path])
        instantiate.assert_not_called()

    @covers_requirement("import-validation::batch-import-rejects-duplicate-character-keys")
    def test_unique_character_keys_pass_the_uniqueness_check(self):
        first = example_record()
        first_path = self.write("first.json", first)
        second = example_record()
        second["key"] = "second_reference"
        second_path = self.write("second.json", second)
        report = validate_batch([first_path, second_path])
        self.assertTrue(report.all_valid)
        self.assertEqual(
            [record["key"] for record in report.character_records],
            ["human_reference", "second_reference"],
        )
