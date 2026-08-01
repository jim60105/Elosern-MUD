## Purpose

The validated `spawn_instance_room()` entry point for map instances: the `INSTANCE_ROOM` module
prototype, prototype whitelisting and typeclass validation, rejection of an `InstanceRoom` as
`origin_room`, and the atomic creation of a room with its TTL/named/origin_room bookkeeping plus a
bidirectional plain-Exit attach pair.

## Requirements


### Requirement: INSTANCE_ROOM is a module prototype resolving to prototype_key "instance_room"
`world/prototypes.py` SHALL define `INSTANCE_ROOM`, a module-level dict with `"typeclass":
"typeclasses.rooms.InstanceRoom"` and no explicit `"prototype_key"`. `world/maps/instance.py` SHALL
define `INSTANCE_PROTOTYPE_WHITELIST: tuple[str, ...]`, containing exactly one entry, `"instance_room"`,
after this change.

#### Scenario: INSTANCE_ROOM resolves to prototype_key "instance_room"
- **WHEN** `evennia`'s module-prototype loading runs against `world/prototypes.py`
- **THEN** a prototype with `prototype_key == "instance_room"` is registered, with `typeclass ==
  "typeclasses.rooms.InstanceRoom"`

#### Scenario: The whitelist has exactly one entry after this change
- **WHEN** `INSTANCE_PROTOTYPE_WHITELIST` is inspected
- **THEN** it contains exactly `("instance_room",)`, and no test in this change's own suite asserts
  that any other value must also appear — a future change (change 21) may extend it

### Requirement: spawn_instance_room rejects an InstanceRoom as origin_room
`spawn_instance_room()` SHALL raise `ValueError` and SHALL NOT call `evennia.prototypes.spawner.spawn()`
when `origin_room` is an instance of `typeclasses.rooms.InstanceRoom`. This prevents a promoted room's
sole attach-exit pair from later being destroyed as a side effect of its `origin_room` (if that origin
were itself a reclaimable `InstanceRoom`) being deleted, which would leave the promoted room existing
but permanently unreachable.

#### Scenario: An ordinary origin_room is accepted
- **WHEN** `spawn_instance_room()` is called with `origin_room` being a `GridRoom`, `AnchorRoom`,
  `TerrainRoom`, or the stock `Room`
- **THEN** it succeeds and returns a new `InstanceRoom`

#### Scenario: An InstanceRoom origin_room is rejected before spawning
- **WHEN** `spawn_instance_room()` is called with `origin_room` being an `InstanceRoom`
- **THEN** it raises `ValueError`, and no new room, and no `Exit`, is created

### Requirement: spawn_instance_room validates prototype_parent against the whitelist before spawning
`world/maps/instance.py::spawn_instance_room(origin_room, prototype, *, exit_key, return_key,
ttl_seconds=None, named=False, caller=None)` SHALL raise `ValueError` and SHALL NOT call
`evennia.prototypes.spawner.spawn()` when `prototype.get("prototype_parent")` is not a member of
`INSTANCE_PROTOTYPE_WHITELIST`, or when the prototype declares an explicit `typeclass` that is not
exactly `"typeclasses.rooms.InstanceRoom"`. The raiser: a `prototype_parent` whitelist alone does not
bind the object `spawner.spawn()` actually creates — a prototype may chain from `"instance_room"` while
also overriding `typeclass` — and a reclaimed-by-exact-typeclass query
(`InstanceRoom.objects.all()`) would silently skip anything spawned that is not exactly an
`InstanceRoom`. This was found by rubber-duck review after the original whitelist-only check.

#### Scenario: A whitelisted prototype_parent is accepted
- **WHEN** `spawn_instance_room()` is called with a prototype whose `prototype_parent` is
  `"instance_room"` and no explicit `typeclass`
- **THEN** it returns an `InstanceRoom` instance, and `spawner.spawn()` was called

#### Scenario: A non-whitelisted prototype_parent is rejected before spawning
- **WHEN** `spawn_instance_room()` is called with a prototype whose `prototype_parent` is not in
  `INSTANCE_PROTOTYPE_WHITELIST`
- **THEN** it raises `ValueError`, and no `InstanceRoom` is created

