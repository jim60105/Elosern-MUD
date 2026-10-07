"""Temporary world fixtures for the save tests (not a test module).

A fake project root holds a SQLite "live" database with a
``django_migrations`` table, an art store, and a ``world/fake/migrations``
package, so the stdlib migration inventory knows ``fake.0001_initial``.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from server.saves.layout import SaveLayout

KNOWN_MIGRATION = ("fake", "0001_initial")
FUTURE_MIGRATION = ("fake", "0002_future")


def fixed_metadata() -> dict:
    return {
        "clock": {"tick": 42, "year": 1, "season": "春", "day": 3, "hour": 9, "minute": 30},
        "players": [{"name": "Tester", "location": "room-a"}],
    }


class TempWorld:
    """A disposable project root with a live database and art store."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.layout = SaveLayout.for_project(self.root)
        self.layout.db_file.parent.mkdir(parents=True)
        self.layout.art_root.mkdir(parents=True)
        migrations = self.root / "world" / "fake" / "migrations"
        migrations.mkdir(parents=True)
        (migrations / "__init__.py").write_text("")
        (migrations / "0001_initial.py").write_text("")
        self.init_db(self.layout.db_file, [KNOWN_MIGRATION])

    @staticmethod
    def init_db(path: Path, migrations: list[tuple[str, str]]) -> None:
        connection = sqlite3.connect(path)
        try:
            connection.execute(
                "CREATE TABLE django_migrations (id INTEGER PRIMARY KEY, app TEXT, name TEXT, applied TEXT)"
            )
            connection.executemany(
                "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, '')", migrations
            )
            connection.execute("CREATE TABLE world (key TEXT PRIMARY KEY, value TEXT)")
            connection.execute("INSERT INTO world VALUES ('state', 'original')")
            connection.commit()
        finally:
            connection.close()

    def write_state(self, value: str, db: Path | None = None) -> None:
        connection = sqlite3.connect(db or self.layout.db_file)
        try:
            connection.execute("UPDATE world SET value = ? WHERE key = 'state'", (value,))
            connection.commit()
        finally:
            connection.close()

    def read_state(self, db: Path | None = None) -> str:
        connection = sqlite3.connect(db or self.layout.db_file)
        try:
            return connection.execute("SELECT value FROM world WHERE key = 'state'").fetchone()[0]
        finally:
            connection.close()

    def add_migration(self, migration: tuple[str, str], db: Path | None = None) -> None:
        connection = sqlite3.connect(db or self.layout.db_file)
        try:
            connection.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, '')", migration
            )
            connection.commit()
        finally:
            connection.close()

    def art(self, relative: str, content: bytes) -> Path:
        path = self.layout.art_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # Like every live art writer: replace, never write in place (a save
        # may hold a hard link to the old inode).
        path.unlink(missing_ok=True)
        path.write_bytes(content)
        return path

    def cleanup(self) -> None:
        self._tmp.cleanup()
