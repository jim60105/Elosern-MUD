# Tasks: implement-church-order-catalogue

Prerequisite: `implement-church-core` is implemented AND archived (its `church-ordination` main spec exists; `REDEEM_CATALOG`, `church.yaml` gates, and the `db.church` ledger are landed). Do not start against an unlanded core — the 24-row test will fail loudly.

Traceability convention (verified against `tools/spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; recompute, do not strip): the exact `covers_requirement` IDs for this change:

church-ordination delta:

1. `series-c-discipline-passives-ship-pure-positive-with-no-baseline-downside`
2. `series-e-utility-rows-feed-the-core-loop`
3. `series-c-e-rule-rows-load-under-the-correspondence-and-polarity-gates`

title-system delta:

4. `the-church-redeemed-count-predicate-family-evaluates-the-redeemed-ledger-only`
5. `the-clergy-title-ladder-unlocks-by-redeemed-count-and-never-displays-聖女`
6. `the-fixed-title-lore-registry-validates-and-syncs-idempotently` (MODIFIED — main-spec ID kept)
7. `the-codex-oob-payload-and-webclient-window-are-server-authored` (MODIFIED — main-spec ID kept)

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard; data-contract-tagged modules go in the test-data ledger files.

## 1. Tuning decisions (decide and record first)

- [ ] 1.1 Record the clergy ladder threshold finals (design baseline 虔信者 3 ／ 修女 6 ／ 神官 10 ／ 主教 15 ／ 樞機 20 — keep unless the price finals in 1.2 make a rung unreachable in a workday's grind; if changed, record the arithmetic in the registry comment). Verify against core's §1.3/§1.4 pray/accrual numbers that rung 1 (3) and rung 2 (6) are reachable.
- [ ] 1.2 Assign final `merit_price` to each of the 8 Series C/E keys inside core's tuned bands (entry 300–600, mid 1200–2500, high 4000–8000; `rite_morning_devotion` mid — it feeds the loop; the other seven per their effect weight); record the table in the `REDEEM_CATALOG` docstring and verify band membership. All 8 rows are prereq-free.
- [ ] 1.3 Fix the Series C numeric finals in `church.yaml` terms: `poverty_vow` copper/pray scales, `obedience` ×2 status-conditional merit, `chastity_discipline` pray +, `temple_endurance` 0.75 penalty-mitigation scale, `public_devotion` public-venue merit +, `rite_martial_blessing` stat-buff magnitude + clock cooldown, `rite_shelter` rest-bonus value, `rite_morning_devotion` cap +1; verify every value is a rulebook row, no Python constants.

## 2. Series C/E rows and rule rows

- [ ] 2.1 Register the 5 Series C PASSIVE + 3 Series E rows in `world/skills/registry/` (appended after core's Series A/B/D block; non-lineage) and the 8 `REDEEM_CATALOG` rows from 1.2; catalogue-completes-at-24 test: 16 + 8 keys, no duplicates, `saintess_vessel` absent, no lineage membership. Annotate ID 3 (and ID 1/2 row-shape halves).
- [ ] 2.2 Append the Series C/E `church.yaml` rows from 1.3 through core's loader sections; one matching test per row (correspondence gate grows) incl. planted-downside loader rejection (e.g. price-increase row on `poverty_vow`). Tests: `obedience` exactly ×2 under / ×1 off the domination-submission status; `temple_endurance` holder penalty 25% below baseline while the non-holder penalty is byte-identical; `public_devotion` public-venue differential; polarity data-contract test enumerates all shipped church PASSIVEs (Series C included) positive-only. Annotate ID 1.
- [ ] 2.3 Implement the Series E actives: `rite_martial_blessing` (single-stat buff, clock-cooled — recast-inside-cooldown is the stable rejection), `rite_shelter` (ledger-flag rest bonus; no wallet/merit movement outside the configured bonus), `rite_morning_devotion` (rulebook skill-owned cap scale composing to exactly +1; over-cap prayer succeeds with, hits cap without). Annotate ID 2.

## 3. Clergy title ladder — predicate family

- [ ] 3.1 Add `TitlePredicateFamily.CHURCH_SKILLS_REDEEMED` (value `church_skills_redeemed`) to `world/lore/titles.py` with its `threshold: int` parameter face (reuse the `counter_threshold` int face), single-family validation, and loader validation treating it as referencing no registry face; update the family-validation tables so a `church_skills_redeemed` row with no/foreign parameter is rejected at load. Annotate ID 4.
- [ ] 3.2 Implement `predicate_satisfied` for the family: `len(db.church.redeemed) >= threshold` via the no-create ledger read (absent ledger ⇒ false, zero writes); evaluator tests: satisfied exactly at k / unsatisfied at k+1; saintess-with-vessel-and-zero-redeemed unsatisfied; unenrolled probe fails closed and creates no `db.church`. Annotate ID 4.

## 4. Clergy title ladder — registry rows and both validator faces

- [ ] 4.1 Add the 聖職 (`clergy`) member to `TitleCategory` and the 5 ladder rows (displays 虔信者／修女／神官／主教／樞機, thresholds from 1.1, non-empty `flavor_zh`/`hint_zh`) in `world/lore/titles.py`; loader gate: reject ANY fixed-title row of ANY category whose display contains 聖女 — the global office-name ban the saintess-vessel delta reaffirms (planted-row tests in two categories + shipped-rows-pass test). One-row-one-test registry tests per ladder row (grant at exact count, locked one below, auto-equip empty slot, redeem-transaction rollback removes it). Annotate ID 5 (and ID 6 for the extended vocabulary validation).
- [ ] 4.2 Move the closed category enum across ALL mirrors in the same commit: Python `TitleCategory`, `web/webclient/presentation/title_codex.py` mirror, `web/static/webclient/js/elosern/protocol/constants.js` client validator enum (tab order 戰鬥／法術／探索／公會／聖職／風流韻事), and `web/static/webclient/js/tests/protocol_title_codex.test.js` literal enumeration — plus payload tests: 聖職-category rows render under the new tab; an out-of-enum category is client-rejected. Annotate ID 7.
- [ ] 4.3 Codex panel tests: ladder rows appear in the fixed-row block locked→unlocked as the redeemed count crosses thresholds; no other system consumes a clergy title as a prerequisite (search-prove). Annotate ID 5.

## 5. Gates

- [ ] 5.1 Register every new test module (Python + JS protocol test needs none new — the existing runner picks it up) in exactly one `.github/evennia-shards.json` shard; data-contract modules in the test-data ledger files; list them in the PR body.
- [ ] 5.2 After both deltas sync, run `uv run --locked python -m tools.spec_traceability check` and confirm IDs 1–7 resolve with zero uncovered requirements and zero unknown-annotation errors.
