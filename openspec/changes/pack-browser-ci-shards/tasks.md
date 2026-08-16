# Tasks: Pack the Browser Suite into Two-Process Shards

## 1. Manifest rewrite with method/class labels

- [ ] 1.1 Rewrite `.github/browser-shards.json` as 11 shards with
      `files_a`/`files_b` process lists; enumerate every test method per
      class of every `web/tests/browser/test_*.py` file (`rg "^    def
      test_"` per file) and compose lists so that:
      - the 19 `CombatMenuBrowserTest` methods and the 4
        `test_browser_combat_rejection` tests spread across ~5 lists of 4–5
        tests (method labels),
      - `test_browser_creation.py` classes split at class level,
        `test_browser_exploration.py` (single class, 16 methods) and
        `test_browser_art.py` split at method level,
        `test_browser_services.py` at class level,
      - shell-family files (`test_browser_shell`, `test_browser_actions`,
        `test_browser_local_map`, `test_browser_input_narrative`,
        `test_browser_session_lifecycle`) pack whole into 1–2 lists with the
        remaining light files,
      - every process list stays ≤ 240 s estimated time using the measured
        per-test weights (combat ~50 s, creation/layout ~38 s, exploration/
        reconnect ~40 s, services/pointer ~47 s, art/harness ~36 s, shell
        family ~6.4 s),
      - every test method appears in exactly one list (the Step 3 contract
        test enforces this)
- [ ] 1.2 Schema-check the manifest: 11 shards, indices 1–11 unique and
      sorted, each shard has non-empty `files_a` and `files_b`

## 2. Workflow: two-workspace browser job

- [ ] 2.1 Replace the `browser` job steps: check out twice
      (`actions/checkout` with `path: w-a` and `path: w-b`), install uv once,
      install pinned Python once, `uv sync --locked` in both workspaces
      (parallel), install Chromium once in `w-a` (`uv run --locked playwright
      install --with-deps chromium`), `mkdir -p server/db server/logs` in
      both workspaces
- [ ] 2.2 The "Run browser shard ${{ matrix.index }}" step runs two
      background processes with inline env vars:
      `(cd w-a && COVERAGE_FILE="coverage-browser-shard-<n>-p1"
      OPENSPEC_TEST_EVIDENCE="evidence.browser-shard-<n>-p1.jsonl" uv run
      --locked coverage run -m unittest ${{ join(matrix.files_a, ' ') }}) &`
      and the `w-b`/`files_b`/`-p2` equivalent; `wait` both with
      `status1=0; wait "$pid1" || status1=$?` (GitHub's default `set -e`
      aborts on a failing bare `wait`), then
      `cat w-a/evidence...-p1.jsonl w-b/evidence...-p2.jsonl >
      evidence.browser-shard-<n>.jsonl` and
      `test "$status1" -eq 0 && test "$status2" -eq 0`; no `|| true`, no
      `continue-on-error`
- [ ] 2.3 Upload step: `w-a/coverage-browser-shard-<n>-p1*`,
      `w-b/coverage-browser-shard-<n>-p2*`, and
      `evidence.browser-shard-<n>.jsonl` as
      `browser-shard-<n>-artifacts` with `if-no-files-found: error`

## 3. Contract tests

- [ ] 3.1 Replace `test_browser_shard_manifest_owns_every_browser_test_file_exactly_once`
      in `tests/test_evennia_test_optimization_contract.py` with a
      method-level partition test (AST-based, no imports): collect every
      `test_*` method per class from the browser files, resolve each
      `files_a`/`files_b` label to (file, class, method) sets, assert the
      resolved set equals the discovered set with no overlap, indices unique
      and sorted, each label resolving to at least one method; annotate with
      `covers_requirement("evennia-test-optimization::browser-method-labels-preserve-exact-ownership")`
      (verify the literal ID with `uv run --locked python -m
      tools.spec_traceability list`)
- [ ] 3.2 `tests/test_browser_verification_contract.py`: update the browser
      run assertions (`matrix.files_a`/`matrix.files_b`, `coverage run`
      present, no `--parallel`, no `discover -s web/tests/browser`), assert
      the two checkout steps with `path: w-a`/`path: w-b`, and update the
      evidence-path assertion to the inline per-process env pattern; add
      assertions that the run step contains both guarded waits
      (`|| status1=$?` and `|| status2=$?`), the A-then-B evidence
      concatenation order (`cat w-a/...-p1.jsonl w-b/...-p2.jsonl >
      evidence.browser-shard-...jsonl`), and the final dual-status check
      (`test "$status1" -eq 0 && test "$status2" -eq 0`) — these pin the
      correct-under-`set -e` process handling; keep all existing
      `covers_requirement` annotations on the same methods
- [ ] 3.3 `tests/test_evennia_test_optimization_contract.py`
      `test_workflow_uses_three_disjoint_coverage_owners`: update the browser
      run/strategy assertions for the two-workspace job; confirm the gate
      `needs` list and evennia assertions are untouched by this change

## 4. Documentation

- [ ] 4.1 Update `AGENTS.md`, `docs/development/evennia-testing-guide.md`,
      and `docs/development/evennia-test-performance.md` to describe the
      two-process browser shards, the two-checkout isolation requirement
      (Evennia launcher pidfiles are GAMEDIR-relative), and the total job
      count (20 = 1 + 6 + 11 + 1 + 1)

## 5. CI validation and rebalance

- [ ] 5.1 Run `uv run --locked -m unittest discover -s tests -t .`,
      `uv run --locked python -m tools.spec_traceability check`, and
      `openspec validate pack-browser-ci-shards --strict`
- [ ] 5.2 Push the branch (with `split-evennia-ci-shards` merged first),
      watch the quality gate, record every browser job's duration, rebalance
      the manifest once if any shard dominates (≥ 2× the median or > 7 min),
      and record final numbers in the performance report

## 6. Final handoff

- [ ] 6.1 Sync the delta spec into
      `openspec/specs/evennia-test-optimization/spec.md` (the requirement
      text must be identical to the one synced by `split-evennia-ci-shards`
      — confirm with `git diff` on the synced file before archiving), archive
      the change, run `openspec validate --all --strict`, and confirm
      `git diff --check` is clean
