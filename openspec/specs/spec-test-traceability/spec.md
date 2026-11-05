# Spec Test Traceability Specification

## Purpose

Define deterministic requirement-to-test traceability and reproducible CI
quality gates for the repository's current OpenSpec contract.
## Requirements
### Requirement: Main-spec requirements have deterministic identities
The verifier SHALL derive one human-readable identifier for every
`### Requirement:` heading in each direct child capability under
`openspec/specs/`. It MUST reject identity collisions, malformed requirement
headings, and requirements outside that current-contract tree MUST NOT affect
the result.

#### Scenario: Main requirement receives an ID
- **WHEN** a capability spec contains a valid requirement heading
- **THEN** the listing command emits an ID composed from the capability and the normalized requirement name

#### Scenario: Proposed and historical specs are excluded
- **WHEN** active or archived change directories contain requirement headings
- **THEN** those headings do not appear in the current-contract requirement index

#### Scenario: Colliding normalized names fail
- **WHEN** two requirement headings in one capability normalize to the same ID
- **THEN** verification fails and reports both source locations

### Requirement: Existing tests declare requirement coverage locally
The repository SHALL provide a transparent Python decorator that associates one
or more literal requirement IDs with a discoverable `test_*` function or method.
Applying the decorator MUST preserve the callable's identity and behavior, and
the verifier MUST discover annotations through static source parsing without
importing game or test modules.

#### Scenario: Unit test declares one requirement
- **WHEN** a unit-test method is decorated with one valid literal requirement ID
- **THEN** the verifier records that test location as coverage for the requirement

#### Scenario: Integration test declares multiple requirements
- **WHEN** an Evennia integration-test method is decorated with multiple valid literal IDs
- **THEN** the verifier records the test once for every declared requirement

#### Scenario: Invalid annotation is rejected
- **WHEN** the decorator is placed on a non-test callable or receives a dynamic or unknown ID
- **THEN** verification fails with the annotation's file and line number

### Requirement: Associated tests provide successful execution evidence
When the CI evidence path is configured, an annotated test SHALL record its
qualified identity and declared requirement IDs only after it returns
successfully. CI completeness verification MUST count only a static association
with matching successful execution evidence; uncollected, skipped,
expected-failing, and failing tests MUST NOT satisfy a requirement.

#### Scenario: Passing collected test counts
- **WHEN** an annotated test is collected and returns successfully under either required test command
- **THEN** its matching evidence makes each valid declared requirement eligible as covered

#### Scenario: Skipped test does not count
- **WHEN** the only associated test for a requirement is skipped
- **THEN** no successful evidence is recorded and CI completeness verification fails for that requirement

#### Scenario: Uncollected annotation does not count
- **WHEN** an annotation exists on source that neither required test command collects
- **THEN** it has no matching execution evidence and cannot satisfy the requirement

### Requirement: Every current requirement is associated with a test
The CI verification command MUST fail when any indexed main-spec requirement lacks
a valid, successfully executed test association, reporting every gap in
deterministic order with no baseline, waiver, or allowlist. Pre-archive only,
`check --change <change>` MAY exclude identifiers the named change removes or
renames; that tolerance MUST NOT cover any other requirement or any annotation
error, and the post-sync command MUST omit it.

#### Scenario: Complete traceability passes
- **WHEN** every indexed requirement has at least one valid test annotation with matching successful execution evidence and no verification error exists
- **THEN** verification exits successfully and reports requirement and association totals

#### Scenario: Every gap is reported
- **WHEN** a verification run without retirement tolerance finds one or more indexed requirements with no valid test annotation
- **THEN** verification exits nonzero and lists every uncovered requirement with its spec source location

#### Scenario: Existing test coverage is reused without fabricating tests
- **WHEN** the initial audit finds an existing test whose assertions cover a requirement
- **THEN** that test may be annotated without changing its assertions or behavior

#### Scenario: Named pre-archive retirement is the only tolerated gap
- **WHEN** every uncovered requirement is removed or renamed by the named active change's delta and no annotation error exists
- **THEN** the named check exits successfully, reports the tolerated identifiers separately, and the gap is closed by the archive sync

#### Scenario: Post-sync verification keeps no waiver
- **WHEN** the archive sync has published a change's delta and its retirement of main requirements
- **THEN** the post-sync command runs without a change name and fails for any remaining uncovered requirement

