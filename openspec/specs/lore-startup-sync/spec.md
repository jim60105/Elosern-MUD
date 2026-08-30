## Purpose

Defines the idempotent Evennia startup process that mirrors code-side lore registries into persistent database records.

## Requirements

### Requirement: Every lore registry entry is mirrored into the DB, keyed by key
`world/lore/sync.py` SHALL provide a `sync_all()` function that, for every entry in every lore
registry defined by this change (`RACE_REGISTRY`, `STATIC_TIER_REGISTRY`, `SUBRACE_REGISTRY`,
`ELEMENT_REGISTRY`, `MAGIC_TIER_REGISTRY`, `NATION_REGISTRY`,
`GUILD_RANK_REGISTRY`, `MONSTER_TIER_REGISTRY`, `ANCHOR_REGISTRY`, `PRICE_TABLE`), ensures a
corresponding persistent DB record exists, addressable by a key derived from the registry's
category and the entry's own `key`. The deleted `RANK_TITLE_REGISTRY` SHALL NOT be mirrored,
and the `"rank_titles"` category key SHALL NOT exist in the sync category map.

#### Scenario: Every registry entry produces a DB record
- **WHEN** `sync_all()` runs against a fresh database with no existing lore records
- **THEN** one persistent record exists for every entry across all ten registries, and each
  record's stored fields match the corresponding frozen dataclass instance's fields, with enum
  members represented by their stable string `.value` for Evennia Attribute serialization

#### Scenario: A record's key is derived from category and entry key
- **WHEN** the DB record for, say, `RACE_REGISTRY["elf"]` is inspected after `sync_all()` runs
- **THEN** its key includes both the registry category (`"races"` or equivalent) and the entry's
  own `key` (`"elf"`), so records from different registries never collide even if two registries
  happened to reuse the same entry key

### Requirement: Sync is idempotent across repeated server starts
Running `sync_all()` more than once, including across separate Evennia server starts, SHALL NOT
create duplicate DB records and SHALL leave exactly one record per registry entry.

#### Scenario: Running sync twice creates no duplicates
- **WHEN** `sync_all()` is called, and then called a second time with the registries unchanged
- **THEN** the total number of lore DB records after the second call equals the total after the
  first call

#### Scenario: Repeated sync updates in place rather than erroring
- **WHEN** `sync_all()` is called a second time
- **THEN** it completes without raising, and every record's stored fields still match the current
  Python registry's fields

### Requirement: A code-side change to a registry is reflected on the next sync
Because `world/lore/` Python modules are the single source of truth (design doc D9), the DB
records SHALL be overwritten from the current registry contents on every sync, not treated as an
independent store that could drift from the code.

#### Scenario: Edited registry value propagates on next sync
- **WHEN** a lore registry entry's field value is changed in Python and `sync_all()` is run again
- **THEN** the corresponding DB record's stored value is updated to match the new Python value,
  with no leftover stale record from the previous value

### Requirement: Sync runs automatically at Evennia server start
The idempotent sync SHALL run automatically every time the Evennia server starts, requiring no
manual step by an operator.

#### Scenario: Server start triggers sync without manual intervention
- **WHEN** the Evennia server (Portal + Server) starts up
- **THEN** `sync_all()` has run to completion before the server accepts player connections, with no
  separate command needing to be issued
