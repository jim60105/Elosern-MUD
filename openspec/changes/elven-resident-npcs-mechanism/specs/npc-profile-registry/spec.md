## MODIFIED Requirements

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
- **THEN** the inventory lists each place host, each dialogue table, each branch-qualified persistent adventurer, each authored resident, each starting-companion declaration, each offline quest template occupant, and each shipped NPC import example

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added
- **THEN** source equality and orphan/age checks accept the person once, with no rank-owned examiner source remaining

#### Scenario: Persistent adventurer sources are inventoried kinds
- **WHEN** the shipped NPC sources are inventoried
- **THEN** the inventory lists each persistent_adventurer source alongside every place host, dialogue table, resident, starting-companion declaration, offline quest template occupant, and shipped NPC import example

#### Scenario: An unlisted resident fails the check
- **WHEN** a resident is added to a village resident slice without an inventory row
- **THEN** the inventory check fails naming that resident's key

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
- **WHEN** a synthetic profile is registered that no hosted place, persistent adventurer or resident references
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
- **WHEN** the roster validation pairs dialogue tables with their authored owners
- **THEN** every dialogue table is answered by exactly one owner: a profiled hosted place, or a profiled resident whose `dialogue_key` names it, and never both

#### Scenario: Scripted hosts and companion presets author their voice
- **WHEN** the roster validation checks voice authorship
- **THEN** every profile behind a scripted-dialogue host authors a misunderstanding reply and no greeting (its table greeting is the single source), every resident with a dialogue table follows the same rule, every resident without one authors an offline greeting, and every companion partner preset authors a non-empty `speech_style` and `greeting`

#### Scenario: Additive normal-person source passes independently
- **WHEN** a persistent-adventurer source with a valid distinct profile/age pair is added
- **THEN** source equality and orphan/age checks accept the person once, with no rank-owned examiner source remaining

#### Scenario: Persistent adventurers must resolve to valid cards
- **WHEN** the roster validation walks every persistent-adventurer source
- **THEN** each must resolve to a profile with a valid compact card

#### Scenario: Resident sources are validated before any write
- **WHEN** a resident references an unregistered profile, a missing dialogue table, a profile shared with another source, or an unknown schedule template
- **THEN** validation fails naming the resident key and the offending reference, and no world synchronization runs
