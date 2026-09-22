# Tasks: implement-church-core

Traceability convention (verified against `tools/spec_traceability.py::normalize_requirement_name` — the current slug regex is `[^\w]+` with `re.UNICODE`, so CJK SURVIVES; recompute every ID with that function, do not copy the archived CJK-stripping IDs): the exact `covers_requirement` IDs for this change's deltas are:

church-ordination (new spec):

1. `the-merit-ledger-is-persisted-character-state-with-a-single-writer`
2. `the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates`
3. `enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost`
4. `enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness`
5. `enrollment-hands-over-exactly-one-vestment-unconditionally`
6. `prayer-is-a-time-costed-capped-venue-bound-accrual`
7. `sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity`
8. `climax-accrual-rides-the-side-reaction-rail-and-fails-closed-for-the-unenrolled`
9. `redemption-is-a-one-shot-all-or-nothing-grace-purchase`
10. `series-a-b-d-rows-ship-as-registry-skills-earned-only-through-the-church-pipeline`
11. `lamb-mark-narrows-monster-target-preference-with-a-charging-buff`
12. `martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr`
13. `every-church-mechanic-is-offline-deterministic-and-observable-at-five-boundaries`
14. `the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts`
15. `lore-documents-state-the-no-uniqueness-office-and-current-status`
16. `the-church-command-surface-is-documented-in-the-docs-trio`

saintess-vessel (the two preset-grant-era requirements are REMOVED and replaced — the validator forbids a MODIFIED block that replaces scenarios and forbids same-name ADDED+REMOVED in one delta, so the replacements carry new headings; re-annotate the vessel tests with the new IDs):

17. `saintess-vessel-is-a-church-enrollment-granted-clergy-qualifier-passive`
18. `the-oath-flip-stays-observable-through-the-facade-and-the-office-name-title-ban-holds`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at.

## 1. Tuning decisions (decide and record first — everything else prices against them)

