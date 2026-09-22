# Tasks: implement-church-redemption

Prerequisites: `implement-church-foundation`, `implement-church-enrollment`, and `implement-church-accrual` are implemented AND archived (ledger + `redeemed` + shell validator landed; enrollment gates the redeemer; pray/offer/climax rails give her spendable merit, and the docs trio carries join + pray/offer already). Traceability convention (verified against `tools.spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; every ID below was recomputed with that function, not copied from the superseded change's slug list): the exact `covers_requirement` IDs for this change's `church-ordination` delta are:

1. `redemption-is-a-one-shot-all-or-nothing-grace-purchase`
2. `series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline`
3. `the-church-redeem-and-merit-commands-are-documented-in-the-docs-trio`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at.

## 1. Price finals (the tuning task moved here from the superseded core's §1.2 — decide and record first)

- [ ] 1.1 Fix the price-band finals inside the design §5.5 placeholders (entry 300–600, mid 1200–2500, high 4000–8000): assign each of the 16 Series A/B/D keys a final `merit_price` (Series A qualifiers entry-tier except the three legacy passives at mid; `rite_lamb_mark`/`rite_martyrdom_vow` high; the Series D high rows carry the only catalogue-internal prereq chain); record the table in the `REDEEM_CATALOG` module docstring and verify every price lands inside its assigned band.

## 2. Rows

- [ ] 2.1 Register the 16 new `SKILL_REGISTRY` rows (Series A incl. new `vow_of_service` with its ledger-multiplier rule rows appended to `church.yaml` under the correspondence gate; Series B actives — `rite_lamb_mark`/`rite_martyrdom_vow` register with declarations only, their combat rails belong to `implement-church-combat-ministry`; Series D actives doubling as advanced offering rows) — no lineage tree membership; grow `REDEEM_CATALOG` with the 16 priced rows from 1.1 behind the foundation's validator and append the advanced `OFFERING_CATALOG` rows by shared key. Data tests: keys, kinds, non-lineage, band membership, offering-key reuse, prereq-chain shape. Annotate ID 2.

## 3. The redeem rail

- [ ] 3.1 Implement `church redeem [list|<key>]` and `church merit` (read-only ledger print: merit, enrollment day, redeemed marks, daily prayer usage): list prints catalogue + merit + redeemed marks; redeem validates (exists ∧ unredeemed ∧ merit ∧ catalogue-internal prereqs), one transaction subtract merit → write `db.skills.passive`/`db.skills.active` per kind → append `redeemed` → `church_skill_redeemed`; every failure a stable rejection leaving everything byte-identical; no repeat redemption. Tests per design §7 incl. the mid-redemption forced-fail rollback. Annotate ID 1.

- [ ] 3.2 Negative-set + guard-green tests: `saintess_vessel` ∉ `REDEEM_CATALOG` ever and `church redeem saintess_vessel` is the unknown-key rejection; the practice/unlock/conferral PASSIVE guards stay untouched with their existing tests green (the pipeline is the channel, not a bypass). Annotate ID 1 (negative set) and ID 2 (guards).

## 4. Docs and gates

- [ ] 4.1 Player-command docs trio: document `church redeem [list|<key>]` and `church merit` in `docs/game/commands.md` AND `docs/game/command-reference.md` in this change; keep `tests/test_command_docs.py` green over the completed surface. Annotate ID 3.

- [ ] 4.2 Register every new test module in exactly one `.github/evennia-shards.json` shard and put data-contract-tagged modules in the test-data ledger files; list them in the PR body. After the delta syncs, run `uv run --locked python -m tools.spec_traceability check` and confirm all 3 IDs above resolve with zero uncovered requirements and zero unknown-annotation errors.
