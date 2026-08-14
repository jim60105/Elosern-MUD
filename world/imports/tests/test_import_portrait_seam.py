"""Tests for the portrait-policy and on-commit scheduling import seam."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from typeclasses.npcs import NPC
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.imports.loader import ImportRejected, load_batch
from world.imports.tests.helpers import EXAMPLE_PATH, example_record

from tools.spec_traceability import covers_requirement


class ImportPortraitSeamTests(EvenniaTest):
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

    def _character_records(self, *keys):
        records = []
        for key in keys:
            record = example_record()
            record["key"] = key
            record["display_name"] = f"角色 {key}"
            records.append(record)
        return records

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    def test_committed_batch_schedules_one_post_commit_ensure_per_record(self):
        first = example_record()
        second = example_record()
        second["key"] = "second_reference"
        paths = [self.write("a.json", first), self.write("b.json", second)]
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            entities = load_batch(paths)
        self.assertEqual(len(entities), 2)
        self.assertEqual(len(callbacks), 2)
        for entity in entities:
            self.assertEqual(
                entity.db.portrait_policy,
                {"mode": "named", "stable_key": entity.key},
            )
            self.assertEqual(entity.db.age, 22)
            self.assertEqual(entity.db.apparent_age, 22)
            record = ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{entity.key}"
            ).first()
            self.assertIsNotNone(record)
            self.assertEqual(record.db.status, ArtAssetStatus.PENDING)

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    def test_rejected_import_batch_emits_no_job(self):
        bad = example_record()
        bad["age"] = 17
        paths = [self.write("bad.json", bad)]
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaises(ImportRejected):
                load_batch(paths)
        self.assertEqual(callbacks, [])
        self.assertEqual(ArtAssetRecord.objects.count(), 0)
        self.assertFalse(
            NPC.objects.filter(db_key="human_reference").exists()
        )

    @covers_requirement("art-asset-lifecycle::queue-failure-never-rolls-back-gameplay")
    def test_art_callback_exception_never_surfaces_as_an_import_error(self):
        path = self.write("ok.json", example_record())
        with (
            self.captureOnCommitCallbacks(execute=True) as callbacks,
            patch(
                "world.art.service._ensure_character_portrait",
                side_effect=RuntimeError("art boom"),
            ),
        ):
            entities = load_batch([path])
        self.assertEqual(len(entities), 1)
        self.assertEqual(len(callbacks), 1)
        self.assertTrue(
            NPC.objects.filter(db_key="human_reference").exists()
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
