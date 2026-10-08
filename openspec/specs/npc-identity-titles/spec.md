# npc-identity-titles Specification

## Purpose

Define the immutable, author-supplied NPC identity title: the single validator every authored write path validates against, the single deterministic composer of the 「姓名　稱號」 full identity, and the display contract that surfaces it only on the room character line, the look header, and the webclient exploration entity/interact rows while every other surface (echoes, compact panels, targeting, prompts) keeps the plain name byte-identical. Zero coupling with the player title system.

## Requirements

### Requirement: NPC titles are validated single-line plain text

The deterministic core SHALL expose one validator, `world.rules.npc_identity.validate_npc_title(value)`, as the single place every NPC-title write path validates against. It SHALL first strip surrounding whitespace (of any kind, U+3000 included), decide acceptance on that stripped form, and return it. It SHALL accept only a `str` (a `bool` is not a `str` and is rejected) whose stripped form contains 1 to 32 code points, and SHALL reject every other value by raising.

#### Scenario: A legal title round-trips stripped

- **WHEN** `validate_npc_title(" 南門守衛 ")` is called
- **THEN** it returns `"南門守衛"` with no surrounding whitespace

#### Scenario: Boundary lengths are decided exactly

- **WHEN** `validate_npc_title` is called with a 32-code-point title and again with a 33-code-point title
- **THEN** the 32-code-point value is accepted and the 33-code-point value is rejected

#### Scenario: Internal separator, whitespace, control, and markup characters are rejected

- **WHEN** `validate_npc_title` is called with a title containing an internal ASCII space, with one containing an internal full-width space U+3000, with one containing a control character, and with one containing `|`
- **THEN** every one of them is rejected, while a value differing from a legal title only by surrounding whitespace is accepted and normalized

#### Scenario: Non-text and empty values are rejected

- **WHEN** `validate_npc_title` is called with `None`, an integer, a boolean, `""`, or `"   "`
- **THEN** every one of them is rejected

#### Scenario: The rejection classes are rejected by raising

- **WHEN** `validate_npc_title` is called with a non-`str` value, a value whose stripped form is empty, a value whose stripped form is longer than 32 code points, or a value whose stripped form contains any internal whitespace character (including the full-width space U+3000 that the composer reserves as its separator), any control character, or the Evennia markup delimiter `|`
- **THEN** every one of them is rejected by raising

#### Scenario: Rejection messages are stable identifiers

- **WHEN** any rejection is raised
- **THEN** the message is a stable English identifier carrying no player-facing prose

### Requirement: The NPC title is a creation-time attribute with no runtime write surface

The `NPC` typeclass SHALL declare a persistent `npc_title` attribute through `AttributeProperty` with the default `""`, materialized lazily (no storage row exists until a write path assigns one). This capability SHALL NOT introduce any runtime write surface: no setter, no assigning helper, no player or staff command, and no generative or dialogue-intent path SHALL change an NPC's title after creation. Only authored creation paths, validating through `validate_npc_title`, SHALL write it.

#### Scenario: An untitled NPC is a degraded storage state, not a production path

- **WHEN** an `NPC` is created directly (e.g. a test fixture) with no title supplied
- **THEN** `npc_title` reads as `""`, every display surface renders the plain name, and the
  presentation degrades silently without error

#### Scenario: No runtime write surface exists

- **WHEN** the `NPC` typeclass surface and the registered command sets are inspected for a title write path
- **THEN** no title setter, title-assigning helper, or title-changing command is present

#### Scenario: The empty default is a storage default, not a production creation shape

- **WHEN** the meaning of the `""` default is inspected
- **THEN** it applies only to entities no authored creation path produced (test fixtures, transient scaffolds) — a degraded state the composer renders as the plain name, NOT a supported production creation shape — while every production NPC path (import loader, SceneBuilder occupants, registry-backed hosts and examiners) is fail-closed at its own author face, owned by the later changes in this batch

#### Scenario: The typeclass provides no create-time title parameter

- **WHEN** the `NPC` typeclass creation surface is inspected
- **THEN** it deliberately provides no create-time title parameter, because title validation belongs to the authored paths

