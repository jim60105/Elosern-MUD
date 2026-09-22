# Tasks: implement-church-foundation

Traceability convention (verified against `tools.spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; every ID below was recomputed with that function, not copied from the superseded change's slug list): the exact `covers_requirement` IDs for this change's `church-ordination` delta are:

1. `the-merit-ledger-is-persisted-character-state-with-a-single-writer`
2. `the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates`
3. `church-venues-and-clergy-hosts-exist-as-authored-content`
4. `the-frozen-church-catalogues-ship-as-validated-shells-awaiting-their-pipeline-rows`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at. The price-band tuning task (superseded core's 1.2) belongs to `implement-church-redemption`, which owns the rows being priced.

## 1. Tuning decisions (decide and record first — every other church change prices against these)

- [ ] 1.1 Fix the acceptance-curve intermediates: keep owner-pinned ordinal 0 = 50% and top ordinal = 100%, choose strictly monotonic values for ordinals 1–3 and record them in `world/rules/rulebook/church.yaml` with a comment naming the owner baseline shape (proposal: 50 / 65 / 80 / 90 / 100); verify the loader monotonicity gate (2.2) accepts them.

- [ ] 1.2 Fix the pray numbers and the accrual/payout numbers in `church.yaml`: pray duration seconds, merit per pray, daily cap (proposal: 600 s, +40 merit, cap 3/day — cap +1 comes from the order-catalogue change's `rite_morning_devotion`, NOT here), `climax_while_enrolled` merit (small: +10), `offering_accepted` per-row merit, and the offering copper payout band (band row + per-row overrides; all integer copper); verify the daily-reset test design (3.1) uses the pray numbers and payout tests can assert exact integers.

## 2. Rulebook slice and loader gates

- [ ] 2.1 Create `world/rules/rulebook/church.yaml` registered through the `load_rules` family with the accrual/acceptance/pray/offering sections from §1; add one matching test per row (one-row-one-test correspondence gate, same audit as `combat_modifiers.yaml`) and REGISTER the correspondence test module in `.github/evennia-shards.json`. Annotate ID 2.

- [ ] 2.2 Implement the loader's acceptance-curve monotonicity gate (reject non-strictly-monotonic rows, ordinal-0 ≠ 50%, top ≠ 100%, naming the offending row) and the PASSIVE polarity gate (reject negative-relative-to-baseline authored effects on PASSIVE catalogue rows; mitigation of an existing penalty counts positive) with planted-bad-row tests for each rejection. Then the data-contract test over SHIPPED rows: every shipped church PASSIVE's rule rows are positive-polarity only — written catalogue-driven, not hardcoded, so it must pass untouched when the order-catalogue change later appends Series C. Annotate ID 2.

## 3. Ledger and lore catalogues

- [ ] 3.1 Create `world/rules/church.py` with the lazy `db.church` ledger (merit/enrolled_tick/redeemed/daily with clock-day reset mirroring `climax_today`), sole-writer accrual/redemption primitives, and `transaction.atomic()` discipline. Ledger lifecycle tests: lazy creation, persistence across save/restore, day-boundary reset, no wallet/transfer path accepts merit. Annotate ID 1.

- [ ] 3.2 Create `world/lore/church/` with frozen `OFFERING_CATALOG` (`{key, act_key, merit, copper, min_lineage?}`; seed rows may be empty/seeded — ship the rows whose act keys are currently ownable and note they stay inert until `implement-church-accrual` wires the offering rail) and `REDEEM_CATALOG` (`{skill_key, merit_price, tier, prereq_keys, polarity}`) as a validated EMPTY shell with its row validator (the 16 Series A/B/D rows arrive with `implement-church-redemption`; placeholder prices are forbidden). Data tests: validator rejects planted malformed rows; offering `act_key`s resolve against the act catalogue; `saintess_vessel` ∉ redemption catalogue. Annotate ID 4.

## 4. Authored venues and clergy hosts

- [ ] 4.1 Implement the church-place derivation in `world/lore/church/` from places authoring a `church` kwarg (the `shops.py` derivation pattern, incl. duplicate-kwarg fail-closed); author the `church` kwarg on the church place records; test the derived set is non-empty and complete. Annotate ID 3.

- [ ] 4.2 Create the `ChurchHost` typeclass component (sibling of `GuildStaff`, zero-state adapter) and attach it to the two clergy NPC roster rows (艾莉安娜·寒水 high celebrant, 羅海西亞·芬威克 sanctuary steward) through their profession blueprint; add the small raised-initial-arousal authoring kwarg to their spawn data; verify `place-driven-service-sync` convergence stays idempotent with the new component. Annotate ID 3.
