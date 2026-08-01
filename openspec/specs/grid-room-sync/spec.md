## Purpose

Define the idempotent grid bootstrap that instantiates real, walkable xyzgrid rooms and exits at
server start, distinct from the `LoreRecord` data-mirror `sync_all()`, plus the Limbo-bridging exit
pair and the `evennia xyzgrid` CLI registration.

## Requirements


### Requirement: sync_grid() is distinct from sync_all() and instantiates real rooms and exits
`world/maps/bootstrap.py` SHALL provide a `sync_grid()` function, distinct in name and module from
`world/lore/sync.py::sync_all()`. `sync_grid()` SHALL register every declared `XYMAP_DATA` with the
`XYZGrid` singleton and cause the corresponding `XYZRoom`/`XYZExit` objects to exist in the database.
`sync_all()` SHALL NOT be renamed, merged with, or repurposed to perform this work.

#### Scenario: sync_grid produces real, puppetable-adjacent room objects
- **WHEN** `sync_grid()` runs against an empty database
- **THEN** thirteen `GridRoom`/`AnchorRoom` instances and twenty-four `XYZExit` instances exist in
  the database for the `capital_altoria` map, each queryable via ordinary Evennia object search —
  not `LoreRecord` Scripts. The twenty-four directed exits reflect the twelve map links spawning
  one exit per travel direction.

#### Scenario: sync_all's own behavior is unaffected
- **WHEN** `sync_all()` runs
- **THEN** it creates or updates only `LoreRecord` Script objects, exactly as before this change; it
  creates no `GridRoom`, `AnchorRoom`, or `XYZExit`

### Requirement: sync_grid() is idempotent across repeated calls and server starts
Running `sync_grid()` more than once, including across separate Evennia server starts, SHALL NOT
create duplicate rooms or exits at any coordinate, and SHALL leave exactly the declared topology in
place.

#### Scenario: Running sync_grid twice creates no duplicate rooms
- **WHEN** `sync_grid()` is called, and then called a second time with no map data changed
- **THEN** the total count of `GridRoom`/`AnchorRoom` instances after the second call equals the
  count after the first call, and the total count of `XYZExit` instances is likewise unchanged

#### Scenario: A room's Attributes are updated in place, not duplicated, when its prototype changes
- **WHEN** `world/maps/altoria_capital.py`'s prototype for one coordinate changes (for example, its
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
- **THEN** the `capital_altoria` sample city's thirteen rooms and twenty-four intra-city exits exist
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
- **THEN** it lists the `capital_altoria` map without error, having been populated by `at_server_
  start()`'s automatic `sync_grid()` call, not by the CLI itself

#### Scenario: docker-entrypoint.sh contains no xyzgrid CLI invocation
- **WHEN** `docker-entrypoint.sh` is inspected
- **THEN** it contains no `evennia xyzgrid` invocation of any kind — grid provisioning happens
  entirely inside the `evennia start` process via `at_server_start()`

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
`sync_grid()` SHALL locate Limbo by object `key="Limbo"` — never by dbref — and, when found, SHALL
idempotently ensure exactly one ordinary (non-grid) `Exit` from Limbo to the sample city's South Gate
coordinate exists, and exactly one return `Exit` from the South Gate back to Limbo, without
duplicating either on repeated calls. When no object keyed `"Limbo"` exists, `sync_grid()` SHALL log a
warning and skip creating the bridging exit pair, and SHALL NOT raise.

#### Scenario: The bridging exit exists after sync_grid runs
- **WHEN** `sync_grid()` runs against a database containing a room keyed `"Limbo"`
- **THEN** that room has exactly one exit leading to `(2, 0, "capital_altoria")`, and the South Gate
  room has exactly one exit leading back to it

#### Scenario: Repeated calls do not duplicate the bridging exits
- **WHEN** `sync_grid()` is called twice against a database containing a room keyed `"Limbo"`
- **THEN** that room still has exactly one exit toward the sample city, and the South Gate room still
  has exactly one exit back to it

#### Scenario: The lookup is by key, not by dbref
- **WHEN** a database's dbref `#2` is occupied by an object not keyed `"Limbo"` (as is the case in
  this project's own `EvenniaTest`-based fixtures, where `#2` is a generic test room) and a separate
  object elsewhere in the database is keyed `"Limbo"`
- **THEN** `sync_grid()` attaches the bridging exits to the object keyed `"Limbo"`, not to dbref `#2`

#### Scenario: A missing Limbo degrades gracefully, without preventing the rest of sync_grid from running
- **WHEN** `sync_grid()` runs against a database with no object keyed `"Limbo"`
- **THEN** the sample city's thirteen rooms and twenty-four intra-city exits are still spawned, no
  bridging exit is created, and `sync_grid()` does not raise
