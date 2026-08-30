## MODIFIED Requirements

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
