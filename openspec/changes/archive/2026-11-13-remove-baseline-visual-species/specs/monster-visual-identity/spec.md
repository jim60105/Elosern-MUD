## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Monster visual identities are authored independently of combat profiles
**Reason**: Baseline art-only visual declarations are removed; the registry is the combat species projection alone.
**Migration**: Replaced by "The monster visual registry is the combat species projection"; retarget its tests' `covers_requirement` IDs.

### Requirement: Monster visual provenance is explicit and authoritative
**Reason**: The baseline visual provenance (`art_species_key`) is removed; species provenance is the only identity.
**Migration**: Replaced by "Stored species provenance is the only monster visual identity"; retarget its tests' `covers_requirement` IDs.
