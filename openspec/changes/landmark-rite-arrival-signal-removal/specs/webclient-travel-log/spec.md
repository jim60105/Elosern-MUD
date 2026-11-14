# Spec Delta

## ADDED Requirements

### Requirement: The landmark arrival notice carries no lighting field
The `landmark_reached` travel notice SHALL carry exactly the arrival node, the landmark name, the prose and the artwork, and its rendered text SHALL be the arrival line alone. A notice carrying a lighting field SHALL be rejected by the server and browser validators.

#### Scenario: Four-field record
- **WHEN** a committed step reaches a landmark
- **THEN** the notice has exactly the four fields and its text names only the arrival

#### Scenario: Stale field rejected
- **WHEN** a `landmark_reached` record that still carries a lit-district field crosses the Python and JavaScript validators
- **THEN** both reject the batch as carrying an unknown field
