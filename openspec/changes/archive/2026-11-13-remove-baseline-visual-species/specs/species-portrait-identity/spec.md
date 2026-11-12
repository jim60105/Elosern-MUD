## ADDED Requirements

### Requirement: A species-backed monster resolves its species-keyed official reference
A monster whose persistent identity carries a registered visual-species provenance SHALL resolve its official content reference as the `monster` kind keyed by exactly that species key, derived solely from stored provenance as a pure read of stored identity plus the startup catalog snapshot. A monster without species provenance SHALL resolve no reference.

#### Scenario: Species key is the whole reference
- **WHEN** a species-backed monster with species key `<s>` presents while the mounted catalog holds `monster/<s>/`
- **THEN** the official reference resolves as `(monster, <s>)` and the official default image is presented through the existing chain step

#### Scenario: Variants share the species image
- **WHEN** two individuals of one species with different registered variants resolve
- **THEN** both resolve the same species reference, and their personal selections and geometry remain independent through the existing personalization machinery

#### Scenario: A monster without species provenance resolves nothing
- **WHEN** a tier-built monster carries no species provenance
- **THEN** it resolves no official reference and no species subject, and it carries monster_anon

#### Scenario: The reference is never derived from tier, name, or variant
- **WHEN** a species-backed individual resolves its official reference
- **THEN** the reference is never derived from the threat tier, the display name, or the variant key
- **AND** an individual's distinctness comes from its personal selection and geometry overrides, not from a different reference

## REMOVED Requirements

### Requirement: A species-backed individual resolves the species-keyed official content reference
**Reason**: Its tier-built baseline scenario relied on the removed explicit visual provenance.
**Migration**: Replaced by "A species-backed monster resolves its species-keyed official reference"; retarget its tests' `covers_requirement` IDs.
