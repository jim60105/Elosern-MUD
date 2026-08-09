## MODIFIED Requirements

### Requirement: Every NPC holds a hidden numeric affinity toward each player
Each NPC SHALL hold one affinity record per player it has interacted with, stored as serialized
data on the NPC's `relations_data` attribute through the `RelationHandler` mounted on
`LivingEntity.relations`. A record SHALL contain `value` (initial 0), `cap` (initial 99, mutable
only through `raise_affinity_cap`), the daily-gain counter, and the world-day tick at which that
counter started. Deserialization SHALL tolerate missing fields with defaults and SHALL reject
type-violating values by resetting the record to a fresh default (logging the event) rather than
raising, so a corrupted record can never crash a look or a conversation. Reading affinity SHALL NOT
create or persist a record: read APIs (`affinity_for`, `stage_for`) return defaults for players
without a record, and a `has_record` check SHALL distinguish a stored record from a default. The
numeric value SHALL be hidden from the player; only stage names are rendered (see the stage-ladder
requirement).

#### Scenario: A fresh NPC starts at zero affinity
- **WHEN** a player reads the affinity record of an NPC with no prior interaction
- **THEN** the reported value is 0, the cap is 99, and no record is persisted on the NPC

#### Scenario: Reading never materializes a record
- **WHEN** a player looks at a recordless NPC and then the NPC's stored data is inspected
- **THEN** `has_record` is false and `relations_data` holds no entry for that player

#### Scenario: A corrupted record resets instead of crashing
- **WHEN** an NPC's `relations_data` attribute holds a record whose `value` is a string
- **THEN** reading the record yields the fresh default record (value 0, cap 99) and logs the
  recovery instead of raising

#### Scenario: Records are keyed per player
- **WHEN** two different players interact with the same NPC
- **THEN** each player's record reads and writes independently

#### Scenario: The cap is mutable only through the sole cap writer
- **WHEN** the code paths that mutate a record's `cap` are inspected
- **THEN** every mutation goes through `raise_affinity_cap`, and a raised cap (e.g. 150) persists
  across serialization round trips without changing the value or the daily-gain fields
