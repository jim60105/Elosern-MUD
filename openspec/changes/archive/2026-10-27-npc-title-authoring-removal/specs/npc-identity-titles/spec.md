# Spec Delta

## ADDED Requirements

### Requirement: Current NPC authoring has no independent title field
All current NPC imports, place hosts, adventurer definitions and generated/materialized characterization SHALL omit independent title fields and writes. Closed input schemas SHALL reject removed fields; stored title/profession data SHALL remain unread without a migration.

#### Scenario: Title-free authoring works
- **WHEN** valid imports, hosts and generated scenes omit titles
- **THEN** each validates/materializes while player titles and scene roles/tiers remain unchanged

#### Scenario: No dormant writer
- **WHEN** a real creation/import/sync/materialization path succeeds
- **THEN** no npc_title or adventurer profession attribute is persisted

## MODIFIED Requirements

### Requirement: The existing appearance and exploration contracts are unchanged

Removing the NPC title behavior SHALL NOT change the requirement text of `localized-appearance` or `webclient-exploration-menu`: the zh-tw appearance frames, the affinity stage line, the displayed-stats block, the exploration panel's schema version, field set, and bounds all keep their current contracts. The plain authored name fills the already-specified display-name slot.

#### Scenario: The zh-tw appearance frame is preserved

- **WHEN** a player looks at a room containing an NPC
- **THEN** the appearance still renders the 「出口」 and 「人物」 zh-tw frames, the affinity stage line, and the displayed-stats block exactly as specified today, with no English frame string

#### Scenario: The exploration panel contract is preserved

- **WHEN** the exploration panel is built in a room containing an NPC
- **THEN** the payload still validates against the unchanged schema version 1 field set and bounds

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

### Requirement: Exam examiners carry their authored identity
Qualified persistent adventurers SHALL retain their authored names and stable person provenance without a title field. Qualification and reception authority SHALL remain separate.

#### Scenario: Stable persistent examiner
- **WHEN** a qualified adventurer hosts repeated exams
- **THEN** its name/dbref/person provenance and normal state remain unchanged with no title or profession write

#### Scenario: A spawned examiner carries the authored title
- **WHEN** the actual qualified persistent adventurer hosts an examination
- **THEN** authored name and stable person provenance remain with no independent title/profession write

## REMOVED Requirements

### Requirement: NPC titles are validated single-line plain text
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.

### Requirement: The NPC title is a creation-time attribute with no runtime write surface
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.

### Requirement: An imported character record carries a required authored title
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.

### Requirement: The import loader persists the validated title on NPC entities only
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.

### Requirement: The reference card and the GM import documentation carry the title field
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.

### Requirement: The existing import contracts are unchanged by the added title field
**Reason**: NPC title authoring and persistence are deleted after all readers are removed.
**Migration**: Remove title/host_title from current authored records and examples; legacy input rejects, stored attributes stay inert, no save migration.
