## 1. Lint tool

- [ ] 1.1 Create `tools/test_data_lint.py` with `check`, `list`, `report`, and `--json`
  (deterministic sorted output, exit codes, stable violation codes
  `unexempted`/`new-debt`/`untagged-contract`/`stale-path`/`duplicate`, plus
  `quantity-pin` findings), following `tools.spec_traceability` conventions
- [ ] 1.2 Implement the shipped-token universe: import the locked catalogs under
  `server.conf.settings` (no DB), harvest dict/mapping keys and CJK display prose, apply
  `tools/test_data_lint_deny.json` with reasons
- [ ] 1.3 Implement Python AST scanning (statically resolvable string expressions:
  constants, literal-only concatenation, all-literal f-strings; `*_REGISTRY` symbol
  refs; `len(...) == N` pins) and JS/TS string/template-literal scanning over the
  git-tracked test corpus (exclude `dist/`, `node_modules/`)
- [ ] 1.4 Implement ledger loading + violation rules per design D2 (`check` never seeds)

## 2. Seed the ledger and classify

- [ ] 2.1 Create `tools/test_data_lint_seed.json` from design Appendix A (54 contract
  paths + reasons, including the 4 currently-clean contract files)
- [ ] 2.2 Add the `Data-contract test:` tag line to the 54 Appendix-A files
- [ ] 2.3 Generate `tools/test_data_freeze.json` (54 `contract` + 291 `debt` +
  frozen `seedDebtPaths`) and verify `check` is green on the untouched tree

## 3. Tests for the gate

- [ ] 3.1 Create `tests/test_test_data_lint.py` (pure `unittest.TestCase` over temp
  trees/ledgers + synthetic catalogs) with
  `@covers_requirement("test-data-independence::data-contract-tests-are-explicitly-classified")`
  on the tag/ledger test,
  `@covers_requirement("test-data-independence::the-test-data-lint-gate-blocks-shipped-content-references")`
  on the scanner test (real literals flagged; synthetic ids clean; token universe follows
  a mutated synthetic catalog; a shipped key assembled only via literal concatenation or
  an all-literal f-string is still flagged; every deny-list entry is paired with a
  regression proving shipped-key references remain caught), and
  `@covers_requirement("test-data-independence::the-exemption-ledger-is-provably-shrink-only")`
  on the ledger-rules test (rules table plus the atomic debt→contract conversion and its
  `new-debt` rejection). Note: these annotation ids live in this change's delta and are
  unknown to `spec_traceability check` until the delta syncs into `openspec/specs/` at
  archive; the annotation step belongs to the archive/sync commit, not this branch
- [ ] 3.2 Run `uv run --locked python -m unittest tests.test_test_data_lint -v` and
  `uv run --locked python -m tools.spec_traceability check`

## 4. Wiring and documentation

- [ ] 4.1 Add the gate step to `.github/workflows/quality-gate.yml` beside the
  observability lint and traceability steps; verify the step command locally
- [ ] 4.2 Add the authoring rule to `AGENTS.md` (Testing area) and
  `docs/development/evennia-testing-guide.md` (kit-or-local-fixtures rule, tag rule,
  meaningful-assertion rule), satisfying
  `@covers_requirement("test-data-independence::the-gate-is-wired-into-ci-and-the-authoring-rules-are-documented")`
  via a workflow+docs content test in `tests/test_test_data_lint.py` (same
  archive-time annotation timing rule as 3.1)
- [ ] 4.3 Run `openspec validate add-test-data-independence-gate --strict` and
  `git diff --check`
