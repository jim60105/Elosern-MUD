# Spec Delta

## ADDED Requirements

### Requirement: Saved database is one self-contained file
A snapshot SHALL save the database as a single file in rollback-journal mode that holds every write committed before the backup, whatever the journal mode of the live database. Reading a saved database SHALL NOT leave a sidecar file in the save.

#### Scenario: Live database in write-ahead-log mode
- **WHEN** a snapshot is taken of a live database in write-ahead-log mode that holds committed rows not yet checkpointed into the main file
- **THEN** the saved file contains those rows, reports rollback-journal mode, and the save directory holds no `-wal` or `-shm` file after the saved clock and the migration list were read

### Requirement: Restoration never pairs a sidecar with another database
The pre-start restore tool SHALL move every sidecar of the live database aside with it, SHALL install the saved database without any sidecar, and on rollback SHALL return the original database together with exactly its own sidecars.

#### Scenario: Successful restore over a write-ahead-log database
- **WHEN** the live database has `-wal` and `-shm` sidecars and a compatible save is restored
- **THEN** the installed database has no `-wal` or `-shm` file beside it and opens with the saved contents

#### Scenario: Rollback returns the original sidecars
- **WHEN** an injected failure occurs after the saved database was installed over a live database that had `-wal` and `-shm` sidecars
- **THEN** the original database and both original sidecars are back with their original bytes, and no sidecar created against the installed file remains
