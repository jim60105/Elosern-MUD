## MODIFIED Requirements

### Requirement: explore.move traverses a re-resolved Exit through the shared movement path
explore.move SHALL accept exactly exit_ref/current_node, optionally plus exact walk:{pace,stop_at_night}; it SHALL re-resolve and re-authorize the Exit and canonical current node through the shared traversal path, preserving authenticated actor ownership and canonical-coordinate success detection.

#### Scenario: Keyboard movement charges the same 30 seconds as the command path
- **WHEN** an actor submits `explore.move` with a valid `exit_ref` and matching `current_node` for a traversable exit
- **THEN** the Exit traverses, `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, the actor's location is the destination, the destination node is recorded, and the snapshot reflects the new location

#### Scenario: A stale current_node guard performs no traversal
- **WHEN** an actor submits `explore.move` with a `current_node` that no longer matches the actor's location
- **THEN** the adapter rejects before any traversal, no time is charged, no knowledge is recorded, and the actor's location is unchanged

#### Scenario: A missing or locked exit rejects without charging
- **WHEN** an actor submits an `exit_ref` that is absent from the actor's room or whose `traverse` lock denies the actor
- **THEN** the adapter rejects with a stable reason, `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded

#### Scenario: Combat blocks menu movement
- **WHEN** an actor in an active combat session submits `explore.move`
- **THEN** the `at_pre_move` veto rejects the traversal, no time is charged, and no knowledge is recorded

#### Scenario: The move adapter never manipulates world state directly
- **WHEN** the `explore.move` adapter runs
- **THEN** it does not relocate the actor directly, does not accept a destination room ID, does not charge time itself, and does not assign location, knowledge, or clock state directly
- **AND** it obtains the actor from the authenticated session

#### Scenario: Traversal charges and records through the shared movement path
- **WHEN** the adapter invokes the Exit's own traversal method
- **THEN** `MovementCostMixin.at_post_traverse` charges the shared `CLOCK_YAML["command_defaults"]["move"]` cost and records the destination node through `record_arrival`
- **AND** the re-checks confirm the Exit's location is the actor's location and that its destination exists

#### Scenario: A rejected move leaves clock and discovery untouched
- **WHEN** a missing exit, a wrong node guard, a denied lock, or an active combat session (the `at_pre_move` veto) blocks a move
- **THEN** the adapter rejects with a stable code and Traditional Chinese message and does not advance the clock or record discovery

#### Scenario: A successful move refreshes everything in one snapshot
- **WHEN** an `explore.move` succeeds
- **THEN** the adapter publishes a full snapshot at one newer revision so the location change, clock charge, map, header, and shop/quest state refresh together

#### Scenario: Reused wilderness rooms report successful coordinate movement
- **WHEN** traversal changes the actor's canonical wilderness coordinates while retaining the same room object
- **THEN** the adapter reports `success` / `moved`, publishes the committed destination, and does not return `move_failed` solely because room identity is unchanged
- **AND** a traversal whose canonical location node is unchanged still rejects `move_failed`, whatever the room object's identity


#### Scenario: Exact optional walk union
- **WHEN** omitted, valid, extra-key, invalid-enum or non-boolean walk payloads are submitted
- **THEN** only the original two-field request and the exact valid three-field request are admitted, with unchanged traversal and stale-location guards
