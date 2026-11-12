# monster-visual-identity Specification

## Purpose
Provide monster visual species identity as the projection of the combat species registry, while sharing one validated species vocabulary across runtime and official artwork.

## Requirements

### Requirement: Threat tiers never address monster imagery
Threat tiers SHALL retain combat and balance semantics and SHALL have no monster image subject, gallery entry, generation prompt or media application. Existing tier artifacts SHALL be unreachable through current producers, readers, workers and media routes, without aliases or migrations.

#### Scenario: Every retired tier is unreachable
- **WHEN** a request, stored job or stored image names low, mid, high or calamity as its monster art key
- **THEN** it cannot generate, be selected, be served or appear as a monster portrait, even when old local records and files exist

#### Scenario: A real species in any tier remains drawable
- **WHEN** a monster with a registered visual species has a valid runtime or official image
- **THEN** that species image can present regardless of its combat threat tier

### Requirement: The monster visual registry is the combat species projection
Monster artwork SHALL use registered stable visual species keys. The visual registry SHALL be exactly the projection of the complete combat species registry: each species contributes its stable key, display label and public physical appearance, and no visual declaration SHALL exist without a combat species. Declarations SHALL contain no combat profile and SHALL reject duplicate, malformed or threat-tier keys.

#### Scenario: A key with no combat species is not a visual species
- **WHEN** a synthetic combat species registry holds species `t_a` and `t_b` and the visual registry is built from it
- **THEN** the visual registry holds exactly `t_a` and `t_b`, and any other key is not a registered visual species

#### Scenario: A new combat species joins through its public visual projection
- **WHEN** a valid complete combat species is registered
- **THEN** its stable key and public physical appearance become available to art consumers without a second hardcoded species roster or hidden-truth prompt content

#### Scenario: Registry closure fails before publication
- **WHEN** combat species keys contain a duplicate, malformed or threat-tier key
- **THEN** the registry is rejected before any prompt, queue job or image URL is produced

### Requirement: Stored species provenance is the only monster visual identity
A monster's stored complete species provenance SHALL be its only visual identity. A monster without species provenance, or with an unregistered one, SHALL resolve no art identity. No image identity SHALL be inferred from display names, threat tiers, variants or catalog entries.

#### Scenario: Renaming a species-backed monster does not change its artwork
- **WHEN** a monster whose stored species provenance is the synthetic species `t_a` is renamed
- **THEN** runtime and official artwork still use `t_a`

#### Scenario: Unregistered provenance resolves no art
- **WHEN** a monster stores a species provenance that is not a registered visual species
- **THEN** no visual reference resolves and it presents `monster_anon` without a state write

#### Scenario: Missing identity stays anonymous
- **WHEN** monster provenance is missing or malformed
- **THEN** it has no generatable species subject and the server resolves `monster_anon`, with no policy, record or generation manufactured by presentation