#### Scenario: Generic attribute access stays framework infrastructure

- **WHEN** the write-surface guarantee is scoped
- **THEN** it is the absence of a title-specific write API on this capability's surfaces: Evennia's generic attribute access (`entity.db.npc_title = ...`) remains framework infrastructure deliberately outside the claim, and tests seed malformed stored state through it

### Requirement: A single deterministic composer renders the NPC full identity

`world.rules.npc_identity` SHALL be the only place the NPC full identity is composed. `npc_title_value(entity)` SHALL return the stored title as a `str`, or `""` for a non-`NPC` entity, a missing or empty title, stored content that is not a non-empty string, a stored string whose stripped form violates the validator's content rules, or a raising title accessor. `npc_display_name(entity)` SHALL return `姓名` + U+3000 + `稱號` when a renderable title and readable key are present, else the plain key.

#### Scenario: A titled NPC composes with the full-width separator

- **WHEN** `npc_display_name` is called for an NPC named 塞提斯 whose title is 南門守衛
- **THEN** it returns `"塞提斯　南門守衛"` with exactly one U+3000 between the two parts

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

### Requirement: Full identity appears only on opt-in text display surfaces

`NPC.get_display_name` SHALL accept an opt-in `full_identity` keyword defaulting to false. Flag absent or false: the return value SHALL be byte-identical to the pre-change plain-name output; flag true: it SHALL return `npc_display_name(self)`. Exactly two text surfaces SHALL pass the flag: the shared room character listing (`ObjectParent.get_display_characters`), and the look-header name slot of an NPC. Every other caller SHALL NOT pass the flag and SHALL render the plain name.

#### Scenario: The room character listing shows the full identity

- **WHEN** a player looks at a room containing a titled NPC
- **THEN** the 「人物」 line shows 「姓名　稱號」 for that NPC

#### Scenario: The look header shows the full identity on every entry path

- **WHEN** a player looks at a titled NPC through the text 「看」 command, the `at_look` seam, and the webclient `explore.look` action
- **THEN** all three headers show 「姓名　稱號」 and the three appearances remain identical to one another

#### Scenario: Echo and notification text stays plain-name

- **WHEN** a titled NPC moves, speaks, whispers, is given an item, or is left behind by a following player
- **THEN** every resulting message names the NPC by its plain key only, byte-identical to the untitled rendering

#### Scenario: Players and monsters in the listing render plain names

- **WHEN** a room contains a player character and a monster alongside the titled NPC
- **THEN** the 「人物」 line renders their plain keys and no separator or placeholder appears for them

#### Scenario: The look header keeps every entry path identical

- **WHEN** the look-header flag is traced through its entry paths
- **THEN** the name slot is the appearance-template name slot, so the text 「看 <目標>」 command, the `at_look` seam, and the webclient `explore.look` action stay identical to one another as the localized-appearance contract requires

#### Scenario: The non-flag caller set is enumerated

- **WHEN** the callers that must not pass the flag are enumerated
- **THEN** they are movement, say, whisper, give and pickup echoes, the follow-lost notification, and combat text, and every resulting message keeps rendering the plain name

#### Scenario: A non-NPC character accepts the flag

- **WHEN** the flag is passed to a non-NPC character
- **THEN** it is accepted and renders that entity's plain name

### Requirement: The webclient exploration panel renders the NPC full identity on entity and interact rows

The `exploration` panel SHALL source the `display_name` of its `look.entities` rows and its `interact` target rows from `npc_display_name`, so a titled NPC reads as 「姓名　稱號」 there. The room row, the `move` rows, and the `look.objects` rows SHALL keep their existing plain-key source. The panel's existing bounds SHALL NOT change; the rows SHALL keep their truncating (never raising) bounding behavior. The change SHALL NOT alter the panel schema version, field set, ordering, or availability.

#### Scenario: A titled NPC reads with its title on both row kinds

- **WHEN** the exploration panel is built for a player in a room with a titled NPC
- **THEN** that NPC's `look.entities` row and its `interact` target row both carry 「姓名　稱號」 as `display_name`

#### Scenario: Non-entity rows are untouched

