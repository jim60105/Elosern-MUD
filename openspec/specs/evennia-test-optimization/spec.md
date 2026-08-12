## Purpose

Measured, isolated, and coverage-preserving execution profiles for the Evennia test suite.

## Requirements

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

### Requirement: Tests restore process-global registry state
Any test that mutates a process-global registry shared across the test process SHALL snapshot the registry's contents before mutating and restore them in teardown, preserving whatever the process held before the test rather than clearing state other tests rely on. Registries covered by this contract include at least `QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`, and `SCENE_REQUIREMENT_REGISTRY`. The restoration MUST be registered before the mutation (for example via `addCleanup`) so a failing setup cannot leak registry state. A test that reads rulebook-driven state requiring registry entries (for example an affinity-rulebook load that resolves quest keys) SHALL register the required catalog definitions in its own setup instead of depending on an earlier test to have registered them. Synchronization entry points that register offers or definitions (such as `sync_guild_economy()`) used inside tests MUST be paired with the same snapshot/restore discipline.

#### Scenario: Leaked offer cannot break a later test
- **WHEN** a test runs `sync_guild_economy()` (or registers catalog offers) and a later test in the same process registers a differently-shaped offer under the same identity
- **THEN** the later registration succeeds because the earlier test restored the registry to its pre-test contents

#### Scenario: Cleared registry is restored to prior contents
- **WHEN** a test clears `QUEST_DEFINITION_REGISTRY` or `GUILD_OFFER_REGISTRY` during its body
- **THEN** the registry is restored to exactly the entries it held before the test, so later tests relying on those entries (for example an affinity-rulebook load resolving `introductory_hunt`) continue to pass

#### Scenario: Failing setup cannot leak registry state
- **WHEN** a test's setup mutates a covered registry and then raises before its teardown would run
- **THEN** the registry is still restored to its pre-test contents because the restoration was registered before the mutation

#### Scenario: Order variation cannot change outcomes
- **WHEN** the full non-browser Evennia suite runs in serial, parallel, shuffled, and reversed order
- **THEN** every test passes in every ordering with the same discovered test count

### Requirement: Parallel execution is gated by equivalence
Parallel Evennia execution SHALL be adopted for the non-browser Evennia profile only after repeated runs demonstrate identical discovered test counts and outcomes, complete parseable requirement evidence, isolated databases and shared resources, equivalent combined branch coverage and source roots, actionable failures, and at least a 20% median wall-time reduction. Once the equivalence evidence exists, the quality-gate workflow MAY execute the non-browser Evennia profile with the documented parallel worker count and subprocess-aware coverage instrumentation, and the performance report SHALL record the adoption evidence. Managed browser acceptance MUST NOT be included in a generic parallel profile. Serial execution SHALL remain the canonical final-handoff evidence profile.

#### Scenario: Unsafe parallel run is rejected
- **WHEN** parallel evaluation loses coverage or evidence, collides on a file, cache, process, database, or port, produces a flake, or improves median wall time by less than 20%
- **THEN** serial execution remains canonical, parallel is not adopted in the workflow, and the failed adoption condition is recorded

#### Scenario: Parallel mode qualifies for canonical use
- **WHEN** repeated clean and retained-database parallel runs satisfy every correctness, artifact-equivalence, isolation, diagnostic, and speed condition
- **THEN** the profile is documented and adopted for the proven non-browser scope, including the committed quality-gate workflow

#### Scenario: Subprocess coverage is captured and combined
- **WHEN** the adopted parallel profile runs under the quality gate with coverage
- **THEN** every worker's coverage data is written to its own file, combined with the parent data, and the combined report equals the serial profile's source roots and statement/branch totals

### Requirement: Existing quality gates remain authoritative
The optimized workflow SHALL execute the managed browser suite exactly once across its committed execution jobs and SHALL collect separate coverage data for the non-browser Evennia, managed browser, and top-level entry points. The managed browser suite MAY be distributed across parallel CI jobs by test file as long as each file has exactly one serial execution owner and the per-job coverage and requirement-evidence files are aggregated exactly once. The workflow SHALL preserve shared successful requirement evidence across all required Python entry points, combine the coverage files of every entry point into one aggregate, verify exact coverage roots for `commands`, `server`, `typeclasses`, `web`, and `world`, enforce aggregate branch coverage of at least 90%, and generate and upload coverage XML only from the verified aggregate data. Aggregation MUST fail when an expected entry-point artifact is missing or empty rather than silently lowering the combined total. Test performance improvements MUST NOT come from skipped tests, reduced assertions, removed annotations, disabled gates, or failure suppression.

#### Scenario: Optimized serial workflow proves equivalence
- **WHEN** final verification runs from a clean test database
- **THEN** strict OpenSpec validation, all three disjoint Python suites, execution-evidence verification, coverage-root verification, the aggregate 90% branch gate, Node tests, and Codecov publication retain their required semantics

#### Scenario: Browser coverage is collected without duplicate execution
- **WHEN** the committed quality workflow is inspected and run
- **THEN** `web/tests/browser/` has exactly one serial execution owner per test file across the workflow's browser jobs, the combined browser coverage files are required by aggregation, and the non-browser Evennia labels use `web.webclient` instead of broad `web` discovery

#### Scenario: Parallel CI aggregation preserves the gate
- **WHEN** the quality gate runs the non-browser Evennia profile with parallel workers and the browser suite across sharded jobs
- **THEN** the final aggregation job combines every entry point's coverage files into one report, verifies the coverage roots, enforces the aggregate branch gate, verifies the concatenated requirement evidence, and publishes coverage XML from the combined data only

#### Scenario: Missing artifact fails the aggregation gate
- **WHEN** an entry-point job finishes without uploading its coverage data or evidence file
- **THEN** aggregation fails with a diagnostic naming the missing artifact instead of producing a coverage report from partial data

### Requirement: Registry-content assertions use the registry's key domain
Any test asserting membership or contents of a process-global registry covered
by the isolation contract SHALL use that registry's documented key domain, not
an incidental attribute of the entities it indexes. The skip-safety battlefield
registry SHALL be asserted with participant dbrefs: a test that checks
`world.rules.skip_safety._BATTLEFIELDS` SHALL assert `str(entity.pk)` keys,
never `str(entity.key)` display keys, matching the dbref indexing the registry
implements.

#### Scenario: Restore path registers each participant by dbref
- **WHEN** a persisted combat session is restored and the test verifies the
  skip-safety registration survived
- **THEN** the test asserts `str(actor.pk)` and `str(monster.pk)` are present in
  `_BATTLEFIELDS` after restoration, never the participants' display keys

#### Scenario: Display-key assertion fails under the dbref-keyed registry
- **WHEN** a test asserts that a participant's display key is a key of
  `_BATTLEFIELDS` whose entries are indexed by participant dbref
- **THEN** the assertion fails, proving the display-key form is not the
  registry's key domain
