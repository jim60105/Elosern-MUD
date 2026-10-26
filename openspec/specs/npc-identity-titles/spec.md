# npc-identity-titles Specification

## Purpose

Define the immutable, author-supplied NPC identity title's validation and storage contract: the single validator every authored write path validates against, the creation-time attribute it persists, and the plain authored name every presentation, targeting and dialogue-prompt surface renders without composing that title. Zero coupling with the player title system.

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

### Requirement: The NPC dialogue context carries the title as read-only data
NPC dialogue context SHALL carry name, description and location without an independent title field. Player title context SHALL remain unchanged.

#### Scenario: NPC context omits independent title
- **WHEN** an NPC with historical title attributes builds dialogue context
- **THEN** the context neither reads nor includes that title

#### Scenario: Player context preserves title
- **WHEN** a player with an equipped title builds its existing context
- **THEN** its current title information is unchanged

#### Scenario: A titled NPC exposes its title to the dialogue context
- **WHEN** an NPC with historical title data builds context
- **THEN** the title is neither read nor emitted; ordinary name/description/location remain

#### Scenario: An untitled NPC exposes an empty title and an unchanged prompt
- **WHEN** an NPC without title data builds context
- **THEN** the same title-free context is emitted without creating an attribute

### Requirement: Command and search targeting matches the plain NPC key only

Player command and object-search targeting SHALL continue to resolve NPCs by their plain `key`. The title SHALL NOT be written into the key, registered as an alias, or added to any search index, so a player never has to type a title to address an NPC.

#### Scenario: The plain name still resolves a titled NPC

- **WHEN** a player targets a titled NPC by its plain name through an ordinary object search
- **THEN** the NPC resolves exactly as it did before the title existed

#### Scenario: The composed full identity is not a search key

- **WHEN** a player searches for the composed 「姓名　稱號」 string
- **THEN** the search does not resolve the NPC through that composed string

#### Scenario: Composed member aliases are removed
- **WHEN** a member is targeted with an old name-plus-title token rather than its current key/dbref
- **THEN** no composed-name alias matches and existing ambiguity rules still apply

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
- **THEN** the constructed NPC's `npc_title` equals `"南門守衛"`, and the room character listing renders the plain authored `key`

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
- **WHEN** a compiled stage with `npc_req: [{"role": "bandit", "tier": "bandit", "display_name": "測試人物", "title": "測試稱號", ...}]` materializes
- **THEN** the spawned NPC's `key` is `測試人物`, its `npc_title` is `測試稱號`, and every
  presentation surface renders the plain name `測試人物`

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
and branch-qualified persistent adventurer records SHALL carry required authored name and title
fields, all declared without defaults so a missing column is a module-import `TypeError`. The
owning lore modules SHALL validate every row's authored names and titles through the shared name
and title validators at module load time (invalid values raise named `ValueError`s).

#### Scenario: A row with an invalid authored title fails module load
- **WHEN** the pure row validator is called with a registry row whose authored title violates the
  shared title rule (empty, overlong, whitespace/control/`|` characters)
- **THEN** it raises a named `ValueError` naming the offending registry key and field

#### Scenario: A duplicated authored name across registries fails load
- **WHEN** the cross-registry uniqueness check is called with rows where a shop host and an
  persistent adventurer share one authored name
- **THEN** it raises a named `ValueError`

#### Scenario: The shipped registries load clean
- **WHEN** `world.lore.settlements.shops` and `world.lore.guild` are imported
- **THEN** every shipped row passes name, title, and cross-registry uniqueness validation

#### Scenario: Rank metadata has no opponent factory identity
- **WHEN** ranks and qualification records load
- **THEN** `GuildRank` owns no examiner name, title or profile field; ranks contain
  progression/reward/title metadata, person identity validates on qualification sources through the
  shared validators, and shop and branch host identity checks stay unchanged

#### Scenario: The lore modules check cross-registry name uniqueness at load

- **WHEN** the lore modules owning the registries load
- **THEN** they check that authored NPC names do not repeat across the shop, guild-branch, and
  persistent-adventurer registries

#### Scenario: The row validators are pure and explicitly callable

- **WHEN** the row validators' shape is inspected
- **THEN** they are pure functions callable with explicit rows, so violations are testable
  without mutating the shipped registries

### Requirement: Guild service hosts reuse by service anchor and never rename
Service hosts SHALL reuse canonical authored profile provenance independent of component IDs/order and preserve existing identity and live state. Whole-row retirement SHALL use explicit source ownership and SHALL never consult title content.

