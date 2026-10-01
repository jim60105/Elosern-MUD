## ADDED Requirements

### Requirement: A place's host profile reference is validated
A place record SHALL be able to name its host's authored NPC profile by profile key. When a place names a host profile, place-registry validation SHALL reject the record if the place authors no host or if the key does not resolve in the NPC profile registry, naming the place and the key. A place that names no host profile SHALL validate exactly as before this requirement.

#### Scenario: An unresolved profile key fails load
- **WHEN** a synthetic hosted place names a host profile key absent from the profile registry
- **THEN** place-registry validation raises naming the place and the key

#### Scenario: A hostless place cannot name a host profile
- **WHEN** a synthetic hostless place names a host profile key
- **THEN** place-registry validation raises naming the place, and the place is not treated as hostless

#### Scenario: A place without a reference is unchanged
- **WHEN** a synthetic hosted place that names no host profile is validated by this rule
- **THEN** this rule raises nothing for it, and every other place rule applies exactly as before
