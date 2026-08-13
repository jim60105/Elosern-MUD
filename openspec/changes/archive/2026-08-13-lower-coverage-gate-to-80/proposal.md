## Why

The aggregate branch-coverage gate sits at exactly the enforced 90%, and every
landed change that adds feature code must first spend effort pushing the
combined report back over the line — the last green run before
`stabilize-and-accelerate-quality-gate` measured exactly 90% with zero
headroom. Coverage as a hard gate should catch regressions, not demand
near-exhaustive branch coverage for every feature landing. This change moves
the enforced gate down to 80% — a deliberately comfortable regression floor —
while keeping 90% as the documented aspirational target ("good to have") so
the project still steers toward high coverage without CI failing on temporary
dips.

## What Changes

- Lower the enforced aggregate branch-coverage threshold from 90% to 80% in
  `pyproject.toml` (`[tool.coverage.report] fail_under = 80`) and in the
  quality-gate workflow (`coverage report --fail-under=80`).
- Keep 90% as the documented project target, not enforced by CI: repository
  documentation and the spec contract state the 80% hard gate and the 90%
  target side by side.
- Update the coverage-gate contract tests (`tests/test_quality_gate_contract.py`,
  `tests/test_evennia_test_optimization_contract.py`) to pin `fail_under = 80`
  and `--fail-under=80`.
- Update `AGENTS.md` and development documentation that describe the gate to
  state the 80% hard gate and the 90% target.
- Update the main-spec requirements that currently mandate "at least 90%"
  aggregate branch coverage to mandate the 80% hard gate with the 90% target.
- No change to coverage scope: sources, omission policy, coverage roots,
  evidence verification, aggregation-missing-artifact failures, Codecov
  publication, or any other gate.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spec-test-traceability`: The enforced aggregate branch-coverage threshold
  changes from 90% to 80%; the 90% figure becomes a documented target instead
  of a CI gate.
- `evennia-test-optimization`: "Existing quality gates remain authoritative"
  changes its aggregate branch-coverage enforcement from 90% to 80% and its
  equivalence scenario language accordingly.
- `webclient-browser-verification`: The mandatory-gate requirement changes its
  reference to the "aggregate 90% branch-coverage gate" to the 80% gate.

## Impact

- `.github/workflows/quality-gate.yml` — the `--fail-under=90` flag in the
  "Enforce aggregate coverage threshold" step becomes `--fail-under=80`.
- `pyproject.toml` — `[tool.coverage.report] fail_under` becomes `80`.
- `tests/test_quality_gate_contract.py` and
  `tests/test_evennia_test_optimization_contract.py` — assertions pin the new
  threshold and the documented 90% target.
- `AGENTS.md`, `docs/development/spec-test-traceability.md`,
  `docs/development/evennia-testing-guide.md`, and
  `docs/development/evennia-test-performance.md` — wording of the gate
  threshold. Historical records (archived OpenSpec changes and dated
  `docs/superpowers/specs/*.md` design documents) are intentionally left
  untouched.
- `openspec/specs/spec-test-traceability/spec.md`,
  `openspec/specs/evennia-test-optimization/spec.md`, and
  `openspec/specs/webclient-browser-verification/spec.md` — requirement text
  amended by this change's delta specs.
- No dependency, API, schema, or data changes. The project is unreleased with
  zero users; no backward-compatibility layer or migration is needed.
