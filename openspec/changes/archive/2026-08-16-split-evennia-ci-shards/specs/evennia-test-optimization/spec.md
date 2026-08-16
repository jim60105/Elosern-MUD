# Evennia Test Optimization Specification (Delta)

## Purpose

Machine-level sharding of the non-browser Evennia suite across parallel CI
jobs, with exact per-module test ownership and unchanged aggregation
semantics.

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

### Requirement: Machine shards preserve exact per-module test ownership
The committed non-browser Evennia shard manifest SHALL partition every discoverable non-browser test module exactly once: a top-level contract test SHALL enumerate all `test*.py` modules under `commands`, `server`, `typeclasses`, `world`, and `web.webclient`, resolve every manifest label to its module(s) without importing them (a label names either a module file directly or a package directory to walk recursively), and assert that the discovered set and the labeled set are identical with no overlap between shards. Shard indices SHALL be unique and sorted. Every shard SHALL contain at least one label, every label SHALL resolve to at least one test module, and the manifest SHALL declare at least one shard. The preflight job SHALL validate these manifest properties before computing the execution matrix, so a syntactically valid but empty or malformed manifest fails the workflow rather than skipping every shard job and the aggregation gate.

#### Scenario: Every non-browser test module is owned exactly once
- **WHEN** the evennia shard manifest is inspected by the ownership contract test
- **THEN** each discovered test module appears in exactly one shard's labels, labels resolve without importing game code, indices are unique and sorted, and no module is orphaned or duplicated

#### Scenario: Manifest labels resolve to real test modules
- **WHEN** a manifest label does not correspond to an existing test module file or a package directory containing test modules
- **THEN** the ownership contract test fails with a diagnostic naming the unresolvable label

#### Scenario: Empty or malformed manifest cannot skip the gate
- **WHEN** the committed evennia manifest declares no shards, a non-sorted or duplicate index, or a shard without non-empty string labels
- **THEN** the preflight job fails before any execution job is dispatched, so the sharded suite and the aggregation gate always run when the workflow runs

#### Scenario: Shard balance is observable and rebalancable
- **WHEN** a CI run reports one evennia shard dominating the others by a wide margin
- **THEN** rebalancing is a manifest edit followed by the contract tests, and the measured per-shard durations are recorded in the performance report
