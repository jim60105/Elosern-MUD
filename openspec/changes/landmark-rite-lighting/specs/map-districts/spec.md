# Spec Delta

## ADDED Requirements

### Requirement: District lighting is derived from completed rites
A district SHALL be lit if and only if the player character's rite record holds at least one completed rite for it and the district registry declares it. Reading lighting SHALL introduce no persistent state. An unreadable rite record SHALL raise from the strict read and SHALL degrade to no lit district with a warning in the read used by presentation and travel.

#### Scenario: A visit lights nothing
- **WHEN** the player visits a landmark's canonical node and completes no rite
- **THEN** the district remains unlit

#### Scenario: A completed rite lights only its district
- **WHEN** the rite record holds one completion for one district and one for a key the registry does not declare
- **THEN** exactly the declared district is lit, and no attribute was created by reading

#### Scenario: Unreadable record
- **WHEN** the rite record violates its envelope
- **THEN** the strict read raises the named record error, and the degrading read returns no lit district and logs one warning

## REMOVED Requirements

### Requirement: District lighting is derived from visited landmark identity
**Reason**: A district is now earned by completing a landmark rite; a visited landmark node no longer lights anything.
**Migration**: None. Development databases are reset; an existing visit history stays valid as visit history and lights nothing.
