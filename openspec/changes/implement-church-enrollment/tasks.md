# Tasks: implement-church-enrollment

Prerequisite: `implement-church-foundation` is implemented AND archived (the `db.church` ledger primitives, `ChurchHost` on the clergy roster rows, and the derived church-place set are landed). Traceability convention (verified against `tools.spec_traceability.py::normalize_requirement_name` — the slug regex `[^\w]+` with `re.UNICODE` means CJK SURVIVES; every ID below was recomputed with that function, not copied from the superseded change's slug list): the exact `covers_requirement` IDs for this change's deltas are:

church-ordination delta:

1. `enrollment-is-a-deterministic-three-stage-transaction-behind-a-churchhost`
2. `enrollment-grants-the-saintess-office-to-female-royal-initiates-only-without-uniqueness`
3. `enrollment-hands-over-exactly-one-vestment-unconditionally`
4. `the-shipped-royal-preset-awaits-nothing-the-vessel-and-the-robe-are-enrollment-gifts`
5. `lore-documents-state-the-no-uniqueness-office-and-current-status`
6. `the-church-join-command-is-documented-in-the-docs-trio`

saintess-vessel delta (the two preset-grant-era requirements are REMOVED and replaced — the validator forbids a MODIFIED block that replaces scenarios and forbids same-name ADDED+REMOVED in one delta, so the replacements carry new headings; re-annotate the vessel tests with the new IDs):

7. `saintess_vessel-is-a-church-enrollment-granted-clergy-qualifier-passive`
8. `the-oath-flip-stays-observable-through-the-facade-and-the-office-name-title-ban-holds`

Any NEW test module MUST be registered in exactly one `.github/evennia-shards.json` shard (unregistered modules silently never run); data-contract-tagged modules go in the test-data ledger files the shard config points at.

## 1. The join flow and its branches

- [ ] 1.1 Implement `commands/church.py::church join` (aliases 入教／洗禮): local `ChurchHost` resolution (the `resolve_local_service_host` pattern), schedule gate `interaction_reason(host, "service_church")`, then `world/rules/church.py::enroll(caller, host)` — zero AI import. `enroll` creates the ledger, stamps `enrolled_tick`, emits `church_enrolled` via `transaction.on_commit`, rejects re-enrollment 「你已屬光明教會」. Tests: clean commit + single event; every stable rejection inert (no host, off-duty, re-enroll); rollback byte-identical. Annotate ID 1 (plus ID 6's command-docs half lands in 2.2).

- [ ] 1.2 Implement the subrace/sex branch inside the same transaction: female `human_royal` → canonical granted-passive write of `saintess_vessel` + reused `saintess_vessel_granted` event exactly once; everyone else plain. Office tests per design §7: female royal grants; male royal and each other subrace do not; two eligible royals BOTH grant (no uniqueness); re-enrollment re-grants nothing; trickle disarmed pre-enrollment. Annotate ID 2 plus saintess-vessel delta IDs 7/8 (move the preset-grant scenario's old test to the enrollment path — the delta REPLACES it; keep the `TitlePredicateFamily`-unchanged probe except the sanctioned church-count family the order-catalogue change later adds, asserted ABSENT here).

- [ ] 1.3 Implement the unconditional vestment handover inside the enrollment transaction via the deterministic `QuestReward` item-quantity rail: `sister_vestments` / `saintess_vestments` (vessel branch), NO holding check, event context carries `char`/`host`/`item`. Tests per §7 (all four cases): ordinary → exactly one sister robe; vessel branch without robe → exactly one saintess robe; already-carrying-key initiate still receives its one; rollback returns it. Annotate ID 3.

- [ ] 1.4 Edit `violet_altoria` in `world/lore/player_presets/data_pack_cards.py`: drop `saintess_vessel` from `passive_skills`, drop `saintess_vestments` from `starting_items`; DELETE the persona's religious narrative — no 聖女/聖女繼承人 wording anywhere, public identity loses the church clause, temple-blessing personality passages and consecration/倾湧-duty life-story sentences removed by deletion, NOT rewritten into a successor framing, story otherwise continuous. Update the preset data-contract tests; run a repo-wide authored-content search for the deleted framing (successor reframings count as failures to revert). Annotate ID 4.

## 2. Lore, docs, and gates

- [ ] 2.1 Lore realignment: `docs/lore/overview.md` §宗教信仰 — retire the once-per-generation donated-princess framing and any sibling wording to "any female royal may be donated to the church and consecrated at enrollment"; `docs/lore/skill-trees/light.md` 聖女 footnote → enrollment grant; `docs/lore/settlement-locations.md` §神殿／聖所 〔提案〕→〔已實作〕 for the ministry counter. Search-prove the retired claim appears nowhere. Annotate ID 5.

- [ ] 2.2 Player-command docs trio for this change's surface: document `church join` (+ 入教／洗禮 aliases) in `docs/game/commands.md` AND `docs/game/command-reference.md` in this change; keep `tests/test_command_docs.py` green over the new surface (pray/offer and redeem/merit are documented by their own landing changes). Annotate ID 6.

- [ ] 2.3 Register every new test module in exactly one `.github/evennia-shards.json` shard and put data-contract-tagged modules in the test-data ledger files; list them in the PR body. After the deltas sync to main specs, run `uv run --locked python -m tools.spec_traceability check` and confirm all 8 IDs above resolve with zero uncovered requirements and zero unknown-annotation errors (IDs 7/8 resolve against the UPDATED main-spec text).
