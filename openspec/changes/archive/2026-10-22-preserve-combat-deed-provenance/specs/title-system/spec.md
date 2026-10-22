# Spec Delta

## ADDED Requirements

### Requirement: Encounter grouping uses unique occurrence identity
Recent-deed encounter joins SHALL use the unique engagement occurrence carried by authoritative producers. Reusable session tokens SHALL NOT replace or merge terminal occurrences. Each retained action and milestone SHALL join only its own encounter outcome, with all retained source IDs and occurrence counts.

#### Scenario: Real repeated combat actions join their outcome
- **WHEN** several real same-skill actions from distinct slots or rounds and their terminal encounter are eligible
- **THEN** the group retains the distinct action occurrences and outcomes with the correct sources and counts

#### Scenario: Zero-time reengagement survives selection
- **WHEN** a zero-time settled encounter is followed by a new engagement with the same reusable session token
- **THEN** selection retains both distinct terminal encounters rather than overwriting one or joining their actions together

#### Scenario: Window filtering precedes the encounter join
- **WHEN** one action from an otherwise eligible encounter is outside the rolling window
- **THEN** the expired action contributes no fact, source reference or repetition count
