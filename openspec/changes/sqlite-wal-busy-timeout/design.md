# Design

## Context

See proposal.md - Why. Facts verified in the tree:

- Django 6.0.7, SQLite library 3.53.1. Django's SQLite backend accepts `OPTIONS["init_command"]` (run on every new connection), `OPTIONS["transaction_mode"]` and `OPTIONS["timeout"]`.
- Evennia's `SQLITE3_PRAGMAS` is applied only by the Server service (`evennia/server/service.py`), never by the Portal, so it cannot carry this change.
- `server/saves/snapshot.py::_backup_database` copies through `sqlite3.Connection.backup`. The backup copies the database header, so a write-ahead-log source produces a write-ahead-log copy.
- `server/saves/inventory.py::applied_migrations` and `server/saves/snapshot.py::snapshot_clock` open a saved database with `mode=ro`. On a write-ahead-log file in a writable directory, that open creates `-wal` and `-shm` files in the save.
- `server/saves/restore.py` already lists `DB_SIDECARS = ("-journal", "-wal", "-shm")` and handles them in `move_aside` and `rollback`. Only the `-journal` case has tests (`server/saves/tests/test_restore_tool.py`).
- The Django parallel test runner clones an on-disk SQLite test database with a plain file copy.

## Goals / Non-Goals

**Goals:**

- One options mapping used by every process.
- Saves stay single-file and readable by the standard-library restore tool.

**Non-Goals:**

- No change to `SQLITE3_PRAGMAS` (`synchronous=OFF` stays as Evennia sets it).
- No change to clock, settlement, art or Stable Diffusion code.
- No new environment variable.
- No change to `server/saves/restore.py` logic unless a new test below fails; if one fails, stop and report instead of redesigning.

## Decisions

### D1. Options module

Create `server/conf/sqlite_options.py`, standard library only, with exactly:

```python
"""SQLite connection options shared by every process (sqlite-concurrency)."""

SQLITE_BUSY_TIMEOUT_SECONDS = 30

SQLITE_OPTIONS: dict[str, object] = {
    "timeout": SQLITE_BUSY_TIMEOUT_SECONDS,
    "transaction_mode": "IMMEDIATE",
    "init_command": "PRAGMA journal_mode=WAL;",
}

SQLITE_TEST_OPTIONS: dict[str, object] = {
    "timeout": SQLITE_BUSY_TIMEOUT_SECONDS,
    "transaction_mode": "IMMEDIATE",
}
```

In `server/conf/settings.py`, directly under the existing `DATABASES["default"]["NAME"] = ...` line, add:

```python
from server.conf.sqlite_options import SQLITE_OPTIONS

DATABASES["default"]["OPTIONS"] = dict(SQLITE_OPTIONS)
```

In `server/conf/test_settings.py`, directly above the existing `DATABASES["default"].setdefault("TEST", {})` statement, add:

```python
from server.conf.sqlite_options import SQLITE_TEST_OPTIONS

DATABASES["default"]["OPTIONS"] = dict(SQLITE_TEST_OPTIONS)
```

Why `OPTIONS` and not `SQLITE3_PRAGMAS`: only `OPTIONS` reaches the Portal and the migrate command. Why `IMMEDIATE`: in write-ahead-log mode a deferred transaction that read first and writes after another process committed fails at once with a busy-snapshot error that ignores the timeout; taking the write lock at `BEGIN` makes the writer wait instead. Why 30 seconds: the same value `server/saves/snapshot.py::_BACKUP_BUSY_TIMEOUT` already uses.

The two smoke settings (`server/conf/monster_population_smoke_settings.py`, `server/conf/monster_field_behaviour_smoke_settings.py`) and `tools/monster_ai_manual_reports_settings.py` star-import the settings and inherit the options. Do not edit them.

### D2. Test database stays in rollback-journal mode

