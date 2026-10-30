## MODIFIED Requirements

### Requirement: map_knowledge.py is the sole writer of a versioned visited-node record
world/rules/map_knowledge.py SHALL exclusively write schema2 map knowledge, with grid/room tick pairs and bounded chunk-addressed wilderness tick/radius observations, preserving corrupt records without conversion.

#### Scenario: record_arrival creates a first observation
- **WHEN** `record_arrival(character)` is called for a character at a canonical node at world tick 30
- **THEN** the character's knowledge record contains that node with `first_seen_tick == 30` and
  `last_seen_tick == 30`

#### Scenario: record_arrival updates last_seen and preserves first_seen
- **WHEN** `record_arrival(character)` is called twice for the same node, at ticks 30 and 90
- **THEN** the record keeps `first_seen_tick == 30` and updates `last_seen_tick == 90`

#### Scenario: record_arrival is a no-op for a non-PlayerCharacter
- **WHEN** `record_arrival()` is called with an `NPC` or `Monster`
- **THEN** no knowledge attribute is created or changed on that object

#### Scenario: record_arrival no-ops on a corrupt pre-existing record without resetting it
- **WHEN** `record_arrival()` is called for a character whose stored record is malformed or has an
  unknown schema version
- **THEN** the stored value is unchanged, a safe diagnostic is logged, no exception reaches the
  caller, and the traversal that triggered the call still completes normally

#### Scenario: Reconnect does not re-observe
- **WHEN** a character logs out, logs back in, and no arrival occurs
- **THEN** every node's `first_seen_tick` and `last_seen_tick` are unchanged from before the reconnect

#### Scenario: The record stores no duplicate geometry or room names
- **WHEN** the knowledge record is inspected after several arrivals
- **THEN** it contains only canonical identities/chunk addresses, observation ticks and wilderness sight, with no room names, descriptions, glyphs, exit keys or duplicate independent geometry

#### Scenario: The module exposes the full knowledge API
- **WHEN** the public surface of `world/rules/map_knowledge.py` is inspected
- **THEN** it exposes `record_arrival(character)`, `prune_reclaimed_room(room_id)`,
  `parse_knowledge(character)`, and node-ID `encode`/`decode`/`validate` helpers

#### Scenario: No other module assigns the knowledge attribute directly
- **WHEN** a presenter, command, adapter, or other module touches map knowledge
- **THEN** it goes through `world/rules/map_knowledge.py` and never assigns the knowledge attribute directly

#### Scenario: Server startup does not re-observe
- **WHEN** the server starts and no arrival occurs
- **THEN** every node's `first_seen_tick` and `last_seen_tick` are unchanged, because only a
  successful arrival records an observation


### Requirement: parse_knowledge isolates corrupt records without resetting them
parse_knowledge SHALL return deterministic schema2 visit projections and reject missing, malformed or unknown records without resetting them; non-wilderness presenters SHALL retain unavailable behavior, while wilderness reveal readers use only independently valid lit membership on observation failure.

#### Scenario: A valid record parses in deterministic order
- **WHEN** `parse_knowledge()` is called on a valid record with several nodes
- **THEN** the returned nodes are in a stable deterministic order independent of dict insertion order

#### Scenario: A corrupt record raises and is not reset
- **WHEN** `parse_knowledge()` is called on a record with an invalid node ID or unknown schema version
- **THEN** it raises the dedicated error and the stored attribute value is unchanged


