## ADDED Requirements

### Requirement: default_ttl_seconds is declared rulebook data
`world/rules/rulebook/instance.yaml` SHALL declare `default_ttl_seconds: 345600` (4 in-game days at
`hours_per_day: 24` / `seconds_per_hour: 3600`, matching `clock.yaml`'s own calendar constants).

#### Scenario: default_ttl_seconds is present and matches the stated arithmetic
- **WHEN** `world/rules/rulebook/instance.yaml` is inspected after this change lands
- **THEN** `default_ttl_seconds == 345600`, equal to `4 * CLOCK_YAML["hours_per_day"] *
  CLOCK_YAML["seconds_per_hour"]`

### Requirement: pin_instance_room and unpin_instance_room are reason-keyed reference holders
`world/maps/instance.py::pin_instance_room(room, reason: str)` SHALL append `reason` to
`room.db.pin_reasons` if not already present. `unpin_instance_room(room, reason: str)` SHALL remove
`reason` from `room.db.pin_reasons` if present, and SHALL NOT raise if `reason` is absent. Neither
function SHALL inspect or interpret the content of `reason` beyond membership testing.

#### Scenario: Pinning adds a reason exactly once
- **WHEN** `pin_instance_room(room, "quest:1:stage:0")` is called twice in succession
- **THEN** `room.db.pin_reasons` contains `"quest:1:stage:0"` exactly once

#### Scenario: Unpinning removes only the matching reason
- **WHEN** a room is pinned with two distinct reasons and `unpin_instance_room()` is called with one
  of them
- **THEN** `room.db.pin_reasons` still contains the other reason, and no longer contains the removed
  one

#### Scenario: Unpinning an absent reason does not raise
- **WHEN** `unpin_instance_room(room, "never_pinned")` is called on a room whose `pin_reasons` does not
  contain `"never_pinned"`
- **THEN** no exception is raised, and `room.db.pin_reasons` is unchanged

### Requirement: register_owned_entity marks an entity for despawn, not relocation, on reclaim
`world/maps/instance.py::register_owned_entity(room, entity)` SHALL append `entity` to
`room.db.owned_entities` if not already present. This is the seam whoever spawns an entity into an
instance room for that scene's own use (per design doc §7.2, ordinarily change 21's `SceneBuilder`
spawning a `ScenarioDirector`-requested `npc_req`) calls immediately afterward, so
`reclaim_due_instances()` knows the entity's lifetime is meant to match the room's own, rather than
treating it as an incidental occupant to merely relocate.

#### Scenario: Registering adds an entity exactly once
- **WHEN** `register_owned_entity(room, npc)` is called twice with the same `npc`
- **THEN** `room.db.owned_entities` contains `npc` exactly once

#### Scenario: An unregistered entity is not treated as owned
- **WHEN** an `NPC` is spawned into a room and placed there without ever calling
  `register_owned_entity()` for it
- **THEN** that `NPC` is absent from `room.db.owned_entities`

### Requirement: reclaim_due_instances defers only rooms with a PlayerCharacter present or an active pin
`world/maps/instance.py::reclaim_due_instances(start_tick, end_tick)` SHALL, for every `InstanceRoom`
with `expire_tick is not None and expire_tick <= end_tick`, defer (neither delete nor promote) any
room whose `pin_reasons` is non-empty or whose `contents` includes any
`typeclasses.characters.PlayerCharacter` instance, emitting a `ScheduledEvent` of kind
`"instance_reclaim_deferred"`. A deferred room's `expire_tick` SHALL be left unchanged, so it is
re-evaluated on every subsequent call. The presence of an `NPC` or `Monster` alone, with no
`PlayerCharacter` present, SHALL NOT defer reclamation — see the despawn/relocate requirement below
for how such entities are resolved instead.

This requirement was corrected by rubber-duck review from an earlier draft that deferred on any
`LivingEntity` (including NPCs). Design doc §7.1/§7.2 makes an NPC-occupied instance room the normal
case for a quest scene, not an edge case, and with no NPC despawn mechanism anywhere in the codebase,
deferring on NPC presence alone meant such a room would never resolve — the corrected rule below is
what a conforming implementation SHALL enforce.

