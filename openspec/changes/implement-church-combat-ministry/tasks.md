# Tasks: implement-church-combat-ministry

Prerequisites: `implement-church-redemption` is implemented AND archived (the `rite_lamb_mark` / `rite_martyrdom_vow` rows and the redeem rail exist to be redeemed); `implement-church-foundation` / `-enrollment` / `-accrual` are archived (the E2E loop walks join → pray → offer → climax → redeem). Independent of `implement-church-order-catalogue`. Traceability convention (verified against `tools.spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; every ID below was recomputed with that function, not copied from the superseded change's slug list): the exact `covers_requirement` IDs for this change's `church-ordination` delta are:

1. `lamb-mark-narrows-monster-target-preference-with-a-charging-buff`
2. `martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr`
3. `the-combat-rails-are-offline-deterministic-and-the-full-church-loop-runs-end-to-end-with-ai-dead`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at. Verification runs the focused test labels that cover this change per the repo AGENTS.md testing rules (smallest label that covers the change; `--parallel 16 --noinput` full suite and CI shard commands are NEVER run locally by this change).

## 1. The charges primitive

- [x] 1.1 Implement the `charges: int` buff-declaration primitive + climax-transition consumption hook (transition into 進行中 consumes one charge; zero → remove the buff). Isolated buff tests FIRST, before any lamb-seal integration: declaration round-trip, save/restore, two-transition consumption sequence, rolled-back consumption does not burn a charge. Annotate ID 1.

## 2. Lamb seal

- [x] 2.1 Implement `rite_lamb_mark` + `lamb_seal` narrowing in `monster_behaviour_policy` BEFORE target-strategy evaluation (single-target candidates narrow to seal-bearers; player-first-then-ascending-pk; AREA and positional markers untouched; ends with the fight). Tests: redirect over `lowest_hp` (and `highest_effective_power`), multi-seal canonical order, two-climaxes-lift, no-seal decision trace byte-identical. Annotate ID 1.

## 3. Martyrdom vow

- [x] 3.1 Implement `rite_martyrdom_vow`: session-record `martyr_key` stamp with the durable session id; one added filter in `defeat_aftermath/violation.py::_victim_pool` (valid stamp ∧ non-fled member → collapse to `[her]`, zero target rolls via the existing short-circuit, resist contests unchanged); victory consumes. Tests: collapse, died/fled/stale/no-stamp fallbacks byte-identical, victory consumption, rollback-retry determinism. Annotate ID 2.

## 4. The loop proof and gates

- [ ] 4.1 The cross-change end-to-end integration test as one registered module: join → pray → offer → climax → redeem with the dialogue model stubbed to raise, all five events observed (`church_enrolled`, `church_pray`, `church_offering_accepted`, `church_offering_declined`, `church_skill_redeemed`), every step deterministic with AI dead. Annotate ID 3.

- [ ] 4.2 Observability lint gate over every module the church pipeline touched across the batch (facade-only, commit-bound, zero findings); register every new test module in exactly one `.github/evennia-shards.json` shard (data-contract modules in the test-data ledger files) and list them in the PR body. After the delta syncs, run `uv run --locked python -m tools.spec_traceability check` and confirm all 3 IDs above resolve with zero uncovered requirements and zero unknown-annotation errors. Annotate ID 3.
