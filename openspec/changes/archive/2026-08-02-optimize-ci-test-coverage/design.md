## Context

The quality gate currently runs `coverage run -m evennia test --settings settings.py .` and then `coverage run -m unittest discover tests`. Django's `DiscoverRunner`, which Evennia's `EvenniaTestSuiteRunner` subclasses, recursively discovers tests beneath each supplied label. The repository-root label therefore collects package-local game tests and the top-level `tests/` contract suite; the second command intentionally collects the top-level suite again. The observed CI run executed 990 tests in 892 seconds before entering the second test command.

Both commands also write successful OpenSpec execution evidence and separate coverage data files. Those files are combined, checked for the exact production roots, and subjected to the 90% gate. The optimization must preserve those semantics while making test ownership disjoint. The same combined data can produce `coverage.xml` for Codecov after local verification succeeds.

Codecov is an external reporting integration. The repository provides a `CODECOV_TOKEN` GitHub Actions secret for authentication, and explicit file selection prevents accidental upload of intermediate or unrelated reports. The secret must be configured before the upload step is enabled; its value is never committed to the repository.

## Goals / Non-Goals

**Goals:**

- Execute every package-local project test and every top-level repository contract test exactly once in CI.
- Preserve evidence-aware OpenSpec traceability and the existing aggregate 90% branch-coverage gate.
- Upload the same verified aggregate coverage represented by the local gate to Codecov.
- Make the current Codecov result visible from `README.md`.
- Keep local documentation and workflow contract tests aligned with CI.

**Non-Goals:**

- Parallelize Evennia tests or redesign database-heavy `EvenniaTest` fixtures.
- Split the quality gate into a matrix or change the 90% threshold and production source roots.
- Replace Codecov's reporting with its own independent coverage policy.
- Change game behavior, data, migrations, or compatibility policy.

## Decisions

### Use explicit production roots as Evennia test labels

The Evennia command will target `commands server typeclasses web world` instead of `.`. These are the complete first-party production roots already established by the coverage contract, and their package-local tests remain discoverable by Evennia. The top-level `tests` directory remains solely owned by `python -m unittest discover -s tests -t .`, which preserves the canonical `tests.*` module identities used by traceability evidence.

This is preferred over deleting the second command because top-level tests are repository-wide contracts and include checks that intentionally do not require the Evennia runner. It is preferred over excluding paths through discovery internals because explicit labels use the supported Django/Evennia interface and are transparent in CI and local documentation.

The workflow contract test will assert the exact labels and reject the repository-root label. It will also continue to assert both separate coverage files and their unconditional combination. This catches a future regression that silently restores duplicate discovery.

### Preserve one shared execution-evidence stream

Both now-disjoint commands will continue to receive the same `OPENSPEC_TEST_EVIDENCE` path. Verification remains after both commands, so annotated tests in either ownership domain can satisfy requirements only after successful execution.

No annotation movement is expected: narrowing the first command only removes top-level tests that are still collected by the second command.

### Export Codecov XML only after aggregate verification

After `coverage combine`, source-root verification, and `coverage report --fail-under=90`, CI will run `coverage xml -o coverage.xml` and upload only that file. Producing XML from the combined data guarantees Codecov receives both entry points rather than either intermediate `.coverage.*` file.

The upload will use the official `codecov/codecov-action` v5.5.5 release pinned to commit `0fb7174895f61a3b6b78fc075e0cd60383518dac`, with `token: ${{ secrets.CODECOV_TOKEN }}`, `files: ./coverage.xml`, `disable_search: true`, and `fail_ci_if_error: true`. The workflow keeps `contents: read` and does not request OIDC permissions. Explicit upload failure keeps the requested publication contractual rather than best-effort, while the secret reference avoids placing the token in repository files.

Codecov remains non-authoritative for coverage measurement: the repository's local `coverage report --fail-under=90` step runs before upload, so an external policy cannot substitute a different calculation. Successful publication is nevertheless a mandatory CI availability dependency; a Codecov outage will fail the job by design.

### Use the repository-specific Codecov badge

The remote's configured default branch is `master`. Because `jim60105/MUD` is private, implementation will copy the repository-specific `master` badge snippet generated by Codecov, including Codecov's badge-display token parameter, and link it to the repository's Codecov page. The badge-display token is distinct from upload authentication; no upload token or GitHub credential may appear in the README.

The badge is presentation only; CI tests will verify its repository identity and destination, not fetch the external image.

## Risks / Trade-offs

- [A package-local test is added outside the five explicit roots] → The project architecture and coverage source contract already restrict production code to those roots; document that top-level `tests/` is only for repository-wide contracts and enforce the exact root set in the workflow test.
- [Explicit labels behave differently from root discovery] → Run the focused workflow contract tests and compare discovery/execution totals in a CI run; successful traceability verification also detects annotated tests that became uncollected.
- [Codecov is not configured or the secret is invalid] → Configure `CODECOV_TOKEN` before landing the hard gate. Let `fail_ci_if_error` expose later authentication or publication regressions. Roll back only the publication step if external setup cannot be completed, without reverting the test-discovery optimization.
- [Codecov reports a value different from the local gate] → Upload only `coverage.xml` generated from the verified combined file and disable action file search.
- [The private badge leaks upload credentials] → Use only Codecov's generated badge-display token; never place `CODECOV_TOKEN`, a GitHub token, or another upload credential in README content.
- [The branch-specific badge becomes stale after the default branch changes] → Update the generated snippet as part of any default-branch rename.

## Migration Plan

1. Confirm the `CODECOV_TOKEN` repository secret, `master` as the configured default branch, and the Codecov project for `jim60105/MUD`.
2. Resolve the v5.5.5 release tag to its reviewed commit SHA. Update contract tests to require disjoint labels, aggregate XML generation, the immutable explicit Codecov upload, secret-based authentication, and Codecov's generated private-repository README badge.
3. Update the workflow and local documentation, then run static traceability checks and focused contract tests.
4. Run both revised entry points with one evidence file, combine coverage, verify source roots and threshold, and generate XML.
5. Push the branch and confirm both push and same-repository pull-request runs report the expected reduced Evennia test count and a successful Codecov upload.

Rollback is configuration-only: restore the repository-root Evennia label if any package tests are proven missing, or remove the Codecov upload/badge if the repository secret or external project cannot be completed. Neither rollback requires data recovery.

## Open Questions

None. External Codecov onboarding results are explicit prerequisites; if they cannot be satisfied, implementation must stop before enabling the mandatory upload.
