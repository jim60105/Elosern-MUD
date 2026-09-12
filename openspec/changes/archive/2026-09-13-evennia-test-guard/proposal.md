# Proposal: OMP Evennia Test Guard

## Why

AGENTS.md already mandates running the smallest focused test label and forbids local commands estimated above 10 minutes, but nothing enforces it mechanically: an agent can still fire `evennia test` against the whole suite and burn a long, database-heavy run. Broad discovery in this repo (Evennia 6.1.0 / Python 3.13, uv-managed) routinely pulls in hundreds of tests, which is exactly the workflow the project rules prohibit. This change mechanizes that rule with a pre-execution guard in the OMP harness itself.

## What Changes

- Add an OMP `ExtensionAPI` extension at `.omp/extensions/evennia-test-guard/` (auto-discovered by OMP from `<cwd>/.omp/extensions/`; no `config.yml` needed) that registers a `tool_call` (pre-execution) handler on the Bash tool.
- The guard detects `evennia test` invocations — including `uv run` / `poetry run` wrappers (with runner flags such as `uv run --locked`, the repo-canonical form) and `cd ... &&` prefixes — and, before the original command runs, performs count-only Django test discovery via a count-only test runner (`--testrunner=omp_evennia_count_runner.CountOnlyRunner`) that calls `setup_test_environment()` then `build_suite()` and prints the discovered count as a machine-readable marker, without creating databases or executing tests.
- If discovery finds more than `MAX_TESTS = 100` tests, the guard returns `{ block: true, reason }` with a "Run Focus Test" instruction and narrowed-label examples; if the count is ≤ 100, the original Bash command proceeds untouched.
- The guard is fail-closed: unsupported shell composition (`;`, `|`, redirects, multi-line, `bash -lc '...'` wrapping, non-`cd` prefixes, multiple `evennia test` segments, a caller-supplied `--testrunner`), discovery errors, timeouts, missing/invalid count markers all block the original command with an actionable reason.
- Add `omp_evennia_count_runner.py`, a count-only Django test runner that subclasses the configured `TEST_RUNNER` base (normally Evennia's `EvenniaTestSuiteRunner`) so discovery runs under the same environment as a real `evennia test`.

## Capabilities

### New Capabilities

- `evennia-test-guard`: Pre-execution guard for Bash-tool `evennia test` commands — command recognition, count-only discovery protocol, the ≤100-test allow/block policy with "Run Focus Test" guidance, and the fail-closed shell/discrimination policy.

### Modified Capabilities

- (none — this is a new developer-experience capability; `evennia-test-optimization` and AGENTS.md test rules stay as-is, and this guard mechanizes them without changing their specs)

## Impact

- New files only: `.omp/extensions/evennia-test-guard/index.ts` and `.omp/extensions/evennia-test-guard/omp_evennia_count_runner.py`. No game-code, settings, or test changes.
- Requires OMP launched from the repository root (project extension discovery is cwd-relative).
- Depends on OMP ExtensionAPI (`pi.on("tool_call")`, `pi.exec()`, `ctx.ui.notify`); each guarded `evennia test` adds one bounded (60 s timeout) discovery subprocess before the real run.
