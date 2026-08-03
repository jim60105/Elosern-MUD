## Context

The repository already removed duplicate test discovery: package-local tests run through explicit `commands server typeclasses web world` labels and top-level contracts run separately. The remaining full Evennia step is database-heavy and broad use of `EvenniaTest` creates accounts, characters, rooms, exits, objects, scripts, and sessions for every inheriting class. Production password hashing also applies when tests create accounts or call `set_password()`.

The source notes suggest `--keepdb`, `--parallel`, an in-memory database, a fast password hasher, `setUpTestData()`, and lighter test bases. These are alternatives with different constraints, not an additive recipe. In particular, an in-memory SQLite database cannot persist across commands for `--keepdb`; Django parallel workers require separate databases; coverage and the shared append-only traceability evidence stream need explicit subprocess validation; and the managed browser tests intentionally serialize server lifecycles because combat sessions can contaminate later logins.

The current mandatory gates are strict OpenSpec validation, static and execution traceability, Node tests, managed Playwright acceptance, package-local Evennia tests, top-level regression tests, exact coverage-root verification, 90% aggregate branch coverage, and Codecov upload. The explicit browser command currently runs `web/tests/browser/`, then the package-local Evennia command discovers the same suite again through its `web` label. Separate non-browser tests live under `web.webclient` and must remain in the Evennia ownership domain. Optimization cannot remove, skip, or weaken any gate, but it can make ownership disjoint and aggregate coverage from three entry points.

## Goals / Non-Goals

**Goals:**

- Reduce repeated local Evennia feedback time with an explicit, isolated test profile.
- Make optimization decisions from repeatable timings and slow-test reports rather than assumptions.
- Remove unnecessary full-world fixtures from measured hot tests while preserving test independence and behavior coverage.
- Determine empirically whether local parallel execution is safe and worthwhile.
- Execute the managed browser suite exactly once while retaining its successful evidence and `web` coverage contribution.
- Keep canonical CI evidence and coverage semantics intact.

**Non-Goals:**

- Change production settings, game behavior, schemas, migrations, or dependencies.
- Set an absolute suite-duration promise that depends on runner hardware and load.
- Parallelize managed browser tests or merge them into a generic fast profile.
- Convert integration tests merely to reduce counts, share mutable state between methods, mock behavior under test, or reduce assertions.
- Replace the required full suite with focused tests.

## Decisions

### Establish normalized baselines before optimization

Implementation will record at least three serial runs after one warm-up for both the baseline commit SHA and optimized revision identity on the same machine. Before a commit exists, the optimized identity is the named worktree branch plus its base SHA and dirty-state disclosure; the eventual commit SHA supersedes it. The report will capture command, each revision identity, Python and Evennia versions, dependency lock identity, processor count, database storage and reuse state, coverage state, total wall time, test count, failures/skips, database setup timing, and the slowest tests. Median wall time is the comparison value; raw runs remain visible. Comparison runs use equivalent target ownership, migrations, fixtures, warm-up protocol, and coverage state. Database storage and cross-process reuse may differ because replacing the ineffective in-memory `--keepdb` profile with retained file storage is part of the measured change; that difference must be explicit rather than presented as controlled.

The baseline commands use Django's supported `--timing` and `--durations` options after verifying those options against the pinned runner. A contract test will inspect stable configuration and commands, not assert seconds on shared CI hardware.

Alternative considered: optimize first and compare one before/after run. This is rejected because cold database creation, browser server startup, and host load would make the result non-repeatable.

### Use an explicit test settings module

`server/conf/test_settings.py` will import project settings, select Django's test-only `MD5PasswordHasher`, and set `DATABASES["default"]["TEST"]["NAME"]` to a unique file path under `server/db/` that is neither `:memory:` nor the developer database. The normal connection name remains unchanged. Canonical commands will pass `--settings test_settings.py` and an explicit `MUD_TEST_SETTINGS=1` opt-in. The module will additionally require the pinned launcher's exact test-command context, verified by a launcher probe, and raise a documented configuration error for direct import or a server command. Exact command-token checking is permitted; loose substring detection is not. Production and browser settings remain unchanged.

