# sample-city-altoria delta

## MODIFIED Requirements

### Requirement: Guild service hosts carry adult identity

The system SHALL persist adult `age`/`apparent_age` on the guild service host NPCs (guild master
and merchant) created during `sync_guild_economy`. The hosts are identified by their service
component anchors (`service_id`), not by their display keys — their display keys are the authored
registry names.

#### Scenario: Service host has adult age after sync
- **WHEN** `sync_guild_economy` creates the guild-master host or the merchant host for their
  service components
- **THEN** both NPCs have integer `age` and `apparent_age` of at least 18