#### Scenario: Canonical host remains stable
- **WHEN** a service ID, display-name declaration or capability order changes
- **THEN** the existing host dbref/name/location/state survive

#### Scenario: No title-based ownership inference
- **WHEN** a host carries an arbitrary historical title
- **THEN** it grants no lookup or deletion authority

#### Scenario: First sync creates the authored host
- **WHEN** no canonical profile-provenance host exists for a valid row
- **THEN** one host is created with its authored name/profile and resolved capability plan atomically

#### Scenario: Re-sync neither duplicates nor renames
- **WHEN** the canonical host exists and source name or capability order changes
- **THEN** its dbref/name/location/runtime state survive without a duplicate

#### Scenario: A host predating authored identities is reused, not backfilled
- **WHEN** an existing canonical npc_profile_key host has historical attributes
- **THEN** it is reused without name/title backfill or component-ID fallback

#### Scenario: An unrelated NPC with no service component survives convergence
- **WHEN** an unmanaged NPC shares a retired name but no source ownership
- **THEN** it is not deleted

#### Scenario: Duplicate service anchors fail closed
- **WHEN** two live hosts claim one canonical authored host profile
- **THEN** the complete operation rejects before host creation/deletion/configuration

#### Scenario: Anchor contention fails closed before any mutation
- **WHEN** canonical profile provenance has multiple claimants
- **THEN** a named integrity failure precedes all writes

#### Scenario: Convergence replaces the legacy-key cleanup as the deletion mechanism
- **WHEN** a managed lifecycle is synchronized
- **THEN** only explicit source ownership and whole-row retirement authorize deletion, never keys or component IDs

#### Scenario: A stale titleless candidate is deleted for recreation
- **WHEN** an NPC lacks current whole-row retirement authority
- **THEN** it survives regardless of old title or component IDs; losing a current host's last capability also preserves the host

#### Scenario: Component-less NPCs survive and anchored titled candidates are kept
- **WHEN** component-less or currently declared canonical hosts carry historical title attributes
- **THEN** they survive without any title-based ownership or lifecycle decision

### Requirement: Exam examiners carry their authored identity
Persistent qualified adventurer assembly SHALL establish authored name/title once through existing identity validators and collision-safe roster discipline. Exams SHALL reuse that identity and stable dbref without rank-derived spawn identities or card/title replacement.

#### Scenario: A spawned examiner carries the authored title
- **WHEN** a qualified host starts two exams
- **THEN** authored name/title/dbref remain the same and no opponent spawns

### Requirement: Host and examiner creation emit boundary info events
Service-host and persistent adventurer creation SHALL each emit one facade info event only on actual creation, never idempotent reuse, with char/service and profile/branch identifiers. Examination starts SHALL emit lifecycle boundary events with exam/host/target identifiers, without entity-creation events or player-facing prose.

#### Scenario: Host creation logs once
- **WHEN** a persistent adventurer is created then reused by sync and exams
- **THEN** one entity-creation event emits and subsequent exam-start events identify the same dbref

#### Scenario: Opponent spawn logs
- **WHEN** persistent adventurer assembly creates the qualified person
- **THEN** its creation event identifies char/profile/branch once, while examination reuse emits no opponent-spawn creation event

### Requirement: Every NPC identity surface uses the plain authored name
NPC text, exploration, dialogue, party, inspection, skill targeting and management identity surfaces SHALL render the plain authored name without reading or composing an independent title. Historical title attributes SHALL remain inert; player title presentation SHALL remain unchanged.

#### Scenario: All identity surfaces ignore historical titles
- **WHEN** a real NPC carries title sentinel data or a raising title accessor
- **THEN** room/look/dialogue/party/editor/GM surfaces retain plain names without accessing it

#### Scenario: No identity replacement
- **WHEN** an NPC title is removed from a display
- **THEN** the old title is not merged into name, description or a replacement role field

### Requirement: The existing scene-builder and generated-quest contracts are unchanged where not amended
Except for the authored-identity behaviour stated in this delta, the scene-builder spawn contracts
(anti-hallucination characterization ownership, the post-commit portrait-eligibility seam, and the
`db.display_name` write) and the generated-quest durable-store contract SHALL remain as previously
specified; this change adds the authored identity on top and SHALL NOT otherwise alter their
observable behaviour.

#### Scenario: The pre-existing scene contracts still hold
- **WHEN** the scene-builder and durable-store suites run after this change
- **THEN** every pre-existing requirement scenario of those capabilities still passes
