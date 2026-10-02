## MODIFIED Requirements

### Requirement: Guild service hosts carry canonical age

The system SHALL persist canonical `age`/`apparent_age` on the guild service host NPCs (guild master
and merchant) created during `sync_guild_economy`. The hosts are identified by their service
component anchors (`service_id`), not by their display keys — their display keys are the authored
registry names. Each absent age attribute SHALL be initialized from the host's authored profile age pair,
preserving any existing attribute value.

#### Scenario: Service host has canonical age after sync
- **WHEN** `sync_guild_economy` creates the guild-master host or the merchant host for their
  service components
- **THEN** both NPCs have integer `age` and `apparent_age` reflecting their authored profile canonical ages