`SQLITE_TEST_OPTIONS` has no `init_command`. Reason: the parallel runner's file copy of a write-ahead-log database can miss rows still in the `-wal` file. The retained test database `server/db/evennia-test.sqlite3` is therefore unchanged.

### D3. Saved database is converted after the backup

In `server/saves/snapshot.py::_backup_database`, after `src.backup(dst)` and before `dst.close()`, add:

```python
dst.execute("PRAGMA journal_mode=DELETE")
```

Do not change the source connection, its `mode=ro` URI or its timeout. With a write-ahead-log source the backup no longer delays writer commits; update the module docstring sentence "one pass under a shared lock, which briefly delays writer commits" to say that the backup reads a consistent snapshot and the saved copy is converted to rollback-journal mode.

Alternative rejected: opening saved databases with `immutable=1` everywhere. It needs edits in three readers and leaves write-ahead-log files in the saves.

### D4. Tests

New module `server/conf/tests/test_sqlite_options.py`, `unittest.TestCase`, no Evennia fixture. Each test builds its own database in `tempfile.TemporaryDirectory()` and opens Django connections with:

```python
from django.db.utils import ConnectionHandler
handler = ConnectionHandler({"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": path, "OPTIONS": dict(SQLITE_OPTIONS)}})
```

Use two handlers for two connections and close every connection in `addCleanup`. The three tests are the three scenarios of `specs/sqlite-concurrency/spec.md`. For the busy scenario the second handler uses `{**SQLITE_OPTIONS, "timeout": 0}` and the test asserts `django.db.utils.OperationalError` when it enters `transaction.atomic(using="default")` on that handler's connection (pass the connection through `django.db.transaction.Atomic` with the private handler's connection object if the alias lookup does not reach a private handler; the assertion is the refusal, the spelling is the worker's choice). No test sleeps and no test measures time.

Register the module in `.github/evennia-shards.json` in the shard that already holds `server.conf.tests.test_art_settings`.

`server/saves/tests/test_snapshot.py`: add one test for the scenario "Live database in write-ahead-log mode". Build the live file with the standard library `sqlite3`, run `PRAGMA journal_mode=WAL` and `PRAGMA wal_autocheckpoint=0`, commit a row, keep that connection open, then call `snapshot._backup_database(source, target)`. Assert the row is in `target`, `PRAGMA journal_mode` on `target` returns `delete`, and after a `mode=ro` open and close of `target` its directory lists only the target file.

`server/saves/tests/test_restore_tool.py`: add the two scenarios of "Restoration never pairs a sidecar with another database", modelled on the existing `-journal` tests at lines 36-80 of that file, using byte sentinels for `evennia.db3-wal` and `evennia.db3-shm`.

### D5. Documentation

- `docs/development/settings-and-environment.md`: one short section naming `server/conf/sqlite_options.py`, the three options and the test exception.
- `docs/development/gm-portal-saves.md`: one sentence that a saved database is a single rollback-journal file.
- `docs/development/database-reset.md` already tells the reader to delete the WAL and SHM files; add that these files now exist during normal running.

Write each edit in the language the file already uses.

## Risks / Trade-offs

- [A reader inside `transaction.atomic()` now takes the write lock and can wait up to 30 seconds behind a long Server transaction] → Portal session reads run in autocommit; the long transaction itself is removed by the settlement changes of this batch.
- [`synchronous=OFF` with write-ahead logging can lose or damage the last transactions on power loss] → the same risk class as today's rollback-journal mode with the same pragma; world saves are the recovery path.
- [A network or overlay filesystem without shared-memory support cannot use write-ahead logging] → the `evennia-db` named volume is a local filesystem; `docs/development/settings-and-environment.md` states the requirement.

## Migration Plan

Deploy the image. The first connection converts the file. Rollback: deploy the previous image and run `sqlite3 evennia.db3 "PRAGMA journal_mode=DELETE"` once with the server stopped; the previous image also runs correctly on a write-ahead-log file.
