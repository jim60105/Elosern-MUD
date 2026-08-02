## 1. Confirm Codecov prerequisites

- [x] 1.1 Confirm the `CODECOV_TOKEN` repository secret, configure `master` as the default branch, and confirm the Codecov project for `jim60105/MUD`.
- [ ] 1.2 Confirm that the configured secret is available to same-repository push and pull-request quality-gate runs before relying on Codecov publication as a hard dependency.
- [x] 1.3 Resolve the `codecov/codecov-action` v5.5.5 release tag to the reviewed immutable commit SHA `0fb7174895f61a3b6b78fc075e0cd60383518dac`.

## 2. Lock the CI contracts

- [x] 2.1 Update `tests/test_quality_gate_contract.py` to require the exact disjoint Evennia labels, retain the dedicated top-level command, and reject repository-root discovery.
- [x] 2.2 Add contract assertions for aggregate XML generation after the local 90% gate, the immutable Codecov v5 action pin, the repository secret reference, explicit report settings, and fail-on-upload-error behavior.
- [x] 2.3 Add a repository contract assertion that `README.md` contains Codecov's generated private-repository badge and link for `jim60105/MUD` on `master`, without containing an upload credential.

## 3. Optimize and publish the quality gate

- [x] 3.1 Replace the Evennia repository-root test label in `.github/workflows/quality-gate.yml` with `commands server typeclasses web world`, preserving the shared traceability-evidence path and separate coverage files.
- [x] 3.2 Generate `coverage.xml` from the combined, source-root-verified data only after the aggregate 90% report gate succeeds.
- [x] 3.3 Add the immutable Codecov v5 action configured with `secrets.CODECOV_TOKEN`, `coverage.xml` only, disabled report search, and `fail_ci_if_error: true`.

## 4. Documentation and badge

- [x] 4.1 Update `docs/development/spec-test-traceability.md` and applicable `AGENTS.md` commands to document disjoint test ownership and the exact revised local aggregate sequence.
- [x] 4.2 Add Codecov's generated private-repository `master` coverage badge and repository link near the top of `README.md`.

## 5. Verification

- [x] 5.1 Run `uv run --locked python -m tools.spec_traceability check`, the focused quality-gate contract tests, `openspec validate optimize-ci-test-coverage --strict`, and `git diff --check`.
- [x] 5.2 Run the revised Evennia package suite and top-level repository suite with one evidence path and separate coverage files; verify successful requirement evidence, combine coverage, verify source roots, enforce 90%, and generate `coverage.xml`.
- [ ] 5.3 Push the branch and confirm both push and same-repository pull-request runs execute package-local and top-level tests once each, upload the aggregate report successfully, and resolve the README badge to that Codecov result.
