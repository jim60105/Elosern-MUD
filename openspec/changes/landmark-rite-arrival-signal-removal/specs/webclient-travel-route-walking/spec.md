# Spec Delta

## ADDED Requirements

### Requirement: The landmark arrival card states no district lighting
The generic landmark arrival card SHALL show the arrival's name, art and prose and SHALL show no row about a district being explored. The walking interrupt texts SHALL contain no entry for district lighting.

#### Scenario: Card content
- **WHEN** the card renders a committed arrival
- **THEN** it shows the name, the art or the quiet ink header, and the prose, and no lighting row

#### Scenario: Interrupt texts
- **WHEN** a walk stops for each remaining interrupt flag
- **THEN** each shows its own text and no text exists for a lighting flag