- **WHEN** the same panel is built in a room carrying exits and present objects
- **THEN** the room row, the `move` rows, and the `look.objects` rows are byte-identical to their pre-change values

#### Scenario: The panel stays available for an untitled or malformed NPC

- **WHEN** the panel is built in a room with an untitled NPC and with an NPC whose stored title is malformed
- **THEN** both rows carry the plain key, the panel is available, and the payload validates

#### Scenario: The composed identity fits the existing display-name bound

- **WHEN** the composed identity's size is checked against the panel's bounds
- **THEN** it is at most 97 code points (a key of at most 64, one separator, a title of at most 32), inside the 128-code-point display-name bound, so the existing bounds need no change

### Requirement: Compact presentation rows keep the plain NPC name

The compact deterministic view models SHALL keep rendering the NPC's plain key: combat participant rows (`world/rules/combat_view.py`), the portrait catalog entries (`world/rules/art_view.py`), and the guild/shop host rows (`world/rules/service_view.py`). These surfaces SHALL NOT consume `npc_display_name`, and each SHALL carry an assertion test pinning the plain-name rendering for a titled NPC so a later change cannot widen them silently.

#### Scenario: Combat participants stay plain-name

- **WHEN** a combat view is built with a titled NPC among the participants
- **THEN** that participant's `display_name` is the plain key with no separator or title

#### Scenario: Portrait catalog and host rows stay plain-name

- **WHEN** an art view is built for a room with a titled NPC and a service view is built for a titled guild or shop host
- **THEN** both rows carry the plain key with no separator or title

### Requirement: The NPC dialogue context carries the title as read-only data

`LLMNPC._npc_context()` SHALL include a `title` key whose value is `npc_title_value(self)` — the stored title, or `""` when the NPC is untitled. Building the context SHALL remain a pure read that never creates, persists, or mutates state. Adding the key SHALL leave every rendered dialogue prompt byte-identical, because the system-message renderer reads only the name, description, and location values.

#### Scenario: A titled NPC exposes its title to the dialogue context

- **WHEN** `_npc_context()` is called on a titled `LLMNPC`
- **THEN** the returned mapping's `title` value is that title and no stored state changed

#### Scenario: An untitled NPC exposes an empty title and an unchanged prompt

- **WHEN** `_npc_context()` is called on an untitled `LLMNPC` and a dialogue prompt is built from it
- **THEN** `title` is `""` and the rendered system message is byte-identical to the pre-change rendering

### Requirement: Command and search targeting matches the plain NPC key only

Player command and object-search targeting SHALL continue to resolve NPCs by their plain `key`. The title SHALL NOT be written into the key, registered as an alias, or added to any search index, so a player never has to type a title to address an NPC.

#### Scenario: The plain name still resolves a titled NPC

- **WHEN** a player targets a titled NPC by its plain name through an ordinary object search
- **THEN** the NPC resolves exactly as it did before the title existed

#### Scenario: The composed full identity is not a search key

- **WHEN** a player searches for the composed 「姓名　稱號」 string
- **THEN** the search does not resolve the NPC through that composed string

### Requirement: The existing appearance and exploration contracts are unchanged

This capability SHALL add the NPC title behavior without changing the requirement text of `localized-appearance` or `webclient-exploration-menu`: the zh-tw appearance frames, the affinity stage line, the displayed-stats block, the exploration panel's schema version, field set, and bounds all keep their current contracts. The title changes only which string fills an already-specified display-name slot.

#### Scenario: The zh-tw appearance frame is preserved

- **WHEN** a player looks at a room containing a titled NPC
- **THEN** the appearance still renders the 「出口」 and 「人物」 zh-tw frames, the affinity stage line, and the displayed-stats block exactly as specified today, with no English frame string

#### Scenario: The exploration panel contract is preserved

- **WHEN** the exploration panel is built in a room containing a titled NPC
- **THEN** the payload still validates against the unchanged schema version 1 field set and bounds

### Requirement: An imported character record carries a required authored title

