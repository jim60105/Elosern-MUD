## RENAMED Requirements

- FROM: `### Requirement: SkillDef carries the action resolver's skill-owned faction constraint`
- TO: `### Requirement: Skills declare only self-only or free target scope`

## MODIFIED Requirements

### Requirement: Skills declare only self-only or free target scope
Every skill in `SKILL_REGISTRY` SHALL declare its `faction_constraint` explicitly. All attack and
recovery skills SHALL use `FactionConstraint.ANY` (freely targetable among enemies and allies). Only a
skill whose effect is inherently self-only SHALL use `FactionConstraint.SELF_ONLY` and restrict its
target to the actor. No skill SHALL be restricted to enemies or allies only.

#### Scenario: Attack skills can hit companions
- **WHEN** a player casts any attack skill (`basic_attack`, `fire_ball`, `wind_blade`, `shadow_slash`) at an explicit companion target or an AREA selection including companions
- **THEN** the targets pass faction validation and receive damage (with the friendly-fire penalty applying to companion hits)

#### Scenario: Recovery skills can target allies and foes
- **WHEN** a player casts a recovery skill at an ally, a companion, or an enemy
- **THEN** the target passes faction validation and the skill resolves normally

#### Scenario: Self-only skills accept only the actor
- **WHEN** a `SELF_ONLY` skill is validated against any target other than the actor
- **THEN** the target is rejected at the faction check

#### Scenario: No skill is enemy-restricted
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** no skill declares an ENEMY-only or ALLY-only constraint
