## Purpose

Define the one-way 虛境 threshold: the authored city-gate registry, the
forward-only gate exits synced from it, the pruning of every exit pointing
back into the starting room, and the hard gate that admits no character into
虛境 by any path (including the first-gate-traversal home re-anchor).

## Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
Immutable game gate views SHALL derive solely from settlement-owned starting-room entry relationships with qualified targets and authored labels, without reverse entry declarations.

#### Scenario: Forward gates and immutability
- **WHEN** two synthetic settlement entries are loaded and synchronized twice
- **THEN** each yields one forward exit with its authored labels, the view rejects mutation, and no reverse entry is created

#### Scenario: Concealed path
- **WHEN** an entry targets a settlement without a walled gate
- **THEN** its authored concealed-path naming is preserved without a bootstrap naming constant

#### Scenario: The registry pins the single capital row
- **WHEN** the capital's loaded starting-room relationship is resolved
- **THEN** its current qualified node and authored labels supply the immutable gate view; conversion preserves existing values without a second coordinate/copy approval table

#### Scenario: Every registry row yields exactly one forward exit
- **WHEN** every loaded entry has a materialized target and synchronization runs twice
- **THEN** each entry yields exactly one forward exit and colliding exit keys/aliases reject

#### Scenario: The registry cannot be mutated at runtime
- **WHEN** a consumer attempts to insert, replace or delete a loaded gate-view entry
- **THEN** mutation fails and the view remains unchanged

#### Scenario: Bootstrap carries no gate surface of its own
- **WHEN** a synthetic settlement entry's labels and target change
- **THEN** synchronization follows the loaded values without a competing bootstrap constant

#### Scenario: The registry carries exactly two rows today
- **WHEN** supported settlement files are added or removed
- **THEN** the derived entry set follows source membership rather than a fixed production count; no Python gate roster must be edited

#### Scenario: A row may name a concealed path, not a walled gate
- **WHEN** the loaded entry names a concealed path
- **THEN** that authored label is retained without assuming a walled gate

#### Scenario: Bootstrap duplicates no gate data
- **WHEN** gate views are rebuilt from modified source relationships
- **THEN** bootstrap uses those current labels and qualified targets rather than a duplicated declaration

### Requirement: sync_grid creates exactly one forward gate exit per registry row and converges it idempotently
For every row of `CITY_GATE_REGISTRY`, `sync_grid()` SHALL idempotently ensure exactly one ordinary (non-grid) `Exit` from the starting room to that row's `gate_xyz` exists, carrying the row's `exit_key` and `exit_aliases`, without duplicating it on repeated calls. `sync_grid()` SHALL NOT create any exit leading from a gate room back to the starting room.

#### Scenario: One forward exit per row after sync
- **WHEN** `sync_grid()` runs against a database containing a room keyed `LIMBO_KEY` and the spawned `capital_altoria` grid
- **THEN** the starting room has exactly one exit leading to `(3050, 150, "capital_altoria")` keyed 「南門」 with aliases 「王都」 and 「城門」, and the South Gate room has no exit leading back to the starting room

#### Scenario: Repeated sync does not duplicate gate exits
- **WHEN** `sync_grid()` is called twice against the same database
- **THEN** the starting room still has exactly one exit per registry row and no duplicate gate exit exists anywhere

#### Scenario: A drifted gate exit converges in place
- **WHEN** `sync_grid()` runs against a database whose 虛境→South Gate exit already exists but carries legacy English aliases (for example `south gate` or `altoria`)
- **THEN** that same exit object is rewritten to the registry row's key and alias set, no duplicate exit is created, and a second call is a no-op

#### Scenario: Drift converges on every call, not only at creation
- **WHEN** an existing gate exit carries a drifted key or aliases
- **THEN** `sync_grid()` rewrites them in place to the authored row values on every call, not
  only at creation

### Requirement: Every sync prunes every exit whose destination is the starting room
On every call, after the forward gate pass, `sync_grid()` SHALL delete every persisted `Exit` object whose destination is the starting room, regardless of the exit's location, key, or aliases, and SHALL log each deletion as the observability event `bootstrap_grid_exit_pruned` with context naming the deleted exit.

#### Scenario: A pre-seeded reverse exit is pruned on the next sync
- **WHEN** a database contains an exit from the South Gate to the starting room (for example the legacy 「離開王都」 with alias 「回虛境」) and `sync_grid()` runs
- **THEN** that exit object no longer exists afterwards, a `bootstrap_grid_exit_pruned` event naming it was logged, and no exit anywhere in the sample city leads to the starting room