`CHARACTER_SCHEMA_V1` SHALL declare `title` as a required property typed `{"type": "string", "minLength": 1}` whose `description` states that the field is a required single-line plain-text NPC title whose full rule set is enforced by `world.rules.npc_identity.validate_npc_title`. The semantic validation phase SHALL run `validate_npc_title` and SHALL convert its rejection into a record-level `Issue` naming the `title` field, so the single validator stays the only place the rule set exists.

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

#### Scenario: The description carries the full rule set pointer

- **WHEN** the `title` property's `description` is read
- **THEN** it states that the field is a required single-line plain-text NPC title and that its full rule set — the stripped 1-to-32-code-point bound included — is enforced by `world.rules.npc_identity.validate_npc_title`

#### Scenario: The rule set is not duplicated in the schema

- **WHEN** the `title` property definition is considered
- **THEN** the rule set is not duplicated as a `pattern` or a `maxLength` keyword: the bound applies to the validator's stripped form, and a raw `maxLength` would reject values the validator canonicalizes and accepts, splitting the single-validator contract

#### Scenario: Any validator-accepted value passes the structural phase

- **WHEN** any value that `validate_npc_title` accepts is submitted as a record's `title`
- **THEN** the structural phase produces no issue for it

#### Scenario: The rejection set is enumerated

- **WHEN** a record is missing `title`, or its `title` is not a string, is empty, has a stripped form exceeding the bound, or contains a whitespace character (including U+3000), a control character, or `|`
- **THEN** the record is rejected

#### Scenario: No compatibility layer or migration is added

- **WHEN** the rollout of the added field is considered
- **THEN** no compatibility layer, alternative schema version, or migration is introduced for it

### Requirement: The import loader persists the validated title on NPC entities only

`world/imports/loader.py` SHALL assign the title during instantiation as the return value of `validate_npc_title(record["title"])` — the stripped canonical form — so the creation point is fail-closed even when reached with an unvalidated record. The assignment SHALL happen only when the constructed entity is an `NPC` (or an `NPC` subclass). The assignment SHALL run inside the existing all-or-nothing transaction, so a batch that fails afterwards persists no title.

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

#### Scenario: A player-character title is persisted nowhere

- **WHEN** a character record is imported as a `PlayerCharacter`
- **THEN** the title is not persisted anywhere on the constructed player character

#### Scenario: The NPC-only assignment is required by the property declaration

- **WHEN** the reason for the NPC-only assignment is inspected
- **THEN** `npc_title` is declared as an `AttributeProperty` on `NPC` alone, and assigning it on another typeclass would create a non-persistent instance attribute

### Requirement: The import face rejects a name already used by an existing NPC

The author-supplied name at the import face is the record's `key` — the value the loader passes to `create_object` and the value every display surface composes with the title. `world/imports/loader.py` SHALL, before constructing anything and inside the same transaction, reject a batch whose record `key` equals the key of an already-persisted `NPC` (including subclasses such as `LLMNPC`), failing the whole batch with zero entities persisted and a `key` diagnostic on the offending record.

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

### Requirement: The offline validation CLI stays a file-scope check with no database access

`world/imports/validate.py` SHALL remain free of any database access: it validates record files structurally, semantically, and for batch-internal key uniqueness only. The existing-NPC name gate SHALL live at the load boundary, not in the CLI, and its absence from the CLI SHALL NOT be reported as a degraded check — the CLI's file scope is a defined boundary, not a degraded one. The division SHALL be documented in the GM import documentation.

#### Scenario: The CLI validates a colliding record file cleanly

- **WHEN** a record file whose key equals an existing NPC's key is validated with `uv run --locked -m world.imports.validate`
- **THEN** the CLI reports no rejection for the collision and exits 0, since the file itself is valid

#### Scenario: The same record is rejected at load time

- **WHEN** that same file is passed to the loader
- **THEN** the batch is rejected on the `key` diagnostic

#### Scenario: The degraded banner gains no new entry

- **WHEN** any batch is validated through the CLI
- **THEN** the degraded-check list is unchanged by this capability, and no banner claims the existing-name check is degraded

#### Scenario: The degraded banner names only genuinely unavailable checks

- **WHEN** the degraded-validation banner is rendered
- **THEN** it keeps naming only genuinely unavailable checks

