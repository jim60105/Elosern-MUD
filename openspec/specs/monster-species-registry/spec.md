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
`MonsterVariant.combat_profile` SHALL be either None or a frozen complete authored record of HP/MP/SP/atk_phys/agility/defense/magic_power. `danger_grade` SHALL be None or a valid authored guild grade. Authoring SHALL provide explicit values; narrative, display names and other variants SHALL NOT infer them. Tests SHALL validate schema and established independent tier/grade constraints without reproducing a literal approval table or forbidding an otherwise valid author edit.

#### Scenario: Incomplete or invalid profile
- **WHEN** a profile omits a field, supplies None in a populated record, a non-integer or negative value, or magic outside its declared tier band
- **THEN** registry validation raises the named error before publication

#### Scenario: None retains optional-source semantics outside the required profiled set
- **WHEN** a variant outside the twelve required first-batch profiles has no authored profile or grade
- **THEN** consumers treat None as absence; only individual construction may use and report its existing tier fallback, and no registry consumer substitutes inferred numbers

#### Scenario: Authored pools remain independent
- **WHEN** an author adjusts explicit MP/SP pools
- **THEN** no MP/SP tier band or narrative-derived pool is introduced, and physical/magic tier validation remains unchanged

#### Scenario: A partial numeric profile is rejected
- **WHEN** one of seven fields is absent or None inside a populated profile
- **THEN** named registry validation rejects before publication

#### Scenario: Flavour never becomes a number
- **WHEN** narrative mentions magical/elemental behavior
- **THEN** magic/MP/SP remain explicit declarations rather than inferred values, with existing zero magic bands enforced

#### Scenario: Balance approval populates the same slot
- **WHEN** an author supplies a valid complete profile and grade
- **THEN** the same record shape validates and becomes the single source consumers read

#### Scenario: An unapproved slot still means "no approved profile"
- **WHEN** an optional future variant outside the required twelve lacks a profile or grade
- **THEN** None means absence, never zero, without requiring a duplicate approval record

#### Scenario: An approved value is never re-derived at the registry
- **WHEN** a consumer reads an explicit authored profile
- **THEN** it never derives replacement values from names, other fields or tier ranges; otherwise valid author edits remain permitted

#### Scenario: MP and SP pools are gated by approval, not inference
- **WHEN** an author declares MP/SP pools
- **THEN** they are explicit valid integer data with no invented tier band or narrative inference; no historical approval table pins their magnitudes

#### Scenario: Only explicit user balance approval populates a slot
- **WHEN** a profile or grade is populated
- **THEN** an explicit author declaration is required, not inferred/interpolated consumer data; valid author retuning does not require changing a duplicate test approval

#### Scenario: Granted approval ships both profile and grade
- **WHEN** a required first-batch profile is published
- **THEN** both its complete authored record and valid guild danger grade are present

#### Scenario: A None slot means no approved profile exists
- **WHEN** an optional future variant has a None slot
- **THEN** no consumer treats absence as zero, invented flavor data or a populated tier-band profile

#### Scenario: The interim fallback is owned by individual construction
- **WHEN** such an absent profile needs numeric construction
- **THEN** only the existing named individual-construction tier fallback provides and records the source; the registry slot itself stays absent

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
All twelve currently shipped first-batch variants SHALL retain complete authored profiles and valid authored grades, with no None slots. Values SHALL be adjustable data, without a duplicate approval table. Completeness, identity/default membership, independent tier-axis/grade-range checks and explicit MP/SP pools SHALL remain. Six delivered ability kits remain delivered; undelivered hare/goat/lynx ability kits remain deferred independently of their already-shipped profiles.

#### Scenario: Benign authoring change
- **WHEN** a delivered or already-profiled first-batch variant's HP, physical axis or MP/SP changes within the established schema and tier constraints
- **THEN** content tests pass without editing expected numerical tables and a newly constructed individual uses the declaration without coefficients baked into storage

#### Scenario: Existing bounds remain authoritative
- **WHEN** a profile is partial, mistyped, negative, or outside an established tier axis or grade range
- **THEN** existing validation rejects it by variant and field, including nonzero magic under a zero magic band

#### Scenario: Live state is preserved
- **WHEN** the registry changes after an individual exists
- **THEN** reload preserves that individual's identity, owned kit and current stored traits/resources without migration or refill

#### Scenario: New instance
- **WHEN** a registered variant constructs a new monster
- **THEN** its current authored profile is authoritative without skill/gear multipliers baked into storage

#### Scenario: Every shipped batch variant carries its approved values
- **WHEN** all twelve first-batch profiles and grades are inspected
- **THEN** all seven fields and a valid grade are present with no None slots; authored values, not an approval mirror, govern

#### Scenario: Approval does not extend to unapproved content
- **WHEN** an undelivered ability kit or profile outside the required first-batch set is inspected
- **THEN** no inference from this batch grants that kit; any explicitly authored optional profile follows the same schema without a historical numerical approval fence

#### Scenario: The approved profile table is pinned verbatim
- **WHEN** authored first-batch profiles are checked
- **THEN** the historical numerical approval table is removed, not moved; completeness and current declared bounds remain independently checked for all twelve

#### Scenario: Zero pools and retained identities survive the batch
- **WHEN** current first-batch declarations are validated
- **THEN** zero remains a valid explicitly authored pool rather than inferred absence; magic remains zero under existing tier magic bands, and all species/variant identities and authored grade validity remain
- **AND** only the six delivered kits are present; tide_devouring_bite, grain_shaking_peck and lamp_carapace_claw retain their existing ownership and effect intent

#### Scenario: The approved literals retire attrition without changing character
- **WHEN** valid authored profiles are revised
- **THEN** the existing cat mobility, crocodile endurance and crab defensive content intent stays reflected in independent axes and ecology; no old-versus-new numerical table or new universal encounter band is imposed

#### Scenario: Crocodile resource values replace only their previous zero pools
- **WHEN** crocodile profiles are authored or consumed
- **THEN** explicit MP/SP pools and complete profile/grade are retained without a 140/30/40 or 210/50/60 approval mirror; kit/binding/effect mechanics remain unchanged

#### Scenario: Approved delivered resource rows are literal
- **WHEN** both delivered variants per crocodile, sparrow and crab species are constructed
- **THEN** their current complete authored profile/grade and defined owned kit are used; the other six required profiles remain complete while their ability kits remain deferred

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
