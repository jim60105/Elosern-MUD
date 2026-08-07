## Purpose

Define the starting room's localized zh-tw identity — where characters first exist — its
idempotent startup convergence, and the zh-tw bridge exit surface to the capital.

## Requirements

### Requirement: The starting room presents a localized zh-tw identity

The starting room where characters first exist SHALL be an Elosern story location authored in
Traditional Chinese: its object key SHALL be the zh-tw name defined by the `LIMBO_KEY` constant in
`world/maps/bootstrap.py` (draft 「虛境」), it SHALL carry `limbo` as an alias so legacy references
still resolve, and its description SHALL be zh-tw prose fitting the world — the threshold where
awakening souls pause before entering 伊洛瑟恩 — and SHALL NOT contain Evennia boilerplate,
English placeholder text, or the upstream welcome message (including any mention of evennia.com or
its tutorial commands).

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

### Requirement: sync_limbo() converges the starting room idempotently at server start

`world/maps/bootstrap.py` SHALL provide a `sync_limbo()` function that runs on every server start,
locates the starting room by key — never by dbref — and rewrites its zh-tw key, `limbo` alias, and
authored description in place on every call. When no room keyed `LIMBO_KEY` exists but a room keyed
the legacy `"Limbo"` exists, the function SHALL rename that room in place to `LIMBO_KEY` before
re-authoring it, so existing developer databases converge without a wipe. When both a canonical
`LIMBO_KEY` room and a legacy `"Limbo"` room exist, the canonical room SHALL be the one synced and
bridged, the legacy room SHALL be left untouched, and a warning SHALL be logged — never a silent
arbitrary pick. When no qualifying room exists at all, the function SHALL log a warning and return
without raising.

#### Scenario: A fresh database gains the localized room

- **WHEN** `sync_limbo()` runs against a database containing only the legacy `"Limbo"` room
- **THEN** that same room object is renamed to `LIMBO_KEY`, keeps its `limbo` alias, and has the
  authored zh-tw description

#### Scenario: Repeated runs are idempotent

- **WHEN** `sync_limbo()` runs twice against the same database
- **THEN** exactly one starting room exists, keyed `LIMBO_KEY`, with the authored description, and
  the second run creates no duplicate room

#### Scenario: A dual-room database converges on the canonical room

- **WHEN** `sync_limbo()` runs against a database that contains both a room keyed `LIMBO_KEY` and a
  separate room keyed the legacy `"Limbo"`
- **THEN** the canonical `LIMBO_KEY` room is re-authored and used for the bridge, the legacy room is
  left in place, and a warning is logged

#### Scenario: A missing room degrades gracefully

- **WHEN** `sync_limbo()` runs against a database with no starting room at all
- **THEN** it does not raise and the rest of startup continues

### Requirement: The bridge to the capital presents zh-tw exit names and aliases, reconciled in place

The directed exit pair bridging the starting room and the capital's South Gate SHALL present
player-facing commands in Traditional Chinese: the exit from the starting room toward the city
SHALL keep key 「南門」 with only zh-tw aliases (no English aliases such as `south gate` or
`altoria`), and the return exit from the South Gate SHALL keep key 「離開王都」 with only zh-tw
aliases (no English aliases such as `leave` or `limbo`). The grid bootstrap SHALL reconcile the
key and aliases of pre-existing bridge exits in place on every sync — not only at creation — so
databases that already contain the bridge with English aliases converge without rebuilding the
exits.

#### Scenario: The exit toward the city carries zh-tw aliases only

- **WHEN** the starting room's exit to the South Gate is inspected after `sync_grid()` runs
- **THEN** its key is 「南門」 and its alias set contains no English word (for example, neither
  `south gate` nor `altoria` appears among the aliases)

#### Scenario: The return exit carries zh-tw aliases only

- **WHEN** the South Gate's exit back to the starting room is inspected after `sync_grid()` runs
- **THEN** its key is 「離開王都」 and its alias set contains no English word (for example, neither
  `leave` nor `limbo` appears among the aliases)

#### Scenario: Pre-existing English aliases are reconciled in place

- **WHEN** `sync_grid()` runs against a database whose bridge exits already exist but carry the
  legacy English aliases (`south gate`, `altoria`, `leave`, `limbo`)
- **THEN** those same exit objects are rewritten to the zh-tw keys and zh-tw alias sets, no
  duplicate exits are created, and a second sync run is a no-op

#### Scenario: Re-sync keeps the aliases zh-tw

- **WHEN** `sync_grid()` runs twice against the same database
- **THEN** the bridge still consists of exactly one exit per direction with the zh-tw keys and
  zh-tw alias sets, and no duplicate or English-alias exit appears
