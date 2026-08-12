## Why

The quality-gate workflow spends about fifteen minutes running 990 tests because its broad Evennia discovery target (`.`) also collects the repository-wide top-level contract tests, which CI immediately executes a second time through their dedicated entry point. CI should preserve the complete project and traceability gates without duplicate discovery, and its already-generated aggregate coverage should be published where contributors can inspect it.

## What Changes

- Replace repository-root Evennia test discovery with explicit production-package test labels so package-local game tests still run once while top-level repository contract tests remain owned by their separate command.
- Keep both test entry points, successful-execution evidence collection, coverage-file combination, source-root verification, and the 90% aggregate threshold intact.
- Generate a standard coverage XML report from the verified combined data and upload that exact aggregate report to Codecov from GitHub Actions using the configured repository secret.
- Add a Codecov coverage badge for `jim60105/Elosern-MUD` to `README.md`.
- Update local quality-gate documentation and workflow contract tests to describe and enforce the non-overlapping test ownership and Codecov publication steps.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spec-test-traceability`: Require non-overlapping CI test entry points that retain complete project coverage, and require publication of the verified aggregate coverage report to Codecov with a README status badge.

## Impact

- Affected workflow: `.github/workflows/quality-gate.yml`.
- Affected quality-gate contract and guidance: `openspec/specs/spec-test-traceability/spec.md`, `tests/test_quality_gate_contract.py`, `docs/development/spec-test-traceability.md`, and the test commands documented in `AGENTS.md` where applicable.
- Affected project presentation: `README.md` gains the Codecov badge.
- External integration: the repository must provide `CODECOV_TOKEN` as a GitHub Actions secret; the workflow will use an immutable v5 release of the official Codecov action and fail when publication of a successful combined report fails.
- No game behavior, persistence model, backward compatibility, or migration work is involved.
