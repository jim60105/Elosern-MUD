## Why

The owner capped this sub-project at eight hours (one engineer-day) per
OpenSpec change; the superseded `implement-church-core` is re-cut into four,
and this is its **combat-ministry layer**: the two tank-making rails that make
the clergy loop ("舍棄防禦") actually tankable — the lamb-seal target-preference
override built on the one new buff primitive, and the martyrdom-vow victim-pool
filter — plus the cross-change end-to-end proof of the whole loop. The rows
`rite_lamb_mark` / `rite_martyrdom_vow` registered with `implement-church-redemption`;
their rails land here. Authoritative design:
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.7/§5.8/§6/§7.

## What Changes

- `charges: int` buff-declaration primitive + climax-transition consumption
  hook: each transition of the bearer's climax phase into 進行中 consumes one
  charge; at zero the buff is removed. Tested in isolation FIRST (declaration
  round-trip, save/restore, two-transition consumption sequence, rolled-back
  consumption does not burn a charge). Its justification stands: charge-on-event
  counters exist nowhere else, and rule rows that remove buffs conditionally
  cannot count (design §5.7).
- `rite_lamb_mark` + `lamb_seal` narrowing in `monster_behaviour_policy`
  BEFORE target-strategy evaluation: if any living enemy carries `lamb_seal`,
  single-target candidates narrow to seal-bearers (multi-seal canonical order:
  player first, then ascending pk). No seal present → every decision
  byte-identical to today (structural, not asserted). AREA skills unaffected;
  positional markers orthogonal, never substituted. Tests: redirect over
  `lowest_hp`, multi-seal order, two-climaxes-lift, no-seal decision trace
  byte-identical.
- `rite_martyrdom_vow` session-record `martyr_key` stamp (durable session id) +
  ONE added filter in `defeat_aftermath/violation.py::_victim_pool`: valid
  stamp ∧ non-fled pool member → pool collapses to `[her]`, zero target rolls
  via the existing single-member short-circuit, resist contests keep their
  normal draws; victory consumes the stamp. Tests: collapse,
  died/fled/stale/no-stamp fallbacks byte-identical, victory consumption,
  rollback-retry determinism.
- The cross-change end-to-end integration test lands here as the pipeline
  proof: join → pray → offer → climax → redeem with the dialogue model stubbed
  to raise, all five events observed (`church_enrolled`, `church_pray`,
  `church_offering_accepted`, `church_offering_declined`,
  `church_skill_redeemed`) — one registered test module — plus the observability
  lint (facade-only, commit-bound, zero findings) over every touched module.

## Capabilities

### New Capabilities
None — the `church-ordination` capability is opened by
`implement-church-foundation`; this change's delta purely ADDS its combat-rail
requirements onto it.

### Modified Capabilities
None.

## Dependencies

depends-on: implement-church-redemption
depends-on: implement-church-foundation
depends-on: implement-church-enrollment
depends-on: implement-church-accrual

Hard dependency is redemption (the two rite rows exist there to be redeemed;
the E2E test redeems one). Enrollment/accrual are transitive prerequisites the
E2E loop walks; foundation is the ledger substrate. Consumes verbatim: the
buff store/declaration, `monster_behaviour_policy`, `defeat_aftermath/violation`
+ combat session record, `climax_settlement`, `world.observability`.
`implement-church-order-catalogue` is independent of this change (title side
vs combat side).

Size: ≤ 8 tasks / one engineer-day.

## Impact

- Edited: buff declaration (`charges` primitive) + the climax-transition
  consumption hook; `world/rules/monster_behaviour.py` (seal narrowing);
  `world/rules/defeat_aftermath/violation.py` (martyr filter); the combat
  session record stamp; `.github/evennia-shards.json`.
- No new commands, no docs trio change, no catalogue data, no SKILL_REGISTRY
  rows (they exist from redemption), no LLM participation (offline
  determinism), no compat shims (unreleased project).

## Batch:

depends-on: implement-church-redemption
depends-on: implement-church-foundation
depends-on: implement-church-enrollment
depends-on: implement-church-accrual

Code-conflict notes: owns `monster_behaviour.py`,
`defeat_aftermath/violation.py`, and the buff declaration — files no other
church change touches; touches no catalogue/`church.yaml`/registry-data file.
Runs in parallel with `implement-church-order-catalogue` once redemption is
archived; the E2E test requires enrollment + accrual + redemption archived but
not order-catalogue (it redeems a Series A row). No other active change exists
at proposal time.
