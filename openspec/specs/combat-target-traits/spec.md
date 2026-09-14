# combat-target-traits Specification

## Purpose
Define explicit, validated target classifications for reusable conditional spell effects without inferring combat identity from narrative names.

## Requirements

### Requirement: Combat target facts are explicit and persist through construction
Conditional spell effects SHALL read elemental affiliation from the existing affinity collection and independent combat classifications from a validated collection. The initial classification vocabulary SHALL include undead; absence SHALL be neutral. Import and authored spawn paths SHALL validate and persist these facts transactionally, rejecting malformed or unknown classifications without changing age bounds. Narrative labels and names SHALL NOT imply a fact.

#### Scenario: Imported and spawned facts survive refetch
- **WHEN** an imported character or authored spawned entity carries the undead classification
- **THEN** the same fact is available after refetch and changes the outcome of a configured conditional effect

#### Scenario: Malformed input is atomic
- **WHEN** a classification contains an unknown value, duplicate or non-string
- **THEN** import or spawn rejects before partial persistence

#### Scenario: Names are not combat facts
- **WHEN** a neutral target is renamed to suggest darkness or undeath
- **THEN** conditional damage remains unchanged