### Requirement: The reference card and the GM import documentation carry the title field

`world/imports/examples/example_character.json` SHALL carry a valid `title` and SHALL keep producing zero rejections and zero warnings. `docs/gm/characters.md` SHALL document `title` in its required-field table, SHALL set it in the inline example record, and SHALL state that the field takes effect only for NPC imports. The player-facing command documentation SHALL NOT change, because this capability adds no command surface.

#### Scenario: The reference card stays clean under the new required field

- **WHEN** the reference example is validated
- **THEN** it reports zero rejections and zero warnings, and its `title` satisfies the shared validator

#### Scenario: The GM documentation describes the field and the check split

- **WHEN** `docs/gm/characters.md` is read
- **THEN** the required-field table lists `title` with its rules, the inline example carries it, and the validation section states that the existing-NPC name check runs at load time rather than in the CLI

#### Scenario: The command documentation is untouched

- **WHEN** `docs/game/commands.md` and `docs/game/command-reference.md` are compared against their pre-change content
- **THEN** they are unchanged, and the command-documentation test stays green

#### Scenario: The GM documentation names `key` as the displayed-name source

- **WHEN** `docs/gm/characters.md` is read
- **THEN** it states that the NPC's displayed name comes from `key` (not from the inert `display_name` field), and that the CLI does not check names against already-persisted NPCs while `load_batch()` does

### Requirement: The import boundary emits commit and rejection events

`world/imports/loader.py` SHALL emit boundary events through the `world.observability` facade: an info event when a batch commits, and a warn event when a batch is rejected, at every rejection site, carrying a reason code that distinguishes a validation rejection from an existing-NPC name rejection. Every call SHALL pass a `context` mapping carrying batch-level identifiers and SHALL NOT carry player-facing prose or title text. The event identifiers SHALL be stable English snake_case.

#### Scenario: A committed batch leaves a trace

- **WHEN** a valid batch is loaded
- **THEN** exactly one info event records the commit with the record count and the target typeclass in its context

#### Scenario: A rejected batch names why

- **WHEN** a batch is rejected for a validation issue, and separately when a batch is rejected for an existing-NPC name collision
- **THEN** each emits a warn event whose context carries the distinguishing reason code, and no entity is persisted in either case

#### Scenario: The observability lint stays green

- **WHEN** the observability lint runs after this change
- **THEN** it exits zero, the loader's calls all carry a non-empty `context`, and the freeze list is still empty

#### Scenario: The context identifiers are enumerated

- **WHEN** a loader event's `context` mapping is inspected
- **THEN** it carries batch-level identifiers — record counts, the target typeclass name, the reason code

#### Scenario: The validation CLI stays outside the facade

- **WHEN** `world/imports/validate.py` is inspected
- **THEN** it does not import the observability facade, so its existing exception-to-diagnostic blocks stay outside the exception-hygiene rule's adopter scope

### Requirement: The existing import contracts are unchanged by the added title field

The added import-side title behavior SHALL NOT change the requirement text of `import-schema`, `import-validation`, `import-loader`, or `import-reference-example`: the record-type discriminator, the age gate, the entity-key charset and digit-only reservation, the base-value stats convention, the opaque persona, the sexual-baseline vocabulary, the batch all-or-nothing semantics, the degraded-validation banner, the verbatim seam storage, and the `typeclass` parameter keep their current contracts.

#### Scenario: Every pre-existing rejection reason still rejects

- **WHEN** records that violate the age gate, the entity-key charset, the digit-only key reservation, the race/subrace cross-check, the magic-power ceiling, or the affinity rules are validated
- **THEN** each is rejected for exactly the same reason and on the same field as before this change

#### Scenario: A valid record's non-title fields load exactly as before

- **WHEN** the reference record — now carrying a `title` — is instantiated
- **THEN** its traits, persona, sexual baseline, skills, equipment, inventory, affinity elements, ages, and portrait policy are byte-identical to their pre-change values

#### Scenario: The title field is the only structural difference

- **WHEN** the import contracts are compared against their pre-change state
- **THEN** the only structural difference is one more required property and one more semantic check

