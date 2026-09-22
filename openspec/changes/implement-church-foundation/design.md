## Context

The authoritative design is
`docs/superpowers/specs/2026-09-22-church-system-design.md` (approved, five
owner amendments baked in). The owner additionally capped every change at one
engineer-day, so the superseded `implement-church-core` re-cut into five: this
foundation, then enrollment / accrual / redemption / combat-ministry, alongside
the already-proposed order-catalogue (design §8 rewritten to the six-row
reality). This change ships the substrate with zero player-visible surface. See
`proposal.md` for
motivation and the `church-ordination` delta spec for requirements.

## Goals / Non-Goals

**Goals:**
- Land `db.church`, `church.yaml` (both loader gates + correspondence gate),
  the frozen `world/lore/church/` catalogues, and the authored
  venues/hosts/ChurchHost content in ≤ 8 tasks.
- Make the iron rule mechanical at this layer: the monotonicity gate and the
  PASSIVE polarity gate exist and reject planted-bad rows before any content
  change can ship effects.

**Non-Goals:**
- No commands, no enrollment/pray/offer/redeem mechanics — those are
  `implement-church-enrollment` / `-accrual` / `-redemption`.
- No Series A/B/D registry rows or price finals (`implement-church-redemption`);
  no Series C/E or title ladder (`implement-church-order-catalogue`).
- No threat/aggro table (design §3), no quest channel, no affinity gate, no LLM
  in any mechanic.

## Decisions

**D1 — One capability, `church-ordination`, opened here.** The pipeline's
halves are only observable together (an accrual row means nothing without the
ledger that receives it); five changes ADD requirements to the same capability,
each purely additive, so no delta ever MODIFIES another change's requirement.
The `settlement-place-registry` capability is NOT delta'd: the `church` kwarg
is ordinary authored content under its existing free-form kwargs contract.

**D2 — Ledger is a plain dict on `db.church`, lazily created.** Mirrors
`climax_today`'s daily-reset pattern; merit stays a dict int, never entering
`db.wallet`/currency paths — the non-currency property is enforced by the
absence of any writer, tested at the wallet boundary.

**D3 — `ChurchHost` is a sibling `GuildStaff` component, not a `Merchant`
extension.** Same capability-adapter shape (zero state writes), authored on the
celebrant NPC roster row via her profession blueprint kwargs (the sanctum steward
stays a plain merchant per owner decision; ministry is the celebrant's office
alone). The
three-stage join flow itself lands with the enrollment change; the component
and its roster authoring land here because the accrual change's venue check and
the enrollment change's host resolution both read it.

**D4 — Catalogue shells ship validated-but-empty.** The lore package's
frozen-dataclass discipline validates at import; an empty `OFFERING_CATALOG`
tuple is trivially valid to the validator, so the shell ships with seed rows
for currently-ownable act keys only (they stay inert until the offering rail
lands in `implement-church-accrual`), and `REDEEM_CATALOG` ships as a
validated empty shell whose row validator (keys, tier, polarity vocabulary)
is exercised by planted-row tests. The 16 Series A/B/D rows and their price
finals arrive with `implement-church-redemption`; nothing in this change
consumes a non-empty redemption catalogue, so no placeholder prices exist to
remove.

**D5 — Polarity gate is loader + data-contract test (owner's iron rule).** The
loader rejects PASSIVE rows whose authored effects are negative-vs-baseline at
load; a second data-contract test enumerates SHIPPED rows and is written
catalogue-driven, not hardcoded, so it must pass untouched when the sibling
order-catalogue change adds the Series C passives (defense: mitigation of an
EXISTING penalty counts positive — `temple_endurance` depends on that reading).

**D6 — Tuning finals decided here, price finals deferred.** The acceptance
intermediates (owner baseline: ordinal 0 = 50%, top = 100%, strictly monotonic;
proposal 50/65/80/90/100), pray numbers (proposal: 600 s, +40 merit, cap
3/day), and the accrual/payout band (climax +10, per-row offering merit,
integer copper band + overrides) are decide-and-record tasks here because
everything downstream prices against them. The 16-key price-band final moves
to the redemption change, which owns the rows being priced.

## Risks / Trade-offs

- [Empty-ish catalogues tempt a downstream change to bypass the shell] → the
  shell's validator and key-resolution data tests grow in place; the
  redemption change appends rows behind the same validator.
- [The polarity data-contract test hardcodes shipped keys and rots when
  Series C lands] → D5 mandates a catalogue-driven enumeration.
- [Adding `ChurchHost` kwargs to the celebrant roster row touches place
  authoring] → `place-driven-service-sync` convergence is roster-authoritative;
  the tasks verify sync idempotence with the new component and a non-empty
  derived church-place set.
- [Acceptance curve ships as tuning placeholders] → finals decided in tasks §1
  and recorded into `church.yaml` comments; the monotonicity gate prevents a
  future retune from breaking the invariant.

## Migration Plan

Unreleased project: no data migrations. `db.church` appears lazily; the place
and NPC authoring is data content. Rollback = revert the change commits;
nothing else persists church state.

## Open Questions

None. The three tuning placeholders (acceptance intermediates, pray numbers,
accrual/payout band) are decide-and-record tasks in `tasks.md` §1, per the
design doc deferring them to this change; the price-band final is the
redemption change's decide-and-record task.
