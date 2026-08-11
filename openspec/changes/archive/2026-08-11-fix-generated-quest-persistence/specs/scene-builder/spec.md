## ADDED Requirements

### Requirement: Generated quest content is durably stored at registration time

The system SHALL persist the compiled definition, guild offer, and stage spawn requirements of every generated quest to durable storage as part of `register_generated_quest`.

#### Scenario: Generated quest registration persists content

- **WHEN** `register_generated_quest` publishes a compiled generated quest
- **THEN** the compiled definition, offer, and spawn requirements are appended to the durable generated-quest store

#### Scenario: Registration is idempotent

- **WHEN** the same generated quest key is registered twice
- **THEN** the durable store contains exactly one payload for that key
