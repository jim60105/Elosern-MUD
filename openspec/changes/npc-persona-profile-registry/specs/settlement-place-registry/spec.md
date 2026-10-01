## ADDED Requirements

### Requirement: A place's host profile reference is validated
A place record SHALL be able to name its host's authored NPC profile by profile key. Place-registry validation SHALL reject a place that names a host profile key which does not resolve in the NPC profile registry, and SHALL reject a hostless place that names any host profile key, naming the place and the key in both cases. A host profile key SHALL count as host material, so a hostless place carrying one is never treated as hostless.

#### Scenario: An unresolved profile key fails load
- **WHEN** a synthetic hosted place names a host profile key absent from the profile registry
- **THEN** place-registry validation raises naming the place and the key

#### Scenario: A hostless place cannot name a host profile
- **WHEN** a synthetic hostless place names a host profile key
- **THEN** place-registry validation raises naming the place, and the place is not treated as hostless
