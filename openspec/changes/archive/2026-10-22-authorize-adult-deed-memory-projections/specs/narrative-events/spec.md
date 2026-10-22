# Spec Delta

## ADDED Requirements

### Requirement: Visibility does not grant adult content knowledge
A narrative event's visibility SHALL govern whether a consumer may read the occurrence. It SHALL NOT grant authority to every content field. Skill and adult producers SHALL preserve field-level knowledge boundaries for every consumer, including shared memory projection.

#### Scenario: A public occurrence still requires field authorization
- **WHEN** a mixed-visibility adult occurrence is eligible for a public narrative consumer
- **THEN** the occurrence may be consumed while another participant's private fields remain excluded unless separately knowable

#### Scenario: Production composition preserves the boundary
- **WHEN** an adult action records public visibility because a third entity is present
- **THEN** nomination and memory use the same recipient parameterization rather than the event visibility flag as field authorization
