# Evennia Test Optimization Specification (Delta)

## Purpose

Two-process browser shards on separate checkouts with method-level label
ownership, keeping every aggregation contract identical.

## MODIFIED Requirements

### Requirement: Existing quality gates remain authoritative
The optimized workflow SHALL execute the managed browser suite exactly once across its committed execution jobs and SHALL collect separate coverage data for the non-browser Evennia, managed browser, and top-level entry points. The managed browser suite MAY be distributed across parallel CI jobs by test file, class, or method label as long as each test method has exactly one serial execution owner; a browser job MAY run two isolated test processes from two separate checkouts on the same runner, each process owning its own serial label set, coverage file, and evidence file, with the evidence files concatenated per shard. The non-browser Evennia suite MAY likewise be distributed across parallel CI jobs by manifest-owned dotted labels (package or module) as long as each test module under `commands`, `server`, `typeclasses`, `world`, and `web.webclient` has exactly one serial execution owner and every shard's coverage and requirement-evidence files are aggregated exactly once. The workflow SHALL preserve shared successful requirement evidence across all required Python entry points, combine the coverage files of every entry point into one aggregate, verify exact coverage roots for `commands`, `server`, `typeclasses`, `web`, and `world`, enforce aggregate branch coverage of at least 80%, and generate and upload coverage XML only from the verified aggregate data. Aggregation MUST fail when an expected entry-point artifact is missing or empty rather than silently lowering the combined total. Test performance improvements MUST NOT come from skipped tests, reduced assertions, removed annotations, disabled gates, or failure suppression.

#### Scenario: Optimized serial workflow proves equivalence
- **WHEN** final verification runs from a clean test database
- **THEN** strict OpenSpec validation, all three disjoint Python suites, execution-evidence verification, coverage-root verification, the aggregate 80% branch gate, Node tests, and Codecov publication retain their required semantics

#### Scenario: Browser coverage is collected without duplicate execution
- **WHEN** the committed quality workflow is inspected and run
- **THEN** `web/tests/browser/` has exactly one serial execution owner per test method across the workflow's browser jobs, the combined browser coverage files are required by aggregation, and the non-browser Evennia labels use `web.webclient` instead of broad `web` discovery

#### Scenario: Browser shard runs two isolated processes
- **WHEN** a browser shard job runs two test processes from two separate checkouts
- **THEN** each process owns its own serial label list, coverage file, and evidence file; the per-process evidence files are concatenated per shard; and the per-shard artifacts satisfy the aggregation completeness checks exactly once

#### Scenario: Non-browser suite is machine-sharded with per-module ownership
- **WHEN** the quality gate runs the non-browser Evennia suite across multiple machine-sharded jobs driven by a committed manifest
- **THEN** every non-browser test module under `commands`, `server`, `typeclasses`, `world`, and `web.webclient` belongs to exactly one shard, every shard runs its labels with the documented parallel worker profile and subprocess-aware coverage, and each shard's coverage sidecars and evidence file are required by aggregation exactly once

#### Scenario: Parallel CI aggregation preserves the gate
- **WHEN** the quality gate runs the non-browser Evennia profile with parallel workers and the browser suite across sharded jobs
- **THEN** the final aggregation job combines every entry point's coverage files into one report, verifies the coverage roots, enforces the aggregate branch gate, verifies the concatenated requirement evidence, and publishes coverage XML from the combined data only

#### Scenario: Missing artifact fails the aggregation gate
- **WHEN** an entry-point job finishes without uploading its coverage data or evidence file
- **THEN** aggregation fails with a diagnostic naming the missing artifact instead of producing a coverage report from partial data

## ADDED Requirements

### Requirement: Browser method labels preserve exact ownership
The committed browser shard manifest SHALL partition every test method of every `test_*.py` file under `web/tests/browser/` exactly once across its process lists: a top-level contract test SHALL parse each browser test file with `ast` without importing it, collect every `test_*` method per class, resolve each manifest label (module, class, or method) to its (file, class, method) set, and assert that the resolved set equals the discovered set with no overlap. Shard indices SHALL be unique and sorted. Every shard SHALL contain exactly two process lists, each with at least one label, and every label SHALL resolve to at least one test method.

#### Scenario: Every browser test method is owned exactly once
- **WHEN** the browser shard manifest is inspected by the method-level ownership contract test
- **THEN** each discovered test method appears in exactly one process list, labels resolve without importing test modules, indices are unique and sorted, and no method is orphaned or duplicated

#### Scenario: Unresolvable browser label fails the contract
- **WHEN** a manifest label does not correspond to an existing browser test module, class, or method
- **THEN** the ownership contract test fails with a diagnostic naming the unresolvable label

#### Scenario: Two isolated processes per shard stay serial per process
- **WHEN** a browser shard's two process lists run on the same runner from separate checkouts
- **THEN** each process executes its own labels serially with its own coverage and evidence files, and the per-shard evidence is the concatenation of both processes' files
