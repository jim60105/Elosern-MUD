## 1. Traceability Model and Verifier

- [x] 1.1 Add the behavior-preserving `covers_requirement` decorator with support for one or more literal requirement IDs and CI-only successful-execution evidence.
- [x] 1.2 Implement main-spec parsing, canonical ID normalization, source-location reporting, and collision detection.
- [x] 1.3 Implement static test-annotation discovery and reject unknown IDs, dynamic arguments, invalid imports, and non-test placement.
- [x] 1.4 Add deterministic list, static-check, JSON-report, and evidence-aware CI verification modes with a nonzero exit for every uncovered requirement or annotation error and no waiver mechanism.

## 2. Existing-Test Traceability Audit

- [x] 2.1 Generate the complete current requirement inventory and associate only existing tests whose assertions substantively cover each requirement.
- [x] 2.2 Add decorator annotations to those existing unit and integration tests without changing their assertions, fixtures, or runtime behavior.
- [x] 2.3 Run both required test entry points with evidence collection and require every static association to have a matching successful execution before it counts.
- [x] 2.4 Treat a zero-gap audit as a prerequisite for the remaining tasks; on any genuine gap, emit the deterministic JSON report, pause this change before workflow enablement, and hand the gap to its owning behavior change without adding tests here.

## 3. Coverage and Continuous Integration

- [x] 3.1 After the zero-gap prerequisite passes, add Coverage.py as a locked development dependency and configure branch measurement for exactly `commands`, `server`, `typeclasses`, `web`, and `world`, omitting only `*/tests/*`, with `fail_under = 90` in `pyproject.toml`.
- [x] 3.2 Add a GitHub Actions workflow for pushes and pull requests that installs the pinned Python and `uv` environment, validates OpenSpec strictly, and runs traceability verification.
- [x] 3.3 Run the full Evennia suite and top-level regression suite unconditionally under distinct coverage data files in CI, combine both named files, assert the combined report covers every configured source root, and enforce the aggregate 90% threshold.

## 4. Verification and Handoff

- [x] 4.1 Exercise successful and failing verifier paths with temporary fixture repositories, including collisions, stale IDs, invalid placement, dynamic arguments, uncovered requirements, and skipped or uncollected annotated tests, without adding product-behavior tests.
- [x] 4.2 Run `openspec validate enforce-spec-test-coverage --strict`, the repository traceability verifier, `git diff --check`, and the exact locked CI test and coverage commands locally.
- [x] 4.3 Document the annotation format, local quality-gate commands, scope exclusion, and the rule that annotations cannot substitute for a genuine behavior test.
