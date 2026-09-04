# Delta: limbo-one-way-gates

## ADDED Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
`world/maps/city_gates.py` SHALL define a frozen, slotted `CityGateDef` dataclass with the fields `map_id` (str), `gate_xyz` (a `(int, int, str)` grid coordinate), `exit_key` (str), and `exit_aliases` (a tuple of strings), and SHALL expose `CITY_GATE_REGISTRY` as a `MappingProxyType` keyed by map id. Today it SHALL carry exactly one row — `capital_altoria` with `gate_xyz` `(2, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`. `world/maps/bootstrap.py` SHALL author city-gate exits exclusively from this registry: no gate exit key, alias, or coordinate SHALL be duplicated as a bootstrap constant (the former `EXIT_TO_CITY` / `EXIT_TO_LIMBO` constants SHALL NOT exist), and no reverse-direction gate data SHALL be authored anywhere.

#### Scenario: The registry pins the single capital row
- **WHEN** `CITY_GATE_REGISTRY` is inspected
- **THEN** it has exactly one key, `capital_altoria`, whose row carries `gate_xyz` `(2, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`

#### Scenario: The registry cannot be mutated at runtime
- **WHEN** a caller attempts to insert, replace, or delete a `CITY_GATE_REGISTRY` entry
- **THEN** the attempt raises and the registry contents are unchanged

#### Scenario: Bootstrap carries no gate surface of its own
- **WHEN** `world/maps/bootstrap.py` is inspected for gate exit authoring
- **THEN** no `EXIT_TO_CITY` or `EXIT_TO_LIMBO` constant exists and the only gate keys, aliases, and coordinates it uses are read from `CITY_GATE_REGISTRY` rows

### Requirement: sync_grid creates exactly one forward gate exit per registry row and converges it idempotently
For every row of `CITY_GATE_REGISTRY`, `sync_grid()` SHALL idempotently ensure exactly one ordinary (non-grid) `Exit` from the starting room to that row's `gate_xyz` exists, carrying the row's `exit_key` and `exit_aliases`, without duplicating it on repeated calls. When the exit already exists with a drifted key or aliases, `sync_grid()` SHALL rewrite them in place to the authored row values on every call, not only at creation. `sync_grid()` SHALL NOT create any exit leading from a gate room back to the starting room.

#### Scenario: One forward exit per row after sync
- **WHEN** `sync_grid()` runs against a database containing a room keyed `LIMBO_KEY` and the spawned `capital_altoria` grid
- **THEN** the starting room has exactly one exit leading to `(2, 0, "capital_altoria")` keyed 「南門」 with aliases 「王都」 and 「城門」, and the South Gate room has no exit leading back to the starting room

#### Scenario: Repeated sync does not duplicate gate exits
- **WHEN** `sync_grid()` is called twice against the same database
- **THEN** the starting room still has exactly one exit per registry row and no duplicate gate exit exists anywhere

#### Scenario: A drifted gate exit converges in place
- **WHEN** `sync_grid()` runs against a database whose 虛境→South Gate exit already exists but carries legacy English aliases (for example `south gate` or `altoria`)
- **THEN** that same exit object is rewritten to the registry row's key and alias set, no duplicate exit is created, and a second call is a no-op

### Requirement: Every sync prunes every exit whose destination is the starting room
On every call, after the forward gate pass, `sync_grid()` SHALL delete every persisted `Exit` object whose destination is the starting room, regardless of the exit's location, key, or aliases, and SHALL log each deletion as the observability event `bootstrap_grid_exit_pruned` with context naming the deleted exit. This is the synchronizer's declarative convergence of its own exit surface: legacy 「離開王都」/「回虛境」 exits and any later reverse object converge away on the next start, without a migration script. On a converged database the prune pass deletes nothing and logs nothing.

#### Scenario: A pre-seeded reverse exit is pruned on the next sync
- **WHEN** a database contains an exit from the South Gate to the starting room (for example the legacy 「離開王都」 with alias 「回虛境」) and `sync_grid()` runs
- **THEN** that exit object no longer exists afterwards, a `bootstrap_grid_exit_pruned` event naming it was logged, and no exit anywhere in the sample city leads to the starting room

#### Scenario: Pruning is idempotent on a converged database
- **WHEN** `sync_grid()` runs twice in a row against a database that was already converged by a prior run
- **THEN** the second run deletes no exit and logs no `bootstrap_grid_exit_pruned` event

### Requirement: A registry row whose gate room is missing warns and is skipped without blocking other rows
When the grid room at a registry row's `gate_xyz` does not exist, `sync_grid()` SHALL log the warning event `bootstrap_grid_gate_missing` with context carrying `map_id`, `xyz`, and `action`, SHALL skip creating that row's forward exit, and SHALL NOT raise. Every other registry row SHALL still be converged, and the rest of `sync_grid()` (grid spawn, the prune pass, wilderness-independent work) SHALL proceed unchanged.

#### Scenario: A missing gate room degrades per row
- **WHEN** `sync_grid()` runs against a database whose `(2, 0, "capital_altoria")` room is absent
- **THEN** a `bootstrap_grid_gate_missing` warning is logged, no gate exit is created for that row, the starting room gains no exit, and `sync_grid()` does not raise

