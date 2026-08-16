## Context

Current CI structure (`.github/workflows/quality-gate.yml`): `preflight`
(OpenSpec validation, static traceability, Node suite, browser-shard matrix
computation) → one `evennia` job (all five non-browser roots, `--parallel 4`,
subprocess coverage, `COVERAGE_FILE=coverage-evennia`,
`OPENSPEC_TEST_EVIDENCE=evidence.evennia.jsonl`) → six `browser` matrix jobs
+ `top-level` → `gate` (artifact completeness, evidence concatenation,
`coverage combine`, root verification, 80% branch gate, Codecov).

Measured baseline (run 31939321935, green): evennia **14m 02s** of a ~20 min
total; browser shards 4m42s–19m09s; gate 22s. The evennia job's test
execution is ~842 s on the 4-core runner. Public Free plan: 20 concurrent
jobs max, `ubuntu-latest` free, larger runners excluded by the operator.

## Goals / Non-Goals

**Goals:**
- Cut the evennia job from ~14 min to ~2–4 min by running 6 shards on 6
  machines, keeping `--parallel 4` inside each shard.
- Keep total jobs ≤ 20 (this change: 1 preflight + 6 evennia + 6 browser +
  1 top-level + 1 gate = 15; the browser packing change adds 5 more).
- Preserve every aggregation contract: artifact completeness checks,
  concatenated evidence, combined coverage, exact roots, 80% branch gate.
- Keep local development commands unchanged and document that shards are
  CI-only (all invocations share `server/db/evennia-test.sqlite3`).

**Non-Goals:**
- Browser shard changes (separate change `pack-browser-ci-shards`).
- Reducing per-test CPU cost (separate change `lighten-evenniatest-fixtures`).
- Replacing the 80% aggregate gate or the coverage/evidence semantics.
- Using larger/paid runners.

## Decisions

- **Manifest-driven matrix**: `.github/evennia-shards.json` mirrors
  `.github/browser-shards.json`; preflight computes the matrix via
  `fromJSON`. The manifest is the single source of truth for ownership and
  balance tuning (rebalancing = editing JSON + contract tests).
- **Six shards, package-aware split**: `world.rules` (112 files, ~half the
  suite) split into three equal file groups by sorted filename; remaining
  packages grouped by measured method-count weight into three shards
  (`world.quests world.skills world.art world.ai world.onboarding world.lore`;
  `world.maps web.webclient world.imports world.prompts world.tests`;
  `commands server typeclasses`). The final grouping reflects the measured
  rebalance (task 5.2): `web.webclient` is kept away from
  `commands`/`typeclasses` because their combined run is ~2× the sum of parts,
  and `world.quests` is paired with lightweight packages. Labels are dotted
  module paths — Django accepts package and module labels alike.
- **Per-shard DB isolation**: each matrix job runs on its own machine and
  creates its own fresh test database (`--noinput`, no `--keepdb`), so
  sharding never shares state. Locally the shards must never run
  concurrently — same retained DB path — hence "CI-only" documentation.
- **Artifact naming**: `coverage-evennia-shard-<n>*` sidecars and
  `evidence.evennia-shard-<n>.jsonl`; the gate's existing globs
  (`coverage-evennia*`) still match, minimizing contract churn.
- **Balance procedure**: initial split by method counts; then local serial
  timing per shard (`--keepdb --noinput`), rebalance once if
  `max/mean > 1.35`; then one CI-observed rebalance pass after the first
  push, recording final durations in the performance report.
- **Contract pins**: the ownership contract test resolves each label to a
  module file (`label.replace(".", "/") + ".py"`) or, for package labels,
  walks the directory for `test_*.py` files recursively — import-free, so it
  runs fast in the top-level suite. The file selection mirrors Django's
  DiscoverRunner discovery pattern (`test*.py`), and a preflight step rejects
  an empty or malformed manifest so the aggregation gate cannot be skipped.
- **Shared MODIFIED requirement text**: the delta's "Existing quality gates
  remain authoritative" MODIFIED block is byte-identical to the one in
  `pack-browser-ci-shards` (browser method/class-level labels, two-process
  shards). This change implements only the Evennia half; the browser clauses
  are forward-declared permissions exercised by the sibling change. Keeping
  the block byte-identical makes main-spec sync idempotent regardless of which
  change archives first.

## Risks / Trade-offs

- **Shard imbalance**: mitigated by the measurement step and the one-CI-pass
  rebalance; the manifest makes re-tuning cheap.
- **Contract-test churn**: three top-level test files pin the workflow
  structure; they are updated in the same change and re-verified.
- **Concurrency ceiling**: this change uses 15 of 20 slots; the browser
  packing change adds exactly 5 more. If GitHub's ceiling is ever lowered,
  shard counts must shrink.
- **More machines = more flake exposure**: matrix jobs share the existing
  per-shard rerun story; no new flake surface is introduced (each shard is
  the same kind of run as today's single evennia job).
- **CI validation cost**: the branch push that validates this change runs the
  full quality gate (~7–10 min after the change lands); acceptable and
  required by the repo's gate-on-push model.
