# npc-identity-titles — Delta Spec

## ADDED Requirements

### Requirement: An imported character record carries a required authored title

`CHARACTER_SCHEMA_V1` SHALL declare `title` as a required property typed `{"type": "string", "minLength": 1}` whose `description` states that the field is a required single-line plain-text NPC title and that its full rule set — the stripped 1-to-32-code-point bound included — is enforced by `world.rules.npc_identity.validate_npc_title`. The rule set SHALL NOT be duplicated in the schema as a `pattern` or a `maxLength` keyword: the bound applies to the validator's stripped form, and a raw `maxLength` would reject values the validator canonicalizes and accepts, splitting the single-validator contract. The semantic validation phase SHALL run `validate_npc_title` and SHALL convert its rejection into a record-level `Issue` naming the `title` field, so the single validator stays the only place the rule set exists; any value the validator accepts SHALL pass the structural phase. A record missing `title`, or whose `title` is not a string, is empty, whose stripped form exceeds the bound, or contains a whitespace character (including U+3000), a control character, or `|` SHALL be rejected. No compatibility layer, alternative schema version, or migration SHALL be introduced for the added field.

#### Scenario: A record without a title is rejected naming the field

- **WHEN** an otherwise valid character record omits `title` entirely
- **THEN** validation rejects it, the reported issue names `title`, and no entity is constructed

#### Scenario: An empty or over-long title is rejected

- **WHEN** a character record's `title` is `""`, is whitespace-only, or whose stripped form is longer than the shared code-point bound
- **THEN** validation rejects the record naming `title`

#### Scenario: A padding-heavy title the validator accepts passes the structural phase

- **WHEN** a character record's `title` carries leading/trailing whitespace pushing the raw value past the code-point bound while its stripped form stays within it (e.g. forty spaces followed by one character)
- **THEN** validation produces no issue for `title` and the loader persists the stripped canonical form — the validator's acceptance, not the raw length, is the contract

#### Scenario: Whitespace, control, and markup characters are rejected through the single validator

- **WHEN** a character record's `title` contains an ASCII space, the full-width space U+3000, a control character, or `|`
- **THEN** validation rejects the record naming `title`, and the rejection message is the stable English identifier the shared validator raises

#### Scenario: A legal title passes both phases

- **WHEN** a character record's `title` is `"南門守衛"`
- **THEN** neither the structural phase nor the semantic phase produces any issue for `title`

#### Scenario: The schema documents the field without restating its rules

- **WHEN** `CHARACTER_SCHEMA_V1` is inspected
- **THEN** `title` appears in the required list, its property carries only `type`/`minLength` plus a description naming the shared validator and its code-point bound, the property definition carries neither `pattern` nor `maxLength`, and the schema's own document-title keyword still reads `"CHARACTER_SCHEMA_V1"`

### Requirement: The import loader persists the validated title on NPC entities only

`world/imports/loader.py` SHALL assign the title during instantiation as the return value of `validate_npc_title(record["title"])` — the stripped canonical form — so the creation point is fail-closed even when reached with an unvalidated record. The assignment SHALL happen only when the constructed entity is an `NPC` (or an `NPC` subclass), because `npc_title` is declared as an `AttributeProperty` on `NPC` alone and assigning it on another typeclass would create a non-persistent instance attribute. A character record imported as a `PlayerCharacter` SHALL still be required to carry a valid `title`, and that title SHALL NOT be persisted anywhere on the constructed player character. The assignment SHALL run inside the existing all-or-nothing transaction, so a batch that fails afterwards persists no title.

#### Scenario: An imported NPC reads back its authored title

- **WHEN** a batch containing a character record whose `title` is `"南門守衛"` is loaded
- **THEN** the constructed NPC's `npc_title` equals `"南門守衛"`, and the room character listing renders the composed 「姓名　稱號」 for it

#### Scenario: A title with surrounding whitespace persists in its stripped form

- **WHEN** a character record's `title` is `" 南門守衛 "`
- **THEN** the record validates and the constructed NPC's `npc_title` equals `"南門守衛"` with no surrounding whitespace

#### Scenario: A player-character import carries no persisted title

- **WHEN** the same record is loaded with `typeclass=PlayerCharacter`
- **THEN** the record is still required to carry a valid `title`, the constructed player character persists no `npc_title` attribute, and its display name stays the plain key

#### Scenario: A rejected batch persists no title

- **WHEN** a batch's second record fails validation, or construction of a later entity raises
- **THEN** no entity from that batch exists and no `npc_title` was persisted for any of them

### Requirement: The import face rejects a name already used by an existing NPC

The author-supplied name at the import face is the record's `key` — the value the loader passes to `create_object` and the value every display surface composes with the title. `world/imports/loader.py` SHALL, before constructing anything and inside the same transaction, reject a batch containing a record whose `key` equals the key of an already-persisted `NPC` (including any `NPC` subclass such as `LLMNPC`). The rejection SHALL fail the whole batch with zero entities persisted, SHALL attach a record-level diagnostic naming the `key` field on the offending record, and SHALL be carried by the existing `ImportRejected` report shape. The loader SHALL NOT reuse the existing entity, rename the incoming record, or overwrite any field of the existing NPC. This gate SHALL apply regardless of the target typeclass of the import. A key that collides with a persisted player character, monster, room, or object SHALL NOT be rejected by this gate, which enforces NPC-name uniqueness only. The existing batch-internal duplicate-key rejection SHALL be unchanged and SHALL compose with this gate.

