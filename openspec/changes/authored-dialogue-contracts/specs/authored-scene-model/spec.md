# Spec Delta

## Purpose

Provide immutable reusable scenes and complete typed topic declarations through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## ADDED Requirements

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

#### Scenario: Protected chain composition rejects
- **WHEN** a public chain bundle contains a server-qualified descendant
- **THEN** declaration validation rejects the bundle rather than disclosing its body