The file-backed database makes `--keepdb` meaningful across repeated local commands. Documentation will state that schema or migration changes, database corruption, or unexplained retained-state failures require one run without `--keepdb` or deletion of only the dedicated test database. Tests must still pass from a newly created database.

Alternatives considered:

- Detect `"test" in sys.argv` in production settings. Rejected because it couples security-sensitive test behavior to substring detection and hides which profile is active.
- Use SQLite `:memory:` together with `--keepdb`. Rejected because process exit destroys the database, so it cannot provide cross-command reuse.
- Replace SQLite with another backend. Rejected because no production requirement or measured bottleneck justifies a new service dependency.

### Define distinct execution profiles

The supported profiles are:

- Focused development: the narrowest dotted module, class, or method label with test settings, `--keepdb`, and optionally `--failfast`.
- Full local correctness: the non-browser labels `commands`, `server`, `typeclasses`, `world`, and `web.webclient` through test settings and `--keepdb`, followed by the separate browser and top-level suites when their ownership domains may be affected.
- Profiling: the full serial Evennia labels with test settings, `--keepdb`, `--timing`, and a bounded `--durations` report, without coverage instrumentation.
- Canonical quality gate: three disjoint Python entry points for non-browser Evennia tests, managed browser acceptance, and top-level contracts, followed by shared evidence verification and aggregate coverage. It may use test settings and the fast hasher, but remains serial unless subprocess coverage and evidence equivalence are separately proven.
- Managed browser acceptance: the existing explicit serial command and isolated temporary-server harness, wrapped in coverage with its own data file so `web` remains an exact aggregate source root.

The documentation will not present focused runs as final verification. It will retain the runtime-budget guidance in `AGENTS.md` and reconcile all command examples with `uv run --locked` and explicit settings.

### Give browser tests one execution owner

The quality workflow will run the managed browser command once under `coverage run -m unittest discover -s web/tests/browser -t .`, writing `.coverage.browser`. The non-browser Evennia coverage command will use `commands server typeclasses world web.webclient`, preserving all non-browser Python tests under `web` without discovering `web/tests/browser/`. The top-level command remains unchanged. Coverage combine will require all three named files before root and threshold verification, and every annotated Python entry point will receive the same evidence path.

Wrapping the browser runner records its parent-process harness coverage; it does not by itself capture production code in the managed Evennia child process. Coverage of the `web` production root therefore remains dependent on the retained `web.webclient` non-browser tests unless subprocess coverage is separately configured and proven. Exact-root and 90% aggregate checks remain the authority; the proposal makes no unsupported child-process coverage claim.

Workflow contract tests will prove that browser discovery appears in exactly one execution step, the Evennia labels use `web.webclient` instead of broad `web` discovery, all three coverage files are combined, and browser execution remains serial. This supersedes the earlier tolerance for duplicate browser collection; dynamic-port isolation remains required for repeatability across separate workflow runs and failures.

Alternative considered: keep the duplicate browser execution so the broad Evennia command supplies `web` coverage. Rejected because retained `web.webclient` tests cover the production root while the coverage-wrapped explicit browser command records parent harness execution without spending another 20 or more minutes.

### Optimize fixture hot spots in descending measured impact

Only tests present in the slow-test report or fixture inventory will be candidates. For each candidate, implementation will identify the minimum required boundary:

- Pure deterministic logic uses `unittest.TestCase`.
- Evennia-aware tests that need Django setup but not the default world use `EvenniaTestCase` and create only required objects.
- Command lifecycle tests retain `EvenniaCommandTestMixin` with an appropriate Evennia database base.
- Tests requiring the complete default account, characters, rooms, exits, object, script, or session retain `EvenniaTest`.

Class-level `setUpTestData()` is permitted only for immutable reference fixtures or fixtures restored by Django between methods. Mutable handlers, Attributes, sessions, module registries, caches, files, ports, and external process state cannot be shared without explicit reset proof. Mocks replace time delays and external I/O, not persistence or lifecycle behavior asserted by the test.

Each conversion must pass in isolation, in its package suite, in reversed or randomized order where supported, and in the final full suite. Requirement annotations stay on substantively equivalent discoverable tests.

Alternative considered: mechanically replace every `EvenniaTest`. Rejected because many tests intentionally exercise typeclass persistence and command integration, and fixture reduction is valid only when the tested boundary permits it.

