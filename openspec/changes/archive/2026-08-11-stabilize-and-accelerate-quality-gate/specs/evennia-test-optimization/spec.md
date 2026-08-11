# Evennia Test Optimization Specification (Delta)

## Purpose

Measured, isolated, and coverage-preserving execution profiles for the Evennia test suite.

## ADDED Requirements

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

## MODIFIED Requirements

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
