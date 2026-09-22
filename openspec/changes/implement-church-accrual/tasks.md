# Tasks: implement-church-accrual

Prerequisites: `implement-church-foundation` and `implement-church-enrollment` are implemented AND archived (ledger + `church.yaml` pray/acceptance/offering rows + `ChurchHost`/venues landed; `church join` landed so an enrollment exists to gate on). Traceability convention (verified against `tools.spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; every ID below was recomputed with that function, not copied from the superseded change's slug list): the exact `covers_requirement` IDs for this change's `church-ordination` delta are:

1. `prayer-is-a-time-costed-capped-venue-bound-accrual`
2. `sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity`
3. `climax-accrual-rides-the-side-reaction-rail-and-fails-closed-for-the-unenrolled`
4. `the-accrual-paths-are-offline-deterministic-with-commit-bound-observability`
5. `the-church-pray-and-offer-commands-are-documented-in-the-docs-trio`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at. Verification runs the focused test labels that cover this change per the repo AGENTS.md testing rules (smallest label that covers the change; `--parallel 16 --noinput` full suite and CI shard commands are NEVER run locally by this change).

## 1. Pray

- [ ] 1.1 Implement `church pray` → `church.py::pray_step(char)`: ledger required (unenrolled → stable "speak with the celebrant"), church-flag venue check on the derived set, daily cap, world-clock advance by the foundation §1.2 duration (existing non-combat clock source), accrual, commit, `church_pray`. Tests: time-cost + merit observable; cap/venue/unenrolled rejections inert. Annotate ID 1.

## 2. Offering

- [ ] 2.1 Implement `church offer <npc> [row_key]`: enrollment-only gate (NOT venue-bound); menu = `OFFERING_CATALOG` rows whose `act_key` the player owns (existing unlock-counter projection, no new unlock system; no placeholder advanced rows — Series D joins later by shared key); acceptance = NPC `entity.sexual.arousal` ordinal → curve row → `roll_d100` via the injected-dice gate, NO affinity term; accept = execute the act through the action-resolution pipeline then same-transaction merit + copper → `church_offering_accepted`; decline = `church_offering_declined`, zero writes, no cooldown. Annotate ID 2.

- [ ] 2.2 Offering test battery: injected ordinal × boundary-die exhaustive matrix (ordinal-0 50% band, monotonicity, top = 100%); accepted settlement atomicity + rollback; declined writes nothing and is instantly re-proposable; an unowned `row_key` rejects; the normal-sex-not-counted baseline (ordinary partnered sex outside the flow byte-identical, no auto-count). Annotate ID 2.

## 3. Climax accrual

- [ ] 3.1 Wire `climax_while_enrolled` on the `state_reactions.yaml` side-reaction rail (entering 進行中 while enrolled → foundation §1.2 merit; fails closed unenrolled). Baseline test: unenrolled climax settlement byte-identical. Annotate ID 3.

## 4. Determinism, observability, docs, gates

- [ ] 4.1 Observability + AI-dead smoke over these paths, one registered test module: pray → offer (accept and decline branches) → enrolled climax with the dialogue model stubbed to raise; assert `church_pray`, `church_offering_accepted`, `church_offering_declined` observed at commit, rolled-back transactions emit nothing, facade-only writes, zero lint findings over the touched modules. Annotate ID 4.

- [ ] 4.2 Player-command docs trio: document `church pray` and `church offer <npc> [row_key]` in `docs/game/commands.md` AND `docs/game/command-reference.md` in this change; keep `tests/test_command_docs.py` green over the grown surface. Annotate ID 5.

- [ ] 4.3 Register every new test module in exactly one `.github/evennia-shards.json` shard and put data-contract-tagged modules in the test-data ledger files; list them in the PR body. After the delta syncs, run `uv run --locked python -m tools.spec_traceability check` and confirm all 5 IDs above resolve with zero uncovered requirements and zero unknown-annotation errors.
