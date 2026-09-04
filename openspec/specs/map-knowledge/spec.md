## Purpose

Persisted visited-node discovery per player character: the versioned knowledge record owned by
`world/rules/map_knowledge.py`, the strict per-layer node-ID grammar, arrival recording at the existing
successful-arrival seams, reclaimed-room pruning inside the
instance-reclamation transaction, and the deterministic read parser presenters consume.

## Requirements

### Requirement: map_knowledge.py is the sole writer of a versioned visited-node record
`world/rules/map_knowledge.py` SHALL be the only module that writes the player's map-knowledge
attribute. The record SHALL be a JSON-safe dict of exactly `{"schema_version": 1, "visited": {...}}`,
where `visited` maps canonical node IDs to `{"first_seen_tick": int, "last_seen_tick": int}` with
non-negative integer ticks. `world/rules/map_knowledge.py` SHALL expose `record_arrival(character)`,
`prune_reclaimed_room(room_id)`, `parse_knowledge(character)`, and node-ID `encode`/`decode`/`validate`
helpers. No presenter, command, adapter, or other module SHALL assign the knowledge attribute directly.
Startup and reconnect SHALL change neither `first_seen_tick` nor `last_seen_tick`; only a successful
arrival records an observation.

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
- **THEN** it contains only node IDs and observation ticks — no room names, descriptions, glyphs,
  exit keys, or coordinates as independent fields

### Requirement: Node IDs use strict per-layer grammar with registered, bounded components
Node IDs SHALL follow exactly one of these forms: `grid:<z-map-key>:<x>:<y>` for the Grid/Anchor
layer, `wild:<wilderness-name>:<x>:<y>` for the Wilderness layer, and `room:<dbref>` for Instance and
ordinary interior rooms. Grid/wilderness X and Y SHALL be integers within the provider/map bounds;
`z-map-key` and `wilderness-name` SHALL be registered bounded strings; `room:<dbref>` SHALL be a
positive integer dbref. Component values SHALL be escaped or restricted so delimiters cannot produce
an ambiguous ID. `decode`/`validate` SHALL reject missing, extra, unknown, non-integer, out-of-bounds,
or malformed components. A `room:<dbref>` whose object no longer exists SHALL resolve as unavailable
and SHALL be eligible for pruning.

#### Scenario: A valid grid node ID round-trips
- **WHEN** a canonical node ID of the form `grid:capital_altoria:2:0` is decoded and re-encoded
- **THEN** the result equals the input and the decoded components are `z-map-key="capital_altoria"`,
  `x=2`, `y=0`

#### Scenario: A valid wilderness node ID round-trips
- **WHEN** a canonical node ID of the form `wild:elosern:10:15` is decoded and re-encoded
- **THEN** the result equals the input and the decoded components are `wilderness-name="elosern"`,
  `x=10`, `y=15`

#### Scenario: A valid room node ID round-trips
- **WHEN** a canonical node ID of the form `room:42` is decoded and re-encoded
- **THEN** the result equals the input and the decoded dbref is `42`

#### Scenario: Malformed and out-of-bounds IDs are rejected
- **WHEN** `validate`/`decode` is called with an unknown layer prefix, a non-integer coordinate, a
  coordinate outside the provider or map bounds, an extra component, a missing component, or a
  zero/negative/boolean dbref
- **THEN** parsing rejects the ID and no node is produced

### Requirement: Arrival recording happens only at existing successful-arrival seams
`world/rules/map_knowledge.py`'s `record_arrival` SHALL be invoked only from the project's existing
successful-arrival seams: the shared movement-completion helper
`typeclasses.exits.after_successful_movement` — which the `MovementCostMixin.at_post_traverse`, the
success branch of `WildernessGateExit.at_traverse`, and both success branches of
`WildernessReturnExit.at_traverse` all call after `charge_movement`. Failed traversal, locked exits, vetoed
`at_pre_move`, rolled-back movement, teleport-style `move_to` calls, quiet reclamation relocations,
search, map rendering, and remote inspection SHALL NOT record discovery. The derived node SHALL be
computed from the character's current location at recording time, so grid, wilderness, instance, and
interior each yield their canonical identity without per-seam node computation.

#### Scenario: Grid traversal records the destination after success
- **WHEN** a `PlayerCharacter` successfully traverses a `CostedXYZExit` or an ordinary `Exit`
  (including the Limbo bridge and an instance doorway pair)
- **THEN** the knowledge record contains the destination's canonical `grid:` or `room:` node ID with a
  `last_seen_tick` equal to the current world tick

#### Scenario: Wilderness stepping records the destination coordinate after success
- **WHEN** a `PlayerCharacter` successfully enters the wilderness through `WildernessGateExit` or
  takes a successful wilderness step through `WildernessReturnExit`
