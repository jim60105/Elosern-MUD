# monster-species-registry Specification

## Purpose
Define the read-only species and variant registries that carry the approved bestiary identity and narrative: frozen keyed lore data with validated species/variant membership, balance-gated (currently unpopulated) numeric and danger-grade slots, a public/private projection that keeps author-private notes out of player-facing output, and habitat data that authorizes nothing on its own.

## Requirements

### Requirement: Species and variant registries are frozen keyed read-only lore data
`world/lore/monster_species.py` SHALL define a frozen `MonsterSpecies` dataclass with fields `key`,
`display_name_zh`, `published_description_zh`, `published_appearance_zh`, `published_ecology_zh`,
`habitat_tags`, `author_hidden_truth_zh`, `author_explanation_zh`, `author_conjecture_zh`,
`default_variant_key`, and `ordinary_variant: bool`, plus a frozen `MonsterVariant` dataclass.

#### Scenario: Identity survives a rename and a tier change
- **WHEN** a species' or variant's `display_name_zh` or a variant's `threat_tier` is changed while its key is kept
- **THEN** every registry lookup by key still resolves the same record, and no consumer resolves the record by its display name

#### Scenario: Species carries no duplicate ability baseline
- **WHEN** the species dataclass definition is inspected
- **THEN** it declares no HP/MP/SP/physical/agility/defense/magic_power field, because the ability baseline of a species is its designated default variant's record

#### Scenario: No override chain exists
- **WHEN** a variant record is constructed
- **THEN** it is a complete standalone record with no parent key, no partial-overwrite field, and no resolution step that merges values from the species record

#### Scenario: The variant dataclass declares its fields

- **WHEN** the `MonsterVariant` dataclass definition is inspected
- **THEN** it is frozen and declares fields `key`, `species_key`, `display_name_zh`,
  `description_zh`, `threat_tier`, `ordinary_variant`, `combat_profile`, and `danger_grade`

#### Scenario: The registries are the source of truth

- **WHEN** consumers look up species or variant lore
- **THEN** module-level `MONSTER_SPECIES_REGISTRY` and `MONSTER_VARIANT_REGISTRY` keyed by those
  stable keys SHALL be the source of truth

#### Scenario: Stable keys satisfy the shared validation contract

- **WHEN** registry keys are authored
- **THEN** stable keys SHALL satisfy the existing shared stable-key validation contract
- **AND** SHALL NOT be derived from a display name, a threat tier, or an individual entity

#### Scenario: Renaming a display name does not change identity

- **WHEN** a record's display name is renamed
- **THEN** identity SHALL NOT change

#### Scenario: Neither class carries an inheritance field

- **WHEN** either dataclass definition is inspected
- **THEN** neither class SHALL carry an inheritance, parent, or override field

### Requirement: Every variant belongs to its species and the default variant is an ordinary variant of it
Registry construction SHALL reject a `MonsterVariant` whose `species_key` names no registered
species, SHALL reject a variant registered under a key already owned by a different species, and
SHALL reject a species whose `default_variant_key` names no registered variant, names a variant of a
different species, or names a variant whose `ordinary_variant` is false.

#### Scenario: An orphan variant is rejected at import time
- **WHEN** a variant declares a `species_key` absent from `MONSTER_SPECIES_REGISTRY`
- **THEN** registry construction raises a named species-registry error and the partially built registry is not published

#### Scenario: A default variant from another species is rejected
- **WHEN** a species declares `default_variant_key` naming a variant owned by a different species
- **THEN** registry construction raises the named error, even though both keys exist

#### Scenario: A stronger variant cannot become the species baseline
- **WHEN** a species declares `default_variant_key` naming a variant with `ordinary_variant=False`
- **THEN** registry construction raises the named error

#### Scenario: Names do not classify
- **WHEN** a variant display name contains wording that suggests strength while its authored `ordinary_variant` is true
- **THEN** registry validation and every consumer treat the variant as ordinary; no name matching participates in classification

#### Scenario: Ordinary classification is an explicit authored field

- **WHEN** a variant's ordinary-or-stronger classification is determined
- **THEN** variant display names SHALL NOT be used to classify it: the classification SHALL be an
  explicit authored field

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
- **AND** approved resource exceptions are bank_lurker MP/SP 30/40, bay_warden 50/60; grain_pecker MP/SP 20/8; flock_leader MP/SP 30/12; shore_walker MP/SP 20/9; reef_warden MP/SP 30/15; variants not yet approved in this sequence retain their existing zero pools

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
- **THEN** MP and SP carry no tier band and require explicit approval; the crocodile pools and explicitly approved complete profiles in “Approved delivered resource rows are literal” are accepted verbatim after approval; every unapproved nonzero pool is rejected

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
The registries SHALL permit executable first-batch abilities only through explicitly approved shared-engine skills and validated kits. Narrative SHALL NOT supply runtime effects. Still-deferred species after this change are ridge_burrow_hare, rock_echo_goat, fog_mane_lynx. Crocodile contact MP drain and completed species kits remain authored configuration.

