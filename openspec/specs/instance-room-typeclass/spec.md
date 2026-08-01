## Purpose

The `InstanceRoom` typeclass for spawnable, reclaimable map instances: a coordinate-free room that
adopts the `SceneArchetypeMixin` seam, persists the six attributes governing its TTL reclamation
lifecycle, and gates `interacted` and deletion on player presence and pin state.

## Requirements


### Requirement: InstanceRoom carries no coordinate and adopts SceneArchetypeMixin
`typeclasses/rooms.py` SHALL define `InstanceRoom`, subclassing `SceneArchetypeMixin` (change 13's
`scene-archetype-mixin` capability) and `evennia.objects.objects.DefaultRoom`. `InstanceRoom` SHALL
NOT subclass `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom` or
`evennia.contrib.grid.wilderness.wilderness.WildernessRoom`, and SHALL expose no `xyz`/coordinate
property of any kind.

#### Scenario: InstanceRoom shares the scene_archetype seam
- **WHEN** `InstanceRoom`'s method resolution order is inspected
- **THEN** `SceneArchetypeMixin` appears in it, and a newly created `InstanceRoom` has
  `scene_archetype is None` by default, accepting an arbitrary string with no registry lookup,
  identically to `GridRoom` and `TerrainRoom`

#### Scenario: InstanceRoom has no coordinate machinery
- **WHEN** `InstanceRoom`'s method resolution order is inspected
- **THEN** it includes neither `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom` nor
  `evennia.contrib.grid.wilderness.wilderness.WildernessRoom`, and the class defines no `xyz`
  attribute or property

#### Scenario: A newly created InstanceRoom has no location
- **WHEN** an `InstanceRoom` is created directly (not yet attached via spawn_instance_room)
- **THEN** its `.location` is `None`, identically to any other freshly created `DefaultRoom`

### Requirement: InstanceRoom persists expire_tick, named, interacted, pin_reasons, owned_entities, and origin_room
`InstanceRoom` SHALL expose six persistent attributes: `expire_tick: int | None` (default `None`),
`named: bool` (default `False`), `interacted: bool` (default `False`), `pin_reasons: list[str]`
(default an empty list), `owned_entities: list` (default an empty list — entities registered via
`register_owned_entity()` to be despawned, rather than merely relocated, when this room reclaims), and
`origin_room` (default `None`). `expire_tick` of `None` SHALL mean the room is not subject to TTL
reclamation (either never assigned one, or promoted).

#### Scenario: Defaults on a freshly created InstanceRoom
- **WHEN** an `InstanceRoom` is created with none of the six attributes explicitly set
- **THEN** `expire_tick is None`, `named is False`, `interacted is False`, `pin_reasons == []`,
  `owned_entities == []`, and `origin_room is None`

#### Scenario: All six attributes persist across a reload
- **WHEN** each of the six attributes is set to a non-default value and the room is re-fetched from
  the database
- **THEN** the re-fetched room's values match what was set

### Requirement: at_object_receive sets interacted to True the first time a PlayerCharacter enters
`InstanceRoom.at_object_receive` SHALL set `self.db.interacted = True` when the entering object is an
instance of `typeclasses.characters.PlayerCharacter`. It SHALL NOT set `interacted` for any other
entering object type, and SHALL NOT unset `interacted` once it is `True`.

#### Scenario: A PlayerCharacter entering sets interacted
- **WHEN** a `PlayerCharacter` moves into an `InstanceRoom` whose `interacted` is `False`
- **THEN** `room.db.interacted` becomes `True`

#### Scenario: An NPC or Monster entering does not set interacted
- **WHEN** an `NPC` or `Monster` (not a `PlayerCharacter`) moves into an `InstanceRoom` whose
  `interacted` is `False`
- **THEN** `room.db.interacted` remains `False`

#### Scenario: interacted stays True once set
- **WHEN** `interacted` is already `True` and any object subsequently enters the room
- **THEN** `room.db.interacted` remains `True`

### Requirement: at_object_delete refuses deletion while a PlayerCharacter is present or the room is pinned
`InstanceRoom.at_object_delete` SHALL return `False`, aborting deletion, when `self.db.pin_reasons` is
non-empty, or when `self.contents` includes any instance of `typeclasses.characters.PlayerCharacter`.
It SHALL return `True` (permitting deletion, subject to the superclass's own `at_object_delete`) when
neither condition holds — including when the room's contents include an `NPC` or `Monster` but no
`PlayerCharacter`, since non-player entity presence alone SHALL NOT block deletion at the typeclass
level (see the `instance-reclamation` capability for how a reclaiming room's own non-player occupants
are despawned or relocated before this check is ever exercised in the normal path).

This requirement was corrected by rubber-duck review from an earlier draft that refused deletion for
*any* `LivingEntity` present, including NPCs. That earlier rule made reclamation of a room containing
a quest-spawned NPC (design doc §7.1/§7.2's normal case, not an edge case) defer forever, since no
NPC-despawn mechanism exists to ever clear the blocking condition. The corrected rule below is what a
conforming implementation SHALL enforce.

#### Scenario: Deletion is refused while pinned
- **WHEN** `room.delete()` is called on an `InstanceRoom` with a non-empty `pin_reasons`
- **THEN** `delete()` returns `False`, and the room still exists in the database afterward

#### Scenario: Deletion is refused while a PlayerCharacter is present
- **WHEN** `room.delete()` is called on an `InstanceRoom` whose contents include a `PlayerCharacter`
- **THEN** `delete()` returns `False`, and the room still exists in the database afterward

#### Scenario: Deletion is NOT refused solely because an NPC or Monster is present
- **WHEN** `room.delete()` is called on an `InstanceRoom` with an empty `pin_reasons` whose contents
  include an `NPC` or `Monster` but no `PlayerCharacter`
- **THEN** `delete()` returns `True`, and the room no longer exists in the database afterward — the
  regression check for the corrected rule above

#### Scenario: Deletion succeeds once unpinned and no PlayerCharacter is present
- **WHEN** `room.delete()` is called on an `InstanceRoom` with an empty `pin_reasons` and no
  `PlayerCharacter` among its contents
- **THEN** `delete()` returns `True`, and the room no longer exists in the database afterward

#### Scenario: The safety check applies regardless of caller
- **WHEN** any code path calls `.delete()` directly on a pinned `InstanceRoom`, or one with a
  `PlayerCharacter` present, not only `reclaim_due_instances()`
- **THEN** deletion is still refused — the safety net does not depend on going through any particular
  call site