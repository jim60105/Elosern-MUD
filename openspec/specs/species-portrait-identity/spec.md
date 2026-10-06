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
A monster whose persistent identity carries a registered `species_key` SHALL resolve its official
content reference as the `monster` kind keyed by exactly that species key, derived solely from stored
species provenance. The reference SHALL NOT be derived from the threat tier, the display name, or the
variant key: all variants of one species share the species' official image identity, and an
individual's distinctness comes from its personal selection and geometry overrides, not from a different
reference. Resolution SHALL be a pure read of stored identity plus the startup catalog snapshot, and a
tier-only individual SHALL resolve no species reference at all.

#### Scenario: Species key is the whole reference
- **WHEN** a species-backed monster with species key `<s>` presents while the mounted catalog holds `monster/<s>/`
- **THEN** the official reference resolves as `(monster, <s>)` and the official default image is presented through the existing chain step

#### Scenario: Variants share the species image
- **WHEN** two individuals of one species with different registered variants resolve
- **THEN** both resolve the same species reference, and their personal selections and geometry remain independent through the existing personalization machinery

#### Scenario: Tier-only individuals resolve nothing new
- **WHEN** a tier-only monster resolves
- **THEN** no species reference exists and its presentation is exactly the current runtime/silhouette chain

### Requirement: Tier substitution for a missing official species image is prohibited with honest fall-through
When a species' official package is absent from the mounted catalog, resolution SHALL fall through to
the existing runtime/silhouette/placeholder chain with no diagnostic beyond the bounded catalog
vocabulary, and no code path SHALL present another species' official image, a different species' bytes,
or a tier-derived stand-in in its place. Threat-tier values SHALL NOT be admitted as species keys
anywhere — no alias table, no tier-to-species mapping — and the generic tier subject SHALL keep serving
only the built-in silhouette/gallery generic layer it serves today.

#### Scenario: An unmapped species falls through, not sideways
- **WHEN** a species-backed monster resolves while the catalog has no `monster/<its species_key>/` entries
- **THEN** the chain proceeds exactly as it does today with runtime artwork or silhouette, and no other species' official bytes are reachable for it

#### Scenario: Tier aliases cannot satisfy the prerequisite
- **WHEN** content or configuration attempts to name a threat tier where a species key is required
- **THEN** the reference is rejected as unregistered, and no compatibility alias resolves it
