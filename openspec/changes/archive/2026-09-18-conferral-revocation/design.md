## Context

`world/rules/skill_effects.py` owns the conferral write; `world/rules/buffs.py` owns
`grant_conferred_growth_rate()`, which applies the `conferred_growth_rate` buff with
`instance_key=f"conferred_growth_rate:{source_key}"` and `stacking: unique_per_source`, so one target
can carry several instances from several sources. `conferral-grant-store` (a dependency) makes the
grant list replace-by-key. See `proposal.md` — Why for motivation.

## Goals / Non-Goals

**Goals:**

- One primitive that removes everything the conferral verb hands out, in one transaction.
- A skill-reachable prefix for it, so the catalog can mount it on a node with no further plumbing.

**Non-Goals:**

- Selective revocation by source or by skill (see D2).
- Any change to how a grant is written or read. That is `conferral-grant-store`'s contract.
- Immunity, resistance, or a contest against revocation. The lore prices it as unconditional.

## Decisions

### D1: One primitive clears both stores

A grant and a conferred growth rate are the two things the conferral verb produces, and they live in
two different stores (an entity attribute and the buff handler). Splitting revocation across two
primitives would let a caller clear half the conferral and leave the other half live. The handler
therefore declares both the `skill_grants` and `buffs` surfaces and performs both writes in the same
staged effect.

### D2: Revocation is total, not selective

The lore node is explicitly "一切授予，不論來源是誰". A selective form would need the caller to name a
source or a skill, which means an `event_context` key and a player-facing picker — precisely the
pattern `conferral-grant-store` removed from the conferral side. Totality also makes revocation a
readable counter-play: it answers "something out there is buffing this creature" without asking the
player to know what.

*Alternative rejected:* revoking only grants written by the caster. That makes the node useless against
an opposing caster, which is its entire reason to exist.

### D3: The prefix is bare

`revoke_grants` carries no payload, matching D2: any payload would imply the selectivity D2 rejects.
A payload form raises at parse, so a mistaken authoring fails at registry load rather than at cast.

### D4: Removing buff instances goes through the buff module, not the attribute

Buff instances are handler-managed with instance keys and active-state bookkeeping; reaching into
storage directly would bypass that. A `clear_conferred_growth_rates(entity)` helper in
`world/rules/buffs.py` removes every instance of the definition regardless of `instance_key`, keeping
the buff store the single writer of its own data.

## Risks / Trade-offs

- **A player revokes their own party's buffs by mistake** → accepted and legible: the effect is
  targeted, and its description says it removes all conferrals on the target.
- **Totality makes revocation strictly better than a selective version would be** → intended; the
  cost is the action and, for a divine node, the day of cadence it consumes.
- **A half-applied revocation on commit failure** → both writes are staged in one pending effect under
  the two declared surfaces, and a rollback test asserts both stores restore byte-equal.
