## MODIFIED Requirements

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
`sync_grid()` SHALL locate the starting room through the shared `LIMBO_KEY` constant
(`world/maps/bootstrap.py`), which holds the room's zh-tw key — never by dbref and never by a
hard-coded `"Limbo"` literal. When the room is found, `sync_grid()` SHALL idempotently ensure
exactly one ordinary (non-grid) `Exit` from the starting room to the sample city's South Gate
coordinate exists, and exactly one return `Exit` from the South Gate back to the starting room,
without duplicating either on repeated calls. The bridging exit pair SHALL use the zh-tw keys
「南門」 (toward the city) and 「離開王都」 (back to the starting room) and SHALL carry no English
aliases; when a bridge exit already exists with legacy English aliases, `sync_grid()` SHALL
reconcile its key and aliases in place to the authored zh-tw values on every call, not only at
creation. When no room keyed `LIMBO_KEY` exists, `sync_grid()` SHALL log a warning and skip
creating the bridging exit pair, and SHALL NOT raise.

#### Scenario: The bridging exit exists after sync_grid runs
- **WHEN** `sync_grid()` runs against a database containing a room keyed `LIMBO_KEY`
- **THEN** that room has exactly one exit leading to `(2, 0, "capital_altoria")`, and the South Gate
  room has exactly one exit leading back to it

#### Scenario: Repeated calls do not duplicate the bridging exits
- **WHEN** `sync_grid()` is called twice against a database containing a room keyed `LIMBO_KEY`
- **THEN** that room still has exactly one exit toward the sample city, and the South Gate room still
  has exactly one exit back to it

#### Scenario: The lookup is by key, not by dbref
- **WHEN** a database's dbref `#2` is occupied by an object not keyed `LIMBO_KEY` (as is the case in
  this project's own `EvenniaTest`-based fixtures, where `#2` is a generic test room) and a separate
  object elsewhere in the database is keyed `LIMBO_KEY`
- **THEN** `sync_grid()` attaches the bridging exits to the object keyed `LIMBO_KEY`, not to dbref `#2`

#### Scenario: A missing Limbo degrades gracefully, without preventing the rest of sync_grid from running
- **WHEN** `sync_grid()` runs against a database with no object keyed `LIMBO_KEY`
- **THEN** the sample city's thirteen rooms and twenty-four intra-city exits are still spawned, no
  bridging exit is created, and `sync_grid()` does not raise

#### Scenario: The bridge exits carry zh-tw keys and no English aliases
- **WHEN** the bridging exit pair is inspected after `sync_grid()` runs
- **THEN** the exit from the starting room toward the city is keyed 「南門」, the return exit is keyed
  「離開王都」, and neither exit lists any English alias

#### Scenario: Pre-existing English bridge aliases are reconciled in place
- **WHEN** `sync_grid()` runs against a database whose bridging exits already exist but carry the
  legacy English aliases (`south gate`, `altoria`, `leave`, `limbo`)
- **THEN** those same exit objects are rewritten to the zh-tw keys and alias sets, no duplicate
  exits are created, and a second call is a no-op
