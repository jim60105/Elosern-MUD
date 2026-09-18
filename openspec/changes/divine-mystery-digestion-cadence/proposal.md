## Why

神之秘法 nodes are zero-cost, no-cooldown and tier-less by design
(`docs/lore/skill-trees/divine-mystery.md` §0). The only shipped brake on practice accrual is the
per-tick `(actor, skill, target)` dedupe, which stops same-tick spam but nothing day over day: at the
elf ×10.0 learning multiplier a canopy node is 50 accruals, so an entire divine family would unlock
in under a minute of repeated free out-of-combat casts. The lore redesign ratified a category-scoped
brake — the 消化節拍 — and no divine-mystery catalog can land honestly without it.

## What Changes

- Add a per-world-calendar-day accrual claim for ACTIVE skills in `SkillCategory.DIVINE_MYSTERY`: at
  most one use-driven practice accrual per actor per skill per calendar day. The cadence governs
  the per-use resolution pathway only; declared booked practice is not a use and is unchanged.
- Scope the brake by **category**, never by `requires_divine_arts`. The 情慾秘術 divine line
  (`divine_sexual_arts`, the seven 神性 acts, `divine_sexual_mastery`) keeps its current accrual
  behavior byte-for-byte.
- Order the cadence gate before the existing per-tick claim, so a day-blocked use never consumes a
  tick claim it cannot turn into an award.
- Persist the claim on the actor and register it in the three snapshot attribute tuples, so a
  rolled-back commit does not burn the day.
- Derive the calendar day deterministically from the world clock's own calendar; wall-clock time is
  never read.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `divine-mystery`: ADDED — the digestion-cadence accrual rule, its category scope, its per-skill
  independence, and its rollback behavior.
- `skill-lineage`: MODIFIED — the practice-accrual requirement names the one category-scoped
  exception and points at `divine-mystery` as its authority, so the two specs cannot drift.

## Impact

`world/rules/progression.py` (the cadence gate and its claim store); `world/rules/action.py`
(`_snapshot_entity_state`/`_restore_entity_state`, the mechanism behind the `progression` surface and
the combat round path) plus the explicit snapshot attribute tuples in `world/rules/cast_settlement.py`
and `world/rules/clock.py` — the new attribute must roll back wherever `skill_proficiency` already
does; a new behavior test module plus its `.github/evennia-shards.json` registration. No registry data,
no player command, no presentation surface changes.

## Batch

- depends-on: none
- Code conflict note for the supervisor: this change edits `_snapshot_entity_state` /
  `_restore_entity_state` in `world/rules/action.py`, while `conferral-grant-store` and
  `divine-veil-cast-path` edit that file's effect-handler and registration regions. The regions are
  disjoint, so the three can run in one batch, but they share the file.
