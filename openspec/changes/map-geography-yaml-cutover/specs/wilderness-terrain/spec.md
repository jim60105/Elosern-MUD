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

