# skill-proficiency-tracking Specification

## Purpose
Define per-entity, race-scaled skill practice progression independent of magic levels.

## Requirements

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

### Requirement: grant_skill_practice_xp scales only by race learning_multiplier, never by conferred growth-rate buffs
`world/rules/progression.py` SHALL define `grant_skill_practice_xp(entity, skill_key, uses=1)` to add
`uses * SKILL_PRACTICE_XP_PER_USE * RaceProfile.learning_multiplier` (or `* 1.0` for an entity with no
race) to `entity.db.skill_proficiency[skill_key]`. This function SHALL NOT read or apply change 6's
`growth_rate_multiplier(entity)`.

#### Scenario: An elf's skill practice gain reflects the race's 10x learning speed
- **WHEN** `grant_skill_practice_xp(elf_entity, "dual_wield_style")` is called once (`uses=1`) on an
  elf entity (`learning_multiplier == 10.0`) with no prior proficiency in that skill
- **THEN** `entity.db.skill_proficiency["dual_wield_style"]` equals exactly `SKILL_PRACTICE_XP_PER_USE
  * 10.0`

#### Scenario: A conferred_growth_rate buff does not affect skill practice gain
- **WHEN** `grant_skill_practice_xp(entity, "dual_wield_style")` is called on an entity that has an
  active `conferred_growth_rate` buff (`growth_rate_multiplier(entity) != 1.0`)
- **THEN** the resulting practice-XP gain equals `SKILL_PRACTICE_XP_PER_USE *
  RaceProfile.learning_multiplier` only — the buff's multiplier is not applied

#### Scenario: Multiple uses accumulate linearly
- **WHEN** `grant_skill_practice_xp(entity, "flash_step", uses=5)` is called on an entity with
  `learning_multiplier == 1.0` and no prior proficiency in that skill
- **THEN** `entity.db.skill_proficiency["flash_step"]` equals exactly `5 * SKILL_PRACTICE_XP_PER_USE`

### Requirement: skill_proficiency_level is a pure, unbounded derived query
`world/rules/progression.py` SHALL define `skill_proficiency_level(entity, skill_key)` as
`floor(accumulated_practice_xp / SKILL_PROFICIENCY_XP_PER_LEVEL)`, returning `0` for a skill with no
recorded practice, with no upper bound enforced by this function.

#### Scenario: A skill never practiced returns proficiency level 0
- **WHEN** `skill_proficiency_level(entity, "never_practiced_skill")` is called on an entity with no
  entry for that key in `entity.db.skill_proficiency`
- **THEN** it returns exactly `0`

#### Scenario: Accumulated practice XP converts to a whole proficiency level
- **WHEN** `entity.db.skill_proficiency["shadow_slash"]` equals exactly `3 *
  SKILL_PROFICIENCY_XP_PER_LEVEL + 1`
- **THEN** `skill_proficiency_level(entity, "shadow_slash")` returns exactly `3`

#### Scenario: skill_proficiency_level performs no write
- **WHEN** `skill_proficiency_level(entity, skill_key)` is called any number of times
- **THEN** `entity.db.skill_proficiency` is unchanged before and after every call

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
