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

#### Scenario: The inventory enumerates every source kind
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each place host, each dialogue table, each guild examiner rank, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example

### Requirement: Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue
Each lower-terrace host owned by the `altoria_lower` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

### Requirement: Altoria middle-terrace trade hosts carry individual authored profiles and rewritten dialogue
Each middle-terrace trade host owned by the `altoria_trade` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

### Requirement: Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue
Each guild host owned by the `altoria_guild` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Every rank names a resolvable examiner profile
- **WHEN** the guild rank registry is validated, including a synthetic rank naming an unregistered examiner profile key
- **THEN** every shipped rank's key resolves to a profile with no voice lines, and the synthetic rank fails load naming the rank and the field

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, guild, and scripted-dialogue behavior tests run against the rewritten table
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Every rank names a valid examiner profile key
- **WHEN** a guild rank is loaded
- **THEN** it names an examiner profile key that resolves to a profile with a complete card and no voice lines, and a missing or unresolved key fails load naming the rank

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

### Requirement: Altoria upper-terrace hosts carry individual authored profiles and rewritten dialogue
Each upper-terrace host owned by the `altoria_upper` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

### Requirement: Village Ciaran first-home hosts carry individual authored profiles and rewritten dialogue
Each village (first four homes) host owned by the `ciaran_homes_a` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Dialogue tables keep identifiers and are rewritten against the card
- **WHEN** the corresponding dialogue tables are rewritten
- **THEN** each keeps its keyword identifiers and its greeting, and every greeting and keyword response is newly authored against the host's card

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

### Requirement: Village Ciaran second-home hosts carry individual authored profiles and rewritten dialogue
Each village (second four homes) host owned by the `ciaran_homes_b` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, merchant, and scripted-dialogue behavior tests run against the rewritten tables
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

#### Scenario: Dialogue tables keep identifiers and are rewritten against the card
- **WHEN** the corresponding dialogue tables are rewritten
- **THEN** each keeps its keyword identifiers and its greeting, and every greeting and keyword response is newly authored against the host's card

#### Scenario: Dialogue lines stay in character
- **WHEN** any owned greeting, keyword response, or voice line renders
- **THEN** it is spoken in character and names no command, game mechanic, or interface element

#### Scenario: Dialogue states no live service data
- **WHEN** the dialogue tables are rewritten
- **THEN** every service semantic the settlement and dialogue specifications require is kept, and no fixed prices, stock counts, or availability that live service data owns are stated

#### Scenario: Rewrite quality is editorially reviewed
- **WHEN** the authored prose is assessed
- **THEN** prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review, not by tests

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
- **WHEN** a synthetic profile is registered that no hosted place or examiner rank references
- **THEN** validation fails naming the orphan profile

#### Scenario: All violations are reported together
- **WHEN** a synthetic registry set has an inventory mismatch and an invalid template card
- **THEN** one failure lists both violations

#### Scenario: Inventory and derived sources must agree both ways
- **WHEN** the roster validation derives sources from the live registries and example files
- **THEN** the check requires the inventory to equal the derived sources in both directions

#### Scenario: Hosts and examiners must resolve to valid cards
- **WHEN** the roster validation walks every place host and guild examiner
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

### Requirement: Every shipped host and examiner profile authors a bounded age pair
Each shipped place-host and guild-examiner profile SHALL author explicit canonical `age` and `apparent_age` integers, rejecting booleans and values outside inclusive 0..10000. Invalid authored ages SHALL reject source loading/preflight before creation writes and name the owning profile.

#### Scenario: The complete roster has age authorship
- **WHEN** the shipped place-host and examiner registries are checked against the authored age inventory
- **THEN** every actual source is covered exactly once with a bounded explicit age pair and no stale source entry is accepted

#### Scenario: Invalid age fails before spawn
- **WHEN** an authored profile declares `age` as true, -1, or 10001
- **THEN** source validation fails naming the profile and no host or examiner is created

#### Scenario: Long-lived identity differs from appearance
- **WHEN** an authored host profile declares age 980 and apparent age 42 with matching long-lived characterization
- **THEN** both values remain distinct canonical identity facts and the card remains independently editable

#### Scenario: The age inventory assigns every source
- **WHEN** the data contract checks the complete shipped host/examiner inventory
- **THEN** each source is associated with its profile and age pair, and missing or stale source assignments fail the data contract

#### Scenario: Initial ages fit the life story
- **WHEN** initial mechanical ages are authored
- **THEN** they are consistent with each profile's appearance and life-story constraints, allowing deliberate narrative ambiguity and different actual/apparent ages for long-lived characters

#### Scenario: Edited instance prose is not an age source
- **WHEN** an instance's prose is edited
- **THEN** it does not become an age source
