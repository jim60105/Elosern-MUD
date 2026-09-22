## Why

The owner capped this sub-project at eight hours (one engineer-day) per OpenSpec
change; the original `implement-church-core` (28 tasks, three independently
deliverable subsystems) violated the cap and is superseded by this four-change
split plus the already-proposed order-catalogue change. The authoritative
design (`docs/superpowers/specs/2026-09-22-church-system-design.md`, five owner
amendments baked in) still governs everything; this change is its **foundation
layer**: the substrate every other church change builds on, with zero
player-visible surface.

## What Changes

- New character ledger `db.church` (merit, enrolled tick, redeemed keys, daily
  counters with clock-day reset) — merit is a non-transferable,
  non-spendable-elsewhere counter; all writes live in the new
  `world/rules/church.py` (single-writer boundary, `transaction.atomic()`
  discipline). No command, typeclass, AI, or presentation module may write it.
- New rulebook slice `world/rules/rulebook/church.yaml` (accrual, acceptance
  curve, pray, offering rows) through the existing `load_rules` family, with
  the one-row-one-test correspondence gate and two loader gates: the strictly
  monotonic acceptance curve, and the passive-no-negativity polarity gate (iron
  rule — no PASSIVE row may carry a negative-relative-to-baseline effect;
  trade-offs live in prices, never in effects). The tuning finals this slice
  prices against — acceptance-curve intermediates, pray numbers, accrual and
  payout band — are decided and recorded here (the price-band final moves to
  `implement-church-redemption`).
- Frozen lore catalogues in `world/lore/church/`: `OFFERING_CATALOG` and
  `REDEEM_CATALOG` shells with their row validators, plus the derived
  church-place set from places authoring a `church` kwarg (the `shop_key`
  derivation pattern, duplicate-kwarg fail-closed). Offering rows seed the
  currently-ownable act keys and stay inert until
  `implement-church-accrual` wires the offering rail; `REDEEM_CATALOG` stays a
  validated shell — its 16 Series A/B/D rows and price finals land with
  `implement-church-redemption`.
- `ChurchHost` typeclass component (sibling of `GuildStaff`, zero-state
  capability adapter) authored on the one registered clergy NPC roster row
  (艾莉安娜·寒水 high celebrant) through her profession blueprint, plus the
  small raised-initial-arousal authoring kwarg on her spawn data and the
  `church` place kwarg on the church place records. Per owner decision the
  聖所執事 (羅海西亞·芬威克) stays a plain merchant who only sells the
  sanctum's wares — ministry is the celebrant's office alone (nuns join the
  roster in a later sub-project). `place-driven-service-sync` convergence
  stays idempotent with the new component.

## Capabilities

### New Capabilities
- `church-ordination`: opened by this change with its substrate requirements —
  the ledger/single-writer contract, the rulebook slice behind its two loader
  gates, the authored church venues and clergy hosts, and the frozen lore
  catalogues. The sibling church changes each ADD their own requirements to
  this same capability (enrollment, pray/offering/accrual, redemption, combat
  ministry); none modifies another's.

### Modified Capabilities
None. The `church` venue kwarg rides the place registry's existing free-form
authored-component-kwargs contract and the `ChurchHost` attachment rides the
existing profession-blueprint roster derivation
(`settlement-place-registry` and `place-driven-service-sync` consume the new
authored content verbatim).

## Dependencies

depends-on: (none — prerequisite capabilities already landed/archived)

Size: ≤ 8 tasks / one engineer-day. Consumed verbatim: `guild-registration`
(the host-component shape), `shop-economy` / integer copper, `world-clock`
(daily-reset pattern of `climax_today`), the rulebook `load_rules` family with
the one-row-one-test gate (`combat_modifiers.yaml` audit pattern), and the
place-driven service sync.

## Impact

- New: `world/rules/church.py` (sole writer, ledger primitives only at this
  stage), `world/rules/rulebook/church.yaml`, `world/lore/church/`
  (`OFFERING_CATALOG`, `REDEEM_CATALOG` shell, church-place derivation),
  `ChurchHost` component (sibling of `GuildStaff`).
- Edited: the celebrant NPC roster row (+ `ChurchHost` blueprint kwargs, +
  raised-initial-arousal authoring kwarg; the sanctum steward's merchant row
  is authored with no ChurchHost and no arousal seed), the church place
  records (+ `church` kwarg), `.github/evennia-shards.json`.
- No player-visible surface, no commands, no docs trio change in this change;
  no quest channel, no LLM participation (offline determinism is a standing
  constraint on everything built on this substrate); no backward-compat shims
  (unreleased project).

## Batch:

depends-on: none

Code-conflict notes: owns `world/rules/church.py`, `world/lore/church/`, and
`church.yaml` — every other church change appends to them after this one
lands. `implement-church-enrollment`, `implement-church-accrual`, and
`implement-church-redemption` each queue behind this change;
`implement-church-combat-ministry` behind redemption;
`implement-church-order-catalogue` behind redemption (it appends
Series C/E rows to the redemption-owned `REDEEM_CATALOG`, clergy skill-registry
block, and `church.yaml`). No other active change exists at proposal time.