### Requirement: Continuous integration enforces both quality dimensions
GitHub Actions MUST run strict OpenSpec validation, complete requirement
traceability verification, the observability lint gate, the full project test
suite, and aggregate first-party code coverage on pushes and pull requests.
The workflow MUST fail if any test fails, any requirement lacks a test
association, the observability lint check reports any violation, aggregate
code coverage is below 80%, or publication of a successful aggregate report
fails.

#### Scenario: Requirement traceability regression fails CI
- **WHEN** a main-spec requirement is added without a valid test association
- **THEN** the continuous-integration job fails and identifies that requirement

#### Scenario: Code coverage regression fails CI
- **WHEN** all tests pass but aggregate measured first-party coverage is below 80%
- **THEN** the continuous-integration job fails at the coverage report step

#### Scenario: Observability lint regression fails CI
- **WHEN** a pushed file imports the Evennia logger directly, or a facade
  adopter file swallows an exception without re-raise, facade log, or
  reasoned exemption
- **THEN** the continuous-integration job fails at the observability lint step

#### Scenario: Package and repository tests execute once
- **WHEN** the quality gate runs the complete project suite
- **THEN** the Evennia entry point discovers package-local tests only from `commands`, `server`, `typeclasses`, `web`, and `world`
- **AND** the separate top-level entry point discovers repository contract tests from `tests`
- **AND** neither entry point discovers tests owned by the other

#### Scenario: Offline deterministic suite passes all gates
- **WHEN** strict specs, annotations, tests, observability lint, and aggregate coverage satisfy their local gates without generative services
- **THEN** the continuous-integration job reaches external coverage publication

#### Scenario: Coverage target remains visible without enforcement
- **WHEN** a contributor reads the documented coverage commands
- **THEN** the documentation states the 90% coverage target while the workflow and project configuration enforce only the 80% gate

#### Scenario: Workflow enablement waits for the initial audit
- **WHEN** the quality-gate workflow has not yet had an initial audit prove zero requirement gaps without adding product-behavior tests in this change
- **THEN** workflow enablement remains blocked

### Requirement: Coverage configuration is reproducible and project-scoped
Coverage measurement MUST use the locked project environment, enable branch
coverage, unconditionally combine data from the disjoint Evennia package suite
and top-level regression suite, and measure exactly the first-party production
roots `commands`, `server`, `typeclasses`, `web`, and `world`. The combined
data MUST be the sole source for the local threshold, source-root
verification, and externally published XML report.

#### Scenario: All required test entry points contribute coverage
- **WHEN** the workflow runs the complete project suite
- **THEN** the Evennia package suite and the top-level regression suite both execute under separate coverage data files
- **AND** their data is combined before the threshold is evaluated or an external report is generated

#### Scenario: Dependency code does not dilute the metric
- **WHEN** imported Evennia or other dependency code executes during tests
- **THEN** that code is outside the configured coverage source scope

#### Scenario: Local and CI thresholds agree
- **WHEN** a contributor runs the documented locked coverage commands locally
- **THEN** the same source, branch, omission, entry-point ownership, and 80% rules used by CI apply

#### Scenario: Published report matches the verified aggregate
- **WHEN** both test entry points pass and their coverage data satisfies local verification
- **THEN** CI generates the Codecov XML report from that combined data
- **AND** it does not upload either intermediate coverage data file as an independent report

#### Scenario: Only test implementation modules may be omitted
- **WHEN** the 80% calculation is configured over the first-party production roots
- **THEN** only test implementation modules under `*/tests/*` may be omitted from those roots

### Requirement: Aggregate coverage is published to Codecov
After all local test, traceability, source-root, and coverage-threshold gates
succeed, GitHub Actions SHALL upload the explicit combined XML report to the
`jim60105/Elosern-MUD` Codecov project using an immutable v5 release of the official
Codecov action and the configured `CODECOV_TOKEN` repository secret.
The action MUST disable automatic report discovery and MUST fail the CI job when
the requested upload fails.

#### Scenario: Verified aggregate report is uploaded
- **WHEN** both test entry points and all local quality gates succeed
- **THEN** the workflow uploads only the generated combined `coverage.xml` report to Codecov
- **AND** authenticates through the repository's `CODECOV_TOKEN` secret without
  exposing the token in repository files

#### Scenario: Upload failure remains visible
- **WHEN** Codecov rejects or cannot process the requested upload
- **THEN** the Codecov action exits nonzero and the quality-gate job fails

#### Scenario: README exposes current coverage
- **WHEN** a reader views `README.md`
- **THEN** Codecov's generated private-repository badge for `jim60105/Elosern-MUD` displays the configured default branch's coverage without exposing an upload credential
- **AND** selecting the badge opens that repository's Codecov page

### Requirement: Test migrations preserve meaningful current requirement coverage
Test migrations SHALL preserve literal current requirement IDs and justified associations with retained behavioral or integrity assertions. Removed balance pins SHALL NOT become blanket decorators on echo tests. Existing successful-execution, no-waiver and aggregate-coverage gates SHALL remain unchanged.

#### Scenario: A removed species suite retains justified coverage
- **WHEN** repetitive per-species vectors are removed
- **THEN** each affected current requirement has a justified integrity, shared synthetic or representative integration association and CI still requires successful execution

#### Scenario: Complete current-contract scope
- **WHEN** the migration inventory is compared with the current main-spec requirement index
- **THEN** every current capability has a disposition, historical archived artifacts and unimplemented proposals remain outside the edited contract tree, and no requirement is omitted by a baseline waiver

### Requirement: Pre-archive traceability tolerates only requirements the named change retires

The traceability check SHALL accept an optional active change name. With a name it
SHALL derive retiring identifiers only from that change's `## REMOVED Requirements`
headings and `## RENAMED Requirements` `FROM` lines, tolerate those identifiers when
they are uncovered, and report them separately from uncovered requirements. `ADDED`
and `MODIFIED` requirements MUST NOT retire an identifier. Without a change name the
check MUST stay strict.

#### Scenario: Removed and renamed identifiers retire

- **WHEN** a change's delta spec has a `## REMOVED Requirements` heading for one main requirement and a `## RENAMED Requirements` `FROM` line for another
- **THEN** the check reports exactly those two main identifiers as retiring

#### Scenario: Modified requirements never retire

- **WHEN** a delta spec also declares a `## MODIFIED Requirements` heading for an uncovered main requirement
- **THEN** the check leaves that modified identifier out of the retiring set

#### Scenario: Only retiring gaps pass

- **WHEN** every uncovered indexed requirement is in the named change's retiring set and no verification error exists
- **THEN** the check exits successfully

#### Scenario: Other gaps still fail

- **WHEN** one indexed requirement is retired by the named change, one is declared only as `MODIFIED`, and neither is covered
- **THEN** the check exits nonzero and lists the modified requirement as uncovered

#### Scenario: Retiring identifiers are reported separately

- **WHEN** the check runs with a change name and finds uncovered retiring identifiers
- **THEN** the traceability report carries those identifiers in a field separate from its uncovered identifiers

#### Scenario: No change name stays strict

- **WHEN** the check runs without a change name against a tree whose only uncovered requirement is retired by an active change
- **THEN** the retiring set is empty, that requirement is listed as uncovered, and the check exits nonzero

#### Scenario: Unknown or malformed change name exits 2

- **WHEN** the supplied change name contains characters outside lowercase letters, digits, and hyphens, or names no active change directory
- **THEN** the check exits with status 2 and produces no traceability report

#### Scenario: Change without delta specs retires nothing

- **WHEN** the named active change has no delta spec files
- **THEN** the retiring set is empty

### Requirement: Pre-archive gates forward the change name only to traceability

The contract gate SHALL accept `--change <name>` or `--change=<name>` exactly once
and forward it only to the traceability gate. The pre-archive phase of the archive
gate script SHALL pass a supplied change name to that check. Malformed, empty, or
duplicated change arguments MUST exit 2 before any gate runs.

#### Scenario: Change reaches only the traceability check

- **WHEN** the contract gate selects traceability with `--change <name>` or `--change=<name>`
- **THEN** the traceability invocation receives `--change <name>` and the gate's other invocations remain unchanged

#### Scenario: Malformed change argument is rejected before any gate

- **WHEN** `--change` has no value, has an empty or option-looking value, or is given more than once
- **THEN** the contract gate exits 2 and runs no gate

#### Scenario: Strict check without a change name

- **WHEN** the contract gate selects traceability without `--change`
- **THEN** it invokes the strict traceability check with no change argument

#### Scenario: Archive-gate phases split by sync

- **WHEN** the archive gate script runs its pre-archive phase with a change name and later its post-archive phase
- **THEN** the pre-archive phase runs the traceability check with `--change <change>` and the post-archive phase runs it without one

