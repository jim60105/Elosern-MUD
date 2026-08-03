## 1. Baseline And Contracts

- [x] 1.1 Verify `--timing`, `--durations`, `--keepdb`, candidate `--parallel` forms, exact settings-command context, and accepted dotted labels against the pinned Evennia/Django runner; record unsupported assumptions from the source notes.
- [x] 1.2 Create `docs/development/evennia-test-performance.md` and record one warm-up plus at least three serial baseline runs with baseline SHA, environment and lock identity, database and coverage state, raw and median wall times, test counts, outcomes, database timing, and slowest tests.
- [x] 1.3 Inventory all `web/**/test*.py` ownership plus `EvenniaTest`, `EvenniaTestCase`, command mixin, `setUp`, and `setUpTestData` use; rank candidate fixture changes by measured cost and required integration boundary.

## 2. Isolated Test Profile

- [x] 2.1 Add guarded `server/conf/test_settings.py` and its contract tests together: require `MUD_TEST_SETTINGS=1` plus the verified exact test-command context, select the fast hasher, set `DATABASES["default"]["TEST"]["NAME"]` to a dedicated file path, reject direct/server use, and prove production and browser settings remain unchanged.
- [x] 2.2 Verify focused and full non-browser runs against both a newly created database and two consecutive `--keepdb` runs, confirming the explicit test database is reused, the developer database is unchanged, and test counts and outcomes match.

## 3. Disjoint Coverage Ownership

- [x] 3.1 Update `.github/workflows/quality-gate.yml` and its contract tests together to require one serial browser discovery under `.coverage.browser`, non-browser labels `commands server typeclasses world web.webclient` under `.coverage.evennia`, top-level contracts under `.coverage.top-level`, combination of all three files, shared evidence, and every existing gate.
- [x] 3.2 Run the three revised entry points and prove that their union owns every current Python test exactly once, produces complete evidence, retains exact five production coverage roots and aggregate branch coverage of at least 90%, and does not claim managed child-process coverage without subprocess support.

## 4. Measured Fixture Optimization

- [x] 4.1 Convert the highest-impact pure-logic candidates from `EvenniaTest` to `unittest.TestCase`, preserving assertions and requirement annotations; verify each test alone and in its package suite.
- [x] 4.2 Assess measured candidates that need Django/Evennia but not default-world fixtures for `EvenniaTestCase`; convert only justified candidates, and retain `EvenniaTest` and command lifecycle integration wherever those are behavior under test.
- [x] 4.3 Introduce class-level data or mocks only for proven immutable/resettable fixtures, delays, or external I/O, and verify isolation with per-test, package, order-variation, and full non-browser runs.
- [x] 4.4 Re-profile after each optimization batch and stop conversions whose complexity or boundary loss is not justified by measured improvement.

## 5. Parallel Evaluation

- [x] 5.1 Run repeated serial and retained `--parallel 4` comparisons for the non-browser profile, proceeding to clean and Django-selected-worker comparisons only while correctness and isolation remain stable; record medians, counts, outcomes, database names, diagnostics, flakes, and the condition that stops evaluation.
- [x] 5.2 Test parallel requirement-evidence integrity and subprocess coverage equivalence only if repeated functional runs remain stable; otherwise document the failed prerequisite and keep serial artifacts authoritative.
- [x] 5.3 Adopt parallel flags only for profiles that preserve every correctness and artifact condition and improve median wall time by at least 20%; otherwise keep serial execution canonical and document each failed condition.

## 6. Documentation And Final Verification

- [x] 6.1 Update `AGENTS.md`, `README.md`, `docs/development/spec-test-traceability.md`, and affected operations documentation with uv-locked focused, full, profiling, browser, and final commands, three coverage files, shared evidence, sole browser ownership, and dedicated test-database rebuild guidance; update documentation contract tests in the same task.
- [x] 6.2 Add substantive tests for the active-change requirements, run `uv run --locked python -m tools.spec_traceability check`, and record that `covers_requirement` annotations must be added from canonical IDs when archival synchronization promotes the new capability into the main requirement index.
- [x] 6.3 Record the optimized revision identity and one warm-up plus at least three post-change serial runs under the baseline machine, lock, target ownership, database state, and coverage state; calculate medians and document whether the 20% non-browser performance gate and independent duplicate-browser-removal acceptance passed.
- [x] 6.4 Run `openspec validate optimize-evennia-testing --strict`, Node tests, the serial managed browser coverage suite, the full non-browser Evennia coverage suite from a clean test database, and the top-level coverage suite with one evidence path; verify evidence, combine all three coverage files, verify exact roots, enforce 90% branch coverage, and generate aggregate XML.
- [x] 6.5 Confirm `git diff --check` is clean and reconcile proposal, design, specs, tasks, commands, test totals, and performance report before handoff.
