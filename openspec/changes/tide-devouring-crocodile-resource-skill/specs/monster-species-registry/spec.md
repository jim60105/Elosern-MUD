# Spec Delta

## ADDED Requirements

### Requirement: Variant skill kits and behavior references are immutable authored configuration
Variants SHALL optionally carry ordered active/passive skill keys and a behavior-profile reference. Referenced skills SHALL resolve with matching kinds, compatible identity and usable prerequisites/effects; behavior references SHALL resolve in the existing behavior vocabulary before individual persistence.

#### Scenario: Invalid configuration creates nothing
- **WHEN** a variant references an unknown skill/profile, wrong kind, identity-ineligible skill, unusable prerequisite chain or unavailable effect
- **THEN** formal construction fails before persistence with no partial ownership/configuration

#### Scenario: No invented progression
- **WHEN** both crocodile variants author the prerequisite-free bite
- **THEN** they own it before innate attack with no new passive or fabricated progression chain

## MODIFIED Requirements

### Requirement: Numeric combat profiles and danger grades are balance-gated slots, never invented values
`MonsterVariant.combat_profile` SHALL be either `None` or a frozen record that carries a complete
value set (HP, MP, SP, physical combat power, agility, defense, `magic_power`) as literal authored
values, and `MonsterVariant.danger_grade` SHALL be either `None` or an authored guild danger grade.
Registry construction SHALL reject a partially populated profile, a non-integer value, a negative
value, and a `magic_power` outside the variant's tier magic band.

#### Scenario: A partial numeric profile is rejected
- **WHEN** a variant profile omits any one of the seven numeric fields or sets one to `None`
- **THEN** registry construction raises the named species-registry error and the variant is not published

#### Scenario: Flavour never becomes a number
- **WHEN** a variant whose narrative mentions magical or elemental behaviour is inspected
- **THEN** its magic power, MP and SP equal explicit approved literals, never values inferred from narrative; all twelve shipped variants retain zero magic power within their zero tier magic bands
- **AND** only the approved crocodile resource exceptions permit nonzero pools, bank_lurker MP/SP 30/40 and bay_warden 50/60; the other ten variants retain zero MP/SP

#### Scenario: Balance approval populates the same slot
- **WHEN** a balance-approved complete profile and grade are authored for one variant
- **THEN** the record validates with no schema change, and the previously empty slot is now the single source of truth that consumers read

#### Scenario: An unapproved slot still means "no approved profile"
- **WHEN** a variant whose approval has not been granted is read
- **THEN** its profile is `None` and its grade is `None`, and no consumer treats that as a zero or as an approved number

#### Scenario: An approved value is never re-derived at the registry
- **WHEN** a registry edit changes an approved literal to a value computed from another field, from a display name, or from the tier band
- **THEN** the shipped-content contract fails, because the approved literals are pinned and tier-band membership alone does not prove a value was approved

#### Scenario: MP and SP pools are gated by approval, not inference
- **WHEN** MP or SP literals are authored for a variant
- **THEN** MP and SP carry no tier band and require explicit approval; the two approved crocodile pools are accepted verbatim and every other unapproved nonzero pool is rejected

#### Scenario: Only explicit user balance approval populates a slot
- **WHEN** a profile or grade slot is populated
- **THEN** only an explicit user balance approval may populate it: the authored values SHALL be the
  approved values verbatim, and a registry edit SHALL NOT re-derive, re-tune, re-round, or
  interpolate them, nor infer any value from a display name, a description, a threat tier, or
  another variant

#### Scenario: Granted approval ships both profile and grade
- **WHEN** approval is granted for a variant
- **THEN** that variant SHALL ship the approved complete profile and the approved guild danger grade

#### Scenario: A None slot means no approved profile exists
- **WHEN** a slot is `None` on some future variant
- **THEN** a consumer SHALL treat it as "no approved per-variant profile exists": never as a zero,
  never as a per-species number invented from flavour, and never as tier-band truth about the
  variant itself

#### Scenario: The interim fallback is owned by individual construction
- **WHEN** a profile is `None` and a numeric value is needed
- **THEN** the single sanctioned numeric fallback is the named interim rule owned by individual
  construction, the existing threat-tier band construction at the variant's declared tier,
  recorded with its numeric source
- **AND** consumers SHALL NOT read the registry slot as if it carried that fallback

### Requirement: Special abilities are narrative boundaries with a named mechanics prerequisite, never fake skills
The registries SHALL NOT register, reference, or imply a skill key, behaviour profile, or combat trait
for the five deferred abilities (wind grain-shaking, lamp-mimicking glow, earth burrow-packing,
fog-channeling, rock-sonance). Crocodile contact MP drain SHALL be executable solely through its
authored shared-engine skill and validated kit, with no prose-derived effects.

#### Scenario: No behaviour seam is faked
- **WHEN** the shipped registry is inspected for skill keys, behaviour-profile keys, or combat traits naming the five deferred abilities
- **THEN** it carries none, and the ability prose remains in the published description fields only

