## ADDED Requirements

### Requirement: Monster entries carry identity facts
A monster entry in the bounded context SHALL carry nullable `individual_name`, `species_name` and `variant_name` beside its display name, and the prompt's monster entries SHALL serialize them. An entity with no identity SHALL carry null in all three. Each value SHALL be bounded to the existing monster entry length.

#### Scenario: Named monster
- **WHEN** a synthetic named monster stands in the room during action-options generation
- **THEN** the rendered prompt's monster entry holds its individual, species and variant names

#### Scenario: Tier-only monster
- **WHEN** a tier-only monster stands in the room
- **THEN** its entry carries null for all three facts and generation proceeds

#### Scenario: Over-long value
- **WHEN** a mapping supplies an identity value longer than the monster entry bound
- **THEN** the built entry holds the value truncated to the bound
