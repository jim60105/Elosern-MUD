# sqlite-concurrency Specification

## Purpose
Defines how the world database is opened, so that a process reading the database is not refused while another process holds a write transaction.

## Requirements

### Requirement: World database connections use write-ahead logging
A connection opened with the project's database options SHALL put the database in write-ahead-log mode, SHALL wait for a busy database instead of failing at once, and SHALL begin a write transaction by taking the write lock immediately.

#### Scenario: Reader is not refused during a write transaction
- **WHEN** one connection opened with the project's options holds an uncommitted write transaction on a temporary database and a second connection reads the same table
- **THEN** the read succeeds and returns the last committed rows, without the uncommitted row

#### Scenario: Second writer is busy, not corrupted
- **WHEN** one connection holds an uncommitted write transaction and a second connection with a zero busy timeout begins a transaction
- **THEN** the second connection is refused as busy before it reads, and the first connection still commits

#### Scenario: Mode is established by the connection
- **WHEN** the first connection with the project's options opens a new rollback-journal database file
- **THEN** the file reports write-ahead-log mode to that connection and to a later plain connection