#### Scenario: Pruning is idempotent on a converged database
- **WHEN** `sync_grid()` runs twice in a row against a database that was already converged by a prior run
- **THEN** the second run deletes no exit and logs no `bootstrap_grid_exit_pruned` event

#### Scenario: Legacy reverse exits converge without a migration script
- **WHEN** the prune pass is read as the synchronizer's declarative convergence of its own
  exit surface
- **THEN** legacy 「離開王都」/「回虛境」 exits and any later reverse object converge away on the
  next start, without a migration script, and on a converged database the prune pass deletes
  nothing and logs nothing

### Requirement: A registry row whose gate room is missing warns and is skipped without blocking other rows
When the grid room at a registry row's `gate_xyz` does not exist, `sync_grid()` SHALL log the warning event `bootstrap_grid_gate_missing` with context carrying `map_id`, `xyz`, and `action`, SHALL skip creating that row's forward exit, and SHALL NOT raise. Every other registry row SHALL still be converged, and the rest of `sync_grid()` (grid spawn, the prune pass, wilderness-independent work) SHALL proceed unchanged.

#### Scenario: A missing gate room degrades per row
- **WHEN** `sync_grid()` runs against a database whose `(3050, 150, "capital_altoria")` room is absent
- **THEN** a `bootstrap_grid_gate_missing` warning is logged, no gate exit is created for that row, the starting room gains no exit, and `sync_grid()` does not raise

#### Scenario: A bad row does not block a good row
- **WHEN** `sync_grid()` runs with a registry containing one row whose gate room exists and one row whose gate room is missing
- **THEN** the existing row's forward exit is created and the missing row only produces its warning

### Requirement: Adding a city means adding a registry row, with no bootstrap code change
Adding a discovered settlement document with a starting-room entry SHALL extend gate synchronization without code registration and retain forward-only entry and reverse pruning.

#### Scenario: Additional source
- **WHEN** a supported settlement document with an entry is added
- **THEN** its forward gate appears after synchronization without Python roster changes and any reverse exit is pruned

#### Scenario: An injected second row gains its own forward exit
- **WHEN** a second synthetic settlement source supplies a distinct valid entry
- **THEN** it gains exactly its own forward exit without bootstrap registration

#### Scenario: Registry growth never reintroduces a reverse exit
- **WHEN** a reverse exit exists while multiple loaded settlement entries synchronize
- **THEN** the reverse exit is pruned and all remaining starting-room entries are forward-only

### Requirement: 虛境 admits no character by any path
The starting room SHALL be converged by `sync_limbo()` onto a dedicated `LimboRoom` typeclass
(`typeclasses/rooms.py`) whose entry hook (`at_pre_object_receive`, Evennia's destination-side
`move_to` abort hook) SHALL abort the move of any non-superuser character into the starting
room — whichever path attempts the move, including ordinary exit traversal and
teleport/`moveto`-style `move_to` — leaving the character in its original location and emitting
a zh-tw localized refusal to it.

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

#### Scenario: Superuser admission is the builder/debug convention
- **WHEN** a superuser-controlled character moves into the starting room
- **THEN** it SHALL be admitted, following the builder/debug convention

### Requirement: The first city-gate traversal re-anchors a 虛境 home to the arrival gate room
The shared movement-completion boundary (`after_successful_movement`, `typeclasses/exits.py`)
SHALL re-anchor `character.home` to the destination gate room when — and only when — all of the
following hold after a successful traversal: the traverser is a player character, the destination
room's grid coordinate matches a `CITY_GATE_REGISTRY` row's `gate_xyz`, and the character's
current `home` IS the 虛境 starting room.

#### Scenario: The first gate traversal re-homes a 虛境-born character
- **WHEN** a player character whose `home` is the 虛境 starting room successfully traverses the
  「南門」 forward gate exit to `(3050, 150, "capital_altoria")`
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

#### Scenario: A persisted 虛境 home would trap the home command
- **WHEN** the re-anchor rule's motivation is examined
- **THEN** it exists because the 虛境 room is the character's creation location (no
  `DEFAULT_HOME` override exists) and the capability's own hard gate refuses every later
  character entry into 虛境, so a persisted 虛境 `home` would make the `home` command deliver
  the player into a room that rejects them

#### Scenario: The home write lives in the rules-side helper
- **WHEN** the re-anchor write is performed
- **THEN** it is performed by the rules-side gate helper (`world/rules/city_gates.py`), never
  inline in the typeclass
