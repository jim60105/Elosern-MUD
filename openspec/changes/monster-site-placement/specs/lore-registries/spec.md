## ADDED Requirements

### Requirement: Placement registries follow the frozen keyed lore-data contract
`world/lore/monster_placement.py` SHALL hold the ambient-placement and monster-site registries as
module-level keyed dicts of frozen dataclasses — the source of truth that consumers read instead of
duplicating constants — validated at construction (import) time with a named error, mirrored into the
runtime store idempotently by the existing `world/lore/sync.py` startup discipline, and never mutated at
runtime by `world/lore/`. The registries SHALL expose no spawn, place, reconcile, or recovery callable:
placement execution belongs to `world/maps/`, which reads these registries.

#### Scenario: Consumers read the registry rather than a copy
- **WHEN** the site owner needs a site's capacity or recovery condition
- **THEN** it reads the registry record, and no second constant or table of those values exists in `world/maps/`

#### Scenario: Startup mirror is idempotent and read-only upward
- **WHEN** the placement mirror step runs twice at startup
- **THEN** the mirrored state is unchanged after the second run, and no monster, room, or quest record is created or modified by the mirror

#### Scenario: The lore module cannot place anything
- **WHEN** the placement module's public surface is inspected
- **THEN** it offers read and validation operations only, with no spawn/reconcile/recovery entry point
