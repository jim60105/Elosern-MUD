# Spec Delta

## ADDED Requirements

### Requirement: Character records exclude the removed NPC title property
Character input records SHALL exclude the removed NPC title field for both NPC and player targets. The JSON Schema document title metadata SHALL remain and unrelated closed-schema validation SHALL be unchanged.

#### Scenario: Absent title accepted
- **WHEN** an otherwise valid NPC or player input omits title
- **THEN** validation succeeds subject to its existing target-specific rules

#### Scenario: Historical title input rejects
- **WHEN** an input record includes title
- **THEN** additional-property validation rejects it without writing a title
