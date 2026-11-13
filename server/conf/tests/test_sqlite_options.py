"""The database connection options every process shares (sqlite-concurrency).

Each test builds its own database in a temporary directory and opens private
``ConnectionHandler`` instances, so neither the retained test database nor the
global connection handler is involved. No test sleeps or measures time.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

import django.db.utils
from django.db.utils import ConnectionHandler

from server.conf.sqlite_options import SQLITE_OPTIONS


class SqliteOptionsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "world.db3"
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("CREATE TABLE world (key TEXT PRIMARY KEY, value TEXT)")
            connection.execute("INSERT INTO world VALUES ('committed', 'row')")
            connection.commit()
        finally:
            connection.close()

    def connection(self, **overrides):
        """One private handler and connection opened with the project's options."""
        handler = ConnectionHandler(
            {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": str(self.path),
                    "OPTIONS": {**SQLITE_OPTIONS, **overrides},
                }
            }
        )
        self.addCleanup(handler.close_all)
        connection = handler["default"]
        connection.ensure_connection()
        return connection

    def test_a_reader_is_not_refused_during_a_write_transaction(self):
        writer = self.connection()
        writer.set_autocommit(False, force_begin_transaction_with_broken_autocommit=True)
        writer.cursor().execute("INSERT INTO world VALUES ('uncommitted', 'row')")

        reader = self.connection()
        rows = reader.cursor().execute("SELECT key FROM world ORDER BY key").fetchall()

        self.assertEqual([row[0] for row in rows], ["committed"])
        writer.commit()
        writer.set_autocommit(True)

    def test_a_second_writer_is_refused_as_busy_and_the_first_still_commits(self):
        first = self.connection()
        first.set_autocommit(False, force_begin_transaction_with_broken_autocommit=True)
        first.cursor().execute("INSERT INTO world VALUES ('uncommitted', 'row')")

        second = self.connection(timeout=0)
        with self.assertRaises(django.db.utils.OperationalError):
            second.set_autocommit(False, force_begin_transaction_with_broken_autocommit=True)

        first.commit()
        first.set_autocommit(True)
        plain = sqlite3.connect(self.path)
        try:
            count = plain.execute("SELECT COUNT(*) FROM world WHERE key = 'uncommitted'").fetchone()[0]
        finally:
            plain.close()
        self.assertEqual(count, 1)

    def test_the_first_connection_converts_a_rollback_journal_file(self):
        plain = sqlite3.connect(self.path)
        try:
            self.assertEqual(plain.execute("PRAGMA journal_mode").fetchone()[0], "delete")
        finally:
            plain.close()

        connection = self.connection()
        self.assertEqual(connection.cursor().execute("PRAGMA journal_mode").fetchone()[0], "wal")

        later = sqlite3.connect(self.path)
        try:
            self.assertEqual(later.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            later.close()
