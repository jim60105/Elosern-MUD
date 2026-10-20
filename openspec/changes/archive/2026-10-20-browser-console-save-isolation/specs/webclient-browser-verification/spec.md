## MODIFIED Requirements

### Requirement: Browser acceptance uses an isolated managed Evennia runtime
The browser-test harness SHALL create a temporary SQLite database and temporary runtime/log paths, allocate dynamic loopback Telnet, HTTP, and WebSocket ports per harness instance, seed deterministic account and character fixtures, start Evennia non-interactively with browser-test-only settings, poll its allocated localhost WebClient with a bounded readiness timeout, and always stop only its owned server process after success, failure, or timeout.

#### Scenario: Browser test uses isolated persistence
- **WHEN** a Playwright test creates or changes game state
- **THEN** all persisted effects are confined to the harness temporary directory and the configured developer database is byte-for-byte untouched

#### Scenario: No fixed port or developer-database access
- **WHEN** the harness picks ports and persistence targets
- **THEN** it SHALL NOT assume port 4001 or read or write the developer database

#### Scenario: Failed readiness still cleans up
- **WHEN** the managed server fails to become ready within its timeout
- **THEN** the harness records useful local diagnostics, terminates its process, removes temporary state, and fails the test

#### Scenario: Separate invocations do not collide
- **WHEN** the managed browser command runs again after success or failure
- **THEN** the new run owns distinct dynamic ports, process identity, database, logs, and cleanup with no port collision or stale server

#### Scenario: Quality gate does not duplicate browser discovery
- **WHEN** the quality workflow runs both managed browser and non-browser Evennia entry points
- **THEN** every browser test executes through the managed browser entry point exactly once

#### Scenario: Invocations share no process state
- **WHEN** the harness runs any invocation
- **THEN** it uses fresh ports and temporary roots without shared process state

#### Scenario: One command owns the browser suite
- **WHEN** the managed browser command and the non-browser Evennia command are compared
- **THEN** the explicit managed browser command is the sole quality-gate owner of `web/tests/browser/`, and the non-browser Evennia command retains `web.webclient` tests but SHALL NOT collect browser tests again

#### Scenario: Protected console intervention owns a private undo snapshot
- **WHEN** an authorized browser-runtime operator with valid CSRF performs the first teleport after process start
- **THEN** a complete pre-intervention snapshot is created under that invocation's private save root, the response identifies it, and the target location commits only after snapshot success

#### Scenario: Snapshot failure refuses before mutation
- **WHEN** the managed runtime cannot create the required intervention snapshot
- **THEN** the console returns `snapshot_failed`, the target location and snapshot baseline are unchanged, and no operation is executed

#### Scenario: Save paths and retention remain isolated
- **WHEN** two managed runtimes create automatic saves using configured retention
- **THEN** each has distinct database, saves and art roots under its owned temporary directory, retention has production-equivalent meaning, developer persistence stays untouched, and teardown removes only the invocation's state