### Keep parallelism experimental unless equivalence is proven

The implementation will compare serial execution with `--parallel 4` and, only if fixed-worker runs remain stable, Django-selected worker count using clean and retained-database runs. Evaluation stops as soon as a correctness, isolation, evidence, coverage, or diagnostic condition fails; a failed mode cannot become canonical regardless of speed. Adoption requires no failures or flakes over repeated runs, identical discovered test counts, complete requirement evidence, isolated database names, no shared file/port/cache collisions, and a median wall-time reduction of at least 20% for the targeted profile.

Parallel execution will initially be local and non-coverage only. It will not enter the canonical quality workflow unless coverage from worker subprocesses combines to the same roots and branches, the shared evidence stream remains complete and parseable, failure diagnostics remain actionable, and browser tests are excluded. If any condition fails, serial execution remains canonical and the negative result is documented.

Alternative considered: enable `--parallel 4` in CI immediately. Rejected because Django worker subprocesses can invalidate the current single-process coverage assumptions and concurrent evidence/file fixtures can introduce flaky results.

### Measure success without weakening gates

Acceptance requires the optimized serial profile to preserve the union of uniquely owned test counts and outcomes, pass from clean and retained databases, preserve static and execution traceability, and preserve aggregate branch coverage at or above 90%. The median full non-browser Evennia wall time must improve by at least 20% between the recorded baseline and optimized SHAs on the same reference machine and equivalent environment; otherwise test-settings support and safe fixture corrections may land, but performance claims and parallel workflow changes must not. Removing the second browser collection is accepted independently when the sole browser run preserves its outcomes, evidence, and aggregate coverage.

The browser, Node, and top-level suites remain separate. Browser acceptance is explicitly excluded from generic parallel profiles because its harness owns real server processes and combat tests require per-test isolation.

## Risks / Trade-offs

- [The fast hasher leaks into a running game server] → Keep it in an explicit module, guard import to test execution, and add contract tests proving production and browser settings do not select it.
- [A retained database hides migration or ordering defects] → Require clean-database verification at final handoff and document targeted rebuild conditions.
- [Replacing the broad `web` label loses Python tests or coverage] → Retain the verified `web.webclient` label, assert that every current non-browser `web/**/test*.py` remains collected, collect browser coverage separately, require all three files in combination, and retain exact-root verification.
- [Shared class fixtures leak mutations] → Restrict sharing to proven resettable data and run isolation, package, order-variation, and full-suite checks.
- [Parallel workers corrupt evidence or lose coverage] → Keep parallelism outside canonical coverage by default and require artifact equivalence before adoption.
- [Timing improvements are host noise] → Compare medians from recorded baseline and optimized SHAs on the same machine and dependency environment, with raw metadata and runs retained.
- [Optimizing tests changes the behavior boundary] → Preserve assertions and requirement annotations, and retain integration coverage wherever persistence, typeclasses, commands, or sessions are the subject.
- [A dedicated test database is mistaken for developer data] → Use an unmistakable test-only path and permit cleanup of only that path.

## Migration Plan

1. Capture the serial baseline and fixture inventory, including every Python test path under `web`.
2. Add the guarded test settings module together with its contract tests and update local commands. Verify the pinned launcher context plus clean and retained database runs before fixture edits.
3. Optimize measured fixture hot spots in small batches, running focused and package tests after each batch and recording timing changes.
4. Evaluate local parallel profiles separately and document whether they meet the adoption gate.
5. Run the three disjoint Python entry points with one evidence path and separate coverage files, combine them, run the complete required verification workflow serially, compare final medians, and update the performance report.
6. Change CI execution flags only if every parallel coverage/evidence condition is proven; otherwise retain the serial quality gate.

Rollback is configuration-only and test-only: restore canonical commands to `settings.py`, remove `server/conf/test_settings.py`, delete only its explicit `DATABASES["default"]["TEST"]["NAME"]` file, and revert individual fixture conversions that fail isolation checks. No application data recovery or migration is required.

## Open Questions

None. The measured hot-test set and whether parallel execution qualifies are implementation outputs governed by explicit acceptance gates rather than unresolved design choices.
