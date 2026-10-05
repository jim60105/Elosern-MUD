## Purpose

Land design §4's individual layer on the existing `Monster` typeclass: persistent species/variant
identity validated before persistence, threat tier and individual danger resolved from the variant
registry rather than stored as contradictable truth, balance-gated numerics with no invented values, no
player-level scaling, no pre-baked skill multipliers, and kill accounting keyed on the persistent
individual identity that dedupes duplicate defeat events.

## ADDED Requirements

### Requirement: Species-backed individuals are constructed through one validated deterministic entry point
The existing `Monster` typeclass SHALL carry persistent `species_key` and `variant_key` identity
alongside its existing traits, state, and location data. Exactly one construction entry point owned by
the deterministic core SHALL create a species-backed individual: it SHALL validate that both keys
resolve in the species/variant registries and that the variant belongs to the species before any
persistence, and only then SHALL it apply the approved combat configuration. Species or variant
identity SHALL NOT be inferred from a display name, an object key string, a threat tier, a quest role,
or generative output. A construction that fails validation SHALL leave no partially built individual
behind.

#### Scenario: A mismatched species and variant pair builds nothing
- **WHEN** construction is asked for a variant whose owning species differs from the supplied species key
- **THEN** construction raises a named construction error and a database before/after comparison shows no new individual

#### Scenario: An unknown key builds nothing
- **WHEN** construction is asked for a species key or variant key absent from the registries
- **THEN** construction raises the named error and no individual exists afterwards

#### Scenario: Names never carry identity
- **WHEN** an individual is created with a display name that matches a registered species' display text but with no species key
- **THEN** it is not a species-backed individual and resolves no species identity from its name

### Requirement: Threat tier and individual danger resolve from the variant, never as independent truth
For a species-backed individual, the threat tier and the individual danger grade SHALL resolve from the
variant's registry record on every read. Assigning a threat tier that contradicts the individual's
variant SHALL be rejected, and no stored attribute SHALL be permitted to hold a tier or danger grade
that disagrees with the registry. Renaming a registry display string SHALL NOT change an individual's
identity, and editing registry data SHALL NOT silently rescale the traits of already-existing
individuals. A tier-only individual — one whose owning caller has not adopted species identity — SHALL
continue to resolve its tier from its existing tier field with unchanged behaviour.

#### Scenario: A contradicting tier assignment is rejected
- **WHEN** code attempts to set a species-backed individual's threat tier to a value different from its variant's registered tier
- **THEN** the assignment raises a named error and the stored/derived tier remains the variant's value

#### Scenario: Registry edits do not rescale existing individuals
- **WHEN** a variant's registered numeric profile or narrative text is edited after individuals exist
- **THEN** those individuals' stored traits and resources are unchanged

#### Scenario: Tier-only individuals are unaffected
- **WHEN** a wilderness or scene-materialization caller creates a monster through the existing tier path with no species identity
- **THEN** its tier and traits resolve exactly as they do today

### Requirement: Individual numerics come only from approved sources, with no scaling and no baked multipliers
A species-backed individual's stored combat configuration SHALL come from the variant's
balance-approved complete profile when one exists. While no approved profile exists, the numeric source
SHALL be the existing threat-tier band construction applied at the variant's declared threat tier — the
only currently approved numeric source — and that interim resolution SHALL be recorded as one boundary
info event through the `world.observability` facade naming the individual, species, variant, and the
numeric source used. No nonzero MP, SP, or `magic_power` SHALL be inferred from a flavored species or
variant name or description. No code path on this construction surface SHALL scale traits by a player
level, quest progress, or world-clock state, and no skill multiplier SHALL be pre-merged into stored
traits: multipliers SHALL stay applied at resolution time by the existing combat path.

#### Scenario: Flavour text yields no resources
- **WHEN** an individual of a variant whose narrative mentions magical behaviour is constructed while its profile is unapproved
- **THEN** its MP, SP and `magic_power` are exactly the values the declared-tier band construction produces, with no inflation from the narrative

#### Scenario: An approved profile replaces the interim source without a schema change
- **WHEN** a balance-approved complete profile is authored for a variant and one individual is then constructed
- **THEN** its stored traits equal the approved profile literally, and the same construction call signature is used

#### Scenario: Nothing scales with the player
- **WHEN** two individuals of the same variant are constructed for players at different progression states
- **THEN** their stored traits are identical

#### Scenario: Multipliers stay out of storage
- **WHEN** an individual's stored traits are inspected after construction
- **THEN** they equal the approved configuration literally, with no damage or effect multiplier folded in

### Requirement: Kill accounting keys on persistent individual identity and dedupes duplicate defeat events
Defeat counting SHALL use the individual's persistent identity — its database row identity — never its
display name or threat tier. The quest layer SHALL record, per quest record, the individual identities
already counted for the current objective, so a duplicate or redelivered defeat event for an individual
already counted by that record SHALL add no progress. Recovery, room recycling, or site recovery that
produces a different individual SHALL give that individual a fresh identity which SHALL NOT be credited
against bindings or counted sets of the old individual.

#### Scenario: A redelivered defeat event adds no progress
- **WHEN** the same defeat event for one individual is presented to the quest planner twice for the same record
- **THEN** the objective's progress advances once

#### Scenario: Two distinct individuals with one display key count separately
- **WHEN** two individuals share a display name and both are defeated for a tier- or species-matching objective
- **THEN** each counts once, by its own persistent identity

#### Scenario: A recovered site's newcomer is a fresh identity
- **WHEN** a site recovers and spawns a new individual after an old one was defeated
- **THEN** the newcomer's identity is distinct, and it is not a member of any counted set or binding recorded for the old individual
