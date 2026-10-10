# Spec Delta

## MODIFIED Requirements

### Requirement: A single deterministic composer renders the NPC full identity

`world.rules.npc_identity` SHALL be the only place the NPC full identity is composed. `npc_title_value(entity)` SHALL return the stored title as a `str`, or `""` for a non-`NPC` entity, a missing or empty title, stored content that is not a non-empty string, a stored string whose stripped form violates the validator's content rules, or a raising title accessor. `npc_display_name(entity)` SHALL return `姓名` + U+3000 + `稱號` when a renderable title and readable key are present, else the plain key.

#### Scenario: A titled NPC composes with the full-width separator

- **WHEN** `npc_display_name` is called for an NPC named 測試人物 whose title is 測試稱號
- **THEN** it returns `"測試人物　測試稱號"` with exactly one U+3000 between the two parts

#### Scenario: An untitled NPC degrades to the plain name

- **WHEN** `npc_display_name` is called for an NPC whose title is `""`
- **THEN** it returns the plain key with no separator and no placeholder

#### Scenario: Players and monsters are never composed

- **WHEN** `npc_title_value` and `npc_display_name` are called for a player character and for a `Monster`
- **THEN** the title is `""` and the display name is the plain key

#### Scenario: Malformed stored state degrades instead of raising

- **WHEN** `npc_display_name` is called for an NPC whose stored title is a non-string value, a whitespace-only string, a string containing markup, internal whitespace or U+3000, or a control character, or whose title accessor raises, or when the title is absent
- **THEN** it returns the plain key and raises nothing

#### Scenario: An unreadable name never composes an ambiguous identity

- **WHEN** `npc_display_name` is called for an entity whose `key` is missing, raises, or renders empty while a title is stored
- **THEN** it returns `""` — never 「　稱號」 with a leading separator — and raises nothing

#### Scenario: An overlong content-legal title is still returned

- **WHEN** `npc_title_value` is called for a stored string that is content-legal but overlong
- **THEN** it still returns that string, since length corruption is the documented degraded state the display bounds truncate rather than a render hazard

#### Scenario: Malformed stored content is never rendered

- **WHEN** the degrade of a stored string whose stripped form violates the validator's content rules is considered
- **THEN** the content rules are internal whitespace, control or non-printable characters, or the markup delimiter; such a row could never come from an authored path, and rendering it would put Evennia markup or a separator-ambiguous identity on screen

#### Scenario: Composition is a pure, contained read

- **WHEN** `npc_title_value` and `npc_display_name` are called
- **THEN** both are pure reads that never write, never log, and never raise: malformed stored state degrades to the plain key so no presentation surface becomes unavailable over one title field, with accessor failure contained by narrow safe-read boundaries

#### Scenario: The separator constant is module-owned

- **WHEN** the U+3000 separator constant's ownership is inspected
- **THEN** it is held by `world.rules.npc_identity` itself and is not imported from the player title system, which this capability leaves entirely unchanged

### Requirement: The import face rejects a name already used by an existing NPC

The author-supplied name at the import face is the record's `key` — the value the loader passes to `create_object` and the value every display surface composes with the title. `world/imports/loader.py` SHALL, before constructing anything and inside the same transaction, reject a batch whose record `key` equals the key of an already-persisted `NPC` (including subclasses such as `LLMNPC`), failing the whole batch with zero entities persisted and a `key` diagnostic on the offending record.

#### Scenario: A record colliding with an existing NPC fails the whole batch

- **WHEN** an NPC named 測試人物 already exists and a two-record batch contains one record keyed 測試人物 alongside one valid new record
- **THEN** the load raises with a report whose 測試人物 record carries a `key` rejection, and neither record produces an entity

#### Scenario: An existing NPC is never reused, renamed, or overwritten

- **WHEN** the colliding batch above is rejected
- **THEN** the pre-existing NPC keeps its key, its title, and every other field unchanged, and no entity was created for the colliding record

#### Scenario: The gate covers NPC subclasses

- **WHEN** the already-persisted entity with that key is an `LLMNPC` rather than a plain `NPC`
- **THEN** the batch is rejected exactly as it is for a plain `NPC`

#### Scenario: The gate applies to a player-character import too

- **WHEN** a batch that collides with an existing NPC key is loaded with `typeclass=PlayerCharacter`
- **THEN** the batch is rejected on the same `key` diagnostic

#### Scenario: A non-NPC entity with the same key does not reject the batch

- **WHEN** the only entity holding that key is a persisted player character, a monster, a room, or an object
- **THEN** the batch is not rejected by this gate

#### Scenario: Batch-internal duplicates still fail on their own grounds

- **WHEN** a batch contains two records sharing one key that no existing NPC uses
- **THEN** the existing batch-internal duplicate-key rejection fails the batch, unchanged by this gate

#### Scenario: The loader never reuses, renames, or overwrites

- **WHEN** a record collides with an already-persisted `NPC`
- **THEN** the loader does not reuse the existing entity, rename the incoming record, or overwrite any field of the existing NPC

#### Scenario: The gate applies regardless of the target typeclass

- **WHEN** a colliding batch is loaded under any target typeclass
- **THEN** the gate rejects it, regardless of the target typeclass of the import

#### Scenario: The gate enforces NPC-name uniqueness only

- **WHEN** a record key collides with a persisted player character, monster, room, or object
- **THEN** it is not rejected by this gate, which enforces NPC-name uniqueness only

#### Scenario: The rejection rides the existing report shape

- **WHEN** the collision rejection is reported
- **THEN** the record-level diagnostic naming the `key` field is carried by the existing `ImportRejected` report shape

### Requirement: Blueprint scene occupants spawn under the authored name with the authored title
The SceneBuilder SHALL spawn every stage occupant whose `key` is the entry's authored
`display_name` in the shared name validator's normalized (stripped) form, and SHALL persist the
entry's authored `title` in the shared title validator's normalized form as the NPC title.
If any occupant lacks a characterization, its `display_name`, or its `title` at spawn time,
the SceneBuilder SHALL raise `SceneBuilderSpawnError` and roll back the whole materialization
before creating any room or entity.

#### Scenario: A materialized occupant answers to its authored name
- **WHEN** a compiled stage with `npc_req: [{"role": "bandit", "tier": "bandit", "display_name": "測試人物", "title": "測試稱號", ...}]` materializes
- **THEN** the spawned NPC's `key` is `測試人物`, its `npc_title` is `測試稱號`, and the full
  identity composer renders 「測試人物　測試稱號」 on full-identity surfaces

#### Scenario: A missing title rolls back the materialization
- **WHEN** a forge-constructed spawn requirement reaches the SceneBuilder with `title` absent or
  invalid
- **THEN** `SceneBuilderSpawnError` is raised and no room, entity, or exit from that
  materialization persists

#### Scenario: Surrounding whitespace never reaches the entity key
- **WHEN** an otherwise-valid authored identity carries surrounding whitespace when the
  materialization revalidator strips and accepts it
- **THEN** the spawned NPC's `key` and `db.display_name` are the stripped form

#### Scenario: The portrait subject name keeps its source
- **WHEN** an occupant spawns under its authored name
- **THEN** `db.display_name` still carries the same authored value for the art-subject consumer

#### Scenario: A missing authored identity fails closed like age-bounds revalidation

- **WHEN** a missing authored identity is compared to the existing age-bounds revalidation
- **THEN** it fails closed exactly like the existing age-bounds revalidation does
