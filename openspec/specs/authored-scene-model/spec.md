# authored-scene-model Specification

## Purpose
Provide immutable reusable scenes and complete typed topic declarations through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: Static and generated primitives share immutable scene validation
Both static YAML primitives and generated JSON primitives SHALL obey the same immutable scene/topic schema, attribution, bounds, variant priority and predecessor rules. Generated identities SHALL be collision-free package-role-phase-local encodings, independent of static profile syntax. Static owner validation SHALL not apply to generated roles.

#### Scenario: Same scene semantics across providers
- **WHEN** equivalent valid primitives arrive from static YAML and generated JSON
- **THEN** both produce equivalent immutable scenes and reject the same malformed attribution, priority, DAG and bound errors

#### Scenario: Generated namespace does not use static bounds
- **WHEN** two packages share local IDs or use maximum valid Unicode source identities
- **THEN** full IDs remain distinct and lossless without applying the static lowercase/96-character pattern

### Requirement: Declarative scenes preserve attribution
The system SHALL represent immutable ordered speech and narration with stable scene identity and explicit revision. Dialogue formal scenes SHALL begin with a complete acting-body utterance and SHALL allow consecutive lines by one speaker. Scenes SHALL contain no executable statements or in-scene choice branches.

#### Scenario: Actor host and narration remain distinct
- **WHEN** a valid scene contains actor speech, two host speeches and narration
- **THEN** serialization preserves that order and narration has no speaker

#### Scenario: Malformed declarations fail before delivery
- **WHEN** a formal scene starts with host speech, is empty or exceeds a declared bound
- **THEN** validation rejects it with the definition identity

### Requirement: Topic declarations retain stable reading identity
Authored topics SHALL have stable identities independent of labels and variants, explicit unique variant priorities, unconditional fallbacks and acyclic predecessor references. Pure reading chains SHALL exclude effects and protected qualified descendants.

#### Scenario: Priority resolves a complete scene
- **WHEN** two conditions match variants with priorities 10 and 20
- **THEN** priority 20 selects the entire scene and no line-level branch is produced

#### Scenario: Protected descendants never enter a public chain
- **WHEN** available-topic projection would place a server-qualified descendant in a `pure_chain` bundle
- **THEN** the projection omits it and the selection delivers only public, predecessor-ordered nodes