### Requirement: Blueprint scene occupants spawn under the authored name with the authored title
The SceneBuilder SHALL spawn every stage occupant whose `key` is the entry's authored
`display_name` in the shared name validator's normalized (stripped) form, and SHALL persist the
entry's authored `title` in the shared title validator's normalized form as the NPC title.
If any occupant lacks a characterization, its `display_name`, or its `title` at spawn time,
the SceneBuilder SHALL raise `SceneBuilderSpawnError` and roll back the whole materialization
before creating any room or entity.

#### Scenario: A materialized occupant answers to its authored name
- **WHEN** a compiled stage with `npc_req: [{"role": "bandit", "tier": "bandit", "display_name": "黑鬍", "title": "林間盜匪頭目", ...}]` materializes
- **THEN** the spawned NPC's `key` is `黑鬍`, its `npc_title` is `林間盜匪頭目`, and the full
  identity composer renders 「黑鬍　林間盜匪頭目」 on full-identity surfaces

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

### Requirement: The blueprint author face enforces occupant name uniqueness
Any two `npc_req` entries within one blueprint — in the same stage or across stages — SHALL NOT
declare the same `display_name`. The name rule is blueprint-wide uniqueness, stricter than the
existing shared-`stable_key` agreement rule it is implemented alongside.

#### Scenario: Same-stage duplicate names are rejected
- **WHEN** one stage declares two `npc_req` entries whose `display_name` values are identical
- **THEN** the blueprint is rejected before compilation with a named diagnostic

#### Scenario: Cross-stage duplicate names are rejected
- **WHEN** two stages of one blueprint declare the same `display_name`, even with identical title
  and characterization
- **THEN** the blueprint is rejected before compilation — the authored name is unique across the
  whole blueprint; shared portrait identity remains the mechanism for one character appearing in
  multiple scenes

#### Scenario: Fresh spawns make any duplicate a same-key hazard

- **WHEN** the reason for blueprint-wide uniqueness is inspected
- **THEN** the authored name becomes the spawned occupant's `key` and each quest materialization
  spawns fresh occupants with no cross-stage identity reuse, so even an identical-characterization
  duplicate could live as two same-`key` entities

### Requirement: Shop and guild registries author host and examiner identities validated at load
`ShopDefinition` and `GuildBranch` SHALL each carry required `host_name` and `host_title` fields,
and `GuildRank` SHALL carry required `examiner_name` and `examiner_title` fields, all declared
without defaults so a missing column is a module-import `TypeError`. The lore modules owning
these registries SHALL validate every row's authored names and titles through the shared name and
title validators at module load time (invalid values raise named `ValueError`s).

#### Scenario: A row with an invalid authored title fails module load
- **WHEN** the pure row validator is called with a registry row whose authored title violates the
  shared title rule (empty, overlong, whitespace/control/`|` characters)
- **THEN** it raises a named `ValueError` naming the offending registry key and field

#### Scenario: A duplicated authored name across registries fails load
- **WHEN** the cross-registry uniqueness check is called with rows where a shop host and an
  examiner share one authored name
- **THEN** it raises a named `ValueError`

#### Scenario: The shipped registries load clean
- **WHEN** `world.lore.settlements.shops` and `world.lore.guild` are imported
- **THEN** every shipped row passes name, title, and cross-registry uniqueness validation

#### Scenario: The lore modules check cross-registry name uniqueness at load

- **WHEN** the lore modules owning the registries load
- **THEN** they check that authored NPC names do not repeat across the shop, guild-branch, and
  guild-rank registries

#### Scenario: The row validators are pure and explicitly callable

- **WHEN** the row validators' shape is inspected
- **THEN** they are pure functions callable with explicit rows, so violations are testable
  without mutating the shipped registries

### Requirement: Guild service hosts reuse by service anchor and never rename
`sync_guild_economy` SHALL locate a service host by the `service_id` recorded on its service
component — never by display `key`. A missing host SHALL be created once under the roster row's
authored `name` as its `key` with the authored `title` persisted as its NPC title. An existing
host located by its service anchor SHALL never be renamed and SHALL never have its title written
at sync time — a host that predates authored identities is reused as-is, never backfilled.