#### Scenario: A room with a PlayerCharacter present is deferred, not reclaimed
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due `InstanceRoom` contains a
  `PlayerCharacter`
- **THEN** the room still exists after the call, its `expire_tick` is unchanged, and the returned list
  includes a `ScheduledEvent` of kind `"instance_reclaim_deferred"` for that room

#### Scenario: A pinned due room is deferred, not reclaimed
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due room with no
  `PlayerCharacter` present has a non-empty `pin_reasons`
- **THEN** the room still exists after the call and its `expire_tick` is unchanged

#### Scenario: A room with only an NPC or Monster present is NOT deferred solely for that reason
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due, unpinned `InstanceRoom`
  contains an `NPC` or `Monster` but no `PlayerCharacter`
- **THEN** the room is routed to promotion or reclamation per the requirements below, not deferred —
  the direct regression check for the corrected rule above

#### Scenario: A deferred room is re-evaluated on the next call
- **WHEN** a room deferred by one `reclaim_due_instances()` call becomes free of any `PlayerCharacter`
  and unpinned before the next `advance()` call
- **THEN** the next `reclaim_due_instances()` call reclaims or promotes it, with no additional
  bookkeeping required to "remember" it was previously due

### Requirement: reclaim_due_instances promotes rooms that are both named and interacted
For every due `InstanceRoom` with no `PlayerCharacter` present and no active pin, whose `named` and
`interacted` are both `True`, `reclaim_due_instances()` SHALL set `expire_tick` to `None` (promotion)
rather than deleting the room, and SHALL emit a `ScheduledEvent` of kind `"instance_promoted"`. The
room, its exits, and any `NPC`/`Monster` still inside it SHALL be left otherwise unchanged — promotion
SHALL NOT despawn or relocate any entity; only the reclaim path (below) does.

#### Scenario: A named, interacted, due room is promoted, not deleted
- **WHEN** `reclaim_due_instances(start_tick, end_tick)` is called and a due room with no
  `PlayerCharacter` present and no pin has `named == True` and `interacted == True`
- **THEN** the room still exists after the call, its `expire_tick` is `None`, and the returned list
  includes a `ScheduledEvent` of kind `"instance_promoted"` for that room

#### Scenario: A promoted room's exits are untouched
- **WHEN** a room is promoted
- **THEN** the `Exit` pair connecting it to its `origin_room` (created by `spawn_instance_room`)
  still exists afterward, unmodified

#### Scenario: A promoted room's NPC occupant is left in place, neither despawned nor relocated
- **WHEN** a room containing an `NPC` is promoted
- **THEN** that `NPC` is still present in the room afterward, unaffected

#### Scenario: A promoted room never becomes due again
- **WHEN** `reclaim_due_instances()` is called again after a room has been promoted
- **THEN** the promoted room is skipped entirely (its `expire_tick is None`), with no
  `ScheduledEvent` emitted for it

#### Scenario: named alone, without interacted, does not promote
- **WHEN** a due room with no `PlayerCharacter` present and no pin has `named == True` but
  `interacted == False`
- **THEN** the room is reclaimed (deleted), not promoted

#### Scenario: interacted alone, without named, does not promote
- **WHEN** a due room with no `PlayerCharacter` present and no pin has `interacted == True` but
  `named == False`
- **THEN** the room is reclaimed (deleted), not promoted

### Requirement: reclaim_due_instances despawns owned entities and relocates unowned ones before reclaiming a room
Immediately before `reclaim_due_instances()` deletes a room routed to reclamation (not promotion), it
SHALL, for every `typeclasses.entities.LivingEntity` instance still in that room's `contents`: delete
it if it appears in `room.db.owned_entities`; otherwise relocate it to `settings.DEFAULT_HOME` (via
the same lookup `DefaultObject.clear_contents()` itself uses) without deleting it. Only after this
step SHALL `room.delete()` be called. This requirement SHALL hold regardless of whether the entity is
an `NPC` or `Monster` — the routing rule (despawn vs. relocate) depends only on `owned_entities`
membership, never on entity type.

