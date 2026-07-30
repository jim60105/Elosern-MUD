## MODIFIED Requirements

### Requirement: SkillDef carries the action resolver's skill-owned faction constraint
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with the fields `key`, `kind`,
`target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, and `faction_constraint`.
`faction_constraint` SHALL be a `FactionConstraint` value (`ANY`, `ALLY`, `ENEMY`, or `SELF_ONLY`)
and SHALL default to `ANY`. Its `cost` and `effects` collections SHALL reject mutation.

#### Scenario: Every skill exposes its immutable targeting policy
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected
- **THEN** it has all eight documented fields and its `faction_constraint` is a
  `FactionConstraint` value

#### Scenario: Direct offensive seed skills target enemies
- **WHEN** the `fire_ball` and `wind_blade` definitions are inspected
- **THEN** their `faction_constraint` is `FactionConstraint.ENEMY`
