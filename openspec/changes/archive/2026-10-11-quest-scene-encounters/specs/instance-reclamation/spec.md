# Spec Delta

## MODIFIED Requirements

### Requirement: register_owned_entity marks an entity for despawn, not relocation, on reclaim

Instance disposable ownership SHALL remain idempotent per entity and mark ordinary owned occupants for despawn on reclamation. A published retained named role SHALL also carry a validated permanent retention locator and exact package-role identity. That retention declaration SHALL take precedence over disposable ownership at reclaim and SHALL never reset living state or grant party/follow or quest mutation authority.

#### Scenario: Disposable ownership remains idempotent
- **WHEN** an ordinary disposable occupant is registered twice as owned
- **THEN** it occurs once in ownership and remains eligible for ordinary despawn

#### Scenario: Retention declaration overrides disposable cleanup
- **WHEN** a retained named role is still inside its due reclaimable instance
- **THEN** its validated retention contract selects transfer rather than actor deletion

#### Scenario: Registering adds an entity exactly once
- **WHEN** `register_owned_entity(room, npc)` is called twice with the same `npc`
- **THEN** `room.db.owned_entities` contains `npc` exactly once

#### Scenario: An unregistered entity is not treated as owned
- **WHEN** an `NPC` is spawned into a room and placed there without ever calling
  `register_owned_entity()` for it
- **THEN** that `NPC` is absent from `room.db.owned_entities`

#### Scenario: Registration is the scene-spawn seam that marks a matching lifetime
- **WHEN** whoever spawns an entity into an instance room for that scene's own use (per design doc
  §7.2, ordinarily change 21's `SceneBuilder` spawning a `ScenarioDirector`-requested `npc_req`)
  calls this seam immediately afterward
- **THEN** `reclaim_due_instances()` knows the entity's lifetime is meant to match the room's own,
  rather than treating it as an incidental occupant to merely relocate

### Requirement: reclaim_due_instances despawns owned entities and relocates unowned ones before reclaiming a room

Before destructive reclamation, the maps owner SHALL transfer retained named actors still inside the room to their validated permanent retention destinations through existing movement hooks and remove ephemeral ownership in the same transaction as cleanup. Actors already outside SHALL remain where they are. Transfers SHALL preserve exact identity, persona, phase, memory, and actual living state and SHALL never clone or resurrect. Party/follow and quest release SHALL remain with their owning APIs, with escort release guarded until its owning capability lands. Other owned living occupants SHALL be deleted; ordinary unowned occupants SHALL retain default-home relocation behavior regardless of entity type. Existing player/pin safety checks SHALL precede writes and promotion SHALL remain non-destructive. Transfer or cleanup failure SHALL prevent destructive reclamation, restore affected caches, and record a named error without partial transfers or deletion.

#### Scenario: Retained role survives instance reclaim
- **WHEN** a due unpinned non-promotable instance contains a retained role and a disposable occupant
- **THEN** the same retained actor is moved to its declared permanent destination with history and state preserved, the disposable occupant is removed, and the room is reclaimed together

#### Scenario: Transfer failure keeps the room intact
- **WHEN** a retention destination is unavailable or a movement/cleanup write fails
- **THEN** the room and actors survive without partial movement, ownership loss or destructive deletion and a named error is recorded

#### Scenario: Outside actors and unrelated occupants are preserved
- **WHEN** a retained actor already left the instance while an ordinary unowned occupant remains
- **THEN** the retained actor's location is unchanged and the unowned occupant follows existing default-home relocation

#### Scenario: Promotion and safety gates remain non-destructive
- **WHEN** a due room is pinned, contains a player, refuses deletion, or qualifies for promotion
- **THEN** no retained or disposable actor is destructively cleared by that routing decision

#### Scenario: An NPC-bearing due room is eventually reclaimed, not permanently deferred
- **WHEN** a due, unpinned `InstanceRoom` contains only an `NPC` (no `PlayerCharacter`), and is not
  both `named` and `interacted`
- **THEN** `reclaim_due_instances()` reclaims the room in that same call: the room no longer exists in
  the database afterward, and the returned list includes a `ScheduledEvent` of kind
  `"instance_reclaimed"` for it; this is the direct test the original, uncorrected design lacked

#### Scenario: A registered (owned) NPC is despawned when its room reclaims
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains an ordinary disposable `NPC` previously passed to
  `register_owned_entity(room, npc)`
- **THEN** after reclamation, that `NPC` no longer exists in the database (it was deleted, not merely
  relocated)

#### Scenario: An unregistered NPC or Monster is relocated, never destroyed, when its room reclaims
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains an ordinary non-retained `NPC` or `Monster` that was
  never passed to `register_owned_entity()`
- **THEN** after reclamation, that entity still exists in the database, relocated to
  `settings.DEFAULT_HOME` rather than destroyed

#### Scenario: Entity clearing happens before the room's own deletion, not after
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains both an ordinary disposable registered and an
  unregistered `NPC`
- **THEN** both entities have already left the room's `contents` (one deleted, one relocated) by the
  time `room.delete()` is called, so the room's own `at_object_delete()` `PlayerCharacter`-only check
  is never put in conflict with a still-present NPC

#### Scenario: A refused delete defers with contents and ownership intact
- **WHEN** a due, unpinned, unoccupied `InstanceRoom` would nevertheless be refused by the typeclass
  safety net (simulated by a stub `InstanceRoom.at_object_delete()` returning `False`), and the room
  contains a registered and an unregistered `NPC` and a non-empty `owned_entities`
- **THEN** the call emits a `ScheduledEvent` of kind `"instance_reclaim_deferred"`, the room still
  exists, and both `NPC`s are still present in its `contents` with `owned_entities` unchanged; the
  safety net is consulted before any entity is despawned or relocated, so no partial state survives a
  refused delete

#### Scenario: Routing depends only on ownership, never on entity type
- **WHEN** an ordinary non-retained living occupant is routed for cleanup
- **THEN** owned membership selects deletion and unowned membership selects relocation regardless of NPC or Monster type; retained exact roles use their validated transfer contract first

#### Scenario: Entity clearing consults the typeclass safety net first
- **WHEN** the entity-clearing step is about to run for a room
- **THEN** it SHALL only ever run for a room the typeclass safety net would accept: the step SHALL
  first consult `InstanceRoom.at_object_delete()` (D-1), and if that returns `False`, SHALL emit
  `"instance_reclaim_deferred"` with no entity despawned or relocated; a deferred room therefore
  keeps its contents and its `owned_entities` registry intact, so the retry is side-effect-free

#### Scenario: The pre-check replaces the rolling-back-transaction draft
- **WHEN** this requirement's history is consulted
- **THEN** the safety-net pre-check replaces an earlier draft that cleared entities and then
  attempted deletion inside a rolling-back transaction; a design Evennia's idmapper does not
  reliably support, and which could leave an owned NPC data-lost on the refused-delete path
  (rubber-duck review)

#### Scenario: The rubber-duck-demanded resolution is eventual reclaim with one of two NPC outcomes
- **WHEN** a due NPC-only room has no player or pin and all required retention transfers can commit
- **THEN** reclamation proceeds with disposable owned NPCs deleted, ordinary unowned NPCs relocated, and retained roles transferred through their validated contract

