# npc-profile-registry Specification

## Purpose
Hold the immutable, keyed authored NPC profiles (a compact card plus bounded prewritten voice lines) that creation paths reference by stable identity, and keep a machine-checked inventory of every shipped NPC source so no NPC or dialogue table can be left without an owner.

## Requirements

### Requirement: Authored NPC profiles are immutable keyed lore records
An authored NPC profile SHALL be a frozen record holding a stable lowercase identifier key, one compact NPC card, and voice lines consisting of an optional greeting and an optional misunderstanding reply, each voice line plain text of at most 300 code points after the card normalization rule. Profiles SHALL be referenced by key, never by display name. Every profile card SHALL satisfy the compact card contract at import time; a malformed card, an over-bound or non-text voice line, or an invalid key SHALL fail import naming the profile key and its slice.

#### Scenario: A malformed profile fails import by name
- **WHEN** a slice declares a profile whose card lacks `speech_style`
- **THEN** importing the profile registry raises naming that profile key, its slice, and the missing leaf

#### Scenario: A valid profile exposes its card as a persona record
- **WHEN** a valid profile's card is converted to its storage record
- **THEN** the record has exactly the seven card fields and validates unchanged through the card contract

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
A machine-readable inventory SHALL list every shipped NPC source — each place host, each dialogue table, each guild examiner rank, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example — with the slice that owns its characterization. A data-contract check SHALL derive the actual sources from the live registries and example files and SHALL fail when any actual source is absent from the inventory or any inventory row names a source that no longer exists.

#### Scenario: The inventory matches the registries
- **WHEN** the inventory check runs against the shipped registries
- **THEN** the derived sources and the inventory rows are equal sets and every row names an owner

#### Scenario: An unlisted source fails the check
- **WHEN** a new hosted place is added to a settlement slice without an inventory row
- **THEN** the inventory check fails naming that place's service identity

### Requirement: Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue
Each lower-terrace host owned by the `altoria_lower` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card. Every greeting, response and voice line SHALL be spoken in character and SHALL NOT name a command, a game mechanic, or an interface element. Rewritten dialogue SHALL keep every service semantic its settlement and dialogue specifications require and SHALL NOT state fixed prices, stock counts, or availability that live service data owns. Tests SHALL NOT pin the authored prose: rewording a line SHALL NOT break any test; prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

### Requirement: Altoria middle-terrace trade hosts carry individual authored profiles and rewritten dialogue
Each middle-terrace trade host owned by the `altoria_trade` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card. Every greeting, response and voice line SHALL be spoken in character and SHALL NOT name a command, a game mechanic, or an interface element. Rewritten dialogue SHALL keep every service semantic its settlement and dialogue specifications require and SHALL NOT state fixed prices, stock counts, or availability that live service data owns. Tests SHALL NOT pin the authored prose: rewording a line SHALL NOT break any test; prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose
