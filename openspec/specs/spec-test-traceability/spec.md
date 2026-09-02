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
The CI verification command MUST fail when any indexed main-spec requirement has
no valid and successfully executed unit-test or integration-test association.
It MUST report all uncovered requirements in deterministic order and MUST NOT
support a baseline, waiver, or allowlist that converts a gap into success.

#### Scenario: Complete traceability passes
- **WHEN** every indexed requirement has at least one valid test annotation with matching successful execution evidence and no verification error exists
- **THEN** verification exits successfully and reports requirement and association totals

#### Scenario: Every gap is reported
- **WHEN** one or more indexed requirements have no valid test annotation
- **THEN** verification exits nonzero and lists every uncovered requirement with its spec source location

#### Scenario: Existing test coverage is reused without fabricating tests
- **WHEN** the initial audit finds an existing test whose assertions cover a requirement
- **THEN** that test may be annotated without changing its assertions or behavior

### Requirement: Continuous integration enforces both quality dimensions
GitHub Actions MUST run strict OpenSpec validation, complete requirement
traceability verification, the observability lint gate, the full project test
suite, and aggregate
first-party code coverage on pushes and pull requests. Package-local project
tests and top-level repository contract tests MUST have disjoint discovery
ownership and each test MUST execute exactly once. The workflow MUST fail if
any test fails, any requirement lacks a test association, the observability
lint check reports any violation, aggregate code coverage is below 80%, or
publication of a successful aggregate report fails.
The project SHALL target aggregate branch coverage of at least 90% as a
documented goal; that target MUST NOT be enforced by CI.
Workflow enablement MUST be blocked until an initial audit proves zero
requirement gaps without adding product-behavior tests in this change.

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

### Requirement: Coverage configuration is reproducible and project-scoped
Coverage measurement MUST use the locked project environment, enable branch
coverage, unconditionally combine data from the disjoint Evennia package suite
and top-level regression suite, and measure exactly the first-party production
roots `commands`, `server`, `typeclasses`, `web`, and `world`. Only test
implementation modules under `*/tests/*` MAY be omitted from those roots for
the 80% calculation. The combined data MUST be the sole source for the local
threshold, source-root verification, and externally published XML report.

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

### Requirement: Aggregate coverage is published to Codecov
After all local test, traceability, source-root, and coverage-threshold gates
succeed, GitHub Actions SHALL upload the explicit combined XML report to the
`jim60105/Elosern-MUD` Codecov project using an immutable v5 release of the official
Codecov action and the configured `CODECOV_TOKEN` repository secret.
The action MUST disable automatic report discovery and MUST fail the CI job when
the requested upload fails. `README.md` SHALL display a Codecov badge linked to
that repository's Codecov page and scoped to the configured default branch.

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

