## Why

The quality gate runs on every push and PR and takes ~20 minutes of wall time.
The `evennia` job alone is **14m 02s** (measured run 31939321935,
2026-08-16): one `ubuntu-latest` runner executing the whole non-browser
Evennia suite (~3,104 tests) with `--parallel 4` and subprocess coverage. The
repository is on the GitHub public Free plan: `ubuntu-latest` machines are
free and unlimited in number, but only **20 jobs may run concurrently** and
larger (paid) runners are out of scope. The suite's total CPU time fits
comfortably on a handful of machines — the bottleneck is that it currently
uses one. Sharding the evennia suite across six matrix jobs (one machine
each, `--parallel 4` internally) cuts this job to ~2–4 minutes and off the
CI critical path, at zero cost.

## What Changes

- New `.github/evennia-shards.json` manifest: six shards owning disjoint
  label sets (`world.rules` split into three file groups; the remaining
  packages in three groups), each with `index`, `name`, and `labels`.
- `preflight` computes an `evennia-shards` matrix output from the manifest
  (mirroring the existing `browser-shards` output).
- The `evennia` job becomes a matrix job: each shard runs its labels with
  `coverage run --concurrency=multiprocessing --parallel-mode -m evennia test
  --settings test_settings.py --noinput --parallel 4`, writing
  `coverage-evennia-shard-<n>*` and `evidence.evennia-shard-<n>.jsonl`, and
  uploads them as per-shard artifacts.
- The gate job validates every evennia shard's artifacts (loop over manifest
  indices), concatenates `evidence.evennia-shard-*.jsonl` with the browser
  and top-level evidence, and combines `coverage-evennia*` with the other
  coverage files — aggregation semantics unchanged.
- Top-level contract tests pin the new structure: an evennia-shard manifest
  ownership test (every non-browser test module under `commands`, `server`,
  `typeclasses`, `world`, `web.webclient` owned by exactly one shard) and
  updated workflow-structure assertions.
- Documentation (`AGENTS.md`, `docs/development/evennia-testing-guide.md`,
  `docs/development/evennia-test-performance.md`) updated to describe the
  sharded CI and to state that shard commands are CI-only (each invocation
  uses the same local test database path and must never run concurrently on
  one machine).
- Measured rebalance: per-shard serial timings recorded locally, one
  rebalance pass on the first CI run if any shard dominates.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: "Existing quality gates remain authoritative"
  is extended so the non-browser Evennia suite MAY be distributed across
  parallel CI jobs by manifest-owned labels (each test module has exactly one
  serial execution owner), keeping the aggregation and coverage gates
  identical. A new requirement "Machine shards preserve exact per-module
  test ownership" is added to the same capability.

## Impact

- `.github/workflows/quality-gate.yml` — evennia job → matrix job; preflight
  output; gate artifact validation/completeness loop.
- `.github/evennia-shards.json` — new manifest.
- `tests/test_quality_gate_contract.py`,
  `tests/test_evennia_test_optimization_contract.py`,
  `tests/test_browser_verification_contract.py` — workflow-contract pins
  updated/added.
- `docs/development/evennia-testing-guide.md`,
  `docs/development/evennia-test-performance.md`, `AGENTS.md` — CI structure
  descriptions.
- No production code, no player-facing commands, no test behavior changes.
- Follow-up change `pack-browser-ci-shards` builds the browser half of the
  sharding on top of this structure.