#### Scenario: Narrative does not unlock a behaviour
- **WHEN** the existing behaviour-selection path resolves a variant whose narrative describes one of the five still-deferred special abilities
- **THEN** the resolved behaviour is exactly the existing damage-oriented decision path with no new effect, and the proposal records the mechanics prerequisite rather than an implementation

#### Scenario: Crocodile behavior comes from validated configuration
- **WHEN** the crocodile contact-drain ability is available in combat
- **THEN** its executable behavior comes from the validated authored kit and shared skill engine, never from interpreting narrative text

#### Scenario: Ability text is published narrative only

- **WHEN** ability text is authored for one of the five deferred abilities
- **THEN** it SHALL be permitted only as published narrative prose, including its approved limits

#### Scenario: Executable abilities are an external prerequisite

- **WHEN** an executable form of one of these deferred abilities is wanted
- **THEN** it is a named external prerequisite owned by the skill/behaviour-mechanics work; a
  registry field, a stored trait, or a placeholder value SHALL NOT stand in for it
- **AND** no consumer SHALL be permitted to interpret narrative text as an available effect

### Requirement: The approved first-batch profiles and grades are user-approved literals
The twelve shipped variants SHALL carry the exact complete approved profiles in the table stated in
the scenario below, except for the explicitly approved crocodile resource values and bite kit.
Magic power SHALL remain zero for all twelve; other ten variants retain zero MP/SP and unchanged
content. Newly constructed instances SHALL use these rows without live migration.

#### Scenario: New instance
- **WHEN** a registered variant constructs a new monster
- **THEN** its literal profile is authoritative without skill/gear coefficients baked in

The approval fence SHALL cover exactly these twelve variants. Each approved seven-value profile and danger grade SHALL equal the approval record, with no None slots. A different literal SHALL be a content defect rather than an implicit retuning decision.

#### Scenario: Every shipped batch variant carries its approved values
- **WHEN** the shipped registry is compared field by field against the twelve-variant approval record
- **THEN** all seven profile values and grades equal the approved literals and no approved slot is None

#### Scenario: Approval does not extend to unapproved content
- **WHEN** a variant outside the approved twelve carries a profile or grade without separate approval
- **THEN** the approved-content contract reports it rather than extending this approval

#### Scenario: The approved profile table is pinned verbatim

- **WHEN** the shipped registry is authored against the approval record
- **THEN** the twelve variants carry exactly the following approved literals:

| Variant key | Display name | Grade | Previous HP | Approved HP | Approved attack | Approved agility | Approved defense |
|---|---|---|---:|---:|---:|---:|---:|
| `grain_pecker` | 穗鳴雀・啄穗型 | F | 55 | 30 | 4 | 7 | 3 |
| `flock_leader` | 穗鳴雀・領群型 | E | 80 | 55 | 8 | 10 | 4 |
| `shore_walker` | 潮燈蟹・灘行型 | F | 70 | 30 | 5 | 4 | 5 |
| `reef_warden` | 潮燈蟹・守礁型 | E | 110 | 60 | 12 | 4 | 7 |
| `burrow_maker` | 築埂兔・掘巢型 | F | 60 | 30 | 4 | 8 | 3 |
| `nest_guard` | 築埂兔・護巢型 | E | 95 | 55 | 11 | 6 | 6 |
| `cliff_stepper` | 岩響山羊・踏崖型 | D | 240 | 130 | 20 | 16 | 12 |
| `pass_warden` | 岩響山羊・守隘型 | C | 330 | 170 | 26 | 14 | 14 |
| `wood_stalker` | 霧鬃山貓・林伏型 | D | 220 | 115 | 20 | 20 | 10 |
| `trail_hunter` | 霧鬃山貓・獵道型 | C | 280 | 165 | 25 | 22 | 12 |
| `bank_lurker` | 吞潮鱷・潛岸型 | D | 340 | 140 | 22 | 12 | 14 |
| `bay_warden` | 吞潮鱷・守灣型 | C | 400 | 210 | 28 | 12 | 15 |

#### Scenario: Zero pools and retained identities survive the batch

- **WHEN** the approved batch is applied to the existing registry
- **THEN** magic power remains zero for all twelve; MP/SP remain zero for the ten non-crocodile variants
- **AND** species keys, variant keys, names and grades are retained; only crocodile ecology and behavior receive the approved bite integration
- **AND** only tide_devouring_bite is added for the two crocodile variants

#### Scenario: The approved literals retire attrition without changing character

- **WHEN** the approved literals are reviewed against the previous values
- **THEN** lower HP and selected defense reductions remove extended attrition
- **AND** stronger forms retain danger through increased offense or agility
- **AND** independent axes preserve the cat's mobility, crocodile's endurance, and crab's defensive character

#### Scenario: Crocodile resource values replace only their previous zero pools
- **WHEN** the full approved profiles are compared with the registry
- **THEN** bank_lurker has HP/MP/SP/attack/agility/defense/magic of 140/30/40/22/12/14/0 and grade D; bay_warden has 210/50/60/28/12/15/0 and grade C
- **AND** no other numeric axis, grade or non-crocodile profile changes and no measured balance claim is implied