#### Scenario: First sync creates the authored host
- **WHEN** `sync_guild_economy` runs with no existing host for a service component
- **THEN** exactly one NPC is created whose `key` is the roster row's authored `name`, whose
  `npc_title` is the row's authored `title`, and which carries the service component

#### Scenario: Re-sync neither duplicates nor renames
- **WHEN** `sync_guild_economy` runs again after the host exists, including with a changed
  roster `name`
- **THEN** the same NPC is reused, no second host exists, and its `key` is unchanged

#### Scenario: A host predating authored identities is reused, not backfilled
- **WHEN** a pre-existing host located by its service anchor carries no authored title and its
  `service_id` is on the roster
- **THEN** the sync reuses it as-is: no title is written, nothing is renamed, and no second
  authored host is created

#### Scenario: An unrelated NPC with no service component survives convergence
- **WHEN** convergence runs while an NPC shares a retired host key but carries no service
  component
- **THEN** the NPC is not deleted

#### Scenario: Duplicate service anchors fail closed
- **WHEN** two live NPCs carry service components with the same `service_id` and sync runs
- **THEN** a named integrity error is raised and no host is created, renamed, or deleted

#### Scenario: Anchor contention fails closed before any mutation

- **WHEN** sync locates a service anchor claimed by more than one live host
- **THEN** it fails closed with a named integrity error before any mutation

#### Scenario: Convergence replaces the legacy-key cleanup as the deletion mechanism

- **WHEN** the deletion mechanism for stale hosts is considered
- **THEN** roster-authoritative convergence replaces the batch's one-time legacy-key cleanup:
  deletion anchors on roster membership of the component `service_id`, never the entity key

#### Scenario: A stale titleless candidate is deleted for recreation

- **WHEN** a titleless candidate's service anchors all match no roster row
- **THEN** it is unambiguous stale development state and is deleted, so the roster pass recreates
  it under the full authored identity when its row returns

#### Scenario: Component-less NPCs survive and anchored titled candidates are kept

- **WHEN** an NPC carrying no service component exists, and separately when a titled candidate
  still holds at least one roster-matching anchor
- **THEN** the component-less NPC survives untouched, and the titled candidate is kept with a
  named warning for manual repair

### Requirement: Exam examiners carry their authored identity
The examination opponent spawn SHALL use the rank's authored `examiner_name` and SHALL persist the
authored `examiner_title` as the NPC title, replacing the anonymous `guild-examiner-<rank>` key
form; the key-collision behaviour is governed by the `guild-rank-exams` requirement restated by
this change.

#### Scenario: A spawned examiner carries the authored title
- **WHEN** `start_guild_exam` spawns the opponent for a rank
- **THEN** the opponent's `npc_title` equals that rank's `examiner_title` and its key begins with
  the rank's `examiner_name`

### Requirement: Host and examiner creation emit boundary info events
The service-host creation path and the examination-opponent spawn SHALL each emit one observability
facade info event when an entity is actually created (never on idempotent reuse), with business
identifiers in the context — `char` and `shop`/`service` for the host, `char` and `rank` for the
opponent — and no player-facing prose.

#### Scenario: Host creation logs once
- **WHEN** a service host is created and a later sync reuses it
- **THEN** the creation event fires exactly once with `char` and service identifiers in context

#### Scenario: Opponent spawn logs
- **WHEN** an examination opponent is spawned
- **THEN** the spawn event fires with `char` and `rank` context keys

### Requirement: The existing scene-builder and generated-quest contracts are unchanged where not amended
Except for the authored-identity behaviour stated in this delta, the scene-builder spawn contracts
(anti-hallucination characterization ownership, the post-commit portrait-eligibility seam, and the
`db.display_name` write) and the generated-quest durable-store contract SHALL remain as previously
specified; this change adds the authored identity on top and SHALL NOT otherwise alter their
observable behaviour.

#### Scenario: The pre-existing scene contracts still hold
- **WHEN** the scene-builder and durable-store suites run after this change
- **THEN** every pre-existing requirement scenario of those capabilities still passes
