# Delta: grid-room-sync

## MODIFIED Requirements

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
`sync_grid()` SHALL locate the starting room through the shared `LIMBO_KEY` constant
(`world/maps/bootstrap.py`), which holds the room's zh-tw key — never by dbref and never by a
hard-coded `"Limbo"` literal. When the room is found, `sync_grid()` SHALL author bridging exits
exclusively from `CITY_GATE_REGISTRY` (`world/maps/city_gates.py`): for every registry row it SHALL
idempotently ensure exactly one ordinary (non-grid) `Exit` from the starting room to that row's
gate coordinate exists — never any exit leading back to the starting room — without duplicating it
on repeated calls. The exit toward the sample city SHALL use the row's zh-tw key 「南門」 with the
row's zh-tw aliases and SHALL carry no English aliases; when a bridge exit already exists with
legacy English aliases, `sync_grid()` SHALL reconcile its key and aliases in place to the authored
registry values on every call, not only at creation. After the forward pass, `sync_grid()` SHALL
delete every persisted `Exit` whose destination is the starting room (the `limbo-one-way-gates`
capability's prune invariant), so a reverse exit seeded into the database converges away on the
next sync. When no room keyed `LIMBO_KEY` exists, `sync_grid()` SHALL log a warning and skip
creating the bridging exits, and SHALL NOT raise.

#### Scenario: The bridging exit exists after sync_grid runs
- **WHEN** `sync_grid()` runs against a database containing a room keyed `LIMBO_KEY`
- **THEN** that room has exactly one exit leading to `(2, 0, "capital_altoria")`, and the South Gate
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
- **THEN** the sample city's thirteen rooms and twenty-four intra-city exits are still spawned, no
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
