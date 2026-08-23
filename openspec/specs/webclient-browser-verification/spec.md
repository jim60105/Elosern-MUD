## Purpose

Required Node and Playwright entry points, isolated deterministic server fixtures, supported viewport acceptance, and CI integration.

## Requirements


### Requirement: DOM-independent client behavior has an executable Node test gate
Protocol validation/reduction, keyboard routing, the narrative markup tokenizer, and the local-map render model SHALL be implemented as DOM-independent, dependency-free UMD/CommonJS pure-model APIs and SHALL have deterministic tests runnable with Node 24's built-in test runner. The suite SHALL cover exact schemas, atomic new-epoch adoption, active-epoch revision ordering, old-epoch rejection, panel replacement, focus movement, Escape stack behavior, command-drawer transition, disabled entries, repeated-Enter suppression, focus-by-key resolution and pointer-sourced confirmation, the narrative allowlist grammar with its degradation and bounds under hostile input, and the minimap lattice with its remembered-node split and its rank-compression fallback — all without adding an npm runtime dependency to these DOM-independent modules, which remain dependency-free UMD/CommonJS pure-model APIs (no `document`/`window` access at load time) imported by the Node gate and reused by the Vue application through Vite's CommonJS interop, and, where browser access to a module requires a global, through the browser-bridge layer (C2) that re-exposes the `window.Elosern.*` façades; where a module carries a DOM builder it is only touched at call time, never at load. The Vue component/view layer is covered by a separate Vitest component gate and is not part of this Node gate.

#### Scenario: Node suite verifies state and keyboard contracts
- **WHEN** `node --test web/static/webclient/js/tests/*.test.js` runs
- **THEN** all protocol reducer and keyboard-router behavior tests pass without a browser, remote request, package installation, or generated game data

#### Scenario: Node suite verifies markup and map models
- **WHEN** the same Node entry point runs
- **THEN** the narrative tokenizer's allowlist, degradation, and bounds and the local-map lattice model's placement and fallback are verified with no DOM, browser, or network access

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

### Requirement: Browser tests are localhost-only and deterministic
Playwright acceptance SHALL use Chromium installed through the locked uv environment, SHALL block or fail every non-local network request, and SHALL use deterministic placeholders without invoking an LLM, image generator, or other external service.

#### Scenario: Browser journey makes no remote request
- **WHEN** the foundation acceptance suite loads and exercises the real WebClient
- **THEN** every successful HTTP and WebSocket request targets localhost and no test result depends on remote availability

### Requirement: Browser acceptance covers foundation recovery and layout behavior
Playwright SHALL verify required shell visibility at 1440x900 and 1280x720; drawer open, send, and cancel behavior including focus retention after an ordinary send and focus restoration on Escape; pointer activation parity on the action dock; narrative rendering of converted server markup; minimap containment within its pane; transport interruption and control locking; lower-revision adoption in a new epoch; rejection of delayed prior-epoch messages; known layout migration; unknown layout reset; presenter degradation; and protocol mismatch with preserved text input.

#### Scenario: Supported viewports pass the shell journey
- **WHEN** the acceptance journey runs at each supported desktop viewport
- **THEN** every required surface is visible, two consecutive commands are sent from the drawer without any pointer interaction, and Escape restores action-dock focus

#### Scenario: Reconnect behavior is exercised end to end
- **WHEN** the harness interrupts the active WebSocket and reconnects it
- **THEN** stale controls remain locked, the browser adopts the new epoch's lower-revision snapshot, and an injected delayed old-epoch message changes no state

#### Scenario: Incompatible protocol preserves text input
- **WHEN** the harness injects a snapshot with an unsupported protocol version
- **THEN** graphical actions disable while an ordinary text command can still be sent and rendered

#### Scenario: Narrative shows prose, not markup source
- **WHEN** the seeded actor looks at the room in the real client
- **THEN** the narrative contains the room's styled prose, contains no literal element or entity source characters, and the colored segments carry their palette classes

#### Scenario: The minimap stays inside its pane
- **WHEN** the shell renders a seeded grid room's minimap at each supported viewport
- **THEN** every node marker is inside the map canvas, no two node markers overlap, and the legend and detail line remain visible

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The npm frontend toolchain is a dev/CI-time dependency only and introduces no runtime npm dependency. The required quality workflow SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before the browser runner, run `node --test web/static/webclient/js/tests/*.test.js`, build the Vue application with the locked npm toolchain (`npm ci` and the Vite production build), run the Vue component (Vitest) test suite, build the Storybook component showcase with its component-coverage check, and run the explicit `web/tests/browser/` discovery once, serially, under coverage. The Vue `dist` artifact SHALL be built in the browser test workspaces and in the container image. Browser tests carrying requirement annotations SHALL write to the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified. Browser coverage SHALL be combined with non-browser Evennia and top-level coverage before exact-root and aggregate threshold verification. Managed browser acceptance MUST NOT be included in a generic parallel Evennia profile. Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 80% branch-coverage, and Codecov gates SHALL remain enabled. The built page makes no remote runtime request.

#### Scenario: Quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected
- **THEN** locked environment sync, Chromium installation, Node tests, the Vue build, the Vue component (Vitest) tests, the Storybook build with its component-coverage check, serial managed browser tests, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` and `npm ci` run from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution and the locked npm toolchain without modifying `uv.lock` or the npm lockfile

#### Scenario: Generic parallel profile excludes managed browser acceptance
- **WHEN** a local or quality-gate Evennia profile enables multiple test workers
- **THEN** the managed Playwright suite continues through its separate serial command with isolated server lifecycle ownership

### Requirement: Art-panel portrait keyboard journeys establish dock focus before key presses
A Playwright acceptance journey that asserts the client-local portrait focus
switching SHALL focus the action dock
(`document.getElementById('action-dock').focus()`) and wait for the combat
dock's mounted router frame (the first combat row `#combat-row-0`) before the
first key press, and SHALL wait for the basic-attack target menu frame
(`#combat-row-0` carrying a `target-` data-item-key) before asserting that the
portrait switched to the focused target. This guarantees the key event reaches
the KeyboardRouter — never the command-drawer field or an unfocused editable
target — and turns a swallowed key press into a precise diagnostic.

