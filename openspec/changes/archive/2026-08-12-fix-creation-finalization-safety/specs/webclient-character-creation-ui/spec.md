## ADDED Requirements

### Requirement: Web activation confirms the exact draft shown

The system SHALL ensure the `creation.activate` flow activates the draft whose save was confirmed, and SHALL surface a stable error when the stored draft changed between confirmation and activation.

#### Scenario: Activation after successful save activates the saved draft

- **WHEN** the player confirms after a successful custom save
- **THEN** the character is activated from that saved draft and `creation_pending` becomes false

#### Scenario: Save rejection followed by activation is refused

- **WHEN** the player confirms while the last save was rejected and an older draft remains stored
- **THEN** the activation is refused with a stable code and no character is activated
