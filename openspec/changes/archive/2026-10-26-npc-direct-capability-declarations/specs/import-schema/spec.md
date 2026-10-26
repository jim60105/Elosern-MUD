# Spec Delta

## MODIFIED Requirements

### Requirement: The character record schema defines an optional profession field and an optional components field
The character schema SHALL accept optional independent components entries with exact type, kwargs and optional binding fields. It SHALL reject profession and unknown capability fields, runtime state and malformed bindings. Capability declarations SHALL remain NPC-only.

#### Scenario: An absent profession field leaves the record unchanged
- **WHEN** a record omits components and profession
- **THEN** it declares no capabilities and retains all unrelated validation

#### Scenario: Unknown profession keys name the record in the batch report
- **WHEN** a record carries any profession field
- **THEN** closed schema rejects the field, without registry lookup or conversion

#### Scenario: Component entries are shape-checked at the schema level, vocabulary-checked semantically
- **WHEN** a record provides components
- **THEN** exact type/kwargs/binding shape and per-type vocabulary/configuration are checked with named errors

#### Scenario: A components list without a profession is rejected
- **WHEN** an NPC record declares components without profession
- **THEN** the independent direct declaration is accepted, including an empty list; no blueprint is needed

#### Scenario: Unknown profession keys are rejected by the shared batch validator, not schema constants
- **WHEN** a player-target record declares components
- **THEN** the NPC-only semantic gate rejects the batch