- **THEN** the knowledge record contains the destination's `wild:` node ID with the current world tick

#### Scenario: A blocked or failed traversal records nothing
- **WHEN** an exit traversal fails its locks, a pre-move veto aborts it, or a movement transaction
  rolls back
- **THEN** the knowledge record is unchanged and no new or updated observation appears

#### Scenario: A quiet reclamation relocation records nothing
- **WHEN** an unowned occupant is relocated to `settings.DEFAULT_HOME` during instance reclamation
- **THEN** no map knowledge is recorded for that relocation

### Requirement: Reclaimed room knowledge is pruned transactionally with the room deletion
`world/rules/map_knowledge.py::prune_reclaimed_room(room_id)` SHALL remove `room:<room_id>` from every
player's knowledge record. It SHALL select only `PlayerCharacter`s that already carry the knowledge
attribute, SHALL strictly parse each selected record, and SHALL write back only records that actually
contain the target node — never creating the attribute for a character that does not already have it.
It SHALL snapshot each affected character's knowledge value before mutation and restore every snapshot
on any write failure, logging a diagnostic. It SHALL return a boolean success indicator and SHALL raise
a dedicated `KnowledgePruneError` only on a genuine persistence failure. `world/maps/instance.py::
reclaim_due_instances` SHALL call it inside the reclaim `transaction.atomic()` block, **before**
`_clear_non_player_entities(room)` and `room.delete()` run, so a knowledge failure never occurs after
room/entity caches have already been mutated. A `KnowledgePruneError` SHALL cause the reclaim branch to
mark the transaction for rollback (`transaction.set_rollback(True)`) and SHALL result in a deferred
`ScheduledEvent` appended only after leaving the atomic block; `reclaim_due_instances` SHALL NOT emit
`"instance_reclaimed"` for a rolled-back transaction. A pruning or deletion failure SHALL leave the
room eligible for a later reclamation attempt and SHALL NOT raise out of `reclaim_due_instances`. A
promoted room SHALL NOT be pruned.

#### Scenario: Reclaiming an instance room removes its node from affected players
- **WHEN** `reclaim_due_instances()` reclaims (deletes) an `InstanceRoom` whose `room:<dbref>` appears
  in a player's knowledge record
- **THEN** after the transaction the player's record no longer contains that node ID

#### Scenario: Players who never visited the room are untouched
- **WHEN** `reclaim_due_instances()` reclaims an `InstanceRoom` absent from a player's knowledge record
- **THEN** that player's record is unchanged, and no knowledge attribute is created or rewritten for
  that player

#### Scenario: A player without a knowledge attribute is not given one by pruning
- **WHEN** `prune_reclaimed_room(room_id)` runs and a `PlayerCharacter` has never had a knowledge
  attribute
- **THEN** that character still has no knowledge attribute afterward

#### Scenario: A promoted room retains its visited identity
- **WHEN** an `InstanceRoom` is promoted (named and interacted, `expire_tick` set to `None`)
- **THEN** its `room:<dbref>` remains in every player's knowledge record that had visited it

#### Scenario: A pruning failure rolls back the reclaim and defers the room
- **WHEN** a persistence failure is injected into the knowledge write inside the reclaim transaction
- **THEN** the room, its exits, and its entities still exist afterward, the player records are restored
  to their prior values, the returned events include `"instance_reclaim_deferred"` (appended after the
  atomic block) rather than `"instance_reclaimed"`, and `reclaim_due_instances` does not raise

#### Scenario: Pruning runs before room or entity mutation
- **WHEN** `reclaim_due_instances()` inspects the reclaim branch's statement order
- **THEN** the `prune_reclaimed_room` call appears before `_clear_non_player_entities` and
  `room.delete()`, so no rollback ever has to restore mutated room/entity caches

### Requirement: parse_knowledge isolates corrupt records without resetting them
`world/rules/map_knowledge.py::parse_knowledge(character)` SHALL return a normalized, deterministically
ordered view of the character's knowledge for presentation, and SHALL raise a dedicated error (not
return a reset record) when the stored value is missing, malformed, has an unknown `schema_version`,
contains an invalid node ID, or has non-integer ticks. A presenter receiving that error SHALL make the
minimap unavailable without clearing or overwriting the player's history during a read.

#### Scenario: A valid record parses in deterministic order
- **WHEN** `parse_knowledge()` is called on a valid record with several nodes
- **THEN** the returned nodes are in a stable deterministic order independent of dict insertion order

#### Scenario: A corrupt record raises and is not reset
- **WHEN** `parse_knowledge()` is called on a record with an invalid node ID or unknown schema version
- **THEN** it raises the dedicated error and the stored attribute value is unchanged
