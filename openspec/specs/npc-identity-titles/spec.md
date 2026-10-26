# npc-identity-titles Specification

## Purpose

Define the plain authored-name contract for NPC identity: the shared name validator every authored write path uses, the absence of any independent NPC title field in authoring, imports, creation and generated characterization, and the plain name every presentation, targeting and dialogue-prompt surface renders. Historical stored title-like attributes are inert and unread. Zero coupling with the player title system.

## Requirements

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

Removing the NPC title behavior SHALL NOT change the requirement text of `localized-appearance` or `webclient-exploration-menu`: the zh-tw appearance frames, the affinity stage line, the displayed-stats block, the exploration panel's schema version, field set, and bounds all keep their current contracts. The plain authored name fills the already-specified display-name slot.

#### Scenario: The zh-tw appearance frame is preserved

- **WHEN** a player looks at a room containing an NPC
- **THEN** the appearance still renders the 「出口」 and 「人物」 zh-tw frames, the affinity stage line, and the displayed-stats block exactly as specified today, with no English frame string

#### Scenario: The exploration panel contract is preserved

- **WHEN** the exploration panel is built in a room containing an NPC
- **THEN** the payload still validates against the unchanged schema version 1 field set and bounds


### Requirement: The import face rejects a name already used by an existing NPC

The author-supplied name at the import face is the record's `key` — the value the loader passes to `create_object` and the plain name every display surface renders. `world/imports/loader.py` SHALL, before constructing anything and inside the same transaction, reject a batch whose record `key` equals the key of an already-persisted `NPC` (including subclasses such as `LLMNPC`), failing the whole batch with zero entities persisted and a `key` diagnostic on the offending record.

#### Scenario: A record colliding with an existing NPC fails the whole batch

- **WHEN** an NPC named 測試人物 already exists and a two-record batch contains one record keyed 測試人物 alongside one valid new record
- **THEN** the load raises with a report whose 測試人物 record carries a `key` rejection, and neither record produces an entity

#### Scenario: An existing NPC is never reused, renamed, or overwritten

- **WHEN** the colliding batch above is rejected
- **THEN** the pre-existing NPC keeps its key, its stored attributes, and every other field unchanged, and no entity was created for the colliding record

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

### Requirement: Blueprint scene occupants spawn under the authored name with the authored title
Scene occupants SHALL materialize under their validated authored name with persona, optional ages and portrait policy, without an NPC title. Existing role/tier and uniqueness constraints SHALL remain.

#### Scenario: Authored identity materializes
- **WHEN** a valid title-free characterization is compiled and spawned
- **THEN** name/persona/age/portrait survive and no title attribute is written

#### Scenario: Legacy field rejects
- **WHEN** a current closed-schema proposal contains title
- **THEN** it is rejected before materialization without conversion

#### Scenario: A materialized occupant answers to its authored name
- **WHEN** a valid title-free characterized occupant materializes
- **THEN** key and display_name use the validated authored name without a title write or composer

#### Scenario: A missing title rolls back the materialization
- **WHEN** a valid current characterization omits title
- **THEN** title absence is valid; supplied removed title fields reject before writes and missing remaining required identity still fails closed

#### Scenario: Surrounding whitespace never reaches the entity key
- **WHEN** the existing authored-name validator strips accepted surrounding whitespace
- **THEN** key and db.display_name use that stripped name

#### Scenario: The portrait subject name keeps its source
- **WHEN** an occupant materializes under its authored name
- **THEN** db.display_name retains that value for existing art-subject readers

#### Scenario: A missing authored identity fails closed like age-bounds revalidation
- **WHEN** a current characterization lacks required name/persona or violates age bounds
- **THEN** materialization rejects before partial construction


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
Host and adventurer sources SHALL author validated names and canonical profile identities without title fields. Existing duplicate-name, profile, race/sex/age and qualification validation SHALL remain.

#### Scenario: Validated title-free identities
- **WHEN** current host and adventurer registries load
- **THEN** all identity validation passes without a title validator

#### Scenario: Identity failure remains atomic
- **WHEN** a duplicate/invalid name or missing profile appears
- **THEN** the complete candidate rejects before host writes

#### Scenario: A row with an invalid authored title fails module load
- **WHEN** current authored input includes a removed title field or invalid remaining name/profile
- **THEN** the appropriate closed-schema/identity check rejects without reinstating a title validator

#### Scenario: A duplicated authored name across registries fails load
- **WHEN** a shop/guild host and persistent adventurer share a forbidden authored name
- **THEN** existing cross-registry uniqueness validation rejects it by name

#### Scenario: The shipped registries load clean
- **WHEN** current shop/guild/adventurer registries load
- **THEN** their title-free names/profiles and cross-registry uniqueness validate

#### Scenario: Rank metadata has no opponent factory identity
- **WHEN** ranks and qualifications load
- **THEN** rank progression/reward/player-title metadata remain separate from persistent adventurer identities; no NPC name/title/profile factory is restored on rank rows

#### Scenario: The lore modules check cross-registry name uniqueness at load
- **WHEN** identity-owning lore modules load
- **THEN** duplicate authored names across shop/guild/adventurer sources still reject

#### Scenario: The row validators are pure and explicitly callable
- **WHEN** explicit synthetic rows are passed to identity validators
- **THEN** they can reject invalid names/profiles without mutating shipped registries


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
Qualified persistent adventurers SHALL retain their authored names and stable person provenance without a title field. Qualification and reception authority SHALL remain separate.

#### Scenario: Stable persistent examiner
- **WHEN** a qualified adventurer hosts repeated exams
- **THEN** its name/dbref/person provenance and normal state remain unchanged with no title or profession write

#### Scenario: A spawned examiner carries the authored title
- **WHEN** the actual qualified persistent adventurer hosts an examination
- **THEN** authored name and stable person provenance remain with no independent title/profession write


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
