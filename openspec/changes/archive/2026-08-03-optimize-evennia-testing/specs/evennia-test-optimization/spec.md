## ADDED Requirements

### Requirement: Optimization is based on reproducible measurements
The project SHALL capture a pre-change and post-change Evennia test performance report using a recorded baseline commit SHA and optimized revision identity on the same reference machine, with the same Python and Evennia versions, dependency lock, target ownership, migrations, fixtures, warm-up protocol, and coverage state. Before a commit exists, the optimized identity SHALL name the worktree branch, base SHA, and dirty state; its eventual commit SHA supersedes that provisional identity. Each side SHALL use a warm-up followed by at least three measured serial runs and report raw wall times, median wall time, test count, result status, database setup timing, storage and reuse state, coverage state, environment versions, and the slowest tests. Database storage and cross-process reuse MAY differ when they are explicit optimization variables and MUST be disclosed. Performance acceptance SHALL require at least a 20% median wall-time reduction for the full non-browser Evennia profile and SHALL NOT use a hardware-independent seconds threshold.

#### Scenario: Baseline identifies measured hot spots
- **WHEN** the profiling profile completes its baseline runs
- **THEN** the report contains sufficient command, environment, timing, count, and slow-test data to select fixture optimizations without guessing

#### Scenario: Performance claim uses comparable runs
- **WHEN** the implementation claims that the full profile is faster
- **THEN** the claim compares serial medians for the recorded baseline and optimized revision identities under the same machine, dependency environment, target ownership, migrations, fixtures, warm-up protocol, and coverage state, discloses any database storage or reuse difference, and demonstrates at least a 20% reduction

### Requirement: Test-only settings are explicit and isolated
The project SHALL provide an explicit Evennia test settings module that uses Django's test-only fast password hasher and sets `DATABASES["default"]["TEST"]["NAME"]` to a unique file-backed SQLite path compatible with `--keepdb`, distinct from both `:memory:` and the developer database. Loading the module MUST require an explicit environment opt-in and the pinned launcher's exact test-command context, MUST reject direct or non-test server use with a documented configuration error, MUST NOT change production or browser-test password hashing or persistence, and MUST confine retained test state to its named test database.

#### Scenario: Repeated local run reuses only test state
- **WHEN** a developer runs a supported Evennia profile twice with the test settings and `--keepdb`
- **THEN** the second run reuses the dedicated test database without reading or writing the developer database

#### Scenario: Production cannot select weak hashing
- **WHEN** the normal server settings or browser-test settings are loaded for their intended runtime
- **THEN** neither settings profile selects the test-only fast password hasher or retained local test database

#### Scenario: Clean database remains supported
- **WHEN** the suite runs after the dedicated test database is absent or retention is disabled
- **THEN** Django creates a fresh test database and the suite passes with the same discovered tests and outcomes

### Requirement: Supported execution profiles preserve suite ownership
The project SHALL document uv-locked focused, full local, profiling, canonical quality-gate, and managed browser profiles. Focused profiles SHALL accept dotted module, class, or method labels and SHALL be described as development feedback rather than final verification. The non-browser Evennia profile SHALL own package-local tests under `commands`, `server`, `typeclasses`, `world`, and `web.webclient`; the top-level regression command SHALL own `tests/`; and the managed browser command SHALL solely own `web/tests/browser/`. Contract verification MUST prove every current Python test path belongs to exactly one Python entry point.

#### Scenario: Developer runs one affected test
- **WHEN** a developer follows the focused profile with a dotted test label
- **THEN** the command uses the locked environment, explicit test settings, retained test database, and no unrelated package label

#### Scenario: Final verification remains complete
- **WHEN** the documented final verification workflow is followed
- **THEN** all package-local, top-level, Node, browser, OpenSpec, traceability, coverage-root, aggregate coverage, and Codecov gates remain represented without failure suppression

#### Scenario: Retained database rebuild is documented
- **WHEN** migrations change or retained-state failures occur
- **THEN** the documentation directs removal or rebuilding of only the dedicated test database before rerunning the clean profile

### Requirement: Fixture optimization preserves the tested boundary
The project SHALL optimize only measured or inventoried test hot spots. Pure logic SHALL use standard `unittest.TestCase`; tests needing Django or Evennia setup without default game objects SHALL use `EvenniaTestCase` with minimal fixtures; command tests SHALL retain the command-test lifecycle; and tests asserting default world, typeclass persistence, account, session, room, exit, object, or script integration SHALL retain an integration-capable base. Fixture conversions MUST preserve substantive assertions and requirement annotations.

#### Scenario: Pure logic avoids default-world creation
- **WHEN** a measured hot test exercises deterministic calculation, parsing, or formatting without persistence behavior
- **THEN** it runs without constructing the default `EvenniaTest` world

#### Scenario: Integration behavior retains real persistence
- **WHEN** a test asserts an Evennia handler, Attribute, typeclass, command lifecycle, session, or database transaction behavior
- **THEN** the optimized test still exercises the real required integration boundary rather than mocking the behavior under assertion

#### Scenario: Shared fixture mutation is isolated
- **WHEN** class-level test data is introduced
- **THEN** isolation, package, order-variation, and full-suite runs demonstrate that one test method cannot affect another method's outcome

### Requirement: Parallel execution is gated by equivalence
Parallel Evennia execution SHALL remain optional and outside the canonical coverage workflow unless repeated runs demonstrate identical discovered test counts and outcomes, complete parseable requirement evidence, isolated databases and shared resources, equivalent combined branch coverage and source roots, actionable failures, and at least a 20% median wall-time reduction. Managed browser acceptance MUST NOT be included in a generic parallel profile.

#### Scenario: Unsafe parallel run is rejected
- **WHEN** parallel evaluation loses coverage or evidence, collides on a file, cache, process, database, or port, produces a flake, or improves median wall time by less than 20%
- **THEN** serial execution remains canonical and the failed adoption condition is recorded

#### Scenario: Parallel mode qualifies for canonical use
- **WHEN** repeated clean and retained-database parallel runs satisfy every correctness, artifact-equivalence, isolation, diagnostic, and speed condition
- **THEN** the profile may be documented or adopted only for the proven non-browser scope

### Requirement: Existing quality gates remain authoritative
The optimized workflow SHALL execute the managed browser suite exactly once under its explicit serial command and SHALL collect separate coverage data for the non-browser Evennia, managed browser, and top-level entry points. It SHALL preserve shared successful requirement evidence across all required Python entry points, combine all three named coverage files, verify exact coverage roots for `commands`, `server`, `typeclasses`, `web`, and `world`, enforce aggregate branch coverage of at least 90%, and generate and upload coverage XML only from the verified aggregate data. Test performance improvements MUST NOT come from skipped tests, reduced assertions, removed annotations, disabled gates, or failure suppression.

#### Scenario: Optimized serial workflow proves equivalence
- **WHEN** final verification runs from a clean test database
- **THEN** strict OpenSpec validation, all three disjoint Python suites, execution-evidence verification, coverage-root verification, the aggregate 90% branch gate, Node tests, and Codecov publication retain their required semantics

#### Scenario: Browser coverage is collected without duplicate execution
- **WHEN** the committed quality workflow is inspected and run
- **THEN** `web/tests/browser/` has exactly one serial execution owner, its dedicated coverage file is required by aggregation, and the non-browser Evennia labels use `web.webclient` instead of broad `web` discovery