The entity clearing SHALL only ever run for a room the typeclass safety net would accept: the step
SHALL first consult `InstanceRoom.at_object_delete()` (D-1), and if that returns `False`, SHALL emit
`"instance_reclaim_deferred"` with no entity despawned or relocated. A deferred room therefore keeps
its contents and its `owned_entities` registry intact, so the retry is side-effect-free. This replaces
an earlier draft that cleared entities and then attempted deletion inside a rolling-back transaction —
a design Evennia's idmapper does not reliably support, and which could leave an owned NPC data-lost on
the refused-delete path (rubber-duck review).

This is the concrete resolution the rubber-duck review demanded: a due room containing only an NPC
(no `PlayerCharacter`, no pin) is not merely deferred forever — it is **actually and eventually
reclaimed**, with its NPC handled by exactly one of the two specified outcomes below.

#### Scenario: An NPC-bearing due room is eventually reclaimed, not permanently deferred
- **WHEN** a due, unpinned `InstanceRoom` contains only an `NPC` (no `PlayerCharacter`), and is not
  both `named` and `interacted`
- **THEN** `reclaim_due_instances()` reclaims the room in that same call: the room no longer exists in
  the database afterward, and the returned list includes a `ScheduledEvent` of kind
  `"instance_reclaimed"` for it — this is the direct test the original, uncorrected design lacked

#### Scenario: A registered (owned) NPC is despawned when its room reclaims
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains an `NPC` previously passed to
  `register_owned_entity(room, npc)`
- **THEN** after reclamation, that `NPC` no longer exists in the database (it was deleted, not merely
  relocated)

#### Scenario: An unregistered NPC or Monster is relocated, never destroyed, when its room reclaims
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains an `NPC` or `Monster` that was
  never passed to `register_owned_entity()`
- **THEN** after reclamation, that entity still exists in the database, relocated to
  `settings.DEFAULT_HOME` rather than destroyed

#### Scenario: Entity clearing happens before the room's own deletion, not after
- **WHEN** a due, unpinned, non-promotable `InstanceRoom` contains both a registered and an
  unregistered `NPC`
- **THEN** both entities have already left the room's `contents` (one deleted, one relocated) by the
  time `room.delete()` is called, so the room's own `at_object_delete()` `PlayerCharacter`-only check
  is never put in conflict with a still-present NPC

#### Scenario: A refused delete defers with contents and ownership intact
- **WHEN** a due, unpinned, unoccupied `InstanceRoom` would nevertheless be refused by the typeclass
  safety net (simulated by a stub `InstanceRoom.at_object_delete()` returning `False`), and the room
  contains a registered and an unregistered `NPC` and a non-empty `owned_entities`
- **THEN** the call emits a `ScheduledEvent` of kind `"instance_reclaim_deferred"`, the room still
  exists, and both `NPC`s are still present in its `contents` with `owned_entities` unchanged — the
  safety net is consulted before any entity is despawned or relocated, so no partial state survives a
  refused delete

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

### Requirement: reclaim_due_instances is registered as the instance_reclamation event source at server start
`world/maps/instance.py::register_instance_reclamation()` SHALL call
`world.rules.clock.register_event_source("instance_reclamation", reclaim_due_instances)`. This SHALL
be invoked from the same startup flow that invokes change 12's grid provisioning, so it runs
automatically on every server start with no manual operator action.

#### Scenario: Registration makes instance_reclamation a live stage
- **WHEN** `register_instance_reclamation()` has run, and `WorldClock.advance()` is subsequently called
  across a boundary at or after a due `InstanceRoom`'s `expire_tick`
- **THEN** that room is reclaimed or promoted as part of that `advance()` call, with no separate
  function call needed beyond `advance()` itself

#### Scenario: Before registration, instance_reclamation is a no-op stage like any other unregistered kind
- **WHEN** `WorldClock.advance()` is called before `register_instance_reclamation()` has ever run
- **THEN** the call completes successfully and no `InstanceRoom` is reclaimed or promoted as a side
  effect
