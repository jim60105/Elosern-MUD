## Context

The authoritative design is `docs/superpowers/specs/2026-09-22-church-system-design.md` (approved, five owner amendments baked in). This change implements its §8 first half; see `proposal.md` for motivation and the `church-ordination` delta spec for requirements. The engine already provides every rail this change rides: the guild's three-stage host flow (`commands/guild.py`), place-derived service-host rosters with free-form authored kwargs (`shop_key` pattern), the rulebook `load_rules` family with the one-row-one-test gate, the injected-dice `roll_d100` gate, the action-resolution pipeline, NPC arousal state, the granted-passive write path (`lineage_ownership_closure` shape), the `QuestReward` item-quantity rail, the `state_reactions.yaml` side-reaction rail, `monster_behaviour_policy` (seeded `lowest_hp`/`highest_effective_power` tie-break), and `defeat_aftermath/violation::_victim_pool`.

## Goals / Non-Goals

**Goals:**
- Ship the ledger + rulebook + enrollment + pray + offering + redemption engine + Series A/B/D (16 rows) in ≤ one engineer-day (design §8 split is the sizing contract).
- Keep every mechanic offline-deterministic and every write inside `world/rules/church.py`.
- Land the byte-identical baselines as first-class requirements: unenrolled climax, no-seal monster decisions, no-martyr violation pool.

**Non-Goals:**
- Series C/E rows and the clergy title ladder/predicate family → `implement-church-order-catalogue` (queued behind this change; §9.2's family-extension sanction is recorded in the saintess-vessel delta, but the family itself ships there).
- Temple service economy (sub-project 2), confession/observance commands (sub-project 3) — merit ledger and `church` place flag are shaped for them but nothing more lands here.
- No threat/aggro table (design §3), no quest channel, no affinity gate, no LLM in any mechanic.

## Decisions

**D1 — One capability, `church-ordination`.** The pipeline's halves (ledger, rails, rows) are only observable together (an accrual row means nothing without the ledger that receives it); splitting into per-command capabilities would fragment the transaction/observability requirements. The `settlement-place-registry` capability is NOT delta'd: the `church` kwarg is ordinary authored content under its existing free-form kwargs contract.

**D2 — `ChurchHost` as a sibling `GuildStaff` component, not a `Merchant` extension.** The three-stage flow (`resolve_local_service_host` → `interaction_reason(host, "service_church")` → deterministic rules call) is byte-copied from `commands/guild.py`; the component stays a capability adapter with zero state writes (the same requirement shape guild-registration pins). Authored on the two clergy NPC roster rows (艾莉安娜·寒水 high celebrant, 羅海西亞·芬威克 sanctuary steward) via their profession blueprint kwargs.

**D3 — Vestment rides the `QuestReward` item-quantity rail, not the LLM `give_item` intent.** The rail is already deterministic and transactional; the dialogue intent would violate offline determinism. Presentation is authored prose around the deterministic grant ("the celebrant places the robe in your hands"). Unconditional handover is the owner's decision — the implementer must NOT add a holding check.

**D4 — The vessel branch reuses the enrollment transaction, not a post-commit hook.** Grant + event + ledger + vestment are one `transaction.atomic()`; `saintess_vessel_granted` emits via `transaction.on_commit` exactly as preset activation did, so the saintess-vessel spec's granted-event requirement transfers verbatim.

**D5 — `charges` is the one new buff primitive, tested in isolation.** Charge-on-event counters exist nowhere else; the rejected alternative (rule rows that remove buffs conditionally) cannot count. Implementation: one field on the buff declaration + one consumption hook on the climax-phase-into-進行中 transition, removal at zero. Everything else about `lamb_seal` is an ordinary buff.

**D6 — Lamb-seal narrowing lives BEFORE target-strategy evaluation in `monster_behaviour_policy`.** Candidate-set narrowing (preference) rather than score manipulation (threat): with zero seals the code path is literally untouched → byte-identity is structural, not asserted-by-test-only. Multi-seal order: player first, then ascending pk (canonical order precedent).

**D7 — Martyr filter is one added filter stage in `_victim_pool` keyed on the durable session id.** Stale stamps can never fire by construction (session-id equality gate first); the existing single-member short-circuit supplies the zero-target-roll property, so no dice behavior changes.

**D8 — Acceptance is read → curve → injected `roll_d100`; decline is inert.** No cooldown, no penalty: the arousal curve itself moves with the clock (design §5.3). The loader's monotonicity gate makes the curve's shape a load-time invariant, so tests only need the boundary-die matrix over the tuned finals.

**D9 — Ledger is a plain dict on `db.church`, lazily created.** Mirrors `climax_today`'s daily-reset pattern; merit stays a dict int, never entering `db.wallet`/currency paths — the non-currency property is enforced by the absence of any writer, tested at the wallet boundary.

**D10 — Polarity gate is loader + data-contract test (owner's iron rule).** The loader rejects PASSIVE rows whose authored effects are negative-vs-baseline at load; a second data-contract test enumerates shipped rows (defense: mitigation of an EXISTING penalty counts positive — Series C's `temple_endurance` in the sibling change depends on that reading).

## Risks / Trade-offs

- [Preset prose deletion leaves dangling narrative references elsewhere (other presets/lore quoting the consecration)] → the tasks include a repo-wide search for 聖女繼承人/consecration wording in authored content; only deletion, no reframing, per owner.
- [`charges` primitive interacts with buff save/restore and rollback] → isolated buff tests include save/restore round-trip and rolled-back-consumption cases before the lamb-seal integration test is trusted.
- [Series D rows double as offering rows: one bad act-key typo breaks both catalogues] → shared-key data-contract test enumerates every offering row's `act_key` against `SKILL_REGISTRY`/act catalogue.
- [The clergy NPC roster rows currently carry only the generic shop counter; adding `ChurchHost` kwargs touches place authoring] → `place-driven-service-sync` convergence is roster-authoritative; the tasks verify sync idempotence with the new component.
- [Acceptance curve ships as tuning placeholders] → finals decided in tasks 1.x and recorded into `church.yaml` comments + spec_traceability; the monotonicity gate prevents a future retune from breaking the invariant.

## Migration Plan

Unreleased project: no data migrations. `db.church` appears lazily; the preset edit is a data row change (no existing characters to migrate — pre-release). Rollback = revert the change commit; nothing else persists church state.

## Open Questions

None mechanical. The three tuning placeholders (acceptance intermediates, price bands, pray numbers) are decide-and-record tasks in `tasks.md` §1, per the design doc deferring them to this change.
