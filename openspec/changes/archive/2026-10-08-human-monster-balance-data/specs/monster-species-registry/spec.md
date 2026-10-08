## MODIFIED Requirements

### Requirement: The approved first-batch profiles and grades are user-approved literals
The twelve shipped variants SHALL carry the exact complete approved profiles in the following table, with MP/SP/magic_power zero and existing species/variant/display/grade/ecology/behavior identities unchanged. No new ability SHALL be introduced; newly constructed instances SHALL use these rows without live migration.


MP, SP, and magic power remain zero for all twelve existing variants. Species keys, variant keys, names, grades, ecology, and existing behavior identities are retained. This change adds no monster spell or special ability.

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

Lower HP and selected defense reductions remove extended attrition. Stronger forms retain danger through increased offense or agility. Independent axes preserve the cat's mobility, crocodile's endurance, and crab's defensive character.



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

### Requirement: Every shipped combat profile and danger grade lies inside its declared tier band
Validation SHALL independently check HP, attack, agility, defense and magic against their own tier axes and guild grade bounds. Calamity upper HP/physical bounds SHALL be open-ended; 3000/150 are reference values. Human racial/tier bounds SHALL remain finite and unchanged. Symmetric-band projection constraints SHALL be removed.
Bands and rank ranges SHALL come from the existing keyed threat-tier registry through injectable tier faces carrying HP, separate attack/agility/defense, magic and guild-rank-range fields. Bounds SHALL be inclusive; an absent declared tier SHALL raise the named species-registry error. Danger grades SHALL be checked by rank order within the tier range, not set membership. Out-of-band authoring SHALL fail at import, and synthetic faces SHALL support every rejection test. MP/SP SHALL remain explicit literal resource pools with no inferred band checks.

#### Scenario: A profile above its tier band is rejected
- **WHEN** a variant exceeds a finite HP maximum or an axis-specific physical bound
- **THEN** registry construction raises a named variant/axis/value error and publishes no registry

#### Scenario: A profile below its tier band is rejected
- **WHEN** a variant HP falls below the tier minimum
- **THEN** registry construction raises the named species-registry error

#### Scenario: A nonzero magic axis outside the tier's magic band is rejected
- **WHEN** magic_power is outside its own band, including nonzero under a zero band
- **THEN** registry construction raises the named species-registry error

#### Scenario: A grade outside the tier's guild rank range is rejected
- **WHEN** danger_grade rank order falls outside the declared range
- **THEN** registry construction raises the named species-registry error

#### Scenario: The shipped batch is inside its declared bands
- **WHEN** every shipped variant profile and grade is checked against its tier
- **THEN** HP and each physical/magic axis lie within their own bounds and grade order lies within guild_rank_range

#### Scenario: A value exactly on a band edge is inside the band
- **WHEN** HP or a physical axis equals one of its finite band edges
- **THEN** validation accepts the inclusive edge

#### Scenario: A tier with no band is rejected rather than skipped
- **WHEN** the injectable tier face lacks a variant's declared tier
- **THEN** the named species-registry error is raised

#### Scenario: Resource pools are not inferred from tier bands
- **WHEN** complete literal MP/SP values differ from a tier physical band
- **THEN** no MP/SP band check is invented

#### Scenario: Independent axes
- **WHEN** synthetic tier attack/agility/defense ranges differ
- **THEN** each field uses its own range and a violation names variant/axis/value

#### Scenario: Open calamity
- **WHEN** literal calamity monster exceeds HP3000 and physical150 within open upper limits
- **THEN** monster classification accepts it without opening human bounds