#### Scenario: Art-panel combat journey presses Enter with the dock focused
- **WHEN** an art-panel acceptance test engages combat, presses Enter to open
  the basic-attack target menu, and moves focus to the enemy target
- **THEN** the action dock was explicitly focused and the combat dock's first
  row was mounted before the Enter press, and the portrait switches to the
  focused enemy target's name without any focus packet

#### Scenario: Target menu mount is awaited before asserting the portrait
- **WHEN** the journey asserts that the portrait switched to the focused
  target
- **THEN** it first waits for the target menu frame (`#combat-row-0` carrying a
  `target-` data-item-key) and then for the focused row to carry the enemy
  target's key, so a swallowed key press fails with a precise diagnostic
  instead of a bare timeout

### Requirement: The implementation-bound public contract is frozen before the shell is swapped
Before the WebClient's GoldenLayout/jQuery shell is replaced, the implementation-bound client
contract SHALL be enumerated and frozen: the `window.Elosern.*` public façades, the keyboard /
plugin key-event path, the DOM identifiers the managed browser tests target, and the versioned
layout-persistence keys. The freeze SHALL be a committed, reviewed deliverable that is the binding
input to the browser-bridge change, and every identifier the browser tests currently target SHALL be
either preserved unchanged or re-mapped to a stable `data-testid` hook per that frozen list.

#### Scenario: A frozen contract list exists before wiring
- **WHEN** the Phase-0 contract audit is complete
- **THEN** a committed list names each implementation-bound contract (façade, key path, targeted DOM id, persistence key) classified as preserve-via-bridge or delta, and is declared the input to the browser-bridge change

#### Scenario: Browser-test targets are preserved or re-mapped per the list
- **WHEN** the GoldenLayout/jQuery shell is later replaced by the Vue app
- **THEN** every identifier the managed Playwright suite currently targets is either preserved unchanged or re-mapped to a stable `data-testid`, per the frozen list

### Requirement: Browser test waits gate on deterministic state within a bounded deadline
The managed Playwright acceptance journeys SHALL gate every test wait by polling the committed
store view and, where an assertion is genuinely DOM-bound, the surface DOM, within a single
bounded monotonic deadline. Waits SHALL NOT depend on a single raw DOM-visibility wait that a
delayed server publish or client render would exhaust under a loaded CI runner. The shared wait
helper in `web/tests/browser/browser_helpers.py` SHALL expose one bounded polling loop that
reads the committed store view (via `store_state_or_none`, tolerating a one-shot recovery reload),
SHALL accept an optional DOM-readiness descriptor (a structured `{selector, predicate, description}`)
whose predicate is evaluated within the same polling loop under the same monotonic deadline (so the
store gate and the DOM gate share one bounded window). A DOM-readiness `page.evaluate` that races an
in-flight navigation SHALL be routed through the same navigation-tolerating path as the store read: a
recoverable "execution context was destroyed" error is recorded as the last evaluation error and the
wait continues to the deadline; a non-navigation JavaScript/selector error SHALL be surfaced in the
timeout diagnostic. The helper SHALL treat a `None` store read (mid-reload) as "not ready yet" without
invoking the store predicate on `None`, and SHALL raise an `AssertionError` on timeout carrying the
last non-`None` store state, whether any `None` reads occurred, the last evaluation error, and — where
a DOM-readiness descriptor is supplied — the selector's connected/visible/enabled state and the current
`activeElement`. Focus operations (e.g. `focus_action_dock`) SHALL gate on the store state first, then
poll the target element's DOM readiness in the same loop, focus it using the remaining deadline, and
verify `document.activeElement` is the target itself or a focusable descendant (or an explicitly allowed
delegated-focus target).

#### Scenario: A journey wait is gated on the store state
- **WHEN** a browser journey waits for a gameplay surface to become available or a mode to change
- **THEN** the wait polls the committed store view (and the surface DOM only where the assertion
  is DOM-bound) within a single bounded deadline, and does not depend on a single raw-visibility
  wait that a delayed render under a loaded CI runner would exhaust

#### Scenario: A bounded wait failure reports the last observed state
- **WHEN** a bounded wait exhausts its deadline
- **THEN** the helper raises an `AssertionError` carrying the last non-`None` store state, whether
  `None` reads occurred, the last evaluation error, and — when a DOM predicate is present — the
  selector's connected/visible/enabled state and the `activeElement`, so the failure is a precise
  diagnostic rather than a bare `TimeoutError`

#### Scenario: A focus wait verifies the focused element
- **WHEN** a journey focuses the action dock
- **THEN** it first gates on the store state, then polls the dock's DOM readiness in the same
  bounded loop, focuses it, and verifies `document.activeElement` is the dock itself or a focusable
  descendant, so a swallowed focus fails with a precise diagnostic instead of a bare timeout

#### Scenario: A DOM-readiness descriptor drives a single bounded wait
- **WHEN** a journey waits for a surface to be both present in the store view AND visible in the DOM
- **THEN** the shared helper accepts a structured `{selector, predicate, description}` descriptor and
  evaluates the DOM predicate in the same polling loop under the same monotonic deadline, so the store
  gate and the DOM gate share one bounded window