- [ ] 1.1 Fix the acceptance-curve intermediates: keep owner-pinned ordinal 0 = 50% and top ordinal = 100%, choose strictly monotonic values for ordinals 1–3 and record them in `world/rules/rulebook/church.yaml` with a comment naming the owner baseline shape (proposal: 50 / 65 / 80 / 90 / 100); verify the loader monotonicity gate accepts them.
- [ ] 1.2 Fix the price-band finals inside the design §5.5 placeholders (entry 300–600, mid 1200–2500, high 4000–8000): assign each of the 16 Series A/B/D keys a final `merit_price` (Series A qualifiers entry-tier except the three legacy passives at mid; `rite_lamb_mark`/`rite_martyrdom_vow` high; Series D high rows carry the only catalogue-internal prereq chain); record the table in the `REDEEM_CATALOG` module docstring and verify every price lands inside its assigned band.
- [ ] 1.3 Fix the pray numbers: duration seconds, merit per pray, daily cap (proposal: 600 s, +40 merit, cap 3/day) in `church.yaml`; verify the daily-reset test design uses them (cap +1 comes from the sibling's `rite_morning_devotion`, NOT here).
- [ ] 1.4 Fix the accrual and payout numbers: `climax_while_enrolled` merit (small: +10), `offering_accepted` per-row merit, and the offering copper payout band (band row + per-row overrides; all integer copper) in `church.yaml`; verify payout tests can assert exact integers.

## 2. Rulebook slice and loader gates

- [ ] 2.1 Create `world/rules/rulebook/church.yaml` registered through the `load_rules` family with the accrual/acceptance/pray/offering sections from §1; add one matching test per row (one-row-one-test correspondence gate, same audit as `combat_modifiers.yaml`) and REGISTER the correspondence test module in `.github/evennia-shards.json`. Annotate ID 2.
- [ ] 2.2 Implement the loader's acceptance-curve monotonicity gate (reject non-strictly-monotonic rows, ordinal-0 ≠ 50%, top ≠ 100%, naming the offending row) and the PASSIVE polarity gate (reject negative-relative-to-baseline authored effects on PASSIVE catalogue rows; mitigation of an existing penalty counts positive) with planted-bad-row tests for each rejection. Annotate ID 2.
- [ ] 2.3 Data-contract test over SHIPPED rows: every shipped church PASSIVE's rule rows are positive-polarity only (this gate must pass for the Series C passives the sibling adds — write it catalogue-driven, not hardcoded). Annotate ID 2.

## 3. Ledger and lore catalogues

- [ ] 3.1 Create `world/rules/church.py` with the lazy `db.church` ledger (merit/enrolled_tick/redeemed/daily with clock-day reset mirroring `climax_today`), sole-writer accrual/redemption primitives, and `transaction.atomic()` discipline. Ledger lifecycle tests: lazy creation, persistence across save/restore, day-boundary reset, no wallet/transfer path accepts merit. Annotate ID 1.
- [ ] 3.2 Create `world/lore/church/` with frozen `OFFERING_CATALOG` (`{key, act_key, merit, copper, min_lineage?}`) and `REDEEM_CATALOG` (`{skill_key, merit_price, tier, prereq_keys, polarity}`, the 16 Series A/B/D rows from 1.2) and the church-place derived set from places authoring a `church` kwarg (the `shops.py` derivation pattern, incl. duplicate-kwarg fail-closed). Data tests: catalogue keys resolve against `SKILL_REGISTRY`/act catalogue; offering rows reuse Series D keys with zero duplication; `saintess_vessel` ∉ catalogue (negative set). Annotate ID 10.
- [ ] 3.3 Author the `church` kwarg on the church place records and attach `ChurchHost` to the two clergy NPC roster rows (艾莉安娜·寒水 high celebrant, 羅海西亞·芬威克 sanctuary steward) through their profession blueprint; add the small raised-initial-arousal authoring kwarg to their spawn data; verify `place-driven-service-sync` convergence stays idempotent with the new component and the derived church-place set is non-empty. Annotate ID 3.

## 4. Enrollment, office branch, vestment

- [ ] 4.1 Implement `commands/church.py::church join` (aliases 入教／洗禮): local `ChurchHost` resolution (the `resolve_local_service_host` pattern), schedule gate `interaction_reason(host, "service_church")`, then `world/rules/church.py::enroll(caller, host)` — zero AI import. `enroll` creates the ledger, stamps `enrolled_tick`, emits `church_enrolled` via `transaction.on_commit`, rejects re-enrollment 「你已屬光明教會」. Tests: clean commit + single event; every stable rejection inert (no host, off-duty, re-enroll); rollback byte-identical. Annotate ID 3 (and ID 13 on the AI-dead smoke: the flow passes with the dialogue model stubbed to raise).
- [ ] 4.2 Implement the subrace/sex branch inside the same transaction: female `human_royal` → canonical granted-passive write of `saintess_vessel` + reused `saintess_vessel_granted` event exactly once; everyone else plain. Office tests per design §7: female royal grants; male royal and each other subrace do not; two eligible royals BOTH grant (no uniqueness); re-enrollment re-grants nothing; trickle disarmed pre-enrollment. Annotate ID 4 plus saintess-vessel delta IDs 17/18 (move the preset-grant scenario's old test to the enrollment path — the delta REPLACES it; keep the `TitlePredicateFamily`-unchanged probe except the sanctioned church-count family the sibling adds, asserted ABSENT here).
- [ ] 4.3 Implement the unconditional vestment handover inside the enrollment transaction via the deterministic `QuestReward` item-quantity rail: `sister_vestments` / `saintess_vestments` (vessel branch), NO holding check, event context carries `char`/`host`/`item`. Tests per §7: ordinary → exactly one sister robe; vessel branch without robe → exactly one saintess robe; already-carrying-key initiate still receives its one; rollback returns it. Annotate ID 5.
- [ ] 4.4 Edit `violet_altoria` in `world/lore/player_presets/data_pack_cards.py`: drop `saintess_vessel` from `passive_skills`, drop `saintess_vestments` from `starting_items`; DELETE the persona's religious narrative — no 聖女/聖女繼承人 wording anywhere, public identity loses the church clause, temple-blessing personality passages and consecration/倾湧-duty life-story sentences removed by deletion, NOT rewritten into a successor framing, story otherwise continuous. Update the preset data-contract tests; run a repo-wide authored-content search for the deleted framing (successor reframings count as failures to revert). Annotate ID 14.

## 5. Pray, offering, climax accrual

- [ ] 5.1 Implement `church pray` → `church.py::pray_step(char)`: ledger required (unenrolled → stable "speak with the celebrant"), church-flag venue check on the derived set, daily cap, world-clock advance by the §1.3 duration (existing non-combat clock source), accrual, commit, `church_pray`. Tests: time-cost + merit observable; cap/venue/unenrolled rejections inert. Annotate ID 6.
- [ ] 5.2 Implement `church offer <npc> [row_key]`: enrollment-only gate (NOT venue-bound); menu = `OFFERING_CATALOG` rows whose `act_key` the player owns (existing unlock-counter projection, no new unlock system); acceptance = NPC `entity.sexual.arousal` ordinal → curve row → `roll_d100` via the injected-dice gate, NO affinity term; accept = execute the act through the action-resolution pipeline then same-transaction merit + copper → `church_offering_accepted`; decline = `church_offering_declined`, zero writes, no cooldown. Tests: injected ordinal × boundary-die exhaustive matrix (ordinal-0 50% band, monotonicity, top = 100%); accepted settlement atomicity + rollback; declined writes nothing and is instantly re-proposable; an unowned row_key rejects; normal partnered sex traces byte-identical. Annotate ID 7.
- [ ] 5.3 Wire `climax_while_enrolled` on the `state_reactions.yaml` side-reaction rail (entering 進行中 while enrolled → §1.4 merit; fails closed unenrolled). Baseline test: unenrolled climax settlement byte-identical. Annotate ID 8.

## 6. Redemption engine

- [ ] 6.1 Implement `church redeem [list|<key>]` and `church merit`: list prints catalogue + merit + redeemed marks; redeem validates (exists ∧ unredeemed ∧ merit ∧ catalogue-internal prereqs), one transaction subtract merit → write `db.skills.passive`/`db.skills.active` per kind → append `redeemed` → `church_skill_redeemed`; every failure a stable rejection leaving everything byte-identical; no repeat redemption. Tests per §7 incl. mid-redemption forced-fail rollback. Annotate ID 9.
- [ ] 6.2 Negative-set + guard-green tests: `saintess_vessel` ∉ `REDEEM_CATALOG` ever and `church redeem saintess_vessel` is the unknown-key rejection; the practice/unlock/conferral PASSIVE guards stay untouched with their existing tests green (the pipeline is the channel, not a bypass). Annotate ID 9 (negative-set) and ID 10 (guards).

## 7. Series A/B/D rows and combat rails

- [ ] 7.1 Register the 16 new `SKILL_REGISTRY` rows (Series A incl. new `vow_of_service` ledger multipliers; Series B actives; Series D actives doubling as advanced offering rows) — no lineage tree membership; catalogue prices from §1.2. Data tests: keys, kinds, non-lineage, band membership, offering-key reuse. Annotate ID 10.
- [ ] 7.2 Implement the `charges: int` buff-declaration primitive + climax-transition consumption hook (transition into 進行中 consumes; zero → remove), isolated buff tests first: declaration round-trip, save/restore, two-transition consumption sequence, rolled-back consumption does not burn a charge. Annotate ID 11.
- [ ] 7.3 Implement `rite_lamb_mark` + `lamb_seal` narrowing in `monster_behaviour_policy` BEFORE target-strategy evaluation (single-target candidates narrow to seal-bearers; player-first-then-ascending-pk; AREA and positional markers untouched). Tests: redirect over `lowest_hp`, multi-seal order, two-climaxes-lift, no-seal decision trace byte-identical. Annotate ID 11.
- [ ] 7.4 Implement `rite_martyrdom_vow`: session-record `martyr_key` stamp with durable session id; one added filter in `defeat_aftermath/violation.py::_victim_pool` (valid stamp ∧ non-fled member → collapse to `[her]`, zero target rolls, resist contests unchanged); victory consumes. Tests: collapse, died/fled/stale/no-stamp fallbacks byte-identical, victory consumption, rollback-retry determinism. Annotate ID 12.
- [ ] 7.5 Observability lint gate over every touched module (facade-only, commit-bound, zero findings) + AI-dead end-to-end smoke as one registered integration test: join → pray → offer → climax → redeem with dialogue model stubbed to raise, all five events observed. Annotate ID 13.

## 8. Docs, lore, and gates

- [ ] 8.1 Lore realignment: `docs/lore/overview.md` §宗教信仰 — retire the once-per-generation donated-princess framing and any sibling wording to "any female royal may be donated to the church and consecrated at enrollment"; `docs/lore/skill-trees/light.md` 聖女 footnote → enrollment grant; `docs/lore/settlement-locations.md` §神殿／聖所 〔提案〕→〔已實作〕 for the ministry counter. Search-prove the retired claim appears nowhere. Annotate ID 15.
- [ ] 8.2 Player-command docs trio: document `church join/pray/offer/redeem/merit` (+ 入教／洗禮 aliases) in `docs/game/commands.md` AND `docs/game/command-reference.md` in this change; keep `tests/test_command_docs.py` green over the new surface. Annotate ID 16.
- [ ] 8.3 Verify every new test module is registered in exactly one `.github/evennia-shards.json` shard and data-contract-tagged modules are in the test-data ledger files; list them in the PR body.
- [ ] 8.4 After the deltas sync to main specs, run `uv run --locked python -m tools.spec_traceability check` and confirm all 18 IDs above resolve with zero uncovered requirements and zero unknown-annotation errors (IDs 17/18 resolve against the UPDATED main-spec text).
