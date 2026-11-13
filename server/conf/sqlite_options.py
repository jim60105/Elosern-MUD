"""SQLite connection options shared by every process (sqlite-concurrency)."""

SQLITE_BUSY_TIMEOUT_SECONDS = 10

SQLITE_OPTIONS: dict[str, object] = {
    "timeout": SQLITE_BUSY_TIMEOUT_SECONDS,
    "transaction_mode": "IMMEDIATE",
    "init_command": "PRAGMA journal_mode=WAL;",
}

SQLITE_TEST_OPTIONS: dict[str, object] = {
    "timeout": SQLITE_BUSY_TIMEOUT_SECONDS,
    "transaction_mode": "IMMEDIATE",
}
