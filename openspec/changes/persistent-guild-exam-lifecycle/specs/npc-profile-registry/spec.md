## MODIFIED Requirements

### Requirement: The shipped NPC source inventory enumerates every source with an owner
A machine-readable inventory SHALL list every shipped NPC source — each place host, each dialogue table, each branch-qualified persistent adventurer, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example — with the slice that owns its characterization. A data-contract check SHALL derive the actual sources from the live registries and example files and SHALL fail when any actual source is absent from the inventory or any inventory row names a source that no longer exists.

#### Scenario: The inventory matches the registries
- **WHEN** the inventory check runs against the shipped registries
- **THEN** the derived sources and the inventory rows are equal sets and every row names an owner

#### Scenario: An unlisted source fails the check
- **WHEN** a new hosted place is added to a settlement slice without an inventory row
- **THEN** the inventory check fails naming that place's service identity

Rank-owned temporary examiner sources SHALL be removed from inventory and roster checks in this cutover. Qualified persistent-person sources SHALL be covered exactly once, including canonical age/provenance and connected residence/schedule authoring. Unrelated place/companion/import/quest checks SHALL remain unchanged.

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated once and stale temporary-rank sources fail

#### Scenario: The inventory enumerates every source kind
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each place host, each dialogue table, each guild examiner rank, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added while existing rank sources still exist
- **THEN** source equality and orphan/age checks accept the person without changing the existing rank profile no-voice-lines contract

#### Scenario: Persistent adventurer sources are inventoried kinds
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each persistent_adventurer source alongside every place host, dialogue table, guild examiner rank, starting-companion declaration, offline quest template occupant, and shipped NPC import example

### Requirement: Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue
Each guild host owned by the `altoria_guild` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Every guild qualification SHALL name a persistent person whose profile contains a complete bounded card and in-character dialogue coverage; missing person/profile keys SHALL fail load naming branch and target. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card. Every greeting, response and voice line SHALL be spoken in character and SHALL NOT name a command, a game mechanic, or an interface element. Rewritten dialogue SHALL keep every service semantic its settlement and dialogue specifications require and SHALL NOT state fixed prices, stock counts, or availability that live service data owns. Tests SHALL NOT pin the authored prose: rewording a line SHALL NOT break any test; prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Every rank names a resolvable examiner profile
- **WHEN** the guild qualification registry is validated, including a synthetic qualification naming an unregistered examiner profile key
- **THEN** every shipped qualification's person profile key resolves to a profile with complete card and dialogue coverage, and the synthetic qualification fails load naming the qualification and the field

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, guild, and scripted-dialogue behavior tests run against the rewritten table
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose

Rank-owned temporary examiner sources SHALL be removed from inventory and roster checks in this cutover. Qualified persistent-person sources SHALL be covered exactly once, including canonical age/provenance and connected residence/schedule authoring. Unrelated place/companion/import/quest checks SHALL remain unchanged.

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated once and stale temporary-rank sources fail

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

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added while existing rank sources still exist
- **THEN** source equality and orphan/age checks accept the person without changing the existing rank profile no-voice-lines contract

#### Scenario: Tables keep identifiers and freshly authored lines
- **WHEN** the owned dialogue tables are rewritten
- **THEN** each table keeps its keyword identifiers and its greeting, and every greeting and keyword response is newly authored against the host's card

### Requirement: The shipped NPC roster is validated as complete before the game starts
Before any world synchronization at server start, the system SHALL validate the complete shipped NPC roster and SHALL abort startup when any check fails, reporting every violation with its source kind, source key, and profile or preset key. The checks SHALL be: the inventory equals the sources derived from the live registries and example files in both directions; every place host and guild examiner resolves to a profile with a valid compact card; every starting-companion declaration derives a valid compact card from its partner preset's persona through the shared companion derivation with a maximum-length synthetic owner name; every offline quest template occupant and every shipped NPC import example carries a valid compact card; every dialogue table is answered by exactly one profiled hosted place; every profile behind a scripted-dialogue host authors a misunderstanding reply and no greeting (its table greeting is the single source), and every companion partner preset authors a non-empty `speech_style` and `greeting`; and no profile exists that no hosted place or persistent examiner identity references. The same validation SHALL be runnable in tests without a server.

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

Rank-owned temporary examiner sources SHALL be removed from inventory and roster checks in this cutover. Qualified persistent-person sources SHALL be covered exactly once, including canonical age/provenance and connected residence/schedule authoring. Unrelated place/companion/import/quest checks SHALL remain unchanged.

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated once and stale temporary-rank sources fail

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

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added while existing rank sources still exist
- **THEN** source equality and orphan/age checks accept the person without changing the existing rank profile no-voice-lines contract

#### Scenario: Persistent adventurers must resolve to valid cards
- **WHEN** the roster validation walks every persistent-adventurer source
- **THEN** each must resolve to a profile with a valid compact card

### Requirement: Every shipped host and examiner profile authors a bounded age pair
Each shipped place-host and guild-examiner profile SHALL author explicit canonical `age` and `apparent_age` integers, rejecting booleans and values outside inclusive 0..10000. Invalid authored ages SHALL reject source loading/preflight before creation writes and name the owning profile. The complete shipped host/examiner inventory SHALL associate each source with its profile and age pair; missing or stale source assignments SHALL fail the data contract. Initial mechanical ages SHALL be consistent with each profile's appearance and life-story constraints, allowing deliberate narrative ambiguity and different actual/apparent ages for long-lived characters. Edited instance prose SHALL NOT become an age source.

#### Scenario: The complete roster has age authorship
- **WHEN** the shipped place-host and examiner registries are checked against the authored age inventory
- **THEN** every actual source is covered exactly once with a bounded explicit age pair and no stale source entry is accepted

#### Scenario: Invalid age fails before spawn
- **WHEN** an authored profile declares `age` as true, -1, or 10001
- **THEN** source validation fails naming the profile and no host or examiner is created

#### Scenario: Long-lived identity differs from appearance
- **WHEN** an authored host profile declares age 980 and apparent age 42 with matching long-lived characterization
- **THEN** both values remain distinct canonical identity facts and the card remains independently editable

Rank-owned temporary examiner sources SHALL be removed from inventory and roster checks in this cutover. Qualified persistent-person sources SHALL be covered exactly once, including canonical age/provenance and connected residence/schedule authoring. Unrelated place/companion/import/quest checks SHALL remain unchanged.

#### Scenario: Persistent sources replace removed rank factories
- **WHEN** source validation runs after cutover
- **THEN** each qualified person is owned and validated once and stale temporary-rank sources fail

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
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added while existing rank sources still exist
- **THEN** source equality and orphan/age checks accept the person without changing the existing rank profile no-voice-lines contract

