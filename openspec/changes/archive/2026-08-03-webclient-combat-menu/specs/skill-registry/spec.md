## MODIFIED Requirements

### Requirement: SkillDef carries the action resolver's skill-owned faction constraint
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with the required fields `key`, `label`, `description`, `kind`, `target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, and `faction_constraint`. `label` and `description` SHALL be nonempty Traditional Chinese player-facing strings bounded to 128 and 512 Unicode code points respectively. `faction_constraint` SHALL be a `FactionConstraint` value (`ANY`, `ALLY`, `ENEMY`, or `SELF_ONLY`) and SHALL default to `ANY`. Its `cost` and `effects` collections SHALL reject mutation. Every production registry entry, including dynamically registered innate skills, SHALL supply all ten fields directly; no generated key fallback or permissive metadata default SHALL exist.

#### Scenario: Every skill exposes immutable targeting and presentation metadata
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected after startup registration
- **THEN** it has all ten documented fields, its `faction_constraint` is a `FactionConstraint`, and its bounded label and description are nonempty

#### Scenario: Direct offensive seed skills target enemies
- **WHEN** the `fire_ball` and `wind_blade` definitions are inspected
- **THEN** their `faction_constraint` is `FactionConstraint.ENEMY`

#### Scenario: Innate skills have curated display text
- **WHEN** `basic_attack` and dynamically registered `flee` are presented to a player
- **THEN** both use their explicit registry label and description rather than exposing a generated key or raw effect ID

#### Scenario: Existing constructors do not receive a compatibility default
- **WHEN** a caller constructs `SkillDef` without `label` or `description`
- **THEN** construction fails and the caller must be updated to the current exact definition contract
