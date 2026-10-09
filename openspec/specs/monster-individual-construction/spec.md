# monster-individual-construction Specification

## Purpose
Land design §4's individual layer on the existing `Monster` typeclass: persistent species/variant
identity validated before persistence, threat tier and individual danger resolved from the variant
registry rather than stored as contradictable truth, balance-gated numerics with no invented values, no
player-level scaling, no pre-baked skill multipliers, and kill accounting keyed on the persistent
individual identity that dedupes duplicate defeat events.

## Requirements

### Requirement: Species-backed individuals are constructed through one validated deterministic entry point
The existing `Monster` typeclass SHALL carry persistent `species_key` and `variant_key` identity
alongside its existing traits, state, and location data. Exactly one construction entry point owned
by the deterministic core SHALL create a species-backed individual: it SHALL validate that both keys
resolve in the species/variant registries and that the variant belongs to the species before any
persistence.

#### Scenario: A mismatched species and variant pair builds nothing
- **WHEN** construction is asked for a variant whose owning species differs from the supplied species key
- **THEN** construction raises a named construction error and a database before/after comparison shows no new individual

#### Scenario: An unknown key builds nothing
- **WHEN** construction is asked for a species key or variant key absent from the registries
- **THEN** construction raises the named error and no individual exists afterwards

#### Scenario: Names never carry identity
- **WHEN** an individual is created with a display name that matches a registered species' display text but with no species key
- **THEN** it is not a species-backed individual and resolves no species identity from its name

#### Scenario: Identity is never inferred from incidental strings or roles
- **WHEN** species or variant identity would have to come from a display name, an object key string, a threat tier, a quest role, or generative output
- **THEN** it is NOT inferred from any of these; only the validated persistent keys carry identity

#### Scenario: A failed construction leaves nothing behind
- **WHEN** a construction fails validation
- **THEN** it leaves no partially built individual behind

### Requirement: The construction entry point validates the declared kit and behavior binding
The construction entry point SHALL validate the complete ordered active/passive kit, matching skill kinds,
identity qualification, prerequisite usability, supported effects and optional behavior-profile reference.
Identity, literal traits, ownership and behavior binding SHALL be applied atomically; failures leave no individual.

#### Scenario: An invalid declared kit or behavior reference creates nothing
- **WHEN** a variant declares an unknown or wrong-kind skill key, an identity-ineligible skill, an unusable prerequisite, an unsupported effect, or an unknown behavior-profile key
- **THEN** construction fails before persistence and leaves no partial individual or ownership

#### Scenario: The declared kit and binding are applied atomically
- **WHEN** a construction with a declared kit and behavior binding fails during or after assignment
- **THEN** no partial individual, ownership or bound configuration remains

### Requirement: Threat tier and individual danger resolve from the variant, never as independent truth
For a species-backed individual, the threat tier and the individual danger grade SHALL resolve from the
variant's registry record on every read, and no stored attribute SHALL be permitted to hold a tier
or danger grade that disagrees with the registry. Renaming a registry display string SHALL NOT
change an individual's identity, and editing registry data SHALL NOT silently rescale the traits of
already-existing individuals.

#### Scenario: A contradicting tier assignment is rejected
- **WHEN** code attempts to set a species-backed individual's threat tier to a value different from its variant's registered tier
- **THEN** the assignment raises a named error and the stored/derived tier remains the variant's value,
  and an assignment of the variant's own registered tier is rejected the same way

#### Scenario: Registry edits do not rescale existing individuals
- **WHEN** a variant's registered numeric profile or narrative text is edited after individuals exist
- **THEN** those individuals' stored traits and resources are unchanged

#### Scenario: A retired variant record degrades the derived read
- **WHEN** a species-backed individual's variant key is no longer present in the registry
- **THEN** its tier and danger grade read as the same optional absence a tier-only individual has,
  rather than raising out of a read that rendering, examination, or combat depends on

