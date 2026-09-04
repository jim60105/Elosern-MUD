# Delta: limbo-room

## MODIFIED Requirements

### Requirement: sync_limbo() converges the starting room idempotently at server start

`world/maps/bootstrap.py` SHALL provide a `sync_limbo()` function that runs on every server start,
locates the starting room by key — never by dbref — and rewrites its zh-tw key, `limbo` alias, and
authored description in place on every call. It SHALL also converge the room's typeclass in place
onto the hard-gate `LimboRoom` typeclass (`typeclasses/rooms.py`, the one-way entry gate described
by the `limbo-one-way-gates` capability): a room not yet carrying `LimboRoom` is swapped in place
without clearing its attributes, and an already-converged room is left as-is, so the convergence is
idempotent and never a migration step. When no room keyed `LIMBO_KEY` exists but a room keyed
the legacy `"Limbo"` exists, the function SHALL rename that room in place to `LIMBO_KEY` before
re-authoring it, so existing developer databases converge without a wipe. When both a canonical
`LIMBO_KEY` room and a legacy `"Limbo"` room exist, the canonical room SHALL be the one synced and
bridged, the legacy room SHALL be left untouched, and a warning SHALL be logged — never a silent
arbitrary pick. When no qualifying room exists at all, the function SHALL log a warning and return
without raising.

#### Scenario: A fresh database gains the localized room

- **WHEN** `sync_limbo()` runs against a database containing only the legacy `"Limbo"` room
- **THEN** that same room object is renamed to `LIMBO_KEY`, keeps its `limbo` alias, has the
  authored zh-tw description, and is typed as `LimboRoom`

#### Scenario: Repeated runs are idempotent

- **WHEN** `sync_limbo()` runs twice against the same database
- **THEN** exactly one starting room exists, keyed `LIMBO_KEY`, with the authored description, the
  second run creates no duplicate room, and the second run performs no further typeclass swap on an
  already-`LimboRoom` room

#### Scenario: A dual-room database converges on the canonical room

- **WHEN** `sync_limbo()` runs against a database that contains both a room keyed `LIMBO_KEY` and a
  separate room keyed the legacy `"Limbo"`
- **THEN** the canonical `LIMBO_KEY` room is re-authored, converged onto `LimboRoom`, and used for
  the bridge, the legacy room is left in place, and a warning is logged

#### Scenario: A missing room degrades gracefully

- **WHEN** `sync_limbo()` runs against a database with no starting room at all
- **THEN** it does not raise and the rest of startup continues

### Requirement: The bridge to the capital presents zh-tw exit names and aliases, reconciled in place
The directed exit bridging the starting room and the capital's South Gate SHALL present
player-facing commands in Traditional Chinese: the forward exit from the starting room toward the
city SHALL keep key 「南門」 with only zh-tw aliases (no English aliases such as `south gate` or
`altoria`), taken from its `CITY_GATE_REGISTRY` row. The bridge is one-way: no return exit from the
South Gate back to the starting room SHALL be authored, and any pre-existing reverse exit (such as
the legacy 「離開王都」 with alias 「回虛境」) SHALL be pruned by `sync_grid()` on every run (see the
`limbo-one-way-gates` capability). The grid bootstrap SHALL reconcile the key and aliases of
pre-existing forward bridge exits in place on every sync — not only at creation — so databases
that already contain the bridge with English aliases converge without rebuilding the exits.

#### Scenario: The exit toward the city carries zh-tw aliases only
- **WHEN** the starting room's exit to the South Gate is inspected after `sync_grid()` runs
- **THEN** its key is 「南門」 and its alias set contains no English word (for example, neither
  `south gate` nor `altoria` appears among the aliases)

#### Scenario: No return exit survives a sync
- **WHEN** the South Gate's exits are inspected after `sync_grid()` runs on a database that
  previously held the legacy 「離開王都」 return exit
- **THEN** no exit from the South Gate (or any other room) leads back to the starting room

#### Scenario: Pre-existing English aliases are reconciled in place
- **WHEN** `sync_grid()` runs against a database whose forward bridge exit already exists but carries
  the legacy English aliases (`south gate`, `altoria`)
- **THEN** that same exit object is rewritten to the zh-tw key and zh-tw alias set, no duplicate
  exit is created, and a second sync run is a no-op

#### Scenario: Re-sync keeps the bridge zh-tw and one-way
- **WHEN** `sync_grid()` runs twice against the same database
- **THEN** the bridge still consists of exactly one forward exit with the zh-tw key and zh-tw alias
  set, no duplicate or English-alias exit appears, and no exit leads back to the starting room
