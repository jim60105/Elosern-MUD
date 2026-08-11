# Design: Stabilize and Accelerate the Quality Gate

## Context

The quality-gate workflow (`.github/workflows/quality-gate.yml`) runs a single
job whose steps are strictly sequential. Two consecutive merge runs failed
(31357805563 on a browser flake, 31393233883 on 8 Evennia-suite errors), and
the last green run sat at exactly 90% aggregate coverage. Measured state at
`e331828` (this design's base):

- **Evennia suite (serial, with coverage, CI):** 3,004 tests in 2,385s (~40 min).
  Fails with 8 `CapBreakTurnInTests` errors: `GuildOfferError: conflicting
  offer 'introductory_hunt' already registered` — reproduced locally in 1.6s
  by running `OnboardingHuntIntegrationTests` before `test_cap_break_turnin`.
- **Parallel probe (local, 4 workers, with coverage):** same 3,004 tests in
  202s (202s includes coverage instrumentation; 392% CPU). Fails with 9
  errors: the same 8 cap-break errors plus
  `DisplayedStatsBlockTests.test_block_ordering...` because the quest
  definition registry was emptied by an unrestored `clear()` in
  `test_scenario_director`.
- **Browser suite (CI):** ~62 min for 148 tests. Foundation tests share one
  per-process server (~6.6s/test locally); combat tests boot a dedicated
  server per test (19 boots, ~35s each locally, slower in CI).
- **Coverage:** evennia-only parallel probe = 88% branch (19,593 statements,
  5,390 branches). The old combined aggregate was exactly 90%.

Root causes, both test-isolation defects:

1. `world/maps/tests/test_wilderness_population.py::OnboardingHuntIntegrationTests.setUp`
   calls `sync_guild_economy()`, which registers the canonical catalog offer
   (`introductory_hunt` at `guild_branch_altoria`, `healing_potion ×2`) into
   the process-global `GUILD_OFFER_REGISTRY`. The class restores only
   `QUEST_DEFINITION_REGISTRY` (via `QuestRegistryIsolation`), so the offer
   leaks; `CapBreakTurnInBase.setUp` then registers a conflicting `×1` offer
   and `register_guild_offer` rejects it.
2. `world/ai/tests/test_scenario_director.py` has three tests that
   `clear()` `QUEST_DEFINITION_REGISTRY`/`GUILD_OFFER_REGISTRY` (and once
   `SCENE_REQUIREMENT_REGISTRY`) without restoring prior contents. Any test
   later in the same process that needs the catalog (e.g.,
   `DisplayedStatsBlockTests`, which loads the affinity rulebook requiring
   `introductory_hunt`) fails — this only manifests when the parallel runner
   mixes labels into one worker.

## Goals / Non-Goals

Goals:

- Make the quality gate green and deterministic: no order-dependent failures
  in serial, parallel, shuffled, or reversed execution.
- Cut the gate wall time from ~1h43m to roughly 20-25 min (Evennia suite
  ~5-8 min in CI, browser suite ~15-25 min across shards, plus a short
  aggregation job).
- Raise measured aggregate branch coverage above the 90% gate with a real
  margin (target ≥91%) by adding genuine tests, never by weakening gates.
- Keep the three-entry-point coverage/evidence aggregation contract intact.

Non-goals:

- No production behavior changes; no new dependencies; no data migrations.
- Not fixing the underlying Evennia server-session state that forces combat
  browser tests onto per-test servers (documented as future work).
- Not removing the serial profile as the canonical handoff evidence standard.

## Decisions

### D1: Snapshot/restore process-global registries instead of clearing

Every test that mutates `QUEST_DEFINITION_REGISTRY`, `GUILD_OFFER_REGISTRY`,
or `SCENE_REQUIREMENT_REGISTRY` must snapshot its contents in `setUp` and
restore them in teardown, using the existing `QuestRegistryIsolation`
pattern. `OnboardingHuntIntegrationTests` additionally snapshots/restores
`GUILD_OFFER_REGISTRY` around its `sync_guild_economy()` calls;
`test_scenario_director` replaces its three `clear()` sites with
snapshot/restore; `DisplayedStatsBlockTests.setUp` calls `register_catalog()`
so it is self-contained.

The restoration MUST be registered (via `addCleanup` or an equivalent
`try/finally`) immediately after the snapshot and before any mutation: a
failing `setUp` does not run `tearDown`, so registering cleanup at snapshot
time is the only way a setup failure cannot leak registry state into later
tests. The three-registry snapshot/restore pair is factored into a reusable
isolation mixin beside `QuestRegistryIsolation` in
`world/quests/tests/_fixtures.py` so all affected tests share one audited
implementation.

Why snapshot/restore and not "reset to empty": workers in a parallel run may
interleave tests from different labels; a test that clears state destroys
registrations other tests rely on (the exact failure observed). Restoring the
pre-test contents preserves whatever the process had, which is the contract
the compile-boundary tests already use ("registry-unchanged relative to their
own setUp snapshot").

### D2: Run the non-browser Evennia suite with `--parallel 4` and subprocess-aware coverage in CI

CI step becomes:

```sh
uv run --locked coverage run \
  --concurrency=multiprocessing --parallel-mode \
  -m evennia test --settings test_settings.py --noinput \
  --parallel 4 commands server typeclasses world web.webclient
```

Validated locally: 5 coverage data files (parent + 4 workers) are produced
and `coverage combine` merges them; 3,004 tests in 202s vs 2,385s serial in
CI. Django's parallel runner forks workers (Linux default), so
`concurrency=multiprocessing` captures each worker's data without a
`COVERAGE_PROCESS_START` hook. The requirement-evidence decorator already
writes with `O_APPEND`, which is atomic for the small per-test lines, so
parallel evidence collection is safe (verified in
`tools/spec_traceability.py:110-118` and exercised in the verification plan).

Alternatives considered: package-level matrix shards (more jobs, uneven `world`
dominance, more DB setups — rejected); keeping serial (rejected: 40 min);
bare `--parallel` auto-detection (rejected: CI has 4 vCPU, and the project's
measured default is 4 workers). Serial remains the canonical final-handoff
evidence profile per the existing spec; CI adopting parallel is consistent
with the documented development default. The first CI run is an acceptance
checkpoint for the worker count: if 4 workers are slower or flakier than the
serial baseline on the GitHub-hosted runner, the documented fallback (2 or 3
workers) is adopted and recorded in the performance report.

### D3: Shard the managed browser suite across parallel CI jobs

Split `web/tests/browser/` into 6 shards by test file, weighting combat files
(per-test server boots) and balancing test counts; each shard runs the
existing serial command against its explicit file list in its own job, so the
exact-once execution contract is preserved per file:

```sh
uv run --locked coverage run --parallel-mode \
  -m unittest web.tests.browser.test_browser_combat web.tests.browser.test_browser_combat_rejection
```

Each shard uploads its combined coverage file and its evidence file as
artifacts. Shard ownership is not a hand-maintained checklist: the shard
manifest lives in a committed JSON file consumed by the workflow's matrix
(`fromJSON`), and a top-level regression test asserts that every discovered
browser test file appears in exactly one shard — so a new browser file cannot
be unowned or double-assigned. The initial grouping is balanced from measured
per-file cost (combat ≈35s/test with own server; foundation ≈7s/test shared,
slower in CI); the grouping is rebalanced after the first CI observation if
one shard dominates.

Alternatives: fixing the Evennia session state that corrupts the shared server
after combat (deep Evennia-internal change with regression risk — deferred and
documented); `pytest-xdist` (new dependency, against project conventions —
rejected); keeping the browser suite in the single job (rejected: it is the
dominant cost).

### D4: Final gate job aggregates coverage and evidence from artifacts

All suite jobs upload named coverage data files and per-entry-point evidence
files; the gate job downloads them, runs
`coverage combine` over the three named files, verifies exact coverage roots,
enforces the 90% aggregate branch gate, generates `coverage.xml` for Codecov,
concatenates the evidence files (in entry-point order), and runs
`spec_traceability verify`. OpenSpec validation, static traceability checks,
and Node tests move to a fast preflight job that fails the pipeline before any
expensive suite starts; every execution job declares `needs: preflight` and
the gate job depends on every execution job, so the fast checks cannot be
bypassed and expensive jobs do not start on a known-bad revision.

The artifact protocol is explicit so aggregation cannot silently lose data:

1. Every coverage-writing job sets a unique `COVERAGE_FILE` base:
   `.coverage.evennia`, `.coverage.browser-shard-1` … `.coverage.browser-shard-6`,
   `.coverage.top-level`. In parallel mode the worker sidecars are
   `<base>.<host>.<pid>.<random>` and never collide across jobs.
2. Each job uploads every sidecar file it produced (a glob of its base).
3. The gate job downloads all artifacts into one fresh workspace and runs
   `coverage combine` with no arguments, which merges every
   `.coverage*` sidecar present — the same additive operation the current
   three-file combine performs, generalized to N files.
4. Before combining, the gate validates that each expected artifact arrived
   and is non-empty (a job that uploaded nothing fails the gate instead of
   silently lowering coverage), and after combining it verifies the exact
   source roots and statement/branch totals against the recorded aggregate.

Evidence aggregation follows the same protocol: each job writes
`evidence.<entry>.jsonl`, uploads it, and the gate concatenates the files in
entry-point order before `spec_traceability verify`. Because each test file
has exactly one execution owner, no evidence record is duplicated.

Rationale: keeps the documented "combine all three named coverage files"
semantics while making the suites run in parallel; artifact-based aggregation
is the standard, restart-tolerant pattern for GitHub Actions matrix work.

### D5: Raise coverage with focused tests, measured not guessed

After the isolation fixes land, measure the full combined aggregate exactly as
the gate computes it: the complete non-browser Evennia suite (parallel,
with subprocess coverage), the complete managed browser suite (one full local
run), and the top-level regression suite, combined with `coverage combine`.
A partial measurement (for example a browser sample) cannot establish the
baseline or the target, so the full run is a required measurement, not a
probe. Generate the coverage JSON report and target the largest uncovered
branches in the newest modules (`world/ai/scene_flavor.py`,
`world/quests/characterization.py`, `world/quests/scene_builder.py`,
`world/quests/compile.py`, `world/rules/affinity.py`,
`world/rules/affinity_config.py`, `server/scene_flavor_service.py`) with
pure-logic or lightweight-fixture tests per the fixture guidance. Iterate
until the full aggregate exceeds 90% by at least one point. The 90% gate
itself stays at the documented value.

## Risks / Trade-offs

- [Parallel workers produce no/incomplete coverage data in CI] → The exact
  command was validated locally (5 files, combined, 88% report); the CI run
  is a task checkpoint before the workflow change is considered done.
- [Evidence file interleaving under 4 workers] → `O_APPEND` small-line writes
  are atomic on Linux; a parallel evidence probe with the exact CI env vars is
  part of the verification plan.
- [Browser shard imbalance] → Initial grouping uses measured per-test costs;
  rebalance after the first CI observation; shard granularity (file level)
  keeps rebalancing cheap; a committed manifest plus contract test prevents
  unowned or duplicate files.
- [A failing `setUp` leaks registry state because `tearDown` is skipped] →
  Restoration is registered via `addCleanup` immediately after the snapshot,
  before any mutation, so even a failed setup restores the registry.
- [Coverage artifacts missing, empty, or colliding at aggregation] → Unique
  per-job `COVERAGE_FILE` bases, per-job sidecar upload, and a gate-side
  presence/non-empty validation before combining; a missing artifact fails
  the gate rather than silently lowering coverage.
- [Parallel Evennia suite exposes further latent order dependencies] →
  Mitigated by the audit tasks (shuffle, reverse, repeated parallel runs) that
  must be green before CI adoption; any newly surfaced defect is fixed in this
  change, not worked around.
- [`--parallel 4` is not optimal on the GitHub-hosted runner] → First CI run
  is an acceptance checkpoint; documented fallback to 2 or 3 workers.
- [Coverage lands below 90% after fixes] → D5 measures the full aggregate
  first and adds tests until the margin exists; the gate is never weakened.
- [Extra shared-server boots from sharding (one per shard process)] → Bounded
  (≤6 additional boots ≈ a few minutes) and far outweighed by the ~4x wall-time
  reduction; noted in the performance report.

## Migration Plan

Workflow-only and test-only change; no runtime migration. Rollback: the old
workflow can be restored from git; no schema or data concerns. Documentation
(performance report, testing guide, `AGENTS.md`) is updated in the same
change so commands and evidence stay reproducible.

## Open Questions

- Exact browser shard grouping after the first CI measurement (initial
  grouping specified in tasks).
- Whether the aggregate coverage measurement reveals gaps beyond the newest
  modules (D5 closes whichever show up largest).
