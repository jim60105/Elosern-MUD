# npc-profile-registry Specification

## Purpose
Hold the immutable, keyed authored NPC profiles (a compact card plus bounded prewritten voice lines) that creation paths reference by stable identity, and keep a machine-checked inventory of every shipped NPC source so no NPC or dialogue table can be left without an owner.

## Requirements

### Requirement: Authored NPC profiles are immutable keyed lore records
An authored NPC profile SHALL be a frozen record holding a stable lowercase identifier key, one compact NPC card, and voice lines consisting of an optional greeting and an optional misunderstanding reply, each voice line plain text of at most 300 code points after the card normalization rule. Profiles SHALL be referenced by key, never by display name. Every profile card SHALL satisfy the compact card contract at import time.

#### Scenario: A malformed profile fails import by name
- **WHEN** a slice declares a profile whose card lacks `speech_style`
- **THEN** importing the profile registry raises naming that profile key, its slice, and the missing leaf

#### Scenario: A valid profile exposes its card as a persona record
- **WHEN** a valid profile's card is converted to its storage record
- **THEN** the record has exactly the seven card fields and validates unchanged through the card contract

#### Scenario: Malformed profile content fails import by name
- **WHEN** a profile has a malformed card, an over-bound or non-text voice line, or an invalid key
- **THEN** importing the profile registry fails naming the profile key and its slice

### Requirement: One module assembles the profile registry from owned slices
The profile registry SHALL be assembled by exactly one module from per-owner slice modules in a fixed, commented order, and SHALL be read-only at runtime. A key declared by two slices SHALL fail import naming both slices. The registry SHALL import nothing from the deterministic rules layer and SHALL NOT be mirrored into persistent lore records, because profiles carry hidden identities that are read only through code.

#### Scenario: A duplicate key fails assembly
- **WHEN** two slices each declare a profile with the same key
- **THEN** importing the registry raises naming the key and both slices

#### Scenario: The registry is read-only
- **WHEN** a consumer attempts to add or replace a registry entry at runtime
- **THEN** the attempt raises and the registry is unchanged

#### Scenario: Profiles are not mirrored into lore records
- **WHEN** the startup lore synchronization runs
- **THEN** it creates no persistent record for any NPC profile

### Requirement: The shipped NPC source inventory enumerates every source with an owner
A machine-readable inventory SHALL list every shipped NPC source with the slice that owns its characterization. A data-contract check SHALL derive the actual sources from the live registries and example files and SHALL fail when any actual source is absent from the inventory or any inventory row names a source that no longer exists.

#### Scenario: The inventory matches the registries
- **WHEN** the inventory check runs against the shipped registries
- **THEN** the derived sources and the inventory rows are equal sets and every row names an owner

#### Scenario: An unlisted source fails the check
- **WHEN** a new hosted place is added to a settlement slice without an inventory row
- **THEN** the inventory check fails naming that place's service identity

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated exactly once, including canonical
  age/provenance and connected residence/schedule authoring, stale temporary-rank sources fail, and
  unrelated place, companion, import and quest checks stay unchanged

#### Scenario: The inventory enumerates every source kind
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each place host, each dialogue table, each branch-qualified persistent adventurer, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added
- **THEN** source equality and orphan/age checks accept the person once, with no rank-owned examiner source remaining

#### Scenario: Persistent adventurer sources are inventoried kinds
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each persistent_adventurer source alongside every place host, dialogue table, starting-companion declaration, offline quest template occupant, and shipped NPC import example

### Requirement: The shipped NPC roster is validated as complete before the game starts
Before any world synchronization at server start, the system SHALL validate the complete shipped NPC roster and SHALL abort startup when any check fails, reporting every violation with its source kind, source key, and profile or preset key. The same validation SHALL be runnable in tests without a server.

#### Scenario: The shipped roster passes
- **WHEN** the roster validation runs against the shipped registries and examples
- **THEN** it reports no violation and startup proceeds

#### Scenario: A missing profile aborts startup by name
- **WHEN** a synthetic registry set contains a hosted place whose profile key resolves to nothing
- **THEN** validation fails naming the place's source key and the missing profile, and no world synchronization runs

#### Scenario: Missing voice coverage is reported
- **WHEN** a synthetic scripted host's profile authors no misunderstanding reply, or a synthetic companion partner preset authors no `speech_style` or no `greeting`
- **THEN** validation fails naming each profile or preset and the missing voice field

#### Scenario: An orphan profile is reported
- **WHEN** a synthetic profile is registered that no hosted place or persistent examiner identity references
- **THEN** validation fails naming the orphan profile

#### Scenario: All violations are reported together
- **WHEN** a synthetic registry set has an inventory mismatch and an invalid template card
- **THEN** one failure lists both violations

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated exactly once, including canonical
  age/provenance and connected residence/schedule authoring, stale temporary-rank sources fail, and
  unrelated place, companion, import and quest checks stay unchanged

#### Scenario: Inventory and derived sources must agree both ways
- **WHEN** the roster validation derives sources from the live registries and example files
- **THEN** the check requires the inventory to equal the derived sources in both directions

#### Scenario: Hosts and examiners must resolve to valid cards
- **WHEN** the roster validation walks every place host and every qualified persistent examiner
- **THEN** each must resolve to a profile with a valid compact card

