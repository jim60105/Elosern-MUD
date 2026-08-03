## MODIFIED Requirements

### Requirement: Browser acceptance uses an isolated managed Evennia runtime
The browser-test harness SHALL create a temporary SQLite database and temporary runtime/log paths, allocate dynamic loopback Telnet, HTTP, and WebSocket ports per harness instance, seed deterministic account and character fixtures, start Evennia non-interactively with browser-test-only settings, poll its allocated localhost WebClient with a bounded readiness timeout, and always stop only its owned server process after success, failure, or timeout. It SHALL NOT assume port 4001 or read or write the developer database. Each invocation SHALL use fresh ports and temporary roots without shared process state. The explicit managed browser command SHALL be the sole quality-gate owner of `web/tests/browser/`; the non-browser Evennia command SHALL retain `web.webclient` tests but SHALL NOT collect browser tests again.

#### Scenario: Browser test uses isolated persistence
- **WHEN** a Playwright test creates or changes game state
- **THEN** all persisted effects are confined to the harness temporary directory and the configured developer database is byte-for-byte untouched

#### Scenario: Failed readiness still cleans up
- **WHEN** the managed server fails to become ready within its timeout
- **THEN** the harness records useful local diagnostics, terminates its process, removes temporary state, and fails the test

#### Scenario: Separate invocations do not collide
- **WHEN** the managed browser command runs again after success or failure
- **THEN** the new run owns distinct dynamic ports, process identity, database, logs, and cleanup with no port collision or stale server

#### Scenario: Quality gate does not duplicate browser discovery
- **WHEN** the quality workflow runs both managed browser and non-browser Evennia entry points
- **THEN** every browser test executes through the managed browser entry point exactly once

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The required quality workflow SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before the browser runner, run `node --test web/static/webclient/js/tests/*.test.js`, and run the explicit `web/tests/browser/` discovery once, serially, under coverage. Browser tests carrying requirement annotations SHALL write to the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified. Browser coverage SHALL be combined with non-browser Evennia and top-level coverage before exact-root and aggregate threshold verification. Managed browser acceptance MUST NOT be included in a generic parallel Evennia profile. Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 90% branch-coverage, and Codecov gates SHALL remain enabled.

#### Scenario: Quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected
- **THEN** locked environment sync, Chromium installation, Node tests, serial managed browser tests, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` runs from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution without modifying `uv.lock`

#### Scenario: Generic parallel profile excludes managed browser acceptance
- **WHEN** a local or quality-gate Evennia profile enables multiple test workers
- **THEN** the managed Playwright suite continues through its separate serial command with isolated server lifecycle ownership
