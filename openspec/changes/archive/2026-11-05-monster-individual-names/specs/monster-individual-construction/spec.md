## ADDED Requirements

### Requirement: A species-backed individual is named by its species or its individual name
Construction SHALL accept an optional individual name, store it on the individual as a nullable field, and write the object key as that name, or else the species display name. A variant display name SHALL NOT name an individual. The key SHALL be a search label only, and no consumer SHALL read a name fact from it for a species-backed individual.

#### Scenario: Default individual
- **WHEN** a synthetic species and variant are constructed with no individual name
- **THEN** the object key equals the species display name and the individual name is null

#### Scenario: Named individual
- **WHEN** construction receives an individual name
- **THEN** the object key and the individual name both equal it, and the species and variant keys are unchanged

#### Scenario: Invalid individual name builds nothing
- **WHEN** construction receives an empty or non-string individual name
- **THEN** it raises the named construction error and no individual exists afterwards

### Requirement: Monster identity reads are lenient and registry-backed
One read SHALL give an entity's individual name, species display name and variant display name. It SHALL read the individual's name from its field and the other two from the registries, SHALL NOT raise, and SHALL return no identity for an entity that has no resolvable species and variant.

#### Scenario: Species-backed individual
- **WHEN** the read receives a named or unnamed species-backed individual
- **THEN** it returns the stored individual name or null with the registry's species and variant display names

#### Scenario: No resolvable identity
- **WHEN** the read receives a player, an NPC, a tier-only monster, or an individual whose variant no longer resolves
- **THEN** it returns no identity and raises nothing

### Requirement: Defeat evidence carries the individual name
Defeat evidence that records a target's species and variant keys SHALL also record its individual name when one exists. The field SHALL be absent otherwise and SHALL never participate in kill accounting.

#### Scenario: Named defeat
- **WHEN** a synthetic named individual is defeated
- **THEN** the defeat entry's data carries the individual name beside the species and variant keys

#### Scenario: Unnamed defeat
- **WHEN** an unnamed individual is defeated
- **THEN** the data carries no individual name field and kill accounting is unchanged
