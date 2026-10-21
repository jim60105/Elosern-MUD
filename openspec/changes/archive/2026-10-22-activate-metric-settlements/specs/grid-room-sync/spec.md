# Spec Delta

## MODIFIED Requirements

### Requirement: sync_grid() runs automatically at server start, after sync_all()
`server/conf/at_server_startstop.py::at_server_start()` SHALL call `sync_grid()` immediately after
`sync_all()`, requiring no manual operator action (no `evennia xyzgrid` CLI invocation) for the sample
city to exist after a fresh container boot.

#### Scenario: A fresh server start produces a fully spawned sample city
- **WHEN** the Evennia server starts against a fresh, migrated, empty database (as
  `docker-entrypoint.sh`'s `evennia migrate --noinput` followed by `evennia start --log` would
  produce)
- **THEN** the `capital_altoria` sample city's twenty-one rooms and fifty-two intra-city exits exist
  before the server accepts player connections, with no separate command having been issued

#### Scenario: at_server_start calls sync_grid after sync_all, not before
- **WHEN** `server/conf/at_server_startstop.py::at_server_start()` is inspected
- **THEN** the call to `sync_grid()` appears after the call to `sync_all()` in source order

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
`sync_grid()` SHALL locate the starting room through the shared `LIMBO_KEY` constant
(`world/maps/bootstrap.py`) — never by dbref, never by a `"Limbo"` literal. When the room
is found, it SHALL author bridging exits exclusively from `CITY_GATE_REGISTRY`
(`world/maps/city_gates.py`): for every registry row, exactly one ordinary (non-grid)
`Exit` from the starting room to that row's gate coordinate, ensured idempotently —
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
- **THEN** the sample city's twenty-one rooms and fifty-two intra-city exits are still spawned, no
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
- **THEN** `sync_grid()` deletes every persisted `Exit` whose destination is the starting room —
  the `limbo-one-way-gates` capability's prune invariant — so a reverse exit seeded into the
  database converges away on the next sync

#### Scenario: A missing Limbo logs a warning before skipping
- **WHEN** `sync_grid()` runs and no room keyed `LIMBO_KEY` is found
- **THEN** it logs a warning, skips creating the bridging exits, and does not raise