#### Scenario: No behaviour seam is faked
- **WHEN** the shipped registry is inspected for skill keys, behaviour-profile keys, or combat traits naming the still-deferred species listed above
- **THEN** it carries none, and the ability prose remains in the published description fields only

#### Scenario: Narrative does not unlock a behaviour
- **WHEN** the existing behaviour-selection path resolves a variant whose narrative describes a still-deferred special ability
- **THEN** the resolved behaviour is exactly the existing damage-oriented decision path with no new effect, and the proposal records the mechanics prerequisite rather than an implementation

#### Scenario: Crocodile behavior comes from validated configuration
- **WHEN** the crocodile contact-drain ability is available in combat
- **THEN** its executable behavior comes from the validated authored kit and shared skill engine, never from interpreting narrative text

#### Scenario: Ability text is published narrative only

- **WHEN** ability text is authored for one of the still-deferred species listed above
- **THEN** it SHALL be permitted only as published narrative prose, including its approved limits

#### Scenario: Executable abilities are an external prerequisite

- **WHEN** an executable form of a still-deferred ability is wanted
- **THEN** it is a named external prerequisite owned by the skill/behaviour-mechanics work; a
  registry field, a stored trait, or a placeholder value SHALL NOT stand in for it
- **AND** no consumer SHALL be permitted to interpret narrative text as an available effect

#### Scenario: sway_whistle_sparrow completes its executable boundary
- **WHEN** this species' two approved kits are constructed
- **THEN** `grain_shaking_peck` is executable through the common engine, while ecological environment conditions remain prose and never generate runtime effects

#### Scenario: tide_lamp_crab completes its executable boundary
- **WHEN** this species' two approved kits are constructed
- **THEN** `lamp_carapace_claw` is executable through the common engine, while ecological environment conditions remain prose and never generate runtime effects

### Requirement: Published projections expose only marked public fields
The species and variant registries SHALL expose published views built from explicitly marked public
fields only. `author_hidden_truth_zh`, `author_explanation_zh`, and `author_conjecture_zh` SHALL NOT
appear in any published view, and a public description gap SHALL NOT be filled from an author-private
field.

#### Scenario: Private notes never serialize
- **WHEN** a published species or variant view is serialized for a player-facing surface
- **THEN** none of the three author-private fields' text appears anywhere in the payload, including in keys, and the fields' absence is asserted against a fixture whose private notes are distinctive

#### Scenario: A missing public description is not backfilled
- **WHEN** a species has no published appearance prose but does carry author-private notes
- **THEN** the published appearance is empty or explicitly absent, and no private text is promoted into it

#### Scenario: Conjecture stays conjecture
- **WHEN** a species publishes unverified scholarly conjecture
- **THEN** the published projection retains its uncertainty marking rather than presenting it as known truth

#### Scenario: Whole-record serialization is forbidden

- **WHEN** a player-facing surface needs species or variant data
- **THEN** no player-facing serializer, presentation payload, or narrative context SHALL serialize
  the whole species or variant record as a shortcut

### Requirement: Habitat tags are compatibility data and never authorize spawning
Species `habitat_tags` SHALL express habitat compatibility only. No function in the species registry
module SHALL decide, enable, prefer, or suppress an actual spawn, placement, respawn, or quantity from
those tags, and no placement decision SHALL be reachable from the registry module. A species whose
tags match a habitat SHALL be equally capable of being absent from every room of that habitat.

#### Scenario: Compatible does not mean present
- **WHEN** a species' habitat tags match a habitat and no authored placement names it there
- **THEN** nothing in the placement or population owners can produce that species from tag matching alone

#### Scenario: The registry offers no spawn API
- **WHEN** the species registry module's public surface is inspected
- **THEN** it exposes read and validation operations only, with no spawn, place, or reconcile callable

### Requirement: Approved bestiary narrative lands as zh-TW display strings and synchronizes idempotently
The registries SHALL carry the six approved bestiary species and their twelve approved named variant
directions with display and description strings in the canonical Traditional Chinese prose of
`docs/lore/bestiary.md`, and the startup synchronization SHALL mirror the registries into their
runtime store idempotently.

#### Scenario: Repeated startup synchronization is a no-op
- **WHEN** the species synchronization step runs twice in one process
- **THEN** the mirrored content is equal before and after the second run and no second creation occurs

#### Scenario: Synchronization touches no runtime entity
- **WHEN** synchronization runs against a database containing monsters, rooms, and quest records
- **THEN** a before/after comparison shows those records unchanged

#### Scenario: Logging stays inside the facade
- **WHEN** the new registry and synchronization modules are linted for logging
- **THEN** they import only `world.observability` named functions and every event carries a context dict with the registry identifiers

#### Scenario: Each synchronization step logs one boundary event

- **WHEN** a synchronization step runs
- **THEN** it emits one boundary info event through the `world.observability` facade with
  registry-scoped context keys

