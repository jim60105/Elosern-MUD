## MODIFIED Requirements

### Requirement: Skills declare only self-only or free target scope
`world/skills/registry.py` SHALL define a frozen `SkillDef` dataclass with the required fields `key`, `label`, `description`, `kind`,
`target_spec`, `cost`, `usable_out_of_combat`, `element`, `effects`, `category`, and `faction_constraint`.
`label` and `description` SHALL be nonempty Traditional Chinese player-facing strings bounded to 128 and 512 Unicode code points respectively.
`faction_constraint` SHALL be a `FactionConstraint` value
and SHALL default to `ANY`. Every skill SHALL declare its `faction_constraint` explicitly: all attack and
recovery skills SHALL use `FactionConstraint.ANY` (freely targetable among enemies and allies); only a
skill whose effect is inherently self-only SHALL use `FactionConstraint.SELF_ONLY` and restrict its
target to the actor. Candidate selection SHALL NOT be restricted to enemies or allies only; an explicitly declared per-effect audience MAY deliver an individual component only to selected self/allies or enemies while leaving selection unrestricted; the legacy `ALLY`/`ENEMY`
enum values are retained for legacy test data and restrict nothing. Its `cost` and `effects` collections SHALL reject mutation. Every
production registry entry, including dynamically registered innate skills, SHALL supply all eleven
fields directly; no generated key fallback or permissive metadata default SHALL exist.

#### Scenario: Every skill exposes immutable targeting and presentation metadata
- **WHEN** any `SkillDef` in `SKILL_REGISTRY` is inspected after startup registration
- **THEN** it has all eleven documented fields, its `faction_constraint` is a
  `FactionConstraint`, and its bounded label and description are nonempty

#### Scenario: Attack skills can hit companions
- **WHEN** a player casts any attack skill (`basic_attack`, `fire_ball`, `wind_blade`, `shadow_slash`) at an explicit companion target or an AREA selection including companions
- **THEN** the targets pass faction validation and receive damage for ordinary selected-audience attacks (with the friendly-fire penalty applying to companion hits); a declared enemy-only effect component does not damage the companion

#### Scenario: Recovery skills can target allies and foes
- **WHEN** a player casts a recovery skill at an ally, a companion, or an enemy
- **THEN** the target passes faction validation and ordinary selected-audience recovery applies; explicitly routed components follow their declared audience

#### Scenario: Self-only skills accept only the actor
- **WHEN** a `SELF_ONLY` skill is validated against any target other than the actor
- **THEN** the target is rejected at the faction check

#### Scenario: No skill is enemy-restricted
- **WHEN** `SKILL_REGISTRY` is inspected
- **THEN** no skill declares an ENEMY-only or ALLY-only constraint

#### Scenario: Innate skills have curated display text
- **WHEN** `basic_attack` and dynamically registered `flee` are presented to a player
- **THEN** both use their explicit registry label and description rather than exposing a generated key or raw effect ID

#### Scenario: Existing constructors do not receive a compatibility default
- **WHEN** a caller constructs `SkillDef` without `label` or `description`
- **THEN** construction fails and the caller must be updated to the current exact definition contract
