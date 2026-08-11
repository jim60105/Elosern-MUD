## ADDED Requirements

### Requirement: Guild service hosts carry adult identity

The system SHALL persist adult `age`/`apparent_age` on the guild service host NPCs (guild master and merchant) created during `sync_guild_economy`.

#### Scenario: Service host has adult age after sync

- **WHEN** `sync_guild_economy` creates `altoria_guild_master` or `altoria_merchant`
- **THEN** both NPCs have integer `age` and `apparent_age` of at least 18
