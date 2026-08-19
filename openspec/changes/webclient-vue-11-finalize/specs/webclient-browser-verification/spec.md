## MODIFIED Requirements

### Requirement: Node and Playwright checks are mandatory quality-gate steps
Playwright SHALL be added to the synchronized uv development dependency group. The npm frontend toolchain
is a dev/CI-time dependency only and introduces no runtime npm dependency. The required quality workflow
SHALL install Chromium with `uv run --locked playwright install --with-deps chromium` before the browser
runner, run `node --test web/static/webclient/js/tests/*.test.js`, build the Vue application with the
locked npm toolchain (`npm ci` and the Vite production build), run the Vue component (Vitest) test suite,
build the Storybook component showcase with its component-coverage check against the frozen required set,
and run the explicit `web/tests/browser/` discovery once, serially, under coverage. The Vue `dist` artifact
SHALL be built in the browser test workspaces and in the container image. The managed browser acceptance
SHALL assert against the preserved DOM contract hooks (`#action-dock`, the `action-`/`target-` keys,
`#combat-row-0`, panel ids) and the re-mapped `data-testid` hooks, and SHALL include the
offline-degradation regression (bundle blocked → text playable via the console; incompatible OOB →
graphical locked with text round-tripping). Browser tests carrying requirement annotations SHALL write to
the same `OPENSPEC_TEST_EVIDENCE` path before execution evidence is verified. Browser coverage SHALL be
combined with non-browser Evennia and top-level coverage before exact-root and aggregate threshold
verification. Managed browser acceptance MUST NOT be included in a generic parallel Evennia profile.
Existing strict OpenSpec, Python suite, traceability, coverage-root, aggregate 80% branch-coverage, and
Codecov gates SHALL remain enabled. The built page makes no remote runtime request.

#### Scenario: The final quality workflow contains every required gate
- **WHEN** the committed quality workflow is inspected after the shell swap
- **THEN** locked environment sync (uv and npm), Chromium installation, Node tests, the Vue build, the Vitest component tests, the Storybook build with its component-coverage check, serial managed browser tests including the offline-degradation regression, full Evennia tests, top-level tests, traceability verification, and aggregate coverage enforcement are all required steps without failure suppression

#### Scenario: Locked dependency state is synchronized
- **WHEN** `uv sync --locked` and `npm ci` run from the committed project files
- **THEN** the development environment includes the pinned Playwright resolution and the locked npm toolchain without modifying `uv.lock` or the npm lockfile

#### Scenario: Generic parallel profile excludes managed browser acceptance
- **WHEN** a local or quality-gate Evennia profile enables multiple test workers
- **THEN** the managed Playwright suite continues through its separate serial command with isolated server lifecycle ownership
