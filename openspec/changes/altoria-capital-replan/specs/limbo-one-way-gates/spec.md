## MODIFIED Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
`world/maps/city_gates.py` SHALL define a frozen, slotted `CityGateDef` dataclass with the fields `map_id` (str), `gate_xyz` (a `(int, int, str)` grid coordinate), `exit_key` (str), and `exit_aliases` (a tuple of strings), and SHALL expose `CITY_GATE_REGISTRY` as a `MappingProxyType` keyed by map id. Today it SHALL carry exactly two rows — `capital_altoria` with `gate_xyz` `(3, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`, and `village_ciaran` with `gate_xyz` at the village's entrance node, `exit_key` 「隱密小徑」, and its own aliases. A row SHALL NOT be assumed to describe a walled settlement: the registry slot expresses "the authored way in from 虛境", and an entry may name a concealed path where the destination has no gate. `world/maps/bootstrap.py` SHALL author gate exits exclusively from this registry: no gate exit key, alias, or coordinate SHALL be duplicated as a bootstrap constant (the former `EXIT_TO_CITY` / `EXIT_TO_LIMBO` constants SHALL NOT exist), and no reverse-direction gate data SHALL be authored anywhere.

#### Scenario: The registry pins the single capital row
- **WHEN** `CITY_GATE_REGISTRY` is inspected
- **THEN** its `capital_altoria` row carries `gate_xyz` `(3, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`

#### Scenario: Every registry row yields exactly one forward exit
- **WHEN** `sync_grid()` runs against a database holding every registered map
- **THEN** the starting room has exactly one forward exit per registry row, each leading to its row's `gate_xyz`, and no two rows' exit keys or aliases collide

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
- **THEN** the starting room has exactly one exit leading to `(3, 0, "capital_altoria")` keyed 「南門」 with aliases 「王都」 and 「城門」, and the South Gate room has no exit leading back to the starting room

#### Scenario: Repeated sync does not duplicate gate exits
- **WHEN** `sync_grid()` is called twice against the same database
- **THEN** the starting room still has exactly one exit per registry row and no duplicate gate exit exists anywhere

#### Scenario: A drifted gate exit converges in place
- **WHEN** `sync_grid()` runs against a database whose 虛境→South Gate exit already exists but carries legacy English aliases (for example `south gate` or `altoria`)
- **THEN** that same exit object is rewritten to the registry row's key and alias set, no duplicate exit is created, and a second call is a no-op

### Requirement: A registry row whose gate room is missing warns and is skipped without blocking other rows
When the grid room at a registry row's `gate_xyz` does not exist, `sync_grid()` SHALL log the warning event `bootstrap_grid_gate_missing` with context carrying `map_id`, `xyz`, and `action`, SHALL skip creating that row's forward exit, and SHALL NOT raise. Every other registry row SHALL still be converged, and the rest of `sync_grid()` (grid spawn, the prune pass, wilderness-independent work) SHALL proceed unchanged.

#### Scenario: A missing gate room degrades per row
- **WHEN** `sync_grid()` runs against a database whose `(3, 0, "capital_altoria")` room is absent
- **THEN** a `bootstrap_grid_gate_missing` warning is logged, no gate exit is created for that row, the starting room gains no exit, and `sync_grid()` does not raise

#### Scenario: A bad row does not block a good row
- **WHEN** `sync_grid()` runs with a registry containing one row whose gate room exists and one row whose gate room is missing
- **THEN** the existing row's forward exit is created and the missing row only produces its warning

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
  「南門」 forward gate exit to `(3, 0, "capital_altoria")`
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
