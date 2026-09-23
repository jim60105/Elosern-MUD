## Context

The authoritative design is
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.7/§5.8/§6/§7.
Everything else in the loop already landed: ledger/gates (foundation),
`church join` (enrollment), pray/offer/climax accrual + the
`church_pray`/`church_offering_*` events (accrual), the redeem rail and all 16
rows incl. `rite_lamb_mark`/`rite_martyrdom_vow` as registered declarations
(redemption). This change lands the two combat rails and the cross-change
end-to-end proof. See `proposal.md` for motivation and the delta spec for
requirements.

## Goals / Non-Goals

**Goals:**
- Ship the `charges` primitive + consumption hook (isolated tests first), the
  lamb-seal narrowing, and the martyr filter in ≤ 8 tasks, with both
  byte-identical baselines (no-seal monster decisions, no-martyr violation
  pool) as first-class requirements.
- Land the E2E AI-dead loop test as one registered integration module — the
  pipeline-wide proof the earlier changes' tests assemble into.

**Non-Goals:**
- No threat/aggro table (design §3) — preference narrowing only.
- No new SKILL_REGISTRY rows, catalogue data, commands, or docs-trio changes
  (rows exist from redemption; the E2E redeems a Series A row).
- No touch on `REDEEM_CATALOG`/`church.yaml` — parallel-safe with
  order-catalogue.

## Decisions

**D1 — `charges` is the one new buff primitive, tested in isolation.**
Charge-on-event counters exist nowhere else; the rejected alternative (rule
rows that remove buffs conditionally) cannot count. Implementation: one field
on the buff declaration + one consumption hook on the climax-phase-into-進行中
transition, removal at zero. Everything else about `lamb_seal` is an ordinary
buff.

**D2 — Lamb-seal narrowing lives BEFORE target-strategy evaluation in
`monster_behaviour_policy`.** Candidate-set narrowing (preference) rather than
score manipulation (threat): with zero seals the code path is literally
untouched → byte-identity is structural, not asserted-by-test-only. Multi-seal
order: player first, then ascending pk (canonical order precedent).

**D3 — Martyr filter is one added filter stage in `_victim_pool` keyed on the
durable session id.** Stale stamps can never fire by construction
(session-id equality gate first); the existing single-member short-circuit
supplies the zero-target-roll property, so no dice behavior changes. Victory
consumes; died/fled markers fall through to the normal chain untouched.

**D4 — The E2E integration test lands here, as the batch's final proof.** It needs a
redeemable state (merit earned via pray/offer, a row redeemed via the
redemption rail) plus both combat rails absent-but-importable; landing it as
the batch's last mechanic change makes it the archive-gate proof for the whole
split. Its requirement also carries the pipeline-wide rollback-quiet clause,
satisfied at loop granularity (each stage's own change already pins its
transaction).

## Risks / Trade-offs

- [`charges` interacts with buff save/restore and rollback] → isolated buff
  tests (declaration round-trip, save/restore, two-transition sequence,
  rolled-back consumption does not burn) run BEFORE the lamb-seal integration
  test is trusted.
- [Seal narrowing accidentally changes AREA or positional-marker paths] →
  narrowing sits on the single-target candidate list only; AREA/marker tests
  pin non-substitution.
- [E2E test flakes on cross-change authoring drift] → it consumes only shipped
  finals (foundation prices/pray numbers, redemption row prices); if any drift
  breaks it, that IS the regression signal the batch queue promises.

## Migration Plan

Unreleased project: no data migrations. Rollback = revert; buff field,
narrowing stage, filter, and E2E module vanish together.

## Open Questions

None.