#### Scenario: Synchronization is state-preserving and entity-safe

- **WHEN** synchronization repeats or runs against runtime data
- **THEN** repeating synchronization SHALL leave the mirrored state unchanged
- **AND** synchronization SHALL NOT create, modify, or delete any monster, room, quest, or art record

### Requirement: The approved first-batch profiles and grades are user-approved literals
The twelve shipped variants SHALL carry the exact complete approved profiles in the table stated in
the scenario below, except for the explicitly approved resource pools and kits recorded below.
Magic power SHALL remain zero for all twelve; only listed delivered species change MP/SP and ability content. Newly constructed instances SHALL use these rows without live migration.

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
- **THEN** magic power remains zero for all twelve; resource pools equal the explicit approved exceptions below and all not-yet-delivered variants retain zero MP/SP
- **AND** species keys, variant keys, names and grades are retained; only explicitly approved delivered species receive their authored ecology and kit integration
- **AND** tide_devouring_bite remains unchanged for the two crocodile variants; approved completed kits are grain_shaking_peck, lamp_carapace_claw

#### Scenario: The approved literals retire attrition without changing character

- **WHEN** the approved literals are reviewed against the previous values
- **THEN** lower HP and selected defense reductions remove extended attrition
- **AND** stronger forms retain danger through increased offense or agility
- **AND** independent axes preserve the cat's mobility, crocodile's endurance, and crab's defensive character

#### Scenario: Crocodile resource values replace only their previous zero pools
- **WHEN** the full approved profiles are compared with the registry
- **THEN** bank_lurker has HP/MP/SP/attack/agility/defense/magic of 140/30/40/22/12/14/0 and grade D; bay_warden has 210/50/60/28/12/15/0 and grade C
- **AND** no crocodile numeric axis, cost, effect, kit, binding or grade changes; the other explicitly approved MP/SP exceptions below supersede prior zero pools without any measured balance claim

#### Scenario: Approved delivered resource rows are literal
- **WHEN** all delivered first-batch rows after this change are compared against their approval record
- **THEN** they carry the following complete profiles in HP/MP/SP/atk_phys/agility/defense/magic_power order, preserving their original grades

| Variant | Complete profile | Grade |
|---|---|---|
| `grain_pecker` | 30/20/8/4/7/3/0 | F |
| `flock_leader` | 55/30/12/8/10/4/0 | E |
| `shore_walker` | 30/20/9/5/4/5/0 | F |
| `reef_warden` | 60/30/15/12/4/7/0 | E |
- **AND** every remaining non-crocodile variant retains its earlier complete profile and zero MP/SP until its own approval and cutover

### Requirement: Every shipped combat profile and danger grade lies inside its declared tier band
Validation SHALL independently check HP, attack, agility, defense and magic against their own tier
axes and guild grade bounds. Bands and rank ranges SHALL come from the existing keyed threat-tier
registry through injectable tier faces carrying HP, separate attack/agility/defense, magic and
guild-rank-range fields. Bounds SHALL be inclusive; an absent declared tier SHALL raise the named
species-registry error.

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

#### Scenario: Calamity bounds stay open, human bounds stay finite

- **WHEN** tier bounds are projected onto validation
- **THEN** Calamity upper HP/physical bounds SHALL be open-ended; 3000/150 are reference values
- **AND** human racial/tier bounds SHALL remain finite and unchanged

#### Scenario: Symmetric-band projection constraints are removed

- **WHEN** validation projects tier bands onto variant fields
- **THEN** symmetric-band projection constraints SHALL be removed

#### Scenario: Out-of-band authoring fails at import

- **WHEN** a variant is authored outside its declared bands
- **THEN** the authoring SHALL fail at import
- **AND** synthetic faces SHALL support every rejection test

#### Scenario: Grades are checked by rank order

- **WHEN** a danger grade is validated against the tier's guild rank range
- **THEN** it SHALL be checked by rank order within the tier range, not set membership

#### Scenario: MP and SP stay explicit literal pools

- **WHEN** profiles are validated against tier bands
- **THEN** MP/SP SHALL remain explicit literal resource pools with no inferred band checks

### Requirement: Variant skill kits and behavior references are immutable authored configuration
Variants SHALL optionally carry ordered active/passive skill keys and a behavior-profile reference. Referenced skills SHALL resolve with matching kinds, compatible identity and usable prerequisites/effects; behavior references SHALL resolve in the existing behavior vocabulary before individual persistence.

#### Scenario: Invalid configuration creates nothing
- **WHEN** a variant references an unknown skill/profile, wrong kind, identity-ineligible skill, unusable prerequisite chain or unavailable effect
- **THEN** formal construction fails before persistence with no partial ownership/configuration

#### Scenario: No invented progression
- **WHEN** both crocodile variants author the prerequisite-free bite
- **THEN** they own it before innate attack with no new passive or fabricated progression chain
