# Proposal

## Why

While the Server process holds one long write transaction (a clock advance that settles the whole world), the separate Portal process cannot read the SQLite database: it runs in rollback-journal mode with the default 5 second busy timeout, so the Portal raises `django.db.utils.OperationalError: database is locked` (seen at `server/conf/websocket_protocol.py:39`) and the web login fails. `server/conf/settings.py` sets only `DATABASES["default"]["NAME"]`.

This change is a mitigation. It removes the lock error for readers. It does not shorten the advance and does not unfreeze the Server reactor; the settlement changes of this batch do that.

## What Changes

- Every database connection of every process (Server, Portal, `evennia migrate`, `evennia collectstatic`, shells) opens the world database in write-ahead-log mode with a 30 second busy timeout and immediate write transactions, through Django's `DATABASES["default"]["OPTIONS"]`.
- The test database keeps rollback-journal mode, because the parallel test runner clones the database file by file copy.
- A world save always contains a single self-contained database file in rollback-journal mode, whatever the mode of the live database.
- The pre-start restore tool keeps its existing `-journal`/`-wal`/`-shm` handling; this change adds the missing tests for the `-wal` and `-shm` pair.
- `docs/development/database-reset.md`, `docs/development/gm-portal-saves.md` and `docs/development/settings-and-environment.md` state the mode and the sidecar files.
- Not in scope: any change to the Stable Diffusion pipeline, any health gate, any change to settlement cost.

## Capabilities

### New Capabilities

- `sqlite-concurrency`: how the world database is opened so that a reader in one process is not refused while another process writes.

### Modified Capabilities

- `gm-save-management`: a saved database is one self-contained file, and restoration never pairs a write-ahead sidecar with the wrong database.

## Impact

- New `server/conf/sqlite_options.py`; edits to `server/conf/settings.py`, `server/conf/test_settings.py`, `server/saves/snapshot.py`.
- Tests: new `server/conf/tests/test_sqlite_options.py` (registered in `.github/evennia-shards.json`), additions to `server/saves/tests/test_snapshot.py` and `server/saves/tests/test_restore_tool.py`.
- The live database directory gains `evennia.db3-wal` and `evennia.db3-shm` next to `evennia.db3`; all three live on the existing `evennia-db` volume. No `compose.yaml` or `Containerfile` edit.
- No data migration: SQLite converts the file on the first connection that runs the pragma.

## Batch:

- depends-on: none
- parallel with: `population-maintenance-log-tally`, `settlement-decode-reuse`, `settlement-outer-rollback`, `settlement-deferred-body-writes`, `population-settlement-units`, `unit-scoped-population-settlement`, `population-catch-up-entry-points`, `observed-unit-advance`, `population-backlog-drain`.
- conflicts: `.github/evennia-shards.json` is edited by every change of this batch that adds a test module; resolve by keeping both entries. `server/conf/settings.py` and `server/conf/test_settings.py` are also edited by `population-backlog-drain` in a different section.
