## MODIFIED Requirements

### Requirement: Continuous integration enforces both quality dimensions
GitHub Actions MUST run strict OpenSpec validation, complete requirement
traceability verification, the full project test suite, and aggregate
first-party code coverage on pushes and pull requests. Package-local project
tests and top-level repository contract tests MUST have disjoint discovery
ownership and each test MUST execute exactly once. The workflow MUST fail if
any test fails, any requirement lacks a test association, aggregate code
coverage is below 90%, or publication of a successful aggregate report fails.
Workflow enablement MUST be blocked until an initial audit proves zero
requirement gaps without adding product-behavior tests in this change.

#### Scenario: Requirement traceability regression fails CI
- **WHEN** a main-spec requirement is added without a valid test association
- **THEN** the continuous-integration job fails and identifies that requirement

#### Scenario: Code coverage regression fails CI
- **WHEN** all tests pass but aggregate measured first-party coverage is below 90%
- **THEN** the continuous-integration job fails at the coverage report step

#### Scenario: Package and repository tests execute once
- **WHEN** the quality gate runs the complete project suite
- **THEN** the Evennia entry point discovers package-local tests only from `commands`, `server`, `typeclasses`, `web`, and `world`
- **AND** the separate top-level entry point discovers repository contract tests from `tests`
- **AND** neither entry point discovers tests owned by the other

#### Scenario: Offline deterministic suite passes all gates
- **WHEN** strict specs, annotations, tests, and aggregate coverage satisfy their local gates without generative services
- **THEN** the continuous-integration job reaches external coverage publication

### Requirement: Coverage configuration is reproducible and project-scoped
Coverage measurement MUST use the locked project environment, enable branch
coverage, unconditionally combine data from the disjoint Evennia package suite
and top-level regression suite, and measure exactly the first-party production
roots `commands`, `server`, `typeclasses`, `web`, and `world`. Only test
implementation modules under `*/tests/*` MAY be omitted from those roots for
the 90% calculation. The combined data MUST be the sole source for the local
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
- **THEN** the same source, branch, omission, entry-point ownership, and 90% rules used by CI apply

#### Scenario: Published report matches the verified aggregate
- **WHEN** both test entry points pass and their coverage data satisfies local verification
- **THEN** CI generates the Codecov XML report from that combined data
- **AND** it does not upload either intermediate coverage data file as an independent report

## ADDED Requirements

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
