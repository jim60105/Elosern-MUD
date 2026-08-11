## ADDED Requirements

### Requirement: Generated guild offers survive a server restart

The system SHALL re-register the guild offers of all generated quests held in the durable store at startup, so the guild board lists them again and they can be accepted.

#### Scenario: Generated offer visible on the board after restart

- **WHEN** the server restarts while a generated quest offer exists in the durable store and has not been accepted
- **THEN** the guild board lists the generated offer and it can be accepted

#### Scenario: Accepted generated offer is not double-registered

- **WHEN** the server restarts after the generated offer was accepted
- **THEN** the offer is not listed again on the board and no duplicate offer record is created
