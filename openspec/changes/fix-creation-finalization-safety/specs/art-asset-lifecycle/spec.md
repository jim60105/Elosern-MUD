## ADDED Requirements

### Requirement: Every player-activation path finalizes the portrait lifecycle

The system SHALL run identical portrait finalization — assigning the named `portrait_policy` and scheduling a post-commit portrait ensure — on every successful player activation path, Telnet and Web alike.

#### Scenario: Web activation assigns the portrait policy

- **WHEN** a character is activated through the Web creation flow
- **THEN** the character has a named `portrait_policy` with stable key `str(pk)` and exactly one portrait ensure is scheduled

#### Scenario: Telnet and Web activation produce identical portrait state

- **WHEN** a character is activated through Telnet and another through the Web flow
- **THEN** both characters carry the same policy shape and both have portrait jobs queued

#### Scenario: Rolled-back activation leaves no portrait state

- **WHEN** the activation transaction fails after the policy would have been assigned
- **THEN** no `portrait_policy` and no portrait job remain on the character
