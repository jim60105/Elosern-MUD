## RENAMED Requirements

- FROM: `### Requirement: Skill proficiency is a per-entity, per-skill counter independent of magic_level`
- TO: `### Requirement: Skill proficiency is a per-entity, per-skill counter independent of magic_power`

## MODIFIED Requirements

### Requirement: Skill proficiency is a per-entity, per-skill counter independent of magic_power
`world/rules/progression.py` SHALL store per-skill practice progress in a new, additive raw attribute,
`entity.db.skill_proficiency: dict[str, float]`, distinct from `entity.traits.magic_power` and from
change 5's `entity.db.skills`/`entity.db.skill_grants`. No function in this module SHALL write to
`entity.traits.magic_power` as a side effect of a skill-proficiency grant, and no function SHALL write
to `entity.db.skill_proficiency` as a side effect of a magic-XP grant.

#### Scenario: Granting skill practice XP does not affect magic_power or its XP accumulator
- **WHEN** `grant_skill_practice_xp(entity, "shadow_slash")` is called
- **THEN** `entity.traits.magic_power.value` and `entity.db.magic_xp` are both unchanged

#### Scenario: Granting magic study or combat-kill XP does not affect skill_proficiency
- **WHEN** `accrue_magic_study([entity], 3600, AdvanceSource.SKIP)` or `grant_combat_kill_xp(entity,
  "low")` is called
- **THEN** `entity.db.skill_proficiency` is unchanged
