# Spec Delta

## REMOVED Requirements

### Requirement: Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

### Requirement: Altoria middle-terrace trade hosts carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

### Requirement: Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

### Requirement: Altoria upper-terrace hosts carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

### Requirement: Village Ciaran first-home hosts carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

### Requirement: Village Ciaran second-home hosts carry individual authored profiles and rewritten dialogue
**Reason**: Content identity belongs to authored data; general behavior is retained.
**Migration**: Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics. Retarget substantive tests in this change.

## ADDED Requirements

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

#### Scenario: Rewording
- **WHEN** a valid greeting, response or misunderstanding line is reworded
- **THEN** behavior and coverage tests pass without updating expected prose; no command/mechanic/UI term or shared placeholder is accepted

#### Scenario: Shared service labels
- **WHEN** two hosts legitimately expose the same keyword labels
- **THEN** valid individual cards and voice are accepted without requiring globally unique keyword sets
