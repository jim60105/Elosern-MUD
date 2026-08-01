# quest-blueprint Specification

## Purpose
The deterministic runtime's quest definition vocabulary — immutable, validated, registry-backed content
that change 20's AI `QuestBlueprint` must translate into. Hand-written offline quests consume this type
directly; no AI proposal dict ever enters the runtime registry.

## Requirements
### Requirement: QuestDefinition is the immutable deterministic input to quest runtime
`world/quests/definitions.py` SHALL define frozen, deeply immutable `QuestDefinition`, `QuestStage`,
`QuestObjective`, and `RoomLocator` dataclasses. `QuestDefinition.stages` SHALL be a tuple of
`QuestStage` values carrying explicit integer indices. No runtime definition field SHALL contain a
mutable dict or list. `QuestDefinition` SHALL be distinct from the future AI `QuestBlueprint` proposal
owned by change 20; raw mappings SHALL NOT be accepted by the runtime registry.

#### Scenario: Explicit stage indices are representable and preserved
- **WHEN** a definition is constructed with stages carrying indices 0 and 2
- **THEN** both explicit indices remain inspectable so registration can reject the gap

#### Scenario: Definition content cannot be mutated after validation
- **WHEN** a registered definition's stages, objective, or destination is accessed
- **THEN** no nested mutable collection is available through which validated content can be changed

#### Scenario: Raw AI-shaped data is not runtime input
- **WHEN** a plain dict shaped like design document §7.1's AI proposal is passed to
  `register_quest_definition()`
- **THEN** registration rejects it without modifying `QUEST_DEFINITION_REGISTRY`

### Requirement: Quest classifications and objective mechanics are separate closed vocabularies
`QuestType` SHALL contain exactly 採集, 討伐, 護衛, 探索, and 緊急. `ObjectiveKind` SHALL contain exactly
`DEFEAT`, `REACH`, and `ESCORT`. A quest type SHALL classify the complete definition and SHALL NOT
restrict which objective kinds its stages may use. ACQUIRE SHALL remain absent until change 16 can add it
at the inventory-owning transaction boundary.

#### Scenario: An emergency quest uses an ordinary completion mechanic
- **WHEN** a `QuestType.EMERGENCY` definition contains a `ObjectiveKind.DEFEAT` stage
- **THEN** it registers and resolves by the same DEFEAT rules as any other quest type

### Requirement: Destinations distinguish permanent locations from future bound instances
`DestinationKind` SHALL contain `ANCHOR`, `GRID`, and `BOUND_INSTANCE`. An ANCHOR locator SHALL carry
exactly one `anchor_key` present in `ANCHOR_PLACEMENT_REGISTRY`; a lore-known anchor without a placement
SHALL be rejected because it has no reachable room. A GRID locator SHALL carry exactly one `(x, y, z)`
tuple whose map key is known to the xyzgrid; a BOUND_INSTANCE locator SHALL carry neither and SHALL
resolve only through the accepted record's `stage_room_id`. Wilderness coordinates SHALL NOT be
representable by this change.

#### Scenario: An anchor destination is structurally valid
- **WHEN** a REACH objective names a key present in `ANCHOR_PLACEMENT_REGISTRY` through an ANCHOR locator
- **THEN** its definition registers without requiring a room dbref at module-import time

#### Scenario: Lore-known but unplaced anchor is rejected
- **WHEN** an ANCHOR locator names a lore anchor absent from `ANCHOR_PLACEMENT_REGISTRY`
- **THEN** registration raises `QuestDefinitionError` because no reachable `AnchorRoom` exists

#### Scenario: A malformed locator is rejected
- **WHEN** an ANCHOR locator also supplies XYZ coordinates, or a BOUND_INSTANCE locator supplies either
  static location field
- **THEN** registration raises `QuestDefinitionError` before mutating the registry

#### Scenario: Wilderness destination cannot be declared
- **WHEN** content attempts to declare a wilderness-coordinate destination
- **THEN** no `DestinationKind` value can represent it in this change

### Requirement: Registration validates every runtime-critical objective field
`register_quest_definition()` SHALL treat re-registering equal content under the same key as an
idempotent no-op and SHALL reject conflicting content under an existing key. It SHALL reject empty
stages, non-contiguous stage indices starting anywhere other than zero, non-positive quantities,
invalid destination shapes, unknown static location keys, and invalid objective parameters. DEFEAT
SHALL declare exactly one of a known `monster_tier` or `requires_bound_targets=True`; REACH SHALL declare
a destination; ESCORT SHALL declare a destination and SHALL be unable to complete until protected
runtime entities are bound. `deadline_hours` SHALL be either `None`, meaning no deadline, or a positive
integer.

#### Scenario: A complete hand-written definition registers
- **WHEN** a definition has contiguous stages and every objective supplies its required typed fields
- **THEN** `QUEST_DEFINITION_REGISTRY[definition.key]` is that immutable definition

#### Scenario: Non-contiguous stages are rejected
- **WHEN** stages carry indices 0 and 2
- **THEN** registration raises `QuestDefinitionError` and leaves the registry unchanged

#### Scenario: Equal registration is idempotent and conflicting registration is rejected
- **WHEN** equal content is registered twice and different content is then registered under the same key
- **THEN** the equal registration is a no-op, the conflicting registration raises
  `QuestDefinitionError`, and the original definition remains registered

#### Scenario: Objective fields are validated before play
- **WHEN** an ESCORT objective has no destination, a DEFEAT objective has no selector, or a quantity is
  zero
- **THEN** registration raises `QuestDefinitionError` rather than deferring failure to event handling

#### Scenario: Deadline None has one meaning
- **WHEN** a definition registers with `deadline_hours=None`
- **THEN** acceptance creates no deadline and no implicit default is applied

### Requirement: The hand-written catalog is idempotent and provides an offline quest
`world/quests/catalog.py` SHALL declare at least one deterministic introductory hunt using only
permanent world content and a DEFEAT objective. `world/quests/bootstrap.py::sync_quest_runtime()` SHALL
register that catalog idempotently on every server start. Repeating synchronization SHALL preserve one
registry entry per definition key and SHALL NOT create persistent quest records.

#### Scenario: Catalog synchronization is repeatable
- **WHEN** `sync_quest_runtime()` is called twice
- **THEN** the introductory quest is registered exactly once and no player's quest log changes

#### Scenario: Catalog works without generative services
- **WHEN** every AI service is unavailable
- **THEN** the introductory definition remains registered and can be accepted through the deterministic
  lifecycle API
