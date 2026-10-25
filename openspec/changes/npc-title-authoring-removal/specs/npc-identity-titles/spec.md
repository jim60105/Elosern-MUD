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
