## MODIFIED Requirements

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The required quality workflow SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before the browser runner, run `node --test web/static/webclient/js/tests/*.test.js`, and run the explicit `web/tests/browser/` discovery once, serially, under coverage. Browser tests carrying requirement annotations SHALL write to the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified. Browser coverage SHALL be combined with non-browser Evennia and top-level coverage before exact-root and aggregate threshold verification. Managed browser acceptance MUST NOT be included in a generic parallel Evennia profile. Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 80% branch-coverage, and Codecov gates SHALL remain enabled.

#### Scenario: Quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected
- **THEN** locked environment sync, Chromium installation, Node tests, serial managed browser tests, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` runs from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution without modifying `uv.lock`

#### Scenario: Generic parallel profile excludes managed browser acceptance
- **WHEN** a local or quality-gate Evennia profile enables multiple test workers
- **THEN** the managed Playwright suite continues through its separate serial command with isolated server lifecycle ownership
