## Purpose

Define the starting room's localized zh-tw identity — where characters first exist — and its
idempotent startup convergence.

## Requirements

### Requirement: The starting room presents a localized zh-tw identity

The starting room where characters first exist SHALL be an Elosern story location authored in
Traditional Chinese: its object key SHALL be the zh-tw name defined by the `LIMBO_KEY` constant in
`world/maps/bootstrap.py` (draft 「虛境」), it SHALL carry `limbo` as an alias so legacy references
still resolve, and its description SHALL be zh-tw prose fitting the world — the threshold where
awakening souls pause before entering 伊洛瑟恩.

#### Scenario: The room shows the zh-tw name and description

- **WHEN** a player looks at the starting room after a server start that ran the startup syncs
- **THEN** the room's displayed name is the zh-tw `LIMBO_KEY` value, its description is the authored
  zh-tw prose, and no upstream Evennia welcome text appears anywhere in the room's presentation

#### Scenario: The legacy English name is gone

- **WHEN** the database is searched for an object keyed exactly `"Limbo"`
- **THEN** no object is found (the room is keyed by `LIMBO_KEY` instead)

#### Scenario: The room resolves under its legacy alias

- **WHEN** the starting room is searched by its `limbo` alias
- **THEN** the same room object is found

#### Scenario: No boilerplate or upstream welcome text

- **WHEN** the authored description is inspected
- **THEN** it SHALL NOT contain Evennia boilerplate, English placeholder text, or the upstream
  welcome message (including any mention of evennia.com or its tutorial commands)

### Requirement: sync_limbo() converges the starting room idempotently at server start

`world/maps/bootstrap.py` SHALL provide a `sync_limbo()` function that runs on every server start,
locates the starting room by key — never by dbref — and rewrites its zh-tw key, `limbo` alias, and
authored description in place on every call. It SHALL also converge the room's typeclass in place
onto the hard-gate `LimboRoom` typeclass (`typeclasses/rooms.py`, the one-way entry gate described
by the `limbo-one-way-gates` capability), so the convergence is idempotent and never a migration
step.

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
- **THEN** the canonical `LIMBO_KEY` room is re-authored and converged onto `LimboRoom`, the legacy room is left in place, and a warning is logged

#### Scenario: A missing room degrades gracefully

- **WHEN** `sync_limbo()` runs against a database with no starting room at all
- **THEN** it does not raise and the rest of startup continues

#### Scenario: The typeclass swap is in place and attribute-preserving

- **WHEN** `sync_limbo()` converges a room's typeclass
- **THEN** a room not yet carrying `LimboRoom` is swapped in place without clearing its attributes,
  and an already-converged room is left as-is

#### Scenario: A legacy-only database renames in place

- **WHEN** no room keyed `LIMBO_KEY` exists but a room keyed the legacy `"Limbo"` exists
- **THEN** the function SHALL rename that room in place to `LIMBO_KEY` before re-authoring it, so
  existing developer databases converge without a wipe

#### Scenario: The canonical pick is never silent or arbitrary

- **WHEN** both a canonical `LIMBO_KEY` room and a legacy `"Limbo"` room exist
- **THEN** the canonical room SHALL be the one synced, the legacy room SHALL be left
  untouched, and a warning SHALL be logged — never a silent arbitrary pick

#### Scenario: A missing qualifying room warns and returns

- **WHEN** no qualifying room exists at all
- **THEN** the function SHALL log a warning and return without raising
