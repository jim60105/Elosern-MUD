## Why

OpenSpec defines the project's behavioral contract, but the repository has no
machine-checkable link between its requirements and the tests that claim to
exercise them. Code coverage alone cannot detect an untested requirement, and
the current test commands have no enforced coverage threshold in continuous
integration.

## What Changes

- Introduce stable, repository-derived requirement identifiers and a lightweight
  annotation that associates an existing unit or integration test with one or
  more OpenSpec requirements and records successful execution in CI.
- Add a deterministic verification script that parses the main OpenSpec specs,
  test source, and CI execution evidence; rejects invalid or ambiguous
  annotations; and fails when any current requirement has no successfully
  executed associated test.
- Annotate existing tests where they already provide requirement coverage. This
  change does not add product-behavior tests; genuine gaps remain visible and
  must be filled by the change that owns that behavior.
- Add GitHub Actions continuous integration, enabled only after the initial audit
  reaches zero genuine gaps, that runs strict OpenSpec and requirement-
  traceability validation, both required test entry points, and an aggregate
  project-code coverage gate of at least 90%.
- Add the coverage measurement tool as a locked development dependency and
  centralize coverage scope and omission policy in project configuration.

## Capabilities

### New Capabilities

- `spec-test-traceability`: Defines requirement identity, test annotations,
  complete traceability validation, diagnostics, and the CI quality gates.

### Modified Capabilities

None. Existing gameplay and infrastructure requirements retain their current
behavioral contracts.

## Impact

The change affects test-source metadata, a repository-local verification tool,
`pyproject.toml`, `uv.lock`, and a new GitHub Actions workflow. It adds no game
runtime behavior, persistence changes, compatibility layer, migration, or live
service dependency. Contributors must associate each new or changed OpenSpec
requirement with a real test before CI can pass. Static annotation is evidence
of traceability, and a successful execution record from the test run proves that
the named test was collected, was not skipped, and passed. If the initial audit
finds a genuine gap, this change pauses before workflow enablement and hands the
gap to the behavior change that owns the missing test.
