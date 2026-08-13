## 1. Lower the enforced coverage gate

- [x] 1.1 Change `[tool.coverage.report] fail_under` from `90` to `80` in `pyproject.toml`.
- [x] 1.2 Change the "Enforce aggregate coverage threshold" step in `.github/workflows/quality-gate.yml` from `coverage report --fail-under=90` to `coverage report --fail-under=80`.

## 2. Update contract tests

- [x] 2.1 Update `tests/test_quality_gate_contract.py` to assert `--fail-under=80` in the workflow and `fail_under == 80` in `pyproject.toml`, keeping the `covers_requirement` annotations on the amended tests.
- [x] 2.2 Update `tests/test_evennia_test_optimization_contract.py` to assert `fail-under=80` in the gate step.
- [x] 2.3 Add a contract-test assertion in `tests/test_quality_gate_contract.py` that the documentation (`docs/development/spec-test-traceability.md`, `AGENTS.md`) states the 90% coverage target while the workflow and project configuration enforce 80%, substantively covering the "Coverage target remains visible without enforcement" scenario.
- [x] 2.4 Extend a test in `tests/test_browser_verification_contract.py` annotated for `webclient-browser-verification::node-and-playwright-checks-are-mandatory-quality-gate-steps` to assert the "Enforce aggregate coverage threshold" step runs `--fail-under=80`.

## 3. Update documentation and agent guidance

- [x] 3.1 Update `AGENTS.md` to state the 80% hard coverage gate and the 90% documented target.
- [x] 3.2 Update `docs/development/spec-test-traceability.md` coverage-command and gate wording to `--fail-under=80` and the 90% target.
- [x] 3.3 Update `docs/development/evennia-testing-guide.md` gate wording to 80% in Traditional Chinese, preserving the zh-TW style.
- [x] 3.4 Update `docs/development/evennia-test-performance.md` gate wording to 80%.

## 4. Verify

- [x] 4.1 Run `uv run --locked python -m unittest discover -s tests -t .` and confirm the updated contract tests pass.
- [x] 4.2 Run `uv run --locked python -m tools.spec_traceability check` and `openspec validate lower-coverage-gate-to-80 --strict`.
- [x] 4.3 Run `rg -n --glob '!openspec/changes/archive/**' --glob '!docs/superpowers/specs/**' --glob '!tmp/**' 'fail-under=90|fail_under = 90|fail_under == 90|coverage is below 90|at least 90%|90% branch|90% gate|90% rules|90% calculation|90% aggregate' .`, confirm every remaining match is an intentional 90% target reference (or historical record), and run `git diff --check`.
