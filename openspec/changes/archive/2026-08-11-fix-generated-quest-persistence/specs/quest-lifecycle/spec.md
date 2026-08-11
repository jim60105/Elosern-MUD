## ADDED Requirements

### Requirement: Generated quest definitions resolve after a server restart

The system SHALL restore all generated quest definitions, offers, and spawn requirements from the durable store at startup, before any player quest-log read, so persisted records referencing generated definitions resolve normally.

#### Scenario: Accepted generated quest remains readable after restart

- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** `guild log` and all other quest-log reads succeed and list the accepted quest

#### Scenario: Accepted generated quest remains abandonable after restart

- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** the player can abandon that quest without error

#### Scenario: Restore is idempotent across repeated restarts

- **WHEN** the server restarts multiple times with generated quests in the store
- **THEN** each generated quest is registered exactly once and quest-log reads succeed
