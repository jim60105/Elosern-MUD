## ADDED Requirements

### Requirement: DOM-independent client behavior has an executable Node test gate
Protocol validation/reduction and keyboard routing SHALL be implemented as DOM-independent JavaScript modules and SHALL have deterministic tests runnable with Node 24's built-in test runner. The suite SHALL cover exact schemas, atomic new-epoch adoption, active-epoch revision ordering, old-epoch rejection, panel replacement, focus movement, Escape stack behavior, command-drawer transition, disabled entries, and repeated-Enter suppression without adding an npm runtime dependency.

#### Scenario: Node suite verifies state and keyboard contracts
- **WHEN** `node --test web/static/webclient/js/tests/*.test.js` runs
- **THEN** all protocol reducer and keyboard-router behavior tests pass without a browser, remote request, package installation, or generated game data

### Requirement: Browser acceptance uses an isolated managed Evennia runtime
The browser-test harness SHALL create a temporary SQLite database and temporary runtime/log paths, allocate dynamic loopback Telnet, HTTP, and WebSocket ports per harness instance, seed deterministic account and character fixtures, start Evennia non-interactively with browser-test-only settings, poll its allocated localhost WebClient with a bounded readiness timeout, and always stop only its owned server process after success, failure, or timeout. It SHALL NOT assume port 4001 or read or write the developer database. The harness SHALL be repeatable when `web/tests/browser/` is collected by both the full Evennia `web` suite and the explicit browser entry point; each collection SHALL use fresh ports and temporary roots without shared process state.

#### Scenario: Browser test uses isolated persistence
- **WHEN** a Playwright test creates or changes game state
- **THEN** all persisted effects are confined to the harness temporary directory and the configured developer database is byte-for-byte untouched

#### Scenario: Failed readiness still cleans up
- **WHEN** the managed server fails to become ready within its timeout
- **THEN** the harness records useful local diagnostics, terminates its process, removes temporary state, and fails the test

#### Scenario: Repeated discovery does not collide
- **WHEN** the browser tests run through the full Evennia suite and later through the explicit browser command
- **THEN** each run owns distinct dynamic ports, process identity, database, logs, and cleanup with no port collision or stale server

### Requirement: Browser tests are localhost-only and deterministic
Playwright acceptance SHALL use Chromium installed through the locked uv environment, SHALL block or fail every non-local network request, and SHALL use deterministic placeholders without invoking an LLM, image generator, or other external service.

#### Scenario: Browser journey makes no remote request
- **WHEN** the foundation acceptance suite loads and exercises the real WebClient
- **THEN** every successful HTTP and WebSocket request targets localhost and no test result depends on remote availability

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required shell visibility at 1440x900 and 1280x720, keyboard-only drawer open/send/close and focus restoration, transport interruption and control locking, lower-revision adoption in a new epoch, rejection of delayed prior-epoch messages, known layout migration, unknown layout reset, presenter degradation, and protocol mismatch with preserved text input.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible and the keyboard-only command journey completes with action-dock focus restored

#### Scenario: Reconnect behavior is exercised end to end
- **WHEN** the harness interrupts the active WebSocket and reconnects it
- **THEN** stale controls remain locked, the browser adopts the new epoch's lower-revision snapshot, and an injected delayed old-epoch message changes no state

#### Scenario: Incompatible protocol preserves text input
- **WHEN** the harness injects a snapshot with an unsupported protocol version
- **THEN** graphical actions disable while an ordinary text command can still be sent and rendered

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The required quality workflow SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before any Python runner that can discover browser tests, run `node --test web/static/webclient/js/tests/*.test.js`, and run `uv run --locked python -m unittest discover -s web/tests/browser -t .`. Browser tests carrying requirement annotations SHALL write to the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified; duplicate successful evidence from repeated discovery is valid. Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 90% branch-coverage, and Codecov gates SHALL remain enabled.

#### Scenario: Quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected
- **THEN** locked environment sync, Chromium installation, Node tests, browser tests, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` runs from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution without modifying `uv.lock`