#### Scenario: A bad row does not block a good row
- **WHEN** `sync_grid()` runs with a registry containing one row whose gate room exists and one row whose gate room is missing
- **THEN** the existing row's forward exit is created and the missing row only produces its warning

### Requirement: Adding a city means adding a registry row, with no bootstrap code change
The gate sync SHALL be registry-driven end to end: supporting an additional city SHALL require adding one `CityGateDef` row to `CITY_GATE_REGISTRY` and the city's map data only. `sync_grid()` SHALL converge however many rows the registry carries — the starting room holding exactly one forward exit per row — and the prune invariant SHALL keep all of them one-way. Race-based selection of which gate a new character takes is explicitly out of scope and SHALL NOT be implemented.

#### Scenario: An injected second row gains its own forward exit
- **WHEN** the registry is rebound in a test to carry a second row whose gate room exists and `sync_grid()` runs
- **THEN** the starting room has exactly one forward exit per row, each keyed from its own row, and no exit leads back to the starting room from either gate room

#### Scenario: Registry growth never reintroduces a reverse exit
- **WHEN** a reverse exit into the starting room exists for either gate and `sync_grid()` runs with multiple rows
- **THEN** the reverse exit is pruned and every remaining starting-room exit is a forward gate exit

### Requirement: 虛境 admits no character by any path
The starting room SHALL be converged by `sync_limbo()` onto a dedicated `LimboRoom` typeclass
(`typeclasses/rooms.py`) whose entry hook (`at_pre_object_receive`, the destination-side abort hook
of Evennia's universal `move_to` pipeline) SHALL abort the move of any non-superuser character into
the starting room — whichever path attempts the move, including ordinary exit traversal and
teleport/`moveto`-style `move_to` — leaving the character in its original location and emitting a
zh-tw localized refusal to it. Superuser-controlled characters SHALL be admitted (builder/debug
convention). `sync_limbo()` SHALL converge the room's typeclass in place idempotently: an
already-converged room is not re-swapped, and the room's `LIMBO_KEY` key, `limbo` alias, and
authored description survive the convergence.

#### Scenario: Ordinary exit traversal into 虛境 is refused
- **WHEN** a non-superuser `PlayerCharacter` traverses an exit whose destination is the converged
  starting room (a hand-built reverse exit seeded for the test)
- **THEN** the traversal fails, the character's location is unchanged, and the character receives a
  zh-tw localized refusal message

#### Scenario: A forced move_to into 虛境 is refused for non-admins and allowed for superusers
- **WHEN** a non-superuser character is moved to the converged starting room via a forced
  `move_to`/teleport-style call, and separately when a superuser-controlled character is moved the
  same way
- **THEN** the non-superuser move is aborted with the character left in place and a zh-tw refusal,
  while the superuser arrival succeeds

#### Scenario: Gate convergence is idempotent and preserves the authored identity
- **WHEN** `sync_limbo()` runs twice against the same starting room
- **THEN** the room's typeclass is `LimboRoom` after both runs with the second run re-swapping
  nothing, and the room still carries the `LIMBO_KEY` key, the `limbo` alias, and the authored
  zh-tw description

### Requirement: The first city-gate traversal re-anchors a 虛境 home to the arrival gate room
Because the 虛境 room is the character's creation location (no `DEFAULT_HOME` override exists) and
the capability's own hard gate refuses every later character entry into 虛境, a persisted 虛境
`home` would make the `home` command deliver the player into a room that rejects them. The
shared movement-completion boundary (`after_successful_movement`, `typeclasses/exits.py`) SHALL
re-anchor `character.home` to the destination gate room when — and only when — all of the
following hold after a successful traversal: the traverser is a player character, the destination
room's grid coordinate matches a `CITY_GATE_REGISTRY` row's `gate_xyz`, and the character's
current `home` IS the 虛境 starting room. The write SHALL be performed by the rules-side gate
helper (`world/rules/city_gates.py`), never inline in the typeclass. A traversal whose settlement
failed and was compensated SHALL NOT re-home. Once `home` is no longer the 虛境 room, no later
traversal of any gate SHALL overwrite it.

#### Scenario: The first gate traversal re-homes a 虛境-born character
- **WHEN** a player character whose `home` is the 虛境 starting room successfully traverses the
  「南門」 forward gate exit to `(2, 0, "capital_altoria")`
- **THEN** the character's `home` is the South Gate arrival room, and issuing the `home` command
  afterwards moves the character to that gate room — never to 虛境

#### Scenario: Later traversals never overwrite a non-Limbo home
- **WHEN** a character whose `home` is already a non-虛境 room traverses any registry city gate
  again (or, once the registry grows, a second city's gate)
- **THEN** the character's `home` is unchanged

#### Scenario: A failed traversal does not re-home
- **WHEN** a traversal toward a gate room fails and the movement-settlement boundary compensates
  it (the character is restored to the source room)
- **THEN** the character's `home` still points at the 虛境 starting room
