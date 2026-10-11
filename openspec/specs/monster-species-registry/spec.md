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
- **WHEN** a synthetic variant authors a prerequisite-free active kit
- **THEN** its declared active order precedes innate actions without fabricated prerequisites or passives

### Requirement: Authored profile requirements are declared per variant
Combat profiles SHALL retain complete explicit seven-field records or optional absence, valid authored grades and established tier/grade checks. Whether a shipped variant requires a populated profile and grade SHALL be declared in its registry data. Required records SHALL reject absence; optional absence SHALL retain the existing individual-construction fallback semantics. Names, prose and other variants SHALL infer no values.

#### Scenario: Complete required rows
- **WHEN** every shipped variant is checked from its profile-required declaration
- **THEN** required profiles have all seven typed fields and a valid grade; optional None is absence and only construction may use its reported tier fallback

#### Scenario: Valid content edit
- **WHEN** a valid variant is added, renamed or retired together with its references
- **THEN** integrity follows the registry without changing a named roster in the spec or tests; established bounds remain unchanged

#### Scenario: Live state
- **WHEN** an existing individual reloads after a registry edit
- **THEN** identity and stored bases/kit/current gauges are preserved without automatic migration or refill

### Requirement: Narrative and executable monster configurations remain separate
Executable abilities SHALL require authored validated skill kits and behavior references through the shared engine. Rows with no delivered kit SHALL retain innate actions and tier-default behavior. Narrated abilities SHALL grant no ownership, resources or effects. Delivery status SHALL follow the authored kit data without a species allowlist, and future executable content SHALL require its own owning implementation.

#### Scenario: No fake seam
- **WHEN** a kit-less row has ecological ability text
- **THEN** no runtime effect or owned skill is inferred; configured kits validate through the same shared engine

#### Scenario: Delivered identity edit
- **WHEN** a configured species or variant display is renamed
- **THEN** its stable-key kit binding remains usable and player eligibility remains unchanged

### Requirement: Authored monster narratives synchronize without a fixed roster
Shipped species and variants SHALL carry non-empty public Traditional Chinese narrative fields and stable identities, with registry membership as the content authority. Synchronization SHALL mirror the authored registries idempotently through the observability facade and SHALL leave runtime monsters, rooms, quests and art untouched. Documentation SHALL satisfy the keyed public-content relationship contract without fixing species counts or narrative sentences.

#### Scenario: Idempotent entity-safe sync
- **WHEN** startup synchronization runs twice with runtime entities present
- **THEN** mirror state and object counts are unchanged after the second run and runtime monsters/rooms/quests/art remain unchanged; one registry-scoped facade boundary event is emitted per step

### Requirement: Shipped profile completeness follows authored declarations
Every variant declared profile-required SHALL ship a complete explicit profile and valid grade. All shipped rows SHALL satisfy identity/default membership and independent tier-axis/grade constraints; MP/SP SHALL remain explicit authored pools. Ability-kit delivery SHALL remain independent of profile completeness. New construction SHALL use current declarations without baked multipliers, and registry edits SHALL preserve live state.

#### Scenario: Complete required rows
- **WHEN** every shipped variant is checked from its profile-required declaration
- **THEN** required profiles have all seven typed fields and a valid grade; optional None is absence and only construction may use its reported tier fallback

#### Scenario: Valid content edit
- **WHEN** a valid variant is added, renamed or retired together with its references
- **THEN** integrity follows the registry without changing a named roster in the spec or tests; established bounds remain unchanged

#### Scenario: Live state
- **WHEN** an existing individual reloads after a registry edit
- **THEN** identity and stored bases/kit/current gauges are preserved without automatic migration or refill
