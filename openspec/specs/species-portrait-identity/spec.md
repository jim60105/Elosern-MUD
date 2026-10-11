# species-portrait-identity Specification

## Purpose

Give a monster its own species-keyed official image identity. A monster whose persistent
provenance carries a registered `species_key` resolves its official content reference as
`(monster, <species_key>)`, read purely from stored identity plus the startup catalog snapshot, so
every variant of one species shares that species' mounted official artwork while each individual's
personal selection and geometry remain its own. Threat-tier substitution is unrepresentable — a
threat tier is never admitted as a species key, no alias table or tier-to-species mapping exists, and
a species whose package the mounted catalog lacks falls through to the existing runtime/silhouette
chain rather than presenting another species' bytes. The tier-validated `portrait:monster:<tier>`
subject keeps serving the built-in silhouette/gallery generic layer unchanged; species identity
joins only at the official reference layer, so the two identity layers can never be confused.

## Requirements

### Requirement: A species-backed individual resolves the species-keyed official content reference
A monster whose persistent identity carries a registered visual-species provenance SHALL resolve its official
content reference as the `monster` kind keyed by exactly that visual species key, derived solely from stored
visual provenance. Resolution SHALL be a pure read of stored identity plus the startup catalog
snapshot.

#### Scenario: Species key is the whole reference
- **WHEN** a species-backed monster with species key `<s>` presents while the mounted catalog holds `monster/<s>/`
- **THEN** the official reference resolves as `(monster, <s>)` and the official default image is presented through the existing chain step

#### Scenario: Variants share the species image
- **WHEN** two individuals of one species with different registered variants resolve
- **THEN** both resolve the same species reference, and their personal selections and geometry remain independent through the existing personalization machinery

#### Scenario: Tier-only individuals resolve nothing new
- **WHEN** a tier-built baseline individual carries valid explicit visual provenance
- **THEN** its reference is monster/<visual-key>; without valid visual provenance it resolves no species subject and carries monster_anon

#### Scenario: The reference is never derived from tier, name, or variant
- **WHEN** a species-backed individual resolves its official reference
- **THEN** the reference is never derived from the threat tier, the display name, or the variant key
- **AND** an individual's distinctness comes from its personal selection and geometry overrides, not from a different reference

### Requirement: Tier substitution for a missing official species image is prohibited with honest fall-through
When a species' official package is absent from the mounted catalog, resolution SHALL fall through to
the existing runtime/silhouette/placeholder chain, and no code path SHALL present another species'
official image, a different species' bytes, or a tier-derived stand-in in its place.

#### Scenario: An unmapped species falls through, not sideways
- **WHEN** a monster has registered visual provenance but its official package is absent
- **THEN** only runtime artwork of that same visual species may resolve; without a valid species image monster_anon resolves, and no other species or threat-tier bytes are reachable

#### Scenario: Tier aliases cannot satisfy the prerequisite
- **WHEN** content or configuration attempts to name a threat tier where a species key is required
- **THEN** the reference is rejected as unregistered, and no compatibility alias resolves it

#### Scenario: The fall-through stays within the bounded catalog vocabulary
- **WHEN** a species' official package falls through
- **THEN** the diagnostic carries nothing beyond the bounded catalog vocabulary

#### Scenario: Threat tiers are never admitted as species keys
- **WHEN** any code path evaluates a value as a species key
- **THEN** threat-tier values are never admitted as species keys anywhere — no alias table, no tier-to-species mapping exists

#### Scenario: The generic tier subject keeps its current scope
- **WHEN** a retired portrait:monster:<tier> subject is encountered in stored state or a direct request
- **THEN** it is rejected at every production, selection, resolution and media-admission boundary; no tier gallery layer remains

### Requirement: Monster portraits never borrow runtime state across visual species
A monster SHALL resolve reusable cards and valid classic identities only inside its declared visual species. Individual official selections and geometry SHALL remain entity-local. Missing, failed or invalid images SHALL retain truthful state and carry monster_anon for browser load failure.

#### Scenario: Same-tier species do not share imagery
- **WHEN** two monsters share a combat tier but declare different visual species, and only one species has a card
- **THEN** only that species presents the card; the other presents its own official image or monster_anon

#### Scenario: Same-species individuals keep independent official choices
- **WHEN** two individuals of one species select different official images and geometry through entity-context preferences
- **THEN** each presents its own selection and geometry, while source files and the species card remain shared and unchanged

#### Scenario: Broken species images degrade without substitution
- **WHEN** a valid species image fails admission or a browser image load fails
- **THEN** presentation uses monster_anon without reaching another species, a tier image or the deprecated humanoid SVG
