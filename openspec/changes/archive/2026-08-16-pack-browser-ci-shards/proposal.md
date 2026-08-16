## Why

The browser matrix is the CI critical path: shard 1 (combat) takes
**19m 09s** and the other shards range from 4m 42s to 17m 24s (run
31939321935). Combat tests boot a dedicated Evennia server per test (~50 s
each), so per-test cost is what matters — and the manifest can only split at
file granularity, so the 19 combat tests in one class cannot be spread out.
The GitHub public Free plan caps concurrent jobs at 20 and offers unlimited
free `ubuntu-latest` machines, but no larger (paid) runners. Packing each
browser job with **two isolated test processes** (two checkouts on the same
runner) doubles effective browser parallelism inside the 20-job budget, and
moving the manifest to class/method-level labels lets the combat tests spread
across many shards. Together with the evennia machine sharding
(`split-evennia-ci-shards`), this cuts the critical path from ~19 min to
~5–6 min.

## What Changes

- `.github/browser-shards.json` is rewritten: 11 shards, each with two label lists
  `files_a`/`files_b` (module, class, or method dotted labels). Every
  test method of every `web/tests/browser/test_*.py` file is owned by exactly
  one of the 22 process lists; combat methods are split at method level and
  spread across ~5 lists of 4–5 tests; single-class files
  (`test_browser_exploration.py`, `test_browser_art.py`) split at method level,
  multi-class files (`test_browser_creation.py`, `test_browser_services.py`)
  split at class level, and the cheap shell-family files pack whole into one or
  two lists; every process list targets ≤ 240 s estimated runtime.
- The `browser` job checks out the repository **twice** (`path: w-a`,
  `path: w-b`), syncs both, installs Chromium once (shared
  `~/.cache/ms-playwright`), and runs the two `unittest` invocations in
  parallel background processes with distinct inline
  `COVERAGE_FILE=coverage-browser-shard-<n>-p1|-p2` and
  `OPENSPEC_TEST_EVIDENCE=evidence.browser-shard-<n>-p1|-p2.jsonl`; the job
  concatenates the two evidence files per shard before uploading. Two
  checkouts are required because the Evennia launcher writes
  `server/server.pid`/`portal.pid` at GAMEDIR-relative paths and two harnesses
  in one working tree would corrupt each other's process tracking.
- The gate's artifact checks, evidence concatenation, and coverage combine
  stay index-based and work unchanged (per-shard files keep the
  `coverage-browser-shard-<n>*` and `evidence.browser-shard-<n>.jsonl`
  names).
- Top-level contract tests are updated: the browser manifest ownership test
  becomes a **method-level partition** check (AST-based, import-free), and
  the workflow-structure assertions cover the two-workspace job.
- Measured rebalance: manifest composed from CI-derived per-test weights
  (combat ~50 s, creation ~38 s, services/pointer ~47 s, shell-family ~6.4 s)
  targeting ≤ 240 s per process list, then one CI-observed rebalance pass.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: "Existing quality gates remain authoritative"
  gains the browser two-process/separate-checkout and method-level-ownership
  sentences (written as the complete final requirement text, identical to the
  `split-evennia-ci-shards` delta so archive order does not matter). A new
  requirement "Browser method labels preserve exact ownership" is added to
  the same capability.

## Impact

- `.github/browser-shards.json` — rewritten with `files_a`/`files_b` and
  method/class-level labels.
- `.github/workflows/quality-gate.yml` — browser job steps (two checkouts,
  two background processes, evidence concatenation, artifact paths).
- `tests/test_browser_verification_contract.py`,
  `tests/test_evennia_test_optimization_contract.py` — method-level manifest
  contract and workflow assertions.
- `docs/development/evennia-testing-guide.md`,
  `docs/development/evennia-test-performance.md`, `AGENTS.md` — CI structure
  descriptions.
- No production code, no harness code (`web/tests/browser/harness.py`,
  `fixtures.py`, `browser_base.py` stay untouched — the two-checkout design is
  the isolation mechanism), no test behavior changes.
