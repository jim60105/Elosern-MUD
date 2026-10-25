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

### Requirement: Shop and guild registries author host and examiner identities validated at load
Host and adventurer sources SHALL author validated names and canonical profile identities without title fields. Existing duplicate-name, profile, race/sex/age and qualification validation SHALL remain.

#### Scenario: Validated title-free identities
- **WHEN** current host and adventurer registries load
- **THEN** all identity validation passes without a title validator

#### Scenario: Identity failure remains atomic
- **WHEN** a duplicate/invalid name or missing profile appears
- **THEN** the complete candidate rejects before host writes

### Requirement: Exam examiners carry their authored identity
Qualified persistent adventurers SHALL retain their authored names and stable person provenance without a title field. Qualification and reception authority SHALL remain separate.

#### Scenario: Stable persistent examiner
- **WHEN** a qualified adventurer hosts repeated exams
- **THEN** its name/dbref/person provenance and normal state remain unchanged with no title or profession write

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
