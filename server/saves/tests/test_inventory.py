"""The stdlib migration inventory agrees with Django's own loader."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from django.conf import settings
from django.db.migrations.loader import MigrationLoader

from server.saves import inventory
from server.saves.layout import InvalidSaveId, new_save_id, normalize_label, validate_save_id
from tools.spec_traceability import covers_requirement


class MigrationInventoryTests(unittest.TestCase):
    @covers_requirement("gm-save-management::guarded-restore-request", "gm-save-management::pre-start-restore-with-rollback-and-result")
    def test_every_disk_migration_django_loads_is_known_without_django(self):
        loader = MigrationLoader(None, ignore_no_migrations=True, load=False)
        loader.load_disk()
        known = inventory.known_migrations(Path(settings.GAME_DIR))
        missing = sorted(
            f"{app}.{name}" for app, name in loader.disk_migrations if name not in known.get(app, set())
        )
        self.assertEqual(missing, [])
        self.assertTrue(loader.disk_migrations)

    def test_applied_rows_latest_per_app_and_unknown_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db.sqlite3"
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE django_migrations (id INTEGER PRIMARY KEY, app TEXT, name TEXT, applied TEXT)")
            connection.executemany(
                "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, '')",
                [("alpha", "0001_initial"), ("beta", "0001_initial"), ("alpha", "0002_more")],
            )
            connection.commit()
            connection.close()
            rows = inventory.applied_migrations(db)
        self.assertEqual(inventory.latest_per_app(rows), {"alpha": "0002_more", "beta": "0001_initial"})
        known = {"alpha": {"0001_initial", "0002_more"}, "beta": set()}
        self.assertEqual(inventory.unknown_migrations(rows, known), ["beta.0001_initial"])


class SaveIdentityTests(unittest.TestCase):
    @covers_requirement("gm-save-management::complete-world-save-contents")
    def test_ids_match_the_pattern_and_malformed_ids_are_refused(self):
        save_id = new_save_id()
        self.assertEqual(validate_save_id(save_id), save_id)
        self.assertRegex(save_id, r"^\d{8}T\d{6}-[0-9a-f]{6}$")
        for bad in ("x", "20260101T000000-abcde", "20260101T000000-abcdeg", "../20260101T000000-abcdef", 7):
            with self.subTest(bad=bad), self.assertRaises(InvalidSaveId):
                validate_save_id(bad)

    def test_labels_are_single_line_and_bounded(self):
        self.assertEqual(normalize_label("  a\n\tb  "), "a b")
        self.assertEqual(normalize_label(None), "")
        self.assertEqual(len(normalize_label("字" * 100)), 80)