#### Scenario: An explicit typeclass override is rejected before spawning
- **WHEN** `spawn_instance_room()` is called with a prototype whose `prototype_parent` is whitelisted
  but which declares `typeclass` other than `"typeclasses.rooms.InstanceRoom"`
- **THEN** it raises `ValueError` before `spawner.spawn()` is called, and no `InstanceRoom` is created

#### Scenario: A spawned object that is not an InstanceRoom is rejected and fully rolled back
- **WHEN** `spawner.spawn()` returns an object that is not an `InstanceRoom` despite a whitelisted
  prototype (defense in depth against a future prototype-resolution change)
- **THEN** `spawn_instance_room()` raises `ValueError`, no `Exit` is created, and the stray object is
  rolled back so it does not linger in the database

### Requirement: spawn_instance_room sets expire_tick, named, and origin_room, and creates a bidirectional attach exit
On success, `spawn_instance_room()` SHALL set the new room's `expire_tick` to
`get_world_clock().tick + ttl_seconds` (using `ttl_seconds` if given, otherwise
`INSTANCE_YAML["default_ttl_seconds"]`), set `named` to the caller-supplied value, set `origin_room` to
the caller-supplied `origin_room`, and create exactly two ordinary `Exit` objects: one at `origin_room`
keyed `exit_key` leading to the new room, and one at the new room keyed `return_key` leading back to
`origin_room`. Neither `Exit` SHALL be a subclass with a custom `at_traverse` override.

The spawn, attribute assignment, and both `Exit.create()` calls SHALL compose one atomic
all-or-nothing operation: if the second exit (or anything after the first) fails, the first exit and the
newly spawned room SHALL both be rolled back. Absent this, a partial attach would leave a room
reachable only one-way, or a room nobody can ever reach again, for the full TTL (rubber-duck review).

`ttl_seconds` SHALL, when provided, be a non-negative `int` (not a `bool`); any other value SHALL raise
`ValueError` before spawn.

#### Scenario: expire_tick is set from the default TTL when ttl_seconds is omitted
- **WHEN** `spawn_instance_room(origin_room, prototype, exit_key="in", return_key="out")` is called
  with `get_world_clock().tick` equal to `T`
- **THEN** the returned room's `expire_tick` equals `T + INSTANCE_YAML["default_ttl_seconds"]`

#### Scenario: expire_tick honors an explicit ttl_seconds override
- **WHEN** `spawn_instance_room(..., ttl_seconds=60)` is called with `get_world_clock().tick` equal to
  `T`
- **THEN** the returned room's `expire_tick` equals `T + 60`

#### Scenario: An invalid ttl_seconds is rejected before spawning
- **WHEN** `spawn_instance_room(..., ttl_seconds=-1)` or `ttl_seconds="60"` or `ttl_seconds=True` or
  `ttl_seconds=1.5` is called
- **THEN** it raises `ValueError` before `spawner.spawn()` is called

#### Scenario: named is set from the caller-supplied value
- **WHEN** `spawn_instance_room(..., named=True)` is called
- **THEN** the returned room's `named` is `True`; when `named` is omitted, it defaults to `False`

#### Scenario: A bidirectional plain Exit pair is created
- **WHEN** `spawn_instance_room(origin_room, prototype, exit_key="into the mist", return_key="back")`
  is called
- **THEN** `origin_room` has exactly one new exit keyed `"into the mist"` leading to the returned room,
  and the returned room has exactly one exit keyed `"back"` leading to `origin_room`, both plain
  `typeclasses.exits.Exit` instances with no `at_traverse` override

#### Scenario: A character can walk from origin_room into the instance room and back via ordinary traversal
- **WHEN** a character traverses the exit created by `spawn_instance_room()` from `origin_room`, then
  traverses the return exit
- **THEN** the character ends up back in `origin_room`, using only Evennia's default
  exit-traversal command with no custom movement code

#### Scenario: A failure creating the second exit rolls back the room and first exit
- **WHEN** the second `Exit.create()` call fails (simulated by a stub raising after the first has
  succeeded) during an otherwise valid `spawn_instance_room()` call
- **THEN** the call raises, and neither the newly spawned `InstanceRoom` nor either half of the attach
  exit pair exists in the database afterward