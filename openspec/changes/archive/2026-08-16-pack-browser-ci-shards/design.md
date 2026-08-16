## Context

The browser matrix today: six jobs, one `unittest` process each, manifest
labels at file granularity (`.github/browser-shards.json`), per-shard
`COVERAGE_FILE=coverage-browser-shard-<n>` and
`OPENSPEC_TEST_EVIDENCE=evidence.browser-shard-<n>.jsonl`. Measured
durations (run 31939321935): combat 19m09s (23 tests, ~50 s each — each
combat test boots a dedicated `ManagedServer`), creation-layout 16m37s (~38
s/test), services-pointer 17m24s (~47 s/test), exploration-reconnect 13m12s
(~40 s/test), art-harness 11m23s (~36 s/test), shell-family 4m42s (~6.4
s/test). Total browser CPU ≈ 4,947 machine-seconds.

The harness (`web/tests/browser/harness.py`) already isolates everything per
process except the Evennia launcher pidfiles: `SERVER_PIDFILE`/`PORTAL_PIDFILE`
are GAMEDIR-relative (`server/server.pid`, `server/portal.pid`), fixed by the
vendored launcher (`evennia/server/evennia_launcher.py`). Two harnesses in one
working tree would race on those files and can kill each other's processes
(harness.py:178-243), so a second process on the same runner requires a
second checkout. The repository is small (~5 MB pack) — double checkout is
cheap.

## Goals / Non-Goals

**Goals:**
- Bring the slowest browser shard from ~19 min to ≤ ~6 min, and the total
  quality-gate wall time under 10 min when combined with
  `split-evennia-ci-shards`.
- Stay within the 20-concurrent-job ceiling: 1 preflight + 6 evennia (from
  the sibling change) + 11 browser + 1 top-level + 1 gate = 20.
- Spread the 23 combat tests (per-test server boot makes grouping irrelevant
  for them) across ~5 process lists; balance everything else by measured
  per-test weights.
- Preserve the per-shard aggregation contract (artifact completeness,
  evidence concatenation, coverage combine) exactly.

**Non-Goals:**
- Changing the harness or the per-test server-boot behavior (a "soft reset"
  harness optimization is tracked separately).
- Changing the evennia job structure (sibling change).
- Using larger/paid runners.

## Decisions

- **Method/class-level labels**: `python -m unittest` accepts
  `module.Class.method` and `module.Class` dotted labels, so the manifest can
  partition at any granularity. Combat tests (one class, 19 methods) split at
  method level; single-class files like `test_browser_exploration.py` (16
  methods) split at method level too; multi-class files
  (`test_browser_creation.py`, `test_browser_services.py`) split at class
  level; cheap files (shell family, ~6.4 s/test) pack whole into lists with
  leftovers.
- **Two checkouts per job**: `actions/checkout` with `path: w-a` / `path:
  w-b`; both run `uv sync --locked` (uv cache shared, parallel); Chromium
  installed once in `w-a` (browser binary lives in shared
  `~/.cache/ms-playwright`); each process runs with its own inline
  `COVERAGE_FILE`/`OPENSPEC_TEST_EVIDENCE`; the job waits on both, then
  concatenates the per-process evidence files into
  `evidence.browser-shard-<n>.jsonl`. Coverage files keep distinct names
  (`-p1`/`-p2`), so no `--parallel-mode` is needed and the "no `--parallel`
  in the browser run" contract stays true.
- **Manifest schema**: `{"shards": [{"index", "name", "files_a": [...],
  "files_b": [...]}]}`; ownership contract resolves labels via AST (no
  imports), so it is fast and safe.
- **Balance target**: every process list ≤ 240 s estimated test time
  (weights in "Context"); 22 lists over ~4,947 s ≈ 225 s mean.
- **Evidence semantics**: per-process JSONL files are concatenated per shard
  before upload; the gate's per-index checks and global concatenation are
  unchanged.
- **Concurrency accounting**: the GitHub Free ceiling of 20 applies to
  concurrent JOBS, not processes — the two browser processes share one job
  slot (one runner), so 1 preflight + 6 evennia + 11 browser + 1 top-level +
  1 gate = 20 slots stays within the limit. Never count the two processes as
  two slots.

## Risks / Trade-offs

- **Two checkouts add ~60–90 s per browser job's setup**: acceptable — the
  jobs run in parallel and the test time saved dominates.
- **PID-file isolation depends on separate workspaces**: the design forbids
  running both processes from one checkout; documented in the workflow and
  the docs.
- **Balance drift**: per-test weights change as journeys grow; rebalancing is
  a manifest edit + contract tests, and CI durations are recorded for future
  tuning.
- **More processes = more machines/parallelism**: no cost on the Free plan,
  but each process is an independent flake surface; the existing per-shard
  rerun story applies unchanged.
- **Contract churn**: the browser ownership contract moves from file-level to
  method-level; the rewritten test is the regression pin.