#### Scenario: Companion declarations derive valid cards
- **WHEN** the roster validation checks a starting-companion declaration
- **THEN** it derives a valid compact card from its partner preset's persona through the shared companion derivation with a maximum-length synthetic owner name

#### Scenario: Template occupants and import examples carry valid cards
- **WHEN** the roster validation checks every offline quest template occupant and every shipped NPC import example
- **THEN** each must carry a valid compact card

#### Scenario: Each dialogue table has exactly one profiled host
- **WHEN** the roster validation pairs dialogue tables with hosted places
- **THEN** every dialogue table is answered by exactly one profiled hosted place

#### Scenario: Scripted hosts and companion presets author their voice
- **WHEN** the roster validation checks voice authorship
- **THEN** every profile behind a scripted-dialogue host authors a misunderstanding reply and no greeting (its table greeting is the single source), and every companion partner preset authors a non-empty `speech_style` and `greeting`

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added
- **THEN** source equality and orphan/age checks accept the person once, with no rank-owned examiner source remaining

#### Scenario: Persistent adventurers must resolve to valid cards
- **WHEN** the roster validation walks every persistent-adventurer source
- **THEN** each must resolve to a profile with a valid compact card

### Requirement: Every shipped host and examiner profile authors a bounded age pair
Each shipped persistent-adventurer, place-host and guild-examiner profile SHALL author explicit canonical `age` and `apparent_age` integers, rejecting booleans and values outside inclusive 0..10000. Invalid authored ages SHALL reject source loading/preflight before creation writes and name the owning profile.

#### Scenario: The complete roster has age authorship
- **WHEN** the shipped place-host and examiner registries are checked against the authored age inventory
- **THEN** every actual source is covered exactly once with a bounded explicit age pair and no stale source entry is accepted

#### Scenario: Invalid age fails before spawn
- **WHEN** an authored profile declares `age` as true, -1, or 10001
- **THEN** source validation fails naming the profile and no host or examiner is created

#### Scenario: Long-lived identity differs from appearance
- **WHEN** an authored host profile declares age 980 and apparent age 42 with matching long-lived characterization
- **THEN** both values remain distinct canonical identity facts and the card remains independently editable

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated exactly once, including canonical
  age/provenance and connected residence/schedule authoring, stale temporary-rank sources fail, and
  unrelated place, companion, import and quest checks stay unchanged

#### Scenario: The age inventory assigns every source
- **WHEN** the data contract checks the complete shipped host/examiner inventory
- **THEN** each source is associated with its profile and age pair, and missing or stale source assignments fail the data contract

#### Scenario: Initial ages fit the life story
- **WHEN** initial mechanical ages are authored
- **THEN** they are consistent with each profile's appearance and life-story constraints, allowing deliberate narrative ambiguity and different actual/apparent ages for long-lived characters

#### Scenario: Edited instance prose is not an age source
- **WHEN** an instance's prose is edited
- **THEN** it does not become an age source

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added
- **THEN** source equality and orphan/age checks accept the person once, with no rank-owned examiner source remaining

### Requirement: Every registry-derived host has complete individual characterization
Every host derived from live place records SHALL reference its own valid compact profile by service identity with explicit bounded ages. Every scripted host SHALL author a misunderstanding reply and use its dialogue table as the sole greeting source. Each table SHALL belong to exactly one profiled host. Qualified persistent people SHALL resolve their own cards and offline voices. Inventory equality SHALL be checked in both directions independently of owner-slice labels.

#### Scenario: Complete live-source coverage
- **WHEN** a new valid hosted place and table are added with characterization and an inventory owner
- **THEN** coverage includes them without adding a district-specific test; no host or table is omitted

#### Scenario: Missing or stale relationship
- **WHEN** a host lacks profile, card, age, voice, table or owner, or an inventory row outlives its source
- **THEN** validation reports source kind/key and missing or stale relationship before world sync

#### Scenario: Qualified people
- **WHEN** a qualification names a persistent person with a missing profile
- **THEN** load fails naming branch, target and person/profile; valid distinct persons are owned once

### Requirement: Authored host dialogue preserves service semantics
Every shipped host dialogue SHALL retain its declared service interactions, bounded in-character greeting/responses and individual voice without fixed prices, stock counts or live availability prose. Prose SHALL remain editable without literal-text tests. Characterization changes SHALL record editorial review of card/voice agreement and rewrite completeness for every affected live source; tests SHALL establish coverage and behavior rather than editorial quality.

#### Scenario: Registry-derived rewrite coverage
- **WHEN** the authored dialogue corpus is reviewed
- **THEN** every live host/table is covered, including newly added sources; keyword actions and service behavior remain verified

#### Scenario: Editorial evidence has complete source coverage
- **WHEN** the characterization review ledger is checked against actual live sources
- **THEN** each source has one dated review/disposition entry, missing or orphan entries fail, and the check makes no claim to prove prose quality or judgment freshness

#### Scenario: Rewording
- **WHEN** a valid greeting, response or misunderstanding line is reworded
- **THEN** behavior and coverage tests pass without updating expected prose; no command/mechanic/UI term or shared placeholder is accepted

#### Scenario: Shared service labels
- **WHEN** two hosts legitimately expose the same keyword labels
- **THEN** valid individual cards and voice are accepted without requiring globally unique keyword sets
