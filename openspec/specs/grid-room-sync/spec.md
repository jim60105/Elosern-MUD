## Purpose

Define the idempotent grid bootstrap that instantiates real, walkable xyzgrid rooms and exits at
server start, distinct from the `LoreRecord` data-mirror `sync_all()`, plus the Limbo-bridging exit
pair and the `evennia xyzgrid` CLI registration.

## Requirements

### Requirement: sync_grid() is distinct from sync_all() and instantiates real rooms and exits
`world/maps/bootstrap.py` SHALL provide a `sync_grid()` function, distinct in name and module from
`world/lore/sync.py::sync_all()`. `sync_grid()` SHALL synchronize every declared sparse node and
explicit road into corresponding `XYZRoom`/`XYZExit` objects, without dense ASCII parsing.
`sync_all()` SHALL NOT be renamed, merged with, or repurposed to perform this work.

#### Scenario: sync_grid produces real, puppetable-adjacent room objects
- **WHEN** `sync_grid()` runs against an empty database
- **THEN** one `GridRoom`/`AnchorRoom` instance per declared node and one costed `XYZExit`
  instance per declared directed road exist for `capital_altoria`, each queryable
  via ordinary Evennia object search rather than as a `LoreRecord` Script

#### Scenario: sync_all's own behavior is unaffected
- **WHEN** `sync_all()` runs
- **THEN** it creates or updates only `LoreRecord` Script objects, exactly as before this change; it
  creates no `GridRoom`, `AnchorRoom`, or `XYZExit`

### Requirement: sync_grid() is idempotent across repeated calls and server starts
Repeated grid synchronization SHALL reuse stable declared rooms/exits and converge to the loaded settlement topology without duplicate objects.

#### Scenario: Running sync_grid twice creates no duplicate rooms
- **WHEN** `sync_grid()` is called, and then called a second time with no map data changed
- **THEN** the total count of `GridRoom`/`AnchorRoom` instances after the second call equals the
  count after the first call, and the total count of `XYZExit` instances is likewise unchanged

#### Scenario: A room's Attributes are updated in place, not duplicated, when its prototype changes
- **WHEN** `content/maps/settlements/capital_altoria.yaml`'s prototype for one coordinate changes (for example, its
  `desc`) and `sync_grid()` is called again
- **THEN** the existing room at that coordinate is updated to the new `desc`, and no second room is
  created at the same coordinate

### Requirement: sync_grid() runs automatically at server start, after sync_all()
`server/conf/at_server_startstop.py::at_server_start()` SHALL call `sync_grid()` immediately after
`sync_all()`, requiring no manual operator action (no `evennia xyzgrid` CLI invocation) for the sample
city to exist after a fresh container boot.

#### Scenario: A fresh server start produces a fully spawned sample city
- **WHEN** the Evennia server starts against a fresh, migrated, empty database (as
  `docker-entrypoint.sh`'s `evennia migrate --noinput` followed by `evennia start --log` would
  produce)
- **THEN** the `capital_altoria` sample city's declared rooms and intra-city exits exist
  before the server accepts player connections, with no separate command having been issued

#### Scenario: at_server_start calls sync_grid after sync_all, not before
- **WHEN** `server/conf/at_server_startstop.py::at_server_start()` is inspected
- **THEN** the call to `sync_grid()` appears after the call to `sync_all()` in source order

### Requirement: The evennia xyzgrid CLI remains available but is not required for boot
`server/conf/settings.py` SHALL register `EXTRA_LAUNCHER_COMMANDS["xyzgrid"]` so `evennia xyzgrid
<option>` remains usable for manual operator inspection and rebuilding, but no container startup path
(`docker-entrypoint.sh`) SHALL depend on it being invoked.

#### Scenario: The CLI subcommand is registered
- **WHEN** `evennia xyzgrid list` is run against a server that has completed at least one start
- **THEN** the registered contrib command remains available for builder maps;
  authored sparse settlements are synchronized independently and are not
  required to appear in `XYZGrid.db.map_data` or its CLI listing

#### Scenario: docker-entrypoint.sh contains no xyzgrid CLI invocation
- **WHEN** `docker-entrypoint.sh` is inspected
- **THEN** it contains no `evennia xyzgrid` invocation of any kind; grid provisioning happens
  entirely inside the `evennia start` process via `at_server_start()`

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
`sync_grid()` SHALL locate the starting room through the shared `LIMBO_KEY` constant
(`world/maps/bootstrap.py`), never by dbref or a `"Limbo"` literal. When the room
is found, it SHALL author bridging exits exclusively from `CITY_GATE_REGISTRY`
(`world/maps/city_gates.py`): for every registry row, exactly one ordinary (non-grid)
`Exit` from the starting room to that row's gate coordinate, created idempotently,
never an exit back to the starting room, never duplicated on repeated calls.

#### Scenario: The bridging exit exists after sync_grid runs
- **WHEN** `sync_grid()` runs against a database containing a room keyed `LIMBO_KEY`
- **THEN** that room has exactly one exit leading to `(3050, 150, "capital_altoria")`, and the South Gate
  room has no exit leading back to it

