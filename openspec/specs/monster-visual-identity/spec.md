# monster-visual-identity Specification

## Purpose
Provide explicit visual species identity for baseline wilderness monsters without fabricating combat species profiles, while sharing one validated species vocabulary across runtime and official artwork.

## Requirements

### Requirement: Monster visual identities are authored independently of combat profiles
Monster artwork SHALL use registered stable visual species keys. Complete combat species SHALL contribute their public physical appearance; baseline population visual declarations SHALL supply their own explicit key, display label and physical category. Visual declarations SHALL contain no combat profile and SHALL reject duplicate, malformed or threat-tier keys.

#### Scenario: Baseline goblin has an art identity without a new combat kit
- **WHEN** a baseline population declaration selects the existing goblin example
- **THEN** its visual identity is the authored `goblin` key, its original label and combat tier remain unchanged, and no new combat species, profile or skill is required

#### Scenario: A new combat species joins through its public visual projection
- **WHEN** a valid complete combat species is registered
- **THEN** its stable key and public physical appearance become available to art consumers without a second hardcoded species roster or hidden-truth prompt content

#### Scenario: Registry closure fails before publication
- **WHEN** visual declarations contain a duplicate key, malformed key, threat-tier key or unresolved population reference
- **THEN** the declarations are rejected before any prompt, queue job or image URL is produced

### Requirement: Monster visual provenance is explicit and authoritative
A monster's registered complete species provenance SHALL govern its visual identity. Only an absent complete species provenance permits its explicit baseline visual provenance to resolve. Invalid declared provenance SHALL resolve no art identity. No image identity SHALL be inferred from display names, threat tiers, variants or catalog entries.

#### Scenario: Renaming a goblin does not change its artwork
- **WHEN** a baseline goblin with persisted visual key `goblin` is renamed
- **THEN** runtime and official artwork still use `goblin`

#### Scenario: Invalid complete provenance does not borrow baseline art
- **WHEN** a monster declares an unregistered complete species and also carries a valid baseline visual key
- **THEN** no visual reference resolves and it presents `monster_anon` without a state write

#### Scenario: Unknown or missing identity stays anonymous
- **WHEN** monster provenance is missing, malformed or unregistered
- **THEN** it has no generatable species subject and the server resolves `monster_anon`, with no policy, record or generation manufactured by presentation

### Requirement: Threat tiers never address monster imagery
Threat tiers SHALL retain combat and balance semantics and SHALL have no monster image subject, gallery entry, generation prompt or media application. Existing tier artifacts SHALL be unreachable through current producers, readers, workers and media routes, without aliases or migrations.

#### Scenario: Every retired tier is unreachable
- **WHEN** a request, stored job or stored image names low, mid, high or calamity as its monster art key
- **THEN** it cannot generate, be selected, be served or appear as a monster portrait, even when old local records and files exist

#### Scenario: A real species in any tier remains drawable
- **WHEN** a monster with a registered visual species has a valid runtime or official image
- **THEN** that species image can present regardless of its combat threat tier
