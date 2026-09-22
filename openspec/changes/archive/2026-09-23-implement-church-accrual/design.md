## Context

The authoritative design is
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.2/§5.3/§5.4/§6/§7.
The substrate (`db.church`, `church.yaml` accrual/acceptance/pray/offering rows
with both loader gates, `ChurchHost`, derived church venues, offering-shell
seed rows) landed with `implement-church-foundation`; `church join` and the
office branch landed with `implement-church-enrollment`. This change turns the
tuned rows into the two earning behaviours and the climax side-reaction. See
`proposal.md` for motivation and the delta spec for requirements.

## Goals / Non-Goals

**Goals:**
- Ship `church pray`, `church offer`, and `climax_while_enrolled` wiring in
  ≤ 8 tasks, with the exhaustive ordinal × boundary-die acceptance matrix and
  the unenrolled byte-identical climax baseline as first-class tests.
- Land the pipeline's observability requirement over these paths
  (`church_pray`, `church_offering_accepted`, `church_offering_declined`) with
  the AI-dead smoke over them.

**Non-Goals:**
- No redeem/merit or Series A/B/D rows (redemption change), no charges
  primitive or combat rails (combat-ministry change), no title ladder
  (order-catalogue change).
- No new unlock machinery (the menu projects existing counters), no affinity
  term anywhere, no cooldown or penalty on decline, no venue binding for
  offering, no auto-counting of normal sex.

## Decisions

**D1 — Acceptance is read → curve → injected `roll_d100`; decline is inert.**
No cooldown, no penalty: the arousal curve itself moves with the clock (design
§5.3). The loader's monotonicity gate (foundation) makes the curve's shape a
load-time invariant, so tests only need the exhaustive ordinal × boundary-die
matrix over the tuned finals.

**D2 — The offering menu is a projection, not a copy.** Selectability is
computed from the existing counter-gated act-unlock state over
`OFFERING_CATALOG.act_key`; the foundation's seed rows go live untouched, and
the redemption change's Series D rows join the same menu by shared key with
zero duplicated data and zero code change here.

**D3 — Accepted settlement runs the act through the action-resolution pipeline
first, then ledger + wallet in the same transaction.** All pleasure/shame/
exposure/counter rails run their normal paths on both bodies; the church
transaction adds merit + copper on top, so a rollback removes the settlement
but the test asserts the rails themselves were the ordinary ones (normal sex
byte-identical baseline covers the non-offering path).

**D4 — Climax accrual is data on the existing side-reaction rail.**
`climax_while_enrolled` rides `state_reactions.yaml` with an enrollment
condition that fails closed — no new hook, no writer outside
`world/rules/church.py`'s accrual primitive; the unenrolled settlement stays
byte-identical because the row simply never fires.

**D5 — The observability requirement splits coverage, not text.** This change
owns the requirement (split-finer from the superseded core's
five-event-omnibus) and covers pray/offer/decline with its own AI-dead smoke;
the cross-change end-to-end loop proof (join → pray → offer → climax → redeem)
lands with combat-ministry, whose test satisfies the same requirement ID plus
its combat-rails text.

## Risks / Trade-offs

- [Series D offering rows don't exist yet, tempting this change to seed
  placeholder keys] → forbidden: the menu projects what exists; redemption
  appends the real advanced rows behind the foundation's validator.
- [Acceptance matrix combinatorics balloon the test] → the matrix is ordinal
  (5) × boundary dice (edge values around each percent) over one row; the
  monotonicity gate removes the need to re-prove curve shape per row.
- [Decline "re-proposable" can mask a hidden cooldown] → the re-propose test
  asserts immediate second proposal with byte-identical state between.

## Migration Plan

Unreleased project: no data migrations. Rollback = revert; the side-reaction
row and subcommands vanish together.

## Open Questions

None. All numbers are foundation §1 finals read from `church.yaml`.
