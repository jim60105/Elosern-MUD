# Spec Delta

## MODIFIED Requirements

### Requirement: WILDERNESS_REGION_REGISTRY covers the authored terrain regions
Game terrain views SHALL expose immutable schema-valid region values loaded from the continent source, with every classifier result resolving to a declared region.

#### Scenario: Complete region references
- **WHEN** a synthetic continent classifier returns a missing region or a region lacks required typed prose
- **THEN** the candidate is rejected before replacing published terrain values

#### Scenario: Round-trip derived view
- **WHEN** a supported region document is loaded twice and mirrored by lore synchronization
- **THEN** both reads are immutable and synchronization remains idempotent

#### Scenario: The registry covers the declared regions without duplicate names
- **WHEN** a synthetic continent supplies region declarations and classifier references
- **THEN** every classifier target resolves, identities/display names satisfy the existing uniqueness rule and duplicate declarations reject

#### Scenario: Every region carries at least two description variants
- **WHEN** a region has fewer than two typed nonblank description variants
- **THEN** authoring validation rejects that region rather than coercing or fabricating prose

