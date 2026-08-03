## MODIFIED Requirements

### Requirement: reclaim_due_instances deletes rooms that are due, unblocked, and not promotable
For every due `InstanceRoom` with no `PlayerCharacter` present, no active pin, that is not both
`named` and `interacted`, `reclaim_due_instances()` SHALL clear its non-player entities (per the
requirement above), call `room.delete()`, and emit a `ScheduledEvent` of kind `"instance_reclaimed"`
if deletion succeeds. `reclaim_due_instances()` SHALL NOT raise under any circumstance on this path:
if the typeclass safety net refuses the room (a `False` return from `InstanceRoom.at_object_delete()`
or from `room.delete()` itself), `reclaim_due_instances()` SHALL emit a `ScheduledEvent` of kind
`"instance_reclaim_deferred"` instead. When the refusal is discovered by the pre-flight safety-net
check (the only path expected to be reachable, and the only one that runs before any entity is
cleared), the deferred room's contents and ownership registry are untouched; a deferred event emitted
from the delete-result branch is an unreachable-in-normal-operation defensive outcome and SHALL still
not raise.

Inside the same `transaction.atomic()` block, `reclaim_due_instances()` SHALL call
`world.rules.map_knowledge.prune_reclaimed_room(room.id)` (the `map-knowledge` capability) **before**
`_clear_non_player_entities(room)` and `room.delete()` run, so every affected player's visited record
loses the reclaimed room's `room:<dbref>` in the same transaction as the room cleanup and deletion and
no knowledge failure ever occurs after room/entity caches have already been mutated. The pruning SHALL
snapshot each affected character's knowledge value before mutation and restore every snapshot on any
write failure, and SHALL raise a dedicated `KnowledgePruneError` only on a genuine persistence failure.
When `prune_reclaimed_room` raises, the reclaim branch SHALL mark the transaction for rollback
(`transaction.set_rollback(True)`) and SHALL append the deferred `ScheduledEvent` only after leaving
the atomic block; `reclaim_due_instances` SHALL NOT emit `"instance_reclaimed"` for a rolled-back
transaction. The pruning or deletion failure SHALL leave the room eligible for a later reclamation
attempt and SHALL NOT raise out of `reclaim_due_instances`. A promoted room (routed to the promotion
branch, `expire_tick` set to `None`) SHALL NOT be pruned and SHALL retain its visited identity.

#### Scenario: An unnamed, uninteracted due room with no occupants is reclaimed
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due room with no
  `PlayerCharacter` present and no pin has `named == False`
- **THEN** the room no longer exists in the database after the call, and the returned list includes a
  `ScheduledEvent` of kind `"instance_reclaimed"` for it

#### Scenario: Reclaiming a room does not destroy items left inside it
- **WHEN** a due, unpinned, unnamed `InstanceRoom` with no `PlayerCharacter` present contains a
  dropped item at the moment of reclamation
- **THEN** after reclamation the item still exists in the database, relocated rather than destroyed

#### Scenario: A ScheduledEvent's payload contains no live object reference
- **WHEN** any `ScheduledEvent` returned by `reclaim_due_instances()` is inspected
- **THEN** its `payload` contains only plain, JSON-compatible values

#### Scenario: Reclaiming a room removes its node from affected players in the same transaction
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due, unpinned, unnamed room is
  reclaimed while a `PlayerCharacter`'s visited record contains that room's `room:<dbref>`
- **THEN** after the call the room no longer exists, the player's record no longer contains the room's
  `room:<dbref>`, and the pruning and deletion committed or rolled back together

#### Scenario: A knowledge-pruning failure rolls back the deletion and defers the room
- **WHEN** a persistence failure is injected into the map-knowledge pruning inside the reclaim
  transaction
- **THEN** the room and its entities still exist afterward, every affected player's knowledge record is
  restored to its prior value, the returned events include `"instance_reclaim_deferred"` (appended
  after the atomic block) rather than `"instance_reclaimed"`, and `reclaim_due_instances` does not
  raise

#### Scenario: Pruning runs before room or entity mutation
- **WHEN** the reclaim branch's statement order is inspected
- **THEN** the `prune_reclaimed_room` call appears before `_clear_non_player_entities` and
  `room.delete()`, so no rollback ever has to restore already-mutated room/entity caches

#### Scenario: A promoted room is not pruned
- **WHEN** a due `InstanceRoom` that is both `named` and `interacted` is promoted
- **THEN** its `room:<dbref>` remains in every affected player's visited record and no pruning runs
