# Spec Delta

## ADDED Requirements

### Requirement: A location accepts an optional spacing exemption reason
A location declaration SHALL accept an optional non-blank spacing exemption reason and SHALL expose it to consumers; an absent reason SHALL stay absent.

#### Scenario: Reason round trip
- **WHEN** a synthetic location declares a reason and another declares none
- **THEN** the first exposes that text, the second exposes no reason, and both documents load

#### Scenario: Blank reason
- **WHEN** a location declares a reason that is empty or only whitespace
- **THEN** schema validation rejects the candidate naming the field
