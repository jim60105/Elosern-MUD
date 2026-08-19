## MODIFIED Requirements

### Requirement: DOM-independent client behavior has an executable Node test gate
Protocol validation/reduction, keyboard routing, the narrative markup tokenizer, and the local-map
render model SHALL be implemented as DOM-independent, dependency-free UMD/CommonJS pure-model APIs and
SHALL have deterministic tests runnable with Node 24's built-in test runner. The suite SHALL cover exact
schemas, atomic new-epoch adoption, active-epoch revision ordering, old-epoch rejection, panel
replacement, focus movement, Escape stack behavior, command-drawer transition, disabled entries,
repeated-Enter suppression, focus-by-key resolution and pointer-sourced confirmation, the narrative
allowlist grammar with its degradation and bounds under hostile input, and the minimap lattice with its
remembered-node split and its rank-compression fallback — all without adding an npm runtime dependency to
these DOM-independent modules, which remain dependency-free UMD/CommonJS pure-model APIs (no
`document`/`window` access at load time) imported by the Node gate and reused by the Vue application
through Vite's CommonJS interop, and, where browser access to a module requires a global, through the
browser-bridge layer (C2) that re-exposes the `window.Elosern.*` façades; where a module carries a DOM
builder it is only touched at call time,
never at load. The Vue component/view layer is covered by a separate Vitest component gate and is not part
of this Node gate.

#### Scenario: Node suite verifies state and keyboard contracts
- **WHEN** `node --test web/static/webclient/js/tests/*.test.js` runs
- **THEN** all protocol reducer and keyboard-router behavior tests pass without a browser, remote request, package installation, or generated game data

#### Scenario: Node suite verifies markup and map models
- **WHEN** the same Node entry point runs
- **THEN** the narrative tokenizer's allowlist, degradation, and bounds and the local-map lattice model's placement and fallback are verified with no DOM, browser, or network access

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The npm frontend toolchain
is a dev/CI-time dependency only and introduces no runtime npm dependency. The required quality workflow
SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before the browser
runner, run `node --test web/static/webclient/js/tests/*.test.js`, build the Vue application with the
locked npm toolchain (`npm ci` and the Vite production build), run the Vue component (Vitest) test suite,
build the Storybook component showcase with its component-coverage check, and run the explicit
`web/tests/browser/` discovery once, serially, under coverage. The Vue `dist` artifact SHALL be built in
the browser test workspaces and in the container image. Browser tests carrying requirement annotations
SHALL write to the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified. Browser
coverage SHALL be combined with non-browser Evennia and top-level coverage before exact-root and
aggregate threshold verification. Managed browser acceptance MUST NOT be included in a generic parallel
Evennia profile. Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 80%
branch-coverage, and Codecov gates SHALL remain enabled. The built page makes no remote runtime request.

#### Scenario: Quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected
- **THEN** locked environment sync, Chromium installation, Node tests, the Vue build, the Vue component (Vitest) tests, the Storybook build with its component-coverage check, serial managed browser tests, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` and `npm ci` run from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution and the locked npm toolchain without modifying `uv.lock` or the npm lockfile

#### Scenario: Generic parallel profile excludes managed browser acceptance
- **WHEN** a local or quality-gate Evennia profile enables multiple test workers
- **THEN** the managed Playwright suite continues through its separate serial command with isolated server lifecycle ownership