#### Scenario: Tier-only individuals are unaffected
- **WHEN** a wilderness or scene-materialization caller creates a monster through the existing tier path with no species identity
- **THEN** its tier and traits resolve exactly as they do today — the same value and the same trait set;
  a tier-only individual that never receives a tier simply carries no stored tier attribute, which no
  consumer reads

#### Scenario: Threat-tier assignment is refused outright
- **WHEN** code attempts to assign a threat tier to a species-backed individual
- **THEN** the assignment is rejected — the field is not independently editable truth, so the
  assignment is refused whether or not its value happens to agree with the variant

#### Scenario: Tier-only individuals keep their own tier resolution
- **WHEN** an individual's owning caller has not adopted species identity
- **THEN** that tier-only individual continues to resolve its tier from its existing tier field
  with unchanged behaviour

### Requirement: Individual numerics come only from approved sources, with no scaling and no baked multipliers
A species-backed individual's stored combat configuration SHALL come from the variant's
balance-approved complete profile when one exists. While no approved profile exists, the numeric source
SHALL be the existing threat-tier band construction applied at the variant's declared threat tier.
No code path on this construction surface SHALL scale traits by a player level, quest progress, or
world-clock state.

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

#### Scenario: The interim band source is recorded observably
- **WHEN** the interim threat-tier band source resolves an individual's numerics
- **THEN** it is the only currently approved numeric source while no approved profile exists, and
  the resolution is recorded as one boundary info event through the `world.observability` facade
  naming the individual, species, variant, and the numeric source used

#### Scenario: Multipliers stay applied at resolution time
- **WHEN** stored traits are composed on the construction surface
- **THEN** no skill multiplier is pre-merged into stored traits — multipliers stay applied at
  resolution time by the existing combat path

#### Scenario: Flavour never invents resources
- **WHEN** a species or variant carries a flavored name or description
- **THEN** no nonzero MP, SP, or `magic_power` is inferred from it

### Requirement: Kill accounting keys on persistent individual identity and dedupes duplicate defeat events
Defeat counting SHALL use the individual's persistent identity — its database row identity — never its
display name or threat tier. The quest layer SHALL record, per quest record, the individual identities
already counted for the current objective, so a duplicate or redelivered defeat event for an individual
already counted by that record SHALL add no progress.

#### Scenario: A redelivered defeat event adds no progress
- **WHEN** the same defeat event for one individual is presented to the quest planner twice for the same record
- **THEN** the objective's progress advances once

#### Scenario: Two distinct individuals with one display key count separately
- **WHEN** two individuals share a display name and both are defeated for a tier- or species-matching objective
- **THEN** each counts once, by its own persistent identity

#### Scenario: A recovered site's newcomer is a fresh identity
- **WHEN** a site recovers and spawns a new individual after an old one was defeated
- **THEN** the newcomer's identity is distinct, and it is not a member of any counted set or binding recorded for the old individual

#### Scenario: Every re-creation path yields an uncreditworthy fresh identity
- **WHEN** recovery, room recycling, or site recovery produces a different individual
- **THEN** that individual gets a fresh identity which is NOT credited against bindings or counted
  sets of the old individual

### Requirement: Constructed kits and depleted resources survive reload without registry resets
Individual persistence SHALL retain identity, owned kit, bound behavior profile and current gauge values. Registry changes SHALL NOT refill or rescale live individuals. Variants without special kits SHALL retain innate actions and tier-default behavior.

#### Scenario: Reload is not reconstruction
- **WHEN** a formally constructed individual spends MP/SP and is reloaded
- **THEN** identity, owned order and behavior binding persist and current depleted gauges are unchanged

#### Scenario: Registry changes leave live state alone
- **WHEN** a variant profile or kit is edited after creation
- **THEN** existing ownership and gauges are not reset by startup or reload; an authorized GM workflow is required for live changes

#### Scenario: Other species retain their defaults
- **WHEN** a variant has no authored special kit or behavior binding
- **THEN** construction keeps basic_attack/flee and tier-default policy with no inferred spells or pools