#### Scenario: Repeated calls do not duplicate the bridging exit
- **WHEN** `sync_grid()` is called twice against a database containing a room keyed `LIMBO_KEY`
- **THEN** that room still has exactly one exit toward the sample city and no exit anywhere leads
  back to it

#### Scenario: The lookup is by key, not by dbref
- **WHEN** a database's dbref `#2` is occupied by an object not keyed `LIMBO_KEY` (as is the case in
  this project's own `EvenniaTest`-based fixtures, where `#2` is a generic test room) and a separate
  object elsewhere in the database is keyed `LIMBO_KEY`
- **THEN** `sync_grid()` attaches the bridging exit to the object keyed `LIMBO_KEY`, not to dbref `#2`

#### Scenario: A missing Limbo degrades gracefully, without preventing the rest of sync_grid from running
- **WHEN** `sync_grid()` runs against a database with no object keyed `LIMBO_KEY`
- **THEN** the sample city's declared rooms and intra-city exits are still spawned, no
  bridging exit is created, and `sync_grid()` does not raise

#### Scenario: The bridge exit carries zh-tw key and aliases from the registry
- **WHEN** the bridging exit is inspected after `sync_grid()` runs
- **THEN** the exit from the starting room toward the city is keyed 「南門」 with the registry row's
  zh-tw aliases, and it lists no English alias

#### Scenario: Pre-existing English bridge aliases are reconciled in place
- **WHEN** `sync_grid()` runs against a database whose bridge exit already exists but carries the
  legacy English aliases (`south gate`, `altoria`)
- **THEN** that same exit object is rewritten to the registry row's zh-tw key and alias set, no
  duplicate exit is created, and a second call is a no-op

#### Scenario: A pre-seeded reverse bridge exit is pruned on the next sync
- **WHEN** `sync_grid()` runs against a database containing a legacy exit from the South Gate back to
  the starting room (keyed 「離開王都」 with alias 「回虛境」)
- **THEN** that exit object no longer exists after the run, the forward 「南門」 exit is converged as
  authored, and a second `sync_grid()` call deletes nothing further and logs no prune event

#### Scenario: Bridge exits converge to the registry on every call
- **WHEN** `sync_grid()` runs and a bridge exit toward the sample city already exists
- **THEN** its key and aliases are reconciled in place to the authored registry values on every
  call, not only at creation

#### Scenario: The forward pass ends with the prune invariant
- **WHEN** the forward bridging pass of `sync_grid()` finishes
- **THEN** `sync_grid()` deletes every persisted `Exit` whose destination is the starting room,
  following the `limbo-one-way-gates` capability's prune invariant, so a reverse exit seeded into the
  database converges away on the next sync

#### Scenario: A missing Limbo logs a warning before skipping
- **WHEN** `sync_grid()` runs and no room keyed `LIMBO_KEY` is found
- **THEN** it logs a warning, skips creating the bridging exits, and does not raise

### Requirement: Authored room prose is Traditional Chinese
Every authored room description the game ships SHALL be Traditional Chinese prose, including both the
`desc` of a grid prototype and the interior description a place record carries. A room's name
and its description SHALL be in the same language: a Chinese room name over an English body is
the specific defect this rule exists to prevent. Authoring notes, specification identifiers and change names SHALL NOT appear
in a description; they are player-facing text. A guard SHALL check the corpus.

#### Scenario: Every shipped room description is Traditional Chinese
- **WHEN** every authored grid prototype description and every place's interior description is
  inspected
- **THEN** each is predominantly Han prose with no sentence-length run of English words

#### Scenario: An English description is rejected
- **WHEN** the guard runs against a synthetic room whose description is an English sentence
- **THEN** it fails, naming the room

#### Scenario: No description carries an authoring note
- **WHEN** the shipped descriptions are searched for specification identifiers and change names
- **THEN** none is found

#### Scenario: The name-language mismatch is the nobody-checking defect
- **WHEN** an authored room pairs a Chinese room name with an English body
- **THEN** it violates the same-language rule; this mismatch is the state the codebase reached
  by nobody checking

#### Scenario: The guard stops English descriptions from accumulating
- **WHEN** a new English description is added to the shipped corpus
- **THEN** the guard fails it over the whole corpus, so the defect fails rather than accumulating

### Requirement: Sparse authored graphs synchronize without identity loss
Settlement graph synchronization SHALL support sparse integer-coordinate nodes and explicit roads
with stable authored identity. Coordinate replacement SHALL converge in place before missing-node
deletion, preserving rooms, occupants and references; conflicting bindings SHALL fail before
mutation.

#### Scenario: Identity replacement and repeat startup
- **WHEN** an occupied synthetic node changes from (1,1) to (5000,200) and synchronization runs
  twice
- **THEN** room dbid, occupant location, homes, inbound references and authored exit identities
  persist; the second run changes nothing and creates no duplicates.

#### Scenario: Sparse route costs
- **WHEN** nodes span millions of coordinate units with only three roads
- **THEN** pathfinding uses those roads with unequal physical lengths and allocates proportional to
  graph size, never a meter lattice.

#### Scenario: Collision rejection
- **WHEN** two authored identities bind the same destination or an old room binds ambiguously
- **THEN** validation refuses before any room, tag, reference or cached coordinate changes.
