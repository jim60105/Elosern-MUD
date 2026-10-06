## MODIFIED Requirements

### Requirement: Numeric combat profiles and danger grades are balance-gated slots, never invented values
`MonsterVariant.combat_profile` SHALL be either `None` or a frozen record that carries a complete
value set (HP, MP, SP, physical combat power, agility, defense, `magic_power`) as literal authored
values, and `MonsterVariant.danger_grade` SHALL be either `None` or an authored guild danger grade.
Registry construction SHALL reject a partially populated profile, a non-integer value, a negative
value, and any nonzero MP/SP/`magic_power` that is not present as an explicit literal in the authored
record. Only an explicit user balance approval may populate a slot: the authored values SHALL be the
approved values verbatim, and a registry edit SHALL NOT re-derive, re-tune, re-round, or interpolate
them, nor infer any value from a display name, a description, a threat tier, or another variant. Once
approval is granted for a variant, that variant SHALL ship the approved complete profile and the
approved guild danger grade. While a slot is `None` on some future variant, a consumer SHALL treat it
as "no approved per-variant profile exists": never as a zero, never as a per-species number invented
from flavour, and never as tier-band truth about the variant itself. The single sanctioned numeric
fallback while a profile is `None` is the named interim rule owned by individual construction — the
existing threat-tier band construction at the variant's declared tier, recorded with its numeric
source — and consumers SHALL NOT read the registry slot as if it carried that fallback.

#### Scenario: A partial numeric profile is rejected
- **WHEN** a variant profile omits any one of the seven numeric fields or sets one to `None`
- **THEN** registry construction raises the named species-registry error and the variant is not published

#### Scenario: Flavour never becomes a number
- **WHEN** a variant whose narrative mentions magical or elemental behaviour is inspected
- **THEN** its `magic_power`, MP, and SP are exactly the authored literals — zero, because the tier magic band is `(0, 0)` and no ability mechanic consumes a pool — and are never read as a value derived from the name, the description, or an ability narrative

#### Scenario: Balance approval populates the same slot
- **WHEN** a balance-approved complete profile and grade are authored for one variant
- **THEN** the record validates with no schema change, and the previously empty slot is now the single source of truth that consumers read

#### Scenario: An unapproved slot still means "no approved profile"
- **WHEN** a variant whose approval has not been granted is read
- **THEN** its profile is `None` and its grade is `None`, and no consumer treats that as a zero or as an approved number

#### Scenario: An approved value is never re-derived at the registry
- **WHEN** a registry edit changes an approved literal to a value computed from another field, from a display name, or from the tier band
- **THEN** the shipped-content contract fails, because the approved literals are pinned and tier-band membership alone does not prove a value was approved

## ADDED Requirements

### Requirement: The approved first-batch profiles and grades are user-approved literals
The twelve shipped variants of the approved first bestiary batch SHALL carry the user-approved complete
combat profile and the user-approved guild danger grade for each variant, as literal values, and no
other variant SHALL carry a profile or a grade that no approval covers. The approved values are
content, not a derivation: a reader SHALL be able to compare each shipped slot against the approval
record and find it equal, and a slot that differs from the approval record SHALL be a content defect
rather than a re-tuning decision.

#### Scenario: Every shipped batch variant carries its approved values
- **WHEN** the shipped registry is compared field by field against the approval record for the twelve first-batch variants
- **THEN** every one of the seven profile values and the danger grade equals the approved literal, and no shipped batch variant carries `None` in either slot

#### Scenario: Approval does not extend to unapproved content
- **WHEN** a variant outside the approved twelve carries a profile or a grade
- **THEN** the approved-content contract reports it, because that approval record names exactly twelve variants

### Requirement: Every shipped combat profile and danger grade lies inside its declared tier band
Registry validation SHALL reject a variant whose `combat_profile` falls outside its declared
`threat_tier`'s bands — `hp` inside the tier's HP band, `atk_phys`, `agility`, and `defense` inside the
tier's physical band for those axes, and `magic_power` inside the tier's magic band — and SHALL reject a
variant whose `danger_grade` falls outside its tier's `guild_rank_range`. Bands and rank ranges SHALL be
read from the existing threat-tier registry through the same injectable face discipline the rest of the
validation uses, so an authored out-of-band rating fails at import while behavior tests can exercise the
rule with invented bands. The tier model declares no band for the MP and SP resource pools, so those two
axes are deliberately not band-checked: their value is an authored literal, not a band inference.

#### Scenario: A profile above its tier band is rejected
- **WHEN** a low-tier variant declares an `hp` above the tier's HP band, or a physical axis outside the tier's physical band
- **THEN** registry construction raises the named species-registry error and no registry is published

#### Scenario: A profile below its tier band is rejected
- **WHEN** a variant declares an `hp` below the tier's HP band
- **THEN** registry construction raises the named species-registry error

#### Scenario: A nonzero magic axis outside the tier's magic band is rejected
- **WHEN** a variant declares a `magic_power` outside its tier's magic band — including any nonzero value while the band is `(0, 0)`
- **THEN** registry construction raises the named species-registry error

#### Scenario: A grade outside the tier's guild rank range is rejected
- **WHEN** a low-tier variant declares a `danger_grade` outside its tier's `guild_rank_range`
- **THEN** registry construction raises the named species-registry error

#### Scenario: The shipped batch is inside its declared bands
- **WHEN** every shipped variant's profile and grade are checked against its own declared tier
- **THEN** each one lies inside that tier's HP band, physical band, magic band, and `guild_rank_range`
