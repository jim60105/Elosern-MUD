## Why

The owner capped this sub-project at eight hours (one engineer-day) per
OpenSpec change; the superseded `implement-church-core` is re-cut into four,
and this is its **accrual layer**: the two merit-earning behaviours the church
sells its grace by — `church pray` (time cost) and `church offer` (explicit
sexual offering judged by arousal, never affinity) — plus the
`climax_while_enrolled` side-reaction row that makes the erotic practice itself
devotion. The ledger, rulebook gates, `ChurchHost`, and church venues landed
with `implement-church-foundation`; enrollment landed with
`implement-church-enrollment`. Authoritative design:
`docs/superpowers/specs/2026-09-22-church-system-design.md` §5.2/§5.3/§5.4/§7.

## What Changes

- `church pray` → `world/rules/church.py::pray_step(char)`: ledger required
  (the unenrolled are told to speak with the celebrant), church-flag venue
  check on the derived set, daily cap, world-clock advance by the foundation's
  tuned duration (the prayer IS the time cost; existing non-combat clock
  source), `pray_completed` accrual, commit, `church_pray` event. Deterministic,
  no rolls; every rejection inert.
- `church offer <npc> [row_key]`: enrollment-only gate (NOT venue-bound —
  ministry travels with the sister); menu = `OFFERING_CATALOG` rows whose
  `act_key` the initiate already owns through the existing unlock-counter
  projection (no new unlock system; the foundation's seed rows become live here
  and the redemption change's Series D rows later extend the same menu by
  shared key); acceptance = NPC `entity.sexual.arousal` ordinal → the
  monotonic `acceptance` curve → injected `roll_d100`, NO affinity term;
  accept = the act through the action-resolution pipeline + same-transaction
  merit + copper → `church_offering_accepted`; decline =
  `church_offering_declined`, zero writes, no cooldown, instantly
  re-proposable. Normal partnered sex never auto-counts and stays
  byte-identical.
- `climax_while_enrolled` accrual wired on the `state_reactions.yaml`
  side-reaction rail (entering 進行中 while enrolled); the unenrolled climax
  settlement stays byte-identical (the row's enrollment condition fails
  closed).
- The pipeline-wide offline-determinism / five-event observability requirement
  lands here (design §6/§7): all state writes inside `transaction.atomic()`,
  events only through the `world.observability` facade, commit-bound; the
  AI-dead smoke over these paths (pray/offer/climax-accrual, dialogue model
  stubbed to raise) is its first covering test — the full cross-change
  end-to-end proof lands with `implement-church-combat-ministry`.
- Docs trio for the `church pray` / `church offer` surface in
  `docs/game/commands.md` + `docs/game/command-reference.md`,
  `tests/test_command_docs.py` green.

## Capabilities

### New Capabilities
None — the `church-ordination` capability is opened by
`implement-church-foundation`; this change's delta purely ADDS its accrual
requirements onto it.

### Modified Capabilities
None. The offering menu's Series D keys reference registry rows the redemption
change will register; the offering row validator already pins key resolution,
and until those rows exist the advanced rows simply project as never-owned.

## Dependencies

depends-on: implement-church-foundation
depends-on: implement-church-enrollment

Needs the ledger + accrual primitives and `church.yaml` pray/acceptance/offering
rows (foundation) and an existing enrollment to gate on (enrollment change).
Consumes verbatim: `action-resolution-pipeline` (offering act execution rails),
`sexual-transition-rulebook` (NPC arousal ordinal), the injected-dice
`roll_d100` gate, `world-clock` + `climax-settlement`, the
`state_reactions.yaml` side-reaction rail, the existing counter-gated act-unlock
projection.

Size: ≤ 8 tasks / one engineer-day.

## Impact

- New: `church pray` / `church offer` subcommands on `commands/church.py`
  (created by the enrollment change); the accrual section of
  `world/rules/church.py`.
- Edited: `world/rules/rulebook/state_reactions.yaml` (+ the enrollment-gated
  row), `.github/evennia-shards.json`, the docs trio.
- No new catalogue data (the foundation's seed offering rows go live; price/
  key additions belong to the redemption change), no affinity gate, no LLM
  participation (offline determinism), no compat shims (unreleased project).

## Batch:

depends-on: implement-church-foundation
depends-on: implement-church-enrollment

Code-conflict notes: appends subcommands to the enrollment-owned
`commands/church.py` and accrual primitives to the foundation-owned
`world/rules/church.py`; touches no `REDEEM_CATALOG` / price content.
`implement-church-redemption` queues behind this change only for the docs-trio
split (it documents redeem/merit once pray/offer are documented);
`implement-church-combat-ministry` queues behind redemption. No other active
change exists at proposal time.