#### Scenario: A record colliding with an existing NPC fails the whole batch

- **WHEN** an NPC named 塞提斯 already exists and a two-record batch contains one record keyed 塞提斯 alongside one valid new record
- **THEN** the load raises with a report whose 塞提斯 record carries a `key` rejection, and neither record produces an entity

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

### Requirement: The offline validation CLI stays a file-scope check with no database access

`world/imports/validate.py` SHALL remain free of any database access: it validates record files structurally, semantically, and for batch-internal key uniqueness only. The existing-NPC name gate SHALL live at the load boundary, not in the CLI, and its absence from the CLI SHALL NOT be reported as a degraded check — the CLI's file scope is a defined boundary, not a degraded one, and the degraded-validation banner keeps naming only genuinely unavailable checks. The division SHALL be documented in the GM import documentation.

#### Scenario: The CLI validates a colliding record file cleanly

- **WHEN** a record file whose key equals an existing NPC's key is validated with `uv run --locked -m world.imports.validate`
- **THEN** the CLI reports no rejection for the collision and exits 0, since the file itself is valid

#### Scenario: The same record is rejected at load time

- **WHEN** that same file is passed to the loader
- **THEN** the batch is rejected on the `key` diagnostic

#### Scenario: The degraded banner gains no new entry

- **WHEN** any batch is validated through the CLI
- **THEN** the degraded-check list is unchanged by this capability, and no banner claims the existing-name check is degraded

### Requirement: The reference card and the GM import documentation carry the title field

`world/imports/examples/example_character.json` SHALL carry a valid `title` and SHALL keep producing zero rejections and zero warnings. `docs/gm/characters.md` SHALL document `title` in its required-field table, SHALL set it in the inline example record, SHALL state that the field takes effect only for NPC imports, SHALL state that the NPC's displayed name comes from `key` (not from the inert `display_name` field), and SHALL state that the CLI does not check names against already-persisted NPCs while `load_batch()` does. The player-facing command documentation SHALL NOT change, because this capability adds no command surface.

#### Scenario: The reference card stays clean under the new required field

- **WHEN** the reference example is validated
- **THEN** it reports zero rejections and zero warnings, and its `title` satisfies the shared validator

#### Scenario: The GM documentation describes the field and the check split

- **WHEN** `docs/gm/characters.md` is read
- **THEN** the required-field table lists `title` with its rules, the inline example carries it, and the validation section states that the existing-NPC name check runs at load time rather than in the CLI

#### Scenario: The command documentation is untouched

- **WHEN** `docs/game/commands.md` and `docs/game/command-reference.md` are compared against their pre-change content
- **THEN** they are unchanged, and the command-documentation test stays green

### Requirement: The import boundary emits commit and rejection events

`world/imports/loader.py` SHALL emit boundary events through the `world.observability` facade: an info event when a batch commits, and a warn event when a batch is rejected, at every rejection site, carrying a reason code that distinguishes a validation rejection from an existing-NPC name rejection. Every call SHALL pass a `context` mapping carrying batch-level identifiers (record counts, the target typeclass name, the reason code) and SHALL NOT carry player-facing prose or title text. The event identifiers SHALL be stable English snake_case. `world/imports/validate.py` SHALL NOT import the facade, so its existing exception-to-diagnostic blocks stay outside the exception-hygiene rule's adopter scope.

#### Scenario: A committed batch leaves a trace

- **WHEN** a valid batch is loaded
- **THEN** exactly one info event records the commit with the record count and the target typeclass in its context

#### Scenario: A rejected batch names why

- **WHEN** a batch is rejected for a validation issue, and separately when a batch is rejected for an existing-NPC name collision
- **THEN** each emits a warn event whose context carries the distinguishing reason code, and no entity is persisted in either case

#### Scenario: The observability lint stays green

- **WHEN** the observability lint runs after this change
- **THEN** it exits zero, the loader's calls all carry a non-empty `context`, and the freeze list is still empty

### Requirement: The existing import contracts are unchanged by the added title field

This capability SHALL add the import-side title behavior without changing the requirement text of `import-schema`, `import-validation`, `import-loader`, or `import-reference-example`: the record-type discriminator, the age gate, the entity-key character-set and digit-only reservation, the base-value stats convention, the opaque persona, the sexual-baseline vocabulary, the batch all-or-nothing semantics, the degraded-validation banner, the verbatim seam storage, and the `typeclass` parameter all keep their current contracts. The only structural difference is one more required property and one more semantic check.

#### Scenario: Every pre-existing rejection reason still rejects

- **WHEN** records that violate the age gate, the entity-key charset, the digit-only key reservation, the race/subrace cross-check, the magic-power ceiling, or the affinity rules are validated
- **THEN** each is rejected for exactly the same reason and on the same field as before this change

#### Scenario: A valid record's non-title fields load exactly as before

- **WHEN** the reference record — now carrying a `title` — is instantiated
- **THEN** its traits, persona, sexual baseline, skills, equipment, inventory, affinity elements, ages, and portrait policy are byte-identical to their pre-change values
