## MODIFIED Requirements

### Requirement: Skill proficiency is a per-entity, per-skill counter independent of magic_power
`world/rules/progression.py` SHALL store per-skill practice progress in a new, additive raw attribute,
`entity.db.skill_proficiency: dict[str, float]`, distinct from `entity.traits.magic_power` and from
change 5's `entity.db.skills`/`entity.db.skill_grants`. No function in this module SHALL write to
`entity.traits.magic_power` — which is static and has no writers — as a side effect of a
skill-proficiency grant.

#### Scenario: Granting skill practice XP does not affect magic_power
- **WHEN** `grant_skill_practice_xp(entity, "shadow_slash")` is called
- **THEN** `entity.traits.magic_power.value` is unchanged

#### Scenario: No magic-XP writer remains that could touch skill_proficiency
- **WHEN** `world/rules/progression.py` is inspected after the magic-XP engine retirement
- **THEN** `accrue_magic_study`, `grant_combat_kill_xp`, and any `entity.db.magic_xp` read or
  write are absent, and the only practice writers to `skill_proficiency` remain the
  practice-XP grant paths

### Requirement: Successful active-skill resolution records one practice grant atomically
`ActionResolver` SHALL stage `grant_skill_practice_xp(actor, skill_key)` after every successful active
skill resolution. The action rollback snapshot SHALL cover `skill_proficiency`, so a failed
later pending effect restores their pre-action values along with every other action surface.

#### Scenario: A successful active skill gains one practice increment
- **WHEN** an active skill resolves successfully through `ActionResolver`
- **THEN** the actor's proficiency for that skill increases by one scaled practice increment

#### Scenario: A failed action records no practice progress
- **WHEN** an action is rejected or its atomic commit fails
- **THEN** the actor's `skill_proficiency` state is unchanged
