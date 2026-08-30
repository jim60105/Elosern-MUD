## REMOVED Requirements

### Requirement: Skill proficiency is a per-entity, per-skill counter independent of magic_power
**Reason**: the storage contract survives verbatim inside `skill-lineage`'s accrual requirement; the capability is folded so one spec owns proficiency end to end.
**Migration**: The new `skill-lineage` capability owns proficiency storage, derivation, accrual, and atomicity from this change forward.

### Requirement: grant_skill_practice_xp scales only by race learning_multiplier, never by conferred growth-rate buffs
**Reason**: superseded by `skill-lineage`: practice accrual now DOES read `growth_rate_multiplier` — the buff regains its live reader with the magic-XP engine gone.
**Migration**: The new `skill-lineage` capability owns proficiency storage, derivation, accrual, and atomicity from this change forward.

### Requirement: skill_proficiency_level is a pure, unbounded derived query
**Reason**: re-homed by `skill-lineage`: the formula survives, and the derivation is bounded by the per-consumer tip cap once `skill-lineage`'s saturation rule applies.
**Migration**: The new `skill-lineage` capability owns proficiency storage, derivation, accrual, and atomicity from this change forward.

### Requirement: Successful active-skill resolution records one practice grant atomically
**Reason**: generalized by `skill-lineage`'s accrual requirement (all ACTIVE skills, full multiplier formula, per-tick dedupe).
**Migration**: The new `skill-lineage` capability owns proficiency storage, derivation, accrual, and atomicity from this change forward.
