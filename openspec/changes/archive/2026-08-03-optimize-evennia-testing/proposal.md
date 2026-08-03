## Why

The full Evennia suite remains the main local feedback bottleneck even after duplicate CI discovery was removed: database setup, deliberately expensive production password hashing, and broad use of `EvenniaTest` add avoidable cost to repeated development runs. The project needs measured, repository-specific optimization that shortens feedback without weakening isolation, requirement evidence, browser acceptance, or the aggregate coverage gate.

## What Changes

- Establish a reproducible timing baseline and an inventory of slow tests before changing runner or fixture behavior.
- Add an explicit test-only Evennia settings module with a fast password hasher and a reusable file-backed SQLite test database suitable for `--keepdb`; production settings remain unchanged.
- Define supported focused, full, and profiling commands, including when retained databases must be rebuilt and when parallel execution is unsafe.
- Make the explicit managed browser command the sole owner of `web/tests/browser/`, retain `web.webclient` under the non-browser Evennia command, collect each owner's coverage once, and remove duplicate browser discovery.
- Optimize only measured hot test classes by replacing unnecessary full-world `EvenniaTest` fixtures with lighter test bases, pure `unittest.TestCase` tests, mocks, or class-level data where test independence can be proven.
- Evaluate parallel execution against the full non-browser Evennia suite and adopt it only if repeated runs preserve correctness, isolation, traceability evidence, coverage inputs, and a material wall-clock improvement.
- Preserve the separately managed browser suite, Node suite, top-level regression suite, strict OpenSpec validation, requirement-evidence verification, exact production coverage roots, aggregate 90% branch gate, and Codecov publication.
- Record before-and-after timings and guard the test-only configuration and canonical commands with repository contract tests.

## Capabilities

### New Capabilities

- `evennia-test-optimization`: Defines measured performance baselines, isolated test settings, supported execution profiles, safe fixture optimization, and acceptance criteria for faster Evennia testing.

### Modified Capabilities

- `webclient-browser-verification`: Clarifies that browser acceptance remains a separate serial managed-server suite and is excluded from any general Evennia parallelization profile.

## Impact

The change affects test settings under `server/conf/`, selected package-local tests identified by profiling, test workflow documentation in `AGENTS.md`, `README.md`, and development docs, repository contract tests under `tests/`, and coverage ownership in `.github/workflows/quality-gate.yml`. It adds no runtime dependency, game-state migration, production behavior change, or backward-compatibility layer.
