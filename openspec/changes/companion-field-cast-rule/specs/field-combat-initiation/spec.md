# Spec Delta

## ADDED Requirements

### Requirement: A companion initiator opens the commander's encounter
When `initiate_field_combat` is called with a present effective companion as the actor, the system SHALL resolve the commander, create the hostile session under the commander's party exactly as for a commander initiator, and seed the named skill as the companion's opening draft entry; every other initiation rule (availability, candidate-battlefield validation, SINGLE/AREA engagement, one failure boundary, combat time, boundary event) SHALL apply unchanged.

#### Scenario: The session belongs to the commander
- **WHEN** companion 艾拉 initiates field combat against a room monster
- **THEN** the persisted session lists the commander and the present companions as the player side, the commander is the session's commander, and 艾拉's draft entry holds the opening skill

#### Scenario: A failed companion initiation leaves nothing behind
- **WHEN** session creation or the opening validation fails for a companion initiator
- **THEN** no session, draft entry, resource change, practice award or clock change remains, exactly as for a commander initiator
